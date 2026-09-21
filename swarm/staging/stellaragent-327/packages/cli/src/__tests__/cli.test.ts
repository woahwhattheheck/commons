import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  formatLimitsStatus,
  formatQuotePreview,
  formatRoute,
  runCli,
  type CliIO,
  type LimitsClient,
} from '../index.js';
import type { PaymentQuote, RateLimitConfig, RateLimitStatus } from '@stellaragent/core';

const pkgRoot = process.cwd();
const entry = resolve(pkgRoot, 'src/index.ts');
const built = resolve(pkgRoot, 'dist/index.js');

function quote(): PaymentQuote {
  return {
    route: {
      id: 'XLM>USDC|amm:CPOOL',
      sourceAsset: 'XLM',
      destinationAsset: 'USDC',
      sourceAmount: '10000000',
      expectedDestinationAmount: '9950000',
      totalFeeBps: 25,
      expectedSlippageBps: 30,
      reliabilityBps: 9700,
      hopCount: 1,
      expiresAtLedger: 12360,
      hops: [{
        venue: 'amm',
        venueId: 'CPOOL',
        sourceAsset: 'XLM',
        destinationAsset: 'USDC',
        sourceAmount: '10000000',
        expectedOutput: '9950000',
        feeAmount: '25000',
        feeBps: 25,
        slippageBps: 30,
        reliabilityBps: 9700,
      }],
      score: '81',
      breakdown: {
        weightedCost: '12',
        weightedSlippage: '9',
        weightedReliability: '60',
        hopPenalty: '0',
      },
    },
    minimumDestinationAmount: '9850500',
    quotedAtLedger: 12340,
    validUntilLedger: 12360,
    failures: [],
  };
}

function rateLimitStatus(overrides: Partial<RateLimitStatus> = {}): RateLimitStatus {
  return {
    configured: true,
    active: true,
    maxPerTx: '2.0000000',
    maxPerHour: '10.0000000',
    maxPerDay: '100.0000000',
    maxTxsPerHour: 20,
    spentThisHour: '3.5000000',
    spentToday: '25.0000000',
    txsThisHour: 4,
    hourWindowStartLedger: 1_000,
    dayWindowStartLedger: 100,
    ...overrides,
  };
}

function limitsClient(status: RateLimitStatus = rateLimitStatus()): {
  client: LimitsClient;
  configured: RateLimitConfig[];
  targets: Array<string | undefined>;
} {
  const configured: RateLimitConfig[] = [];
  const targets: Array<string | undefined> = [];
  return {
    configured,
    targets,
    client: {
      address: 'GCLIAGENT',
      setRateLimits: async (config) => {
        configured.push(config);
        return { hash: 'abc123', success: true, ledger: 1_234 };
      },
      getRateLimitStatus: async (target) => {
        targets.push(target);
        return status;
      },
      getLedgerCloseEstimate: async () => ({
        currentLedger: 1_360,
        avgLedgerCloseSeconds: 5,
        observed: true,
      }),
    },
  };
}

function capture(): { io: CliIO; stdout: string[]; stderr: string[] } {
  const stdout: string[] = [];
  const stderr: string[] = [];
  return {
    stdout,
    stderr,
    io: {
      stdout: (message) => stdout.push(message),
      stderr: (message) => stderr.push(message),
    },
  };
}

function writeQuote(value: unknown = quote()): string {
  const path = join(mkdtempSync(join(tmpdir(), 'stellaragent-cli-')), 'quote.json');
  writeFileSync(path, JSON.stringify(value));
  return path;
}

describe('@stellaragent/cli packaging', () => {
  const pkg = JSON.parse(readFileSync(resolve(pkgRoot, 'package.json'), 'utf8'));

  it('declares an executable stellaragent bin entry', () => {
    expect(pkg.bin).toEqual({ stellaragent: 'dist/index.js' });
    expect(readFileSync(entry, 'utf8').startsWith('#!/usr/bin/env node')).toBe(true);
  });

  it.runIf(existsSync(built))('the built bin shows help', () => {
    const out = execFileSync(process.execPath, [built, '--help'], {
      encoding: 'utf8',
      env: { ...process.env, NODE_ENV: 'production' },
    });
    expect(out).toContain('route preview');
    expect(out).toContain('limits set');
    expect(out).toContain('limits show');
  });
});

describe('route preview', () => {
  it('shows route, cost, output floor, and expiry before confirmation', async () => {
    const output = capture();
    const exitCode = await runCli(['route', 'preview', '--quote', writeQuote()], output.io);
    const contents = output.stdout.join('\n');

    expect(exitCode).toBe(0);
    expect(contents).toContain('You pay:             1.0000000 XLM');
    expect(contents).toContain('Recipient receives:  0.9950000 USDC');
    expect(contents).toContain('Minimum received:    0.9850500 USDC');
    expect(contents).toContain('XLM → AMM[CPOOL] → USDC');
    expect(contents).toContain('Estimated fee:       25 bps');
    expect(contents).toContain('Expected slippage:   30 bps');
    expect(contents).toContain('Valid through:       12360');
    expect(contents).toContain('Preview only');
    expect(contents).not.toContain('Confirmed route');
  });

  it('prints the same preview before accepting explicit confirmation', async () => {
    const output = capture();
    const exitCode = await runCli(
      ['route', 'preview', '--quote', writeQuote(), '--confirm'],
      output.io,
    );

    expect(exitCode).toBe(0);
    expect(output.stdout[0]).toContain('Routed payment preview');
    expect(output.stdout.at(-1)).toContain('Confirmed route XLM>USDC|amm:CPOOL');
  });

  it('uses the deterministic selector to reject an inadmissible quote', async () => {
    const invalid = quote();
    invalid.route.reliabilityBps = 100;
    const output = capture();
    const exitCode = await runCli(
      ['route', 'preview', '--quote', writeQuote(invalid)],
      output.io,
    );

    expect(exitCode).toBe(1);
    expect(output.stderr.join('\n')).toContain('outside routing policy bounds');
  });

  it('reports command and option errors without terminating the process', async () => {
    const unknown = capture();
    const missing = capture();
    expect(await runCli(['unknown'], unknown.io)).toBe(2);
    expect(await runCli(['route', 'preview'], missing.io)).toBe(2);
    expect(unknown.stderr.join('\n')).toContain('Unknown command');
    expect(missing.stderr.join('\n')).toContain('Missing required option');
  });

  it('formats path-payment intermediates and provider warnings', () => {
    const value = quote();
    value.route.hops[0] = {
      ...value.route.hops[0]!,
      venue: 'path_payment',
      venueId: 'horizon',
      path: ['AQUA'],
    };
    value.failures = [{
      providerId: 'broken-amm',
      code: 'VENUE_UNAVAILABLE',
      message: 'timeout',
    }];

    expect(formatRoute(value.route)).toBe('XLM → PATH[horizon via AQUA] → USDC');
    expect(formatQuotePreview(value)).toContain('broken-amm/VENUE_UNAVAILABLE');
  });
});

describe('limits commands', () => {
  it('sets all on-chain limits through the SDK and prints the transaction receipt', async () => {
    const mock = limitsClient();
    const output = capture();
    const exitCode = await runCli([
      'limits',
      'set',
      '--max-per-tx',
      '2',
      '--max-per-hour',
      '10',
      '--max-per-day',
      '100',
      '--max-txs-per-hour',
      '20',
    ], output.io, { createLimitsClient: async () => mock.client });

    expect(exitCode).toBe(0);
    expect(mock.configured).toEqual([{
      maxPerTx: '2',
      maxPerHour: '10',
      maxPerDay: '100',
      maxTxsPerHour: 20,
    }]);
    expect(output.stdout.join('\n')).toContain('Transaction:           abc123');
    expect(output.stdout.join('\n')).toContain('Confirmed ledger:      1234');
  });

  it('shows remaining amount and transaction headroom with ledger-time resets', async () => {
    const mock = limitsClient();
    const output = capture();
    const exitCode = await runCli(
      ['limits', 'show', '--agent', 'GTARGET'],
      output.io,
      { createLimitsClient: async () => mock.client },
    );
    const contents = output.stdout.join('\n');

    expect(exitCode).toBe(0);
    expect(mock.targets).toEqual(['GTARGET']);
    expect(contents).toContain('6.5000000 remaining of 10.0000000');
    expect(contents).toContain('16 remaining of 20');
    expect(contents).toContain('75.0000000 remaining of 100.0000000');
    expect(contents).toContain('ledger 1720 in ~30m');
    expect(contents).toContain('(observed 5.00s/ledger)');
  });

  it('treats expired windows as reset headroom instead of stale spend', () => {
    const contents = formatLimitsStatus(
      'GEXPIRED',
      rateLimitStatus({
        spentThisHour: '9.0000000',
        txsThisHour: 19,
        hourWindowStartLedger: 100,
      }),
      { currentLedger: 1_000, avgLedgerCloseSeconds: 5, observed: true },
    );

    expect(contents).toContain('10.0000000 remaining of 10.0000000 (0 spent)');
    expect(contents).toContain('20 remaining of 20 (0 used)');
    expect(contents).toContain('window expired at ledger 820');
  });

  it('states plainly when the agent has no configured limits', async () => {
    const mock = limitsClient(rateLimitStatus({ configured: false }));
    const output = capture();
    const exitCode = await runCli(
      ['limits', 'show'],
      output.io,
      { createLimitsClient: async () => mock.client },
    );

    expect(exitCode).toBe(0);
    expect(output.stdout.join('\n')).toBe(
      'No rate limits configured for GCLIAGENT. ' +
      'Payments are unrestricted by the rate limiter.',
    );
  });

  it('rejects missing and sub-stroop limit options before an SDK mutation', async () => {
    const mock = limitsClient();
    const output = capture();
    const exitCode = await runCli([
      'limits',
      'set',
      '--max-per-tx',
      '0.00000001',
      '--max-per-hour',
      '10',
      '--max-per-day',
      '100',
      '--max-txs-per-hour',
      '20',
    ], output.io, { createLimitsClient: async () => mock.client });

    expect(exitCode).toBe(2);
    expect(mock.configured).toEqual([]);
    expect(output.stderr.join('\n')).toContain('at most 7 fractional digits');
  });
});
