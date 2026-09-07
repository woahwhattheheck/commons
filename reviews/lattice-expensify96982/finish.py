#!/usr/bin/env python3
"""Complete the measured lint gap on the pinned Expensify peer candidate.

Uses run.py's verified restore and command logging. Keeps the original two-line
key patch separate, then records a narrow source/test lint repair. No baseline,
configuration, assertion, package, or lockfile edits are permitted.
"""
from __future__ import annotations
import hashlib
import json
import re
import run as common

APP, OUT = common.APP, common.OUT
SOURCE, TEST = common.SOURCE, common.TEST


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError('Repair anchor not unique: ' + old[:160])
    return text.replace(old, new, 1)


def main() -> None:
    if common.sha(APP/SOURCE) != common.SOURCE_SHA or common.sha(APP/TEST) != common.TEST_SHA:
        raise RuntimeError('Restored input differs from verified peer candidate')
    originals = {path: (APP/path).read_text() for path in (SOURCE, TEST)}
    frozen = ('package.json', 'package-lock.json', 'config/eslint/eslint.seatbelt.tsv',
              'jest.config.js', 'config/eslint/eslint.config.mjs')
    frozen_hashes = {p: common.sha(APP/p) for p in frozen}
    for tool in ('node', 'npm', 'bun'):
        common.must([tool, '--version'], 'version-' + tool)
    common.must(['node', 'node_modules/typescript/bin/tsc', '--version'], 'version-typescript')

    # The first measured run already reproduced all four exact TS2322 errors,
    # and the two-const-only version passed all five projects. Do not silently
    # present that inherited execution as a new before-test in this run.
    (OUT/'prior-measured-run.json').write_text(json.dumps({
        'run': 34070157756, 'artifact': 10000278374,
        'zip_sha256': 'cac4b62276f34608cc7ed438848995994291a855717375135bb5b06b211fc3b0',
        'before': 'four TS2322 at 43/93/171/186; source/test hashes in manifest',
        'two_const_only': 'five projects + 36 focused tests + spelling pass; lint fails',
        'remaining': 'new source/test assertion and synchronous-effect-state diagnostics',
    }, indent=2)+'\n')

    fixed_test = originals[TEST]
    for old, new in (
        ('const TRANSACTION_KEY = `${ONYXKEYS.COLLECTION.TRANSACTION}${TRANSACTION_ID}`;',
         'const TRANSACTION_KEY = `${ONYXKEYS.COLLECTION.TRANSACTION}${TRANSACTION_ID}` as const;'),
        ('const nextKey = `${ONYXKEYS.COLLECTION.TRANSACTION}43`;',
         'const nextKey = `${ONYXKEYS.COLLECTION.TRANSACTION}43` as const;')):
        fixed_test = replace_once(fixed_test, old, new)
    (OUT/'test-key-only.ts').write_text(fixed_test)
    fixed_test = replace_once(fixed_test, '''        return Object.keys(searchData ?? {}).flatMap((key) => {
            if (!key.startsWith(ONYXKEYS.COLLECTION.TRANSACTION)) {
                return [];
            }
            // Keys are narrowed by the collection prefix before looking up the transaction.
            const transaction = searchData?.[key as `${typeof ONYXKEYS.COLLECTION.TRANSACTION}${string}`];
            return transaction ? [buildTransactionRow(Number(transaction.transactionID), transaction.transactionID, {...transaction, errors: undefined})] : [];
        });''', '''        return Object.keys(searchData ?? {})
            .filter((key): key is `${typeof ONYXKEYS.COLLECTION.TRANSACTION}${string}` => key.startsWith(ONYXKEYS.COLLECTION.TRANSACTION))
            .flatMap((key) => {
                const transaction = searchData?.[key];
                return transaction ? [buildTransactionRow(Number(transaction.transactionID), transaction.transactionID, {...transaction, errors: undefined})] : [];
            });''')

    fixed_source = originals[SOURCE]
    watch_lookup = 'transactions?.[optimisticWatchKey as `${typeof ONYXKEYS.COLLECTION.TRANSACTION}${string}`]'
    fixed_source = replace_once(fixed_source,
        '    const [isCreationLifecycleArmed, setIsCreationLifecycleArmed] = useState(() => hasPendingWriteOnMount);',
        '''    const [isCreationLifecycleArmed, setIsCreationLifecycleArmed] = useState(() => hasPendingWriteOnMount);
    const watchedTx = ''' + watch_lookup + ''';
    const isPendingCreation = watchedTx?.pendingAction === CONST.RED_BRICK_ROAD_PENDING_ACTION.ADD;

    // Remember the pending creation during this render, before child hooks see
    // its settled state. The state guard makes this a one-time adjustment per
    // lifecycle instead of an extra cascading render from the watch-key effect.
    if (!isCreationLifecycleArmed && !isOptimisticTrackingCleared && isPendingCreation) {
        setIsCreationLifecycleArmed(true);
    }''')
    fixed_source = replace_once(fixed_source, '        const watchedTx = ' + watch_lookup + ';\n', '')
    fixed_source = replace_once(fixed_source, '            setIsCreationLifecycleArmed(true);\n', '')
    fixed_source = replace_once(fixed_source,
        '    }, [isOptimisticTrackingCleared, optimisticWatchKey, transactions]);',
        '    }, [isOptimisticTrackingCleared, optimisticWatchKey, transactions, watchedTx]);')
    fixed_source = replace_once(fixed_source, '''    const isPendingCreation =
        ''' + watch_lookup + '''?.pendingAction === CONST.RED_BRICK_ROAD_PENDING_ACTION.ADD;
''', '')

    for path, value in ((SOURCE, fixed_source), (TEST, fixed_test)):
        (APP/path).write_text(value)
        (OUT/(('source' if path == SOURCE else 'test')+'-before.ts')).write_text(originals[path])
        (OUT/(('source' if path == SOURCE else 'test')+'-after.ts')).write_text(value)
    assertions_before = re.findall(r'^.*expect\(.*$', originals[TEST], re.M)
    assertions_after = re.findall(r'^.*expect\(.*$', fixed_test, re.M)
    common.result('preserve-all-existing-expect-lines', assertions_before == assertions_after,
                  count=len(assertions_before))
    suppressions_before = re.findall(r'^.*eslint-disable.*$', originals[SOURCE]+'\n'+originals[TEST], re.M)
    suppressions_after = re.findall(r'^.*eslint-disable.*$', fixed_source+'\n'+fixed_test, re.M)
    common.result('no-new-lint-suppression', suppressions_before == suppressions_after,
                  existing_suppression_count=len(suppressions_before))
    patch = common.must(['git','diff','--',SOURCE,TEST], 'final-repair-diff').stdout
    (OUT/'final-repair.patch').write_bytes(patch)
    common.must(['git','diff','--check'], 'diff-whitespace-check')
    manifest = json.loads((OUT/'manifest.json').read_text())
    manifest.update({'source_after_sha256': common.sha(APP/SOURCE),
                     'test_after_sha256': common.sha(APP/TEST),
                     'repair_sha256': hashlib.sha256(patch).hexdigest(),
                     'scope': 'two const keys; typed test prefix filter; deduplicated watched transaction and guarded render-time lifecycle latch'})
    (OUT/'final-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')

    for project in ('tsconfig.jest.json','tsconfig.json','tsconfig.bun.json','tsconfig.node.json','server/victory-chart-renderer/tsconfig.json'):
        label = 'final-types-'+project.replace('/','-').replace('.','-')
        cp = common.typecheck(project,label)
        common.result(label, cp.returncode == 0, exit=cp.returncode)
    selected = [TEST, 'tests/unit/Search/useSearchSnapshotTest.ts', 'tests/unit/deferredLayoutWriteTest.ts']
    for path in selected:
        if not (APP/path).is_file():
            raise RuntimeError('Missing focused test: '+path)
    (OUT/'selected-tests.json').write_text(json.dumps(selected,indent=2)+'\n')
    cp = common.command(['node','node_modules/jest/bin/jest.js','--runInBand','--runTestsByPath',*selected,
                         '--json','--outputFile',str(OUT/'jest-results.json')], 'final-focused-jest', timeout=900)
    jest = json.loads((OUT/'jest-results.json').read_text()) if (OUT/'jest-results.json').exists() else {}
    common.result('all-three-focused-project-jest-suites',
                  cp.returncode == 0 and jest.get('numTotalTests') == 47 and jest.get('numPassedTests') == 47,
                  exit=cp.returncode, total=jest.get('numTotalTests'), passed=jest.get('numPassedTests'), selected=selected)
    cp = common.command(['bun','scripts/lint.ts','--no-cache','--show-warnings',SOURCE,TEST], 'final-affected-lint', timeout=900)
    common.result('affected-project-lint-frozen-baseline',cp.returncode == 0,exit=cp.returncode)
    cp = common.command(['node','node_modules/cspell/bin.mjs','--no-progress',SOURCE,TEST], 'final-affected-spell')
    common.result('affected-spell',cp.returncode == 0,exit=cp.returncode)
    dirty = common.must(['git','diff','--name-only'],'final-paths').stdout.decode().splitlines()
    common.result('only-two-reviewed-files-modified', set(dirty)=={SOURCE,TEST}, paths=dirty)
    after_hashes = {p: common.sha(APP/p) for p in frozen}
    common.result('packages-configs-and-lint-baseline-unchanged', frozen_hashes == after_hashes,
                  before=frozen_hashes, after=after_hashes)
    summary={'checked':len(common.RESULTS),'passed':sum(x['pass'] for x in common.RESULTS),
             'failed':[x['check'] for x in common.RESULTS if not x['pass']],
             'manual_account_qa':False,'upstream_submission':False}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY '+json.dumps(summary,sort_keys=True),flush=True)
    if summary['failed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
