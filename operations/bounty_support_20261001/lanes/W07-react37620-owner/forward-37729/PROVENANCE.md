# Forward candidate for react/react#37729 (W07)

- Upstream base: facebook/react main 7c6ac13e19fef500b7f669a16bbd01ecc95965ca
- #37729 head as fetched (`git fetch origin pull/37729/head`, and the fork branch `woahwhattheheck:fix-37620-keep-browser-fallback-20261001`): 04f17e09b7a77ff671d1a78a2816da323f7a49a9 (4cfbc7b, eea9ced, 04f17e0)
  - Ignoring CR, its content is identical to W07 9e31598 (`git diff --ignore-cr-at-eol --stat 9e31598 04f17e0` is empty), i.e. the first fix version plus the dedicated test file.
  - All three touched files are CRLF on that head: ReactFiberBeginWork.js has 4548 CR lines, ReactDOMFizzServer-test.js 11101 and ReactDOMFizzSuspenseFallbackHydration-test.js 212. Main has 0. That is why GitHub shows a ~15.8k-line diff.
- Forward commit: 24520824dc27405ccfae3e097f34b5d1e7235be4, parent 04f17e0, author woahwhattheheck <293286387+woahwhattheheck@users.noreply.github.com>, no trailers.
  - Tree 0316c28ce14d97184c841929d32ee7b3eedeb276, byte-identical to W07 8fce8b7's tree.
  - Net diff vs main: ReactFiberBeginWork.js +72, ReactFiberCompleteWork.js +13, ReactDOMFizzServer-test.js +492. All LF. The dedicated test file is removed; its scenario is folded into ReactDOMFizzServer-test.js, and the 37729 copy still passes against the forward reconciler (experimental + stable).
- Final blobs (LF):
  - packages/react-reconciler/src/ReactFiberBeginWork.js: blob 943c318dfc524294adb0e5ad768a00dbba67a309, sha256 7b0bb6d6966c84c49a4715da980ae53ef75cef1433545a99b168e049052344b3, 159216 bytes
  - packages/react-reconciler/src/ReactFiberCompleteWork.js: blob eb972aa091626eb23188f85e4dc3bf470c04e176, sha256 c42f5e281f7810e0208a7350e4f6fc2bfb6c2ac86a7449476a29cf6283f1f55c, 79081 bytes
  - packages/react-dom/src/__tests__/ReactDOMFizzServer-test.js: blob 4b055fb5ab0dd3887ee17e208da28133d3ebfa75, sha256 bc86be2d8c6b38acf382c5a2886315d1986843ca2a1fe177e4d7268a616d1d71, 316461 bytes
  - Full bodies are in `files/`. Delete packages/react-dom/src/__tests__/ReactDOMFizzSuspenseFallbackHydration-test.js.
- Patch: `0001-Retry-kept-server-fallbacks-like-other-suspended-bou.patch`, 997708 bytes, sha256 29e97a778aa84f6b0e76c663277faa38b58ffd236a7d117f1d069b438c1a4f36. Its removed lines carry the CRs of 04f17e0. Apply with `git am --keep-cr` on 04f17e0: exit 0, tree 0316c28 (checked in a clean worktree).
- `net-diff-vs-main-7c6ac13.diff`: the LF net change against main.
- Discriminating evidence (experimental, the 8 new tests):
  - #37729 reconciler (04f17e0 files) with the new tests: 6 fail (context fallback, context unblock, unrelated transition, sibling prerender, stylesheet, useDeferredValue) and 2 pass.
  - main 7c6ac13 with the new tests: 6 fail on fallback node identity (the issue); the stylesheet and deferred tests pass.
  - Forward commit: 8 of 8 pass.
