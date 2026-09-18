#!/usr/bin/env node
"use strict";

// This file is deliberately named to sort last in the root `test_*.js` glob.
// It detects tracked checkout mutation left behind by any earlier Python or
// Node test without treating ordinary untracked/ignored scratch as a failure.
const { spawnSync } = require("node:child_process");
const path = require("node:path");

const ROOT = __dirname;

function git(args) {
  return spawnSync("git", args, {
    cwd: ROOT,
    encoding: "utf8",
    env: process.env,
  });
}

function commandFailure(label, result) {
  const detail = result.error ? result.error.message : `exit ${String(result.status)}`;
  console.error(`tracked-checkout-clean: ${label} failed (${detail})`);
  process.exit(1);
}

function changedPaths(args) {
  const result = git(args);
  if (result.status !== 0) commandFailure("changed-path readback", result);
  return result.stdout
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function failWithPaths(message, args) {
  console.error(`tracked-checkout-clean: ${message}`);
  for (const item of changedPaths(args)) console.error(item);
  process.exit(1);
}

const head = git(["rev-parse", "HEAD"]);
if (head.status !== 0) commandFailure("HEAD readback", head);
const actualHead = head.stdout.trim();
const expectedHead = (process.env.GITHUB_SHA || process.env.CHECKOUT_SHA || "").trim();
if (expectedHead && actualHead !== expectedHead) {
  console.error(
    `tracked-checkout-clean: test battery moved HEAD: expected ${expectedHead}, got ${actualHead}`
  );
  process.exit(1);
}

const unstaged = git(["diff", "--quiet", "--no-ext-diff", "--", "."]);
if (unstaged.status === 1) {
  failWithPaths("test battery modified tracked files", [
    "diff",
    "--name-only",
    "--no-ext-diff",
    "--",
    ".",
  ]);
}
if (unstaged.status !== 0) commandFailure("unstaged tracked-state check", unstaged);

const staged = git(["diff", "--cached", "--quiet", "--no-ext-diff", "--", "."]);
if (staged.status === 1) {
  failWithPaths("test battery staged tracked-file changes", [
    "diff",
    "--cached",
    "--name-only",
    "--no-ext-diff",
    "--",
    ".",
  ]);
}
if (staged.status !== 0) commandFailure("staged tracked-state check", staged);

console.log("ok   tracked checkout remained at the expected clean postimage");
