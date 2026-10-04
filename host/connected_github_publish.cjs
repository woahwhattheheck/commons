'use strict';

// Caller supplies the already-discovered native bindings and authorized change.
// No filesystem, network client, credential lookup, forced ref update, or write retry.
const ACTIONS = ['fetch', 'fetch_file', 'fetch_blob', 'create_blob', 'create_tree', 'create_commit',
  'create_branch', 'create_pull_request', 'merge_pull_request'];
const SHA = /^[0-9a-f]{40}$/;
const EMPTY_BLOB_SHA = 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391';

class GitHubPublishError extends Error {
  constructor(message, progress, cause) {
    super(message);
    this.name = 'GitHubPublishError';
    this.progress = progress;
    this.cause = cause;
  }
}

function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
  return value;
}

function text(value, label) {
  if (typeof value !== 'string' || !value.trim()) throw new TypeError(`${label} is required`);
  return value;
}

function branch(value, label) {
  text(value, label);
  if (value === '@' || value.startsWith('-') || value.startsWith('refs/')
      || /[\x00-\x20\x7f~^:?*\[\\]/.test(value) || value.includes('..') || value.includes('@{')
      || value.split('/').some(part => !part || part.startsWith('.') || part.endsWith('.') || part.endsWith('.lock'))) {
    throw new TypeError(`${label} must be a short Git branch name`);
  }
  return value;
}

function validateFiles(input) {
  if (!Array.isArray(input.files) || !input.files.length) throw new TypeError('files must contain at least one source file');
  const paths = new Set();
  const files = input.files.map((file, index) => {
    object(file, `files[${index}]`);
    const path = text(file.path, `files[${index}].path`);
    if (path.includes('\\') || /[\x00-\x1f\x7f]/.test(path)
        || path.split('/').some(part => !part || part === '.' || part === '..')) {
      throw new TypeError(`Noncanonical repository path: ${path}`);
    }
    if (paths.has(path)) throw new TypeError(`Duplicate source path: ${path}`);
    paths.add(path);
    if (!Object.prototype.hasOwnProperty.call(file, 'expected_blob_sha')
        || (file.expected_blob_sha !== null && (typeof file.expected_blob_sha !== 'string' || !SHA.test(file.expected_blob_sha)))) {
      throw new TypeError(`Supply the observed expected_blob_sha, or null for a new file: ${path}`);
    }
    if (typeof file.content !== 'string') throw new TypeError(`content must be a string: ${path}`);
    const encoding = file.encoding ?? 'utf-8';
    if (!['utf-8', 'base64'].includes(encoding)) throw new TypeError(`Unsupported encoding: ${path}`);
    if (Object.prototype.hasOwnProperty.call(file, 'expected_new_blob_sha')
        && (typeof file.expected_new_blob_sha !== 'string' || !SHA.test(file.expected_new_blob_sha))) {
      throw new TypeError(`expected_new_blob_sha requires a lowercase Git SHA: ${path}`);
    }
    if (encoding === 'base64' && !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(file.content)) {
      throw new TypeError(`content must be padded base64 without whitespace: ${path}`);
    }
    if (encoding === 'utf-8') {
      for (let i = 0; i < file.content.length; i++) {
        const code = file.content.charCodeAt(i);
        if (code >= 0xd800 && code <= 0xdbff) {
          const next = file.content.charCodeAt(++i);
          if (!(next >= 0xdc00 && next <= 0xdfff)) throw new TypeError(`Unpaired Unicode surrogate: ${path}`);
        } else if (code >= 0xdc00 && code <= 0xdfff) throw new TypeError(`Unpaired Unicode surrogate: ${path}`);
      }
    }
    if (file.mode !== undefined && !['100644', '100755'].includes(file.mode)) {
      throw new TypeError(`Only regular-file modes are supported: ${path}`);
    }
    return {...file, path, encoding};
  });
  for (const path of paths) {
    const parts = path.split('/');
    while (parts.length > 1) {
      parts.pop();
      if (paths.has(parts.join('/'))) throw new TypeError(`A source file is also a parent directory: ${path}`);
    }
  }
  return files;
}

function validate(input) {
  object(input, 'change');
  const repo = text(input.repository_full_name, 'repository_full_name');
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)
      || repo.split('/').some(part => part === '.' || part === '..')) {
    throw new TypeError('repository_full_name must be owner/repository');
  }
  const base = branch(input.base_branch ?? 'main', 'base_branch');
  const head = branch(input.branch_name, 'branch_name');
  if (base === head) throw new TypeError('branch_name must differ from base_branch');
  if (input.merge !== undefined && typeof input.merge !== 'boolean') throw new TypeError('merge must be boolean');
  const method = input.merge_method ?? 'merge';
  if (!['merge', 'squash', 'rebase'].includes(method)) throw new TypeError('unsupported merge_method');
  if (input.body !== undefined && typeof input.body !== 'string') throw new TypeError('body must be a string');
  const title = text(input.title, 'title');
  const message = text(input.commit_message ?? title, 'commit_message');
  const files = validateFiles(input);
  return {repository_full_name: repo, base_branch: base, branch_name: head,
    title, body: input.body ?? '', commit_message: message, files,
    merge: input.merge === true, merge_method: method};
}

function inspectToolError(action, result) {
  if (!result || typeof result !== 'object' || result.isError !== true) return null;
  const structured = result.structuredContent;
  const data = structured && typeof structured === 'object' ? structured.error_data : undefined;
  const status = data && /^[1-5][0-9]{2}$/.test(String(data.status))
    ? Number(data.status) : null;
  const details = {
    action,
    error_code: 'native_tool_error',
    http_status: status,
    message: action + ' returned a native tool error'
      + (status === null ? '' : ' (GitHub HTTP ' + status + ')'),
  };
  if (typeof structured?.error_code === 'string'
      && /^[A-Z0-9_]{1,64}$/.test(structured.error_code)) {
    details.connector_error_code = structured.error_code;
  }
  if (status === 405 && data.message === 'Base branch was modified. Review and try the merge again.') {
    details.error_code = 'base_branch_modified';
    details.message = action + ' was refused because the base branch moved; '
      + 'read the current PR and base before continuing the same merge';
  } else if (Array.isArray(result.content) && result.content.some(block =>
    block?.type === 'text' && typeof block.text === 'string'
    && /\bTransport closed\b/.test(block.text.slice(-1024)))) {
    details.error_code = 'transport_closed';
    details.message = action + ' returned no usable result because its transport closed; '
      + 'reconcile provider state before retrying a write';
  }
  return details;
}

function unpack(result, action) {
  object(result, `${action} response`);
  if (result.isError) {
    const details = inspectToolError(action, result);
    const error = new Error(details?.message ?? action + ' returned a tool error');
    if (details) error.tool_error = details;
    throw error;
  }
  if (result.structuredContent !== undefined) return object(result.structuredContent, `${action} payload`);
  if (Array.isArray(result.content)) {
    for (const block of result.content) {
      if (block.type !== 'text') continue;
      try { return object(JSON.parse(block.text), `${action} payload`); } catch (_) { /* Try the next native block. */ }
    }
    throw new Error(`${action} did not return a readable object`);
  }
  return result;
}

function sha(value, label) {
  if (typeof value !== 'string' || !SHA.test(value)) throw new Error(`${label} did not return a Git SHA`);
  return value;
}

function checkNewBlobPin(file, source) {
  if (source.expected_new_blob_sha === undefined) return;
  file.expected_new_blob_sha = source.expected_new_blob_sha;
  file.source_pin_matches = file.blob_sha === source.expected_new_blob_sha;
  if (!file.source_pin_matches) {
    throw new Error(`New source blob mismatch: ${file.path}; expected ${source.expected_new_blob_sha}, observed ${file.blob_sha}`);
  }
}

function isMissingFileResponse(response) {
  const payload = response?.structuredContent;
  return response?.isError === true && payload?.error_code === 'NOT_FOUND'
    && [404, '404'].includes(payload.error_data?.status)
    && payload.error_data?.message === 'Not Found';
}

/** Resolve exact entries; only an absent leaf can replace an unreadable tree. */
function baseFileReader({api, repository_full_name, commitSha, treeSha,
  fetchJSON, readPreimage, progress, treeLabel}) {
  const trees = new Map();
  const unavailable = new Map();
  const tree = async current => {
    if (unavailable.has(current)) throw unavailable.get(current);
    if (!trees.has(current)) {
      let data;
      try { data = await fetchJSON(`${api}/git/trees/${current}`); }
      catch (error) {
        if (error.tool_error?.error_code === 'transport_closed'
            && error.tool_error.http_status === null) unavailable.set(current, error);
        throw error;
      }
      if (data.sha !== current || !Array.isArray(data.tree) || data.truncated !== false) {
        const error = new Error(`The ${treeLabel} tree could not be read completely: ${current}`);
        if (data.sha === current && Array.isArray(data.tree) && data.truncated === true) {
          error.truncated_tree = true;
          unavailable.set(current, error);
        }
        throw error;
      }
      trees.set(current, data.tree);
    }
    return trees.get(current);
  };
  return async (path, expectedBlob) => {
    let current = treeSha;
    const parts = path.split('/');
    for (let index = 0; index < parts.length; index++) {
      let entries;
      try { entries = await tree(current); }
      catch (error) {
        // The successful prefix reads must already establish the immediate parent.
        if (index === 0 || index !== parts.length - 1 || !unavailable.has(current)) throw error;
        const request = {repository_full_name, path, ref: commitSha, encoding: 'utf-8',
          start_line: 1, end_line: 1};
        const record = {path, base_commit_sha: commitSha, parent_tree_sha: current,
          reason: error.truncated_tree ? 'truncated_tree' : 'transport_closed',
          ...(error.tool_error ? {tree_error: error.tool_error} : {}),
          request, outcome: 'pending'};
        (progress.preimage_fallbacks ??= []).push(record);
        let response;
        try { response = await readPreimage(request); }
        catch (readError) {
          record.outcome = 'unavailable';
          if (readError.tool_error) record.tool_error = readError.tool_error;
          throw readError;
        }
        if (response.absent) {
          Object.assign(record, {outcome: 'absent', observed_blob_sha: null,
            http_status: 404, connector_error_code: 'NOT_FOUND'});
          return null;
        }
        const data = response.data;
        record.outcome = 'unavailable';
        if (data.display_url !== `https://github.com/${repository_full_name}/blob/${commitSha}/${path}`) {
          throw new Error(`File precheck did not identify the exact immutable path: ${path}`);
        }
        const observed = sha(data.sha, 'Existing file precheck');
        Object.assign(record, {outcome: 'existing_blob', observed_blob_sha: observed,
          file_type_observed: false, mode_observed: false});
        // A differing blob proves a version conflict without assuming type or mode.
        if (observed !== expectedBlob) return {sha: observed};
        throw new Error(`The existing path's Git type and mode are unavailable: ${path}; a caller-selected mode cannot replace the unreadable tree`);
      }
      const item = entries.find(entry => entry.path === parts[index]);
      if (!item) return null;
      if (index === parts.length - 1) return item;
      if (item.type !== 'tree') throw new Error(`A parent path is not a directory: ${path}`);
      current = sha(item.sha, 'Parent tree');
    }
  };
}

function inspectReadback(file, source, data) {
  if (source.encoding === 'utf-8') {
    const observed = sha(data.sha, 'Published text blob');
    const expected = source.expected_new_blob_sha ?? null;
    // Large-file metadata can retain the blob SHA while omitting the body.
    if (typeof data.content !== 'string' || (data.content === '' && observed !== EMPTY_BLOB_SHA)) {
      return {path: file.path, expected_blob_sha: expected, observed_blob_sha: observed,
        content_matches: null, content_available: false, matches: false,
        error_code: 'readback_content_unavailable'};
    }
    const contentMatches = data.content === source.content;
    const matches = contentMatches && (expected === null || observed === expected);
    if (matches) file.blob_sha = observed;
    return {path: file.path, expected_blob_sha: expected, observed_blob_sha: observed,
      content_matches: contentMatches, matches};
  }
  return {path: file.path, expected_blob_sha: file.blob_sha, observed_blob_sha: data.sha,
    matches: data.sha === file.blob_sha};
}

/** Recover omitted text with one optional read of the observed immutable blob. */
async function resolveReadback(file, source, data, readBlob) {
  const initial = inspectReadback(file, source, data);
  if (initial.error_code !== 'readback_content_unavailable' || typeof readBlob !== 'function') {
    return initial;
  }
  let blob;
  try {
    blob = await readBlob(initial.observed_blob_sha);
  } catch (error) {
    return {...initial, blob_readback_attempted: true,
      blob_readback_error: String(error?.message ?? error),
      ...(error?.tool_error ? {tool_error: error.tool_error} : {})};
  }
  return {...inspectReadback(file, source, {
    sha: initial.observed_blob_sha, content: blob?.content,
  }), blob_readback_attempted: true, readback_source: 'blob', file_content_available: false};
}

/** Publish regular-file changes through native GitHub tools, optionally merge. */
async function publishGitHubChange(tools, change, options = {}) {
  const progress = {status: 'incomplete', stage: 'validate', calls: {}, files: [], progress_callback_errors: []};
  let lastResponse;
  let announce = async () => {};
  try {
    const spec = validate(change);
    const sourceByPath = new Map(spec.files.map(file => [file.path, file]));
    const repository_full_name = spec.repository_full_name;
    Object.assign(progress, {repository_full_name, base_branch: spec.base_branch, branch_name: spec.branch_name});
    const bindings = Object.fromEntries(ACTIONS.map(action => [action,
      options.bindings?.[action] ?? `mcp__codex_apps__github_${action}`]));
    const required = ACTIONS.filter(action => action !== 'fetch_blob'
      && (action !== 'merge_pull_request' || spec.merge)
      && (action !== 'create_blob' || spec.files.some(file =>
        file.encoding === 'base64' || file.expected_new_blob_sha !== undefined)));
    for (const action of required) {
      if (typeof tools?.[bindings[action]] !== 'function') {
        throw new Error(`Binding not present: ${bindings[action]}. Repeat discovery alongside independent work.`);
      }
    }
    announce = async () => {
      if (typeof options.onProgress !== 'function') return;
      try { await options.onProgress(JSON.parse(JSON.stringify(progress))); }
      catch (error) { progress.progress_callback_errors.push(String(error.message ?? error)); }
    };
    const call = async (action, args) => {
      progress.calls[action] = (progress.calls[action] ?? 0) + 1;
      lastResponse = undefined;
      lastResponse = await tools[bindings[action]](args);
      return unpack(lastResponse, action);
    };
    const fetchJSON = async url => {
      const payload = await call('fetch', {url});
      return typeof payload.content === 'string' ? object(JSON.parse(payload.content), 'GitHub resource') : payload;
    };
    const readPreimage = async args => {
      try { return {data: await call('fetch_file', args)}; }
      catch (error) {
        if (isMissingFileResponse(lastResponse)) return {absent: true};
        throw error;
      }
    };
    const api = `https://api.github.com/repos/${repository_full_name}`;
    progress.stage = 'read_base';
    const base = await fetchJSON(`${api}/branches/${encodeURIComponent(spec.base_branch)}`);
    progress.base_commit_sha = sha(base.commit?.sha, 'Base branch');
    progress.base_tree_sha = sha(base.commit?.commit?.tree?.sha, 'Base tree');
    const existingFile = baseFileReader({api, repository_full_name,
      commitSha: progress.base_commit_sha, treeSha: progress.base_tree_sha,
      fetchJSON, readPreimage, progress, treeLabel: 'base'});
    progress.stage = 'check_file_versions';
    for (const file of spec.files) {
      const existing = await existingFile(file.path, file.expected_blob_sha);
      if ((existing?.sha ?? null) !== file.expected_blob_sha) {
        throw new Error(`Base file changed: ${file.path}; expected ${file.expected_blob_sha ?? 'absent'}, observed ${existing?.sha ?? 'absent'}`);
      }
      if (existing && (existing.type !== 'blob' || !['100644', '100755'].includes(existing.mode))) {
        throw new Error(`The existing path is not a regular file: ${file.path}`);
      }
      progress.files.push({path: file.path, previous_blob_sha: existing?.sha ?? null,
        previous_mode: existing?.mode ?? null, mode: file.mode ?? existing?.mode ?? '100644',
        ...(file.expected_new_blob_sha === undefined ? {} : {
          expected_new_blob_sha: file.expected_new_blob_sha, source_pin_matches: null})});
    }
    await announce();
    progress.stage = 'create_blobs';
    for (let index = 0; index < spec.files.length; index++) {
      const file = spec.files[index];
      if (file.encoding === 'utf-8' && file.expected_new_blob_sha === undefined) continue;
      const data = await call('create_blob', {repository_full_name, content: file.content, encoding: file.encoding});
      progress.files[index].blob_sha = sha(data.sha, 'Created blob');
      checkNewBlobPin(progress.files[index], file);
      await announce();
    }
    const candidates = progress.files.filter(file => file.blob_sha === undefined
      || file.blob_sha !== file.previous_blob_sha || file.mode !== file.previous_mode);
    if (!candidates.length) {
      progress.status = 'no_source_changes'; progress.stage = 'complete';
      await announce(); return progress;
    }
    progress.stage = 'create_tree';
    const createdTree = await call('create_tree', {repository_full_name, base_tree_sha: progress.base_tree_sha,
      tree_elements: candidates.map(file => {
        const source = sourceByPath.get(file.path);
        return {path: file.path, mode: file.mode, type: 'blob',
          ...(file.blob_sha === undefined ? {content: source.content} : {sha: file.blob_sha})};
      })});
    progress.tree_sha = sha(createdTree.sha, 'Created tree');
    await announce();
    if (progress.tree_sha === progress.base_tree_sha) {
      for (const file of progress.files) file.blob_sha = file.previous_blob_sha;
      progress.status = 'no_source_changes'; progress.stage = 'complete';
      await announce(); return progress;
    }
    progress.stage = 'create_commit';
    const commit = await call('create_commit', {repository_full_name, parent_sha: progress.base_commit_sha,
      tree_sha: progress.tree_sha, message: spec.commit_message});
    progress.commit_sha = sha(commit.sha, 'Created commit');
    await announce();
    progress.stage = 'create_branch';
    const createdBranch = await call('create_branch', {repository_full_name, branch_name: spec.branch_name, sha: progress.commit_sha});
    if (createdBranch.branch !== spec.branch_name && createdBranch.ref !== `refs/heads/${spec.branch_name}`) {
      throw new Error('The branch response does not identify the requested branch');
    }
    if (createdBranch.object?.sha && createdBranch.object.sha !== progress.commit_sha) {
      throw new Error('The branch response does not identify the created commit');
    }
    progress.branch_created = true;
    await announce();
    progress.stage = 'create_pull_request';
    const pr = await call('create_pull_request', {repository_full_name, head: spec.branch_name,
      base: spec.base_branch, title: spec.title, body: spec.body});
    progress.pull_request = {number: pr.number, url: pr.url ?? pr.display_url, head_sha: pr.head_sha};
    if (!Number.isInteger(pr.number) || pr.number < 1 || pr.head_sha !== progress.commit_sha) {
      throw new Error('The returned pull request does not identify the created commit');
    }
    progress.publication_status = 'pull_request_open';
    await announce();
    if (spec.merge) {
      progress.stage = 'merge_pull_request';
      const merged = await call('merge_pull_request', {repository_full_name, pr_number: pr.number,
        expected_head_sha: progress.commit_sha, merge_method: spec.merge_method});
      progress.merge_result = merged;
      if (merged.merged !== true) throw new Error('GitHub did not report a completed merge');
      progress.publication_status = 'merged';
      progress.merge_sha = sha(merged.sha, 'Merge');
      await announce();
    }
    progress.stage = 'readback';
    progress.readback_ref = progress.merge_sha ?? progress.commit_sha;
    const readBlob = typeof tools?.[bindings.fetch_blob] === 'function'
      ? blob_sha => call('fetch_blob', {repository_full_name, blob_sha}) : undefined;
    // Every read is independent. Inspect every outcome before reporting completion.
    const reads = await Promise.allSettled(candidates.map(async file => {
      const source = sourceByPath.get(file.path);
      const data = await call('fetch_file', {repository_full_name, path: file.path,
        ref: progress.readback_ref, encoding: source.encoding});
      return resolveReadback(file, source, data, readBlob);
    }));
    progress.readback = reads.map((read, index) => read.status === 'fulfilled' ? read.value
      : {path: candidates[index].path, matches: false, error: String(read.reason?.message ?? read.reason),
        ...(read.reason?.tool_error ? {tool_error: read.reason.tool_error} : {})});
    const unavailable = progress.readback.some(read => read.error_code === 'readback_content_unavailable');
    progress.readback_status = unavailable ? 'content_unavailable'
      : progress.readback.some(read => !read.matches) ? 'incomplete' : 'complete';
    if (unavailable) throw new Error('Published source content was not returned; finish readback at readback_ref without repeating publication');
    if (progress.readback.some(read => !read.matches)) throw new Error('One or more published source readbacks did not match');
    progress.status = spec.merge ? 'merged' : 'pull_request_open';
    progress.stage = 'complete';
    await announce();
    return progress;
  } catch (error) {
    if (error.tool_error) progress.tool_error = error.tool_error;
    await announce();
    const failure = new GitHubPublishError(String(error.message ?? error), progress, error);
    if (error.tool_error) failure.tool_error = error.tool_error;
    failure.response = lastResponse;
    throw failure;
  }
}

/** Explicitly finish a known publication's merge without replaying its creation. */
async function continueGitHubMerge(tools, change, previousProgress, options = {}) {
  const progress = {operation: 'merge_continuation', status: 'incomplete', stage: 'validate',
    calls: {}, files: [], progress_callback_errors: []};
  let lastResponse;
  let announce = async () => {};
  try {
    const spec = validate(change);
    if (!spec.merge) throw new TypeError('Set merge: true for this explicit merge continuation');
    const saved = object(previousProgress, 'previousProgress');
    for (const key of ['repository_full_name', 'base_branch', 'branch_name']) {
      if (saved[key] !== spec[key]) throw new Error(`Retained publication differs from change: ${key}`);
      progress[key] = spec[key];
    }
    for (const key of ['base_commit_sha', 'base_tree_sha', 'tree_sha', 'commit_sha']) {
      progress[key] = sha(saved[key], `Retained ${key}`);
    }
    const retainedPR = object(saved.pull_request, 'Retained pull_request');
    if (!Number.isInteger(retainedPR.number) || retainedPR.number < 1
        || retainedPR.head_sha !== progress.commit_sha) {
      throw new Error('Retain the confirmed pull request number and original head SHA');
    }
    progress.pull_request = {number: retainedPR.number, url: retainedPR.url, head_sha: progress.commit_sha};
    if (!Array.isArray(saved.files)) throw new TypeError('Retain the publication file versions');
    const savedFiles = new Map(saved.files.map(file => [object(file, 'Retained file').path, file]));
    if (savedFiles.size !== spec.files.length || saved.files.length !== spec.files.length) {
      throw new Error('Retained file paths differ from the original prepared change');
    }
    for (const source of spec.files) {
      const file = savedFiles.get(source.path);
      if (!file || file.previous_blob_sha !== source.expected_blob_sha
          || (file.previous_blob_sha === null ? file.previous_mode !== null
            : !['100644', '100755'].includes(file.previous_mode))
          || file.mode !== (source.mode ?? file.previous_mode ?? '100644')) {
        throw new Error(`Retained file version or mode differs from change: ${source.path}`);
      }
      const record = {path: source.path, previous_blob_sha: file.previous_blob_sha,
        previous_mode: file.previous_mode, mode: file.mode};
      if (file.expected_new_blob_sha !== undefined
          && file.expected_new_blob_sha !== source.expected_new_blob_sha) {
        throw new Error(`Retained source pin differs from change: ${source.path}`);
      }
      if (source.encoding === 'base64' || source.expected_new_blob_sha !== undefined) {
        record.blob_sha = sha(file.blob_sha, source.encoding === 'base64' ? 'Retained binary blob' : 'Retained text blob');
      }
      progress.files.push(record);
      checkNewBlobPin(record, source);
    }
    const repository_full_name = spec.repository_full_name;
    const actions = ['get_pr_info', 'fetch', 'fetch_file', 'fetch_blob', 'merge_pull_request'];
    const bindings = Object.fromEntries(actions.map(action => [action,
      options.bindings?.[action] ?? `mcp__codex_apps__github_${action}`]));
    const requireBinding = action => {
      if (typeof tools?.[bindings[action]] !== 'function') {
        throw new Error(`Binding not present: ${bindings[action]}. Repeat discovery alongside independent work.`);
      }
    };
    requireBinding('get_pr_info');
    requireBinding('fetch_file');
    announce = async () => {
      if (typeof options.onProgress !== 'function') return;
      try { await options.onProgress(JSON.parse(JSON.stringify(progress))); }
      catch (error) { progress.progress_callback_errors.push(String(error.message ?? error)); }
    };
    const call = async (action, args) => {
      progress.calls[action] = (progress.calls[action] ?? 0) + 1;
      lastResponse = undefined;
      lastResponse = await tools[bindings[action]](args);
      return unpack(lastResponse, action);
    };
    const fetchJSON = async url => {
      const payload = await call('fetch', {url});
      return typeof payload.content === 'string' ? object(JSON.parse(payload.content), 'GitHub resource') : payload;
    };
    const readPreimage = async args => {
      try { return {data: await call('fetch_file', args)}; }
      catch (error) {
        if (isMissingFileResponse(lastResponse)) return {absent: true};
        throw error;
      }
    };
    progress.stage = 'read_pull_request';
    const pr = await call('get_pr_info', {repository_full_name, pr_number: retainedPR.number});
    if (pr.number !== retainedPR.number || pr.base !== spec.base_branch || pr.head !== spec.branch_name
        || typeof pr.head_repo_full_name !== 'string'
        || pr.head_repo_full_name.toLowerCase() !== repository_full_name.toLowerCase()
        || pr.head_sha !== progress.commit_sha) {
      throw new Error('The current pull request differs from the retained repository, branches, or head');
    }
    progress.pull_request.url = pr.url ?? retainedPR.url;
    if (pr.merged === true) {
      progress.publication_status = 'merged';
      progress.merge_sha = sha(pr.merge_commit_sha, 'Existing merge');
      progress.merge_skipped = 'already_merged';
      await announce();
    } else {
      if (pr.merged !== false || pr.state !== 'open') throw new Error('The pull request is not open or confirmed merged');
      progress.publication_status = 'pull_request_open';
      await announce();
      requireBinding('fetch');
      requireBinding('merge_pull_request');
      const api = `https://api.github.com/repos/${repository_full_name}`;
      progress.stage = 'read_base';
      const base = await fetchJSON(`${api}/branches/${encodeURIComponent(spec.base_branch)}`);
      progress.current_base_commit_sha = sha(base.commit?.sha, 'Current base branch');
      progress.current_base_tree_sha = sha(base.commit?.commit?.tree?.sha, 'Current base tree');
      const existingFile = baseFileReader({api, repository_full_name,
        commitSha: progress.current_base_commit_sha, treeSha: progress.current_base_tree_sha,
        fetchJSON, readPreimage, progress, treeLabel: 'current base'});
      progress.stage = 'check_file_versions';
      for (const file of progress.files) {
        const existing = await existingFile(file.path, file.previous_blob_sha);
        if ((existing?.sha ?? null) !== file.previous_blob_sha
            || (existing?.mode ?? null) !== file.previous_mode
            || (existing && existing.type !== 'blob')) {
          throw new Error(`Base file changed: ${file.path}; read the current source and compose deliberately`);
        }
      }
      await announce();
      progress.stage = 'merge_pull_request';
      const merged = await call('merge_pull_request', {repository_full_name, pr_number: retainedPR.number,
        expected_head_sha: progress.commit_sha, merge_method: spec.merge_method});
      progress.merge_result = merged;
      if (merged.merged !== true) throw new Error('GitHub did not report a completed merge');
      progress.publication_status = 'merged';
      progress.merge_sha = sha(merged.sha, 'Merge');
      await announce();
    }
    progress.stage = 'readback';
    progress.readback_ref = progress.merge_sha;
    const readBlob = typeof tools?.[bindings.fetch_blob] === 'function'
      ? blob_sha => call('fetch_blob', {repository_full_name, blob_sha}) : undefined;
    const reads = await Promise.allSettled(progress.files.map(async (file, index) => {
      const source = spec.files[index];
      const data = await call('fetch_file', {repository_full_name, path: file.path,
        ref: progress.readback_ref, encoding: source.encoding});
      return resolveReadback(file, source, data, readBlob);
    }));
    progress.readback = reads.map((read, index) => read.status === 'fulfilled' ? read.value
      : {path: progress.files[index].path, matches: false, error: String(read.reason?.message ?? read.reason),
        ...(read.reason?.tool_error ? {tool_error: read.reason.tool_error} : {})});
    const unavailable = progress.readback.some(read => read.error_code === 'readback_content_unavailable');
    progress.readback_status = unavailable ? 'content_unavailable'
      : progress.readback.some(read => !read.matches) ? 'incomplete' : 'complete';
    if (unavailable) throw new Error('Merged source content was not returned; finish readback without repeating publication');
    if (progress.readback.some(read => !read.matches)) throw new Error('One or more merged source readbacks did not match');
    progress.status = 'merged';
    progress.stage = 'complete';
    await announce();
    return progress;
  } catch (error) {
    if (error.tool_error) progress.tool_error = error.tool_error;
    await announce();
    const failure = new GitHubPublishError(String(error.message ?? error), progress, error);
    if (error.tool_error) failure.tool_error = error.tool_error;
    failure.response = lastResponse;
    throw failure;
  }
}


function validateContribution(input) {
  object(input, 'change');
  const result = {};
  for (const key of ['repository_full_name', 'pull_request_repository_full_name']) {
    const value = text(input[key], key);
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(value)
        || value.split('/').some(part => part === '.' || part === '..')) {
      throw new TypeError(key + ' must be owner/repository');
    }
    result[key] = value;
  }
  if (!Number.isSafeInteger(input.pull_request_number) || input.pull_request_number < 1) {
    throw new TypeError('pull_request_number must identify the existing pull request');
  }
  for (const key of ['merge', 'merge_method', 'title', 'body', 'force']) {
    if (input[key] !== undefined) throw new TypeError(key + ' is not part of a contribution advancement');
  }
  return {...result, pull_request_number: input.pull_request_number,
    branch_name: branch(input.branch_name, 'branch_name'),
    base_branch: branch(input.base_branch, 'base_branch'),
    expected_head_sha: sha(input.expected_head_sha, 'expected_head_sha'),
    expected_base_sha: sha(input.expected_base_sha, 'expected_base_sha'),
    commit_message: text(input.commit_message, 'commit_message'), files: validateFiles(input)};
}

function contributionPR(pr, spec) {
  if (pr.number !== spec.pull_request_number || pr.head?.ref !== spec.branch_name
      || pr.base?.ref !== spec.base_branch
      || pr.head?.repo?.full_name?.toLowerCase() !== spec.repository_full_name.toLowerCase()
      || pr.base?.repo?.full_name?.toLowerCase() !== spec.pull_request_repository_full_name.toLowerCase()
      || !['open', 'closed'].includes(pr.state) || typeof pr.merged !== 'boolean') {
    throw new Error('The pull request differs from the specified repositories or branches');
  }
  return {number: pr.number, url: pr.html_url,
    head_sha: sha(pr.head.sha, 'PR head'), base_sha: sha(pr.base.sha, 'PR base'),
    state: pr.state, merged: pr.merged, author_login: pr.user?.login ?? null};
}

function requireContributionHead(pr, spec) {
  if (pr.state !== 'open' || pr.merged !== false || pr.head_sha !== spec.expected_head_sha
      || pr.base_sha !== spec.expected_base_sha) {
    throw new Error('The open contribution head or base changed; reconcile the original PR before publishing');
  }
}

function completeContributionTree(data, expected) {
  if (data.sha !== expected || data.truncated !== false || !Array.isArray(data.tree)) {
    throw new Error('The contribution tree was not returned completely: ' + expected);
  }
  const entries = new Map();
  for (const entry of data.tree) {
    if (!entry || typeof entry.path !== 'string'
        || entry.path.split('/').some(part => !part || part === '.' || part === '..')
        || entries.has(entry.path) || !['blob', 'tree', 'commit'].includes(entry.type)
        || typeof entry.mode !== 'string' || !/^[0-7]{6}$/.test(entry.mode)) {
      throw new Error('The contribution tree contains an invalid or duplicate entry');
    }
    sha(entry.sha, 'Contribution tree entry');
    entries.set(entry.path, entry);
  }
  for (const path of entries.keys()) {
    const parts = path.split('/');
    while (parts.length > 1) {
      parts.pop();
      if (entries.get(parts.join('/'))?.type !== 'tree') {
        throw new Error('The contribution tree omitted a parent directory: ' + path);
      }
    }
  }
  return entries;
}

function contributionFiles(spec, parentEntries) {
  return spec.files.map(source => {
    const before = parentEntries.get(source.path);
    if ((before?.sha ?? null) !== source.expected_blob_sha) {
      throw new Error('Contribution file changed: ' + source.path);
    }
    if (before && (before.type !== 'blob' || !['100644', '100755'].includes(before.mode))) {
      throw new Error('The contribution path is not a regular file: ' + source.path);
    }
    const parts = source.path.split('/');
    while (parts.length > 1) {
      parts.pop();
      const parent = parentEntries.get(parts.join('/'));
      if (parent && parent.type !== 'tree') {
        throw new Error('A contribution parent path is not a directory: ' + source.path);
      }
    }
    return {path: source.path, previous_blob_sha: before?.sha ?? null,
      previous_mode: before?.mode ?? null, mode: source.mode ?? before?.mode ?? '100644',
      ...(source.expected_new_blob_sha === undefined ? {} : {
        expected_new_blob_sha: source.expected_new_blob_sha, source_pin_matches: null})};
  });
}

function compareContributionTrees(before, after, files, sources) {
  const targetPaths = new Set(files.map(file => file.path));
  const parentPaths = new Set();
  for (const path of targetPaths) {
    const parts = path.split('/');
    while (parts.length > 1) { parts.pop(); parentPaths.add(parts.join('/')); }
  }
  const same = (a, b) => a?.sha === b?.sha && a?.type === b?.type && a?.mode === b?.mode;
  let unchangedLeaves = 0;
  for (const path of new Set([...before.keys(), ...after.keys()])) {
    if (targetPaths.has(path)) continue;
    const a = before.get(path), b = after.get(path);
    if (parentPaths.has(path)) {
      if ((a && (a.type !== 'tree' || a.mode !== '040000'))
          || b?.type !== 'tree' || b.mode !== '040000') {
        throw new Error('A prepared parent directory changed type or mode: ' + path);
      }
    } else if (!same(a, b)) {
      throw new Error('An unrequested contribution path changed: ' + path);
    }
    if (a && a.type !== 'tree') unchangedLeaves++;
  }
  const changedPaths = [];
  for (let index = 0; index < files.length; index++) {
    const file = files[index], entry = after.get(file.path);
    if (!entry || entry.type !== 'blob' || entry.mode !== file.mode
        || (file.blob_sha !== undefined && entry.sha !== file.blob_sha)) {
      throw new Error('The prepared contribution file has a different blob or mode: ' + file.path);
    }
    file.blob_sha = entry.sha;
    checkNewBlobPin(file, sources[index]);
    if (!same(before.get(file.path), entry)) changedPaths.push(file.path);
  }
  return {complete: true, unchanged_leaf_count: unchangedLeaves, changed_paths: changedPaths};
}

async function contributionOperation(tools, change, options, readOnly, previousProgress) {
  const progress = {operation: readOnly ? 'contribution_reconciliation' : 'contribution_advance',
    status: 'incomplete', stage: 'validate', publication_status: 'not_updated',
    calls: {}, files: [], progress_callback_errors: []};
  let lastResponse;
  let announce = async () => {};
  try {
    const spec = validateContribution(change);
    const identityKeys = ['repository_full_name', 'pull_request_repository_full_name',
      'pull_request_number', 'branch_name', 'base_branch', 'expected_head_sha', 'expected_base_sha'];
    for (const key of identityKeys) progress[key] = spec[key];
    progress.parent_commit_sha = spec.expected_head_sha;
    let saved;
    if (readOnly) {
      saved = object(previousProgress, 'previousProgress');
      if (!['contribution_advance', 'contribution_reconciliation'].includes(saved.operation)) {
        throw new Error('Retain the existing contribution operation, not a new-PR publication');
      }
      for (const key of identityKeys) {
        if (saved[key] !== spec[key]) throw new Error('Retained contribution differs from change: ' + key);
      }
      if (saved.parent_commit_sha !== spec.expected_head_sha) throw new Error('Retained contribution parent changed');
      for (const key of ['parent_tree_sha', 'tree_sha', 'commit_sha']) {
        progress[key] = sha(saved[key], 'Retained ' + key);
      }
      if (!Array.isArray(saved.files) || saved.files.length !== spec.files.length) {
        throw new Error('Retain all contribution file versions');
      }
      progress.previous_publication_status = saved.publication_status;
      progress.previous_ref_update_state = saved.ref_update_state ?? null;
      progress.publication_status = 'unreconciled';
    }
    const actions = ['fetch', 'fetch_file', 'fetch_blob',
      ...(readOnly ? [] : ['create_blob', 'create_tree', 'create_commit', 'update_ref'])];
    const bindings = Object.fromEntries(actions.map(action => [action,
      options.bindings?.[action] ?? 'mcp__codex_apps__github_' + action]));
    for (const action of actions) {
      if (action === 'fetch_blob' || (action === 'create_blob' && !spec.files.some(file =>
        file.encoding === 'base64' || file.expected_new_blob_sha !== undefined))) continue;
      if (typeof tools?.[bindings[action]] !== 'function') {
        throw new Error('Binding not present: ' + bindings[action] + '. Repeat discovery alongside independent work.');
      }
    }
    announce = async () => {
      if (typeof options.onProgress !== 'function') return;
      try { await options.onProgress(JSON.parse(JSON.stringify(progress))); }
      catch (error) { progress.progress_callback_errors.push(String(error.message ?? error)); }
    };
    const call = async (action, args) => {
      progress.calls[action] = (progress.calls[action] ?? 0) + 1;
      let response;
      try {
        lastResponse = undefined;
        response = await tools[bindings[action]](args);
        lastResponse = response;
        return unpack(response, action);
      } catch (error) {
        if (response !== undefined) error.response = response;
        throw error;
      }
    };
    const fetchJSON = async url => {
      const payload = await call('fetch', {url});
      return typeof payload.content === 'string' ? object(JSON.parse(payload.content), 'GitHub resource') : payload;
    };
    const repository_full_name = spec.repository_full_name;
    const api = 'https://api.github.com/repos/' + repository_full_name;
    const prURL = 'https://api.github.com/repos/' + spec.pull_request_repository_full_name
      + '/pulls/' + spec.pull_request_number;
    const refURL = api + '/git/ref/heads/' + spec.branch_name.split('/').map(encodeURIComponent).join('/');
    const observe = async label => {
      const outcomes = await Promise.allSettled([fetchJSON(prURL), fetchJSON(refURL)]);
      const record = {stage: label};
      for (let index = 0; index < outcomes.length; index++) {
        if (outcomes[index].status === 'rejected') {
          const error = outcomes[index].reason;
          record[index === 0 ? 'pull_request_error' : 'ref_error'] = {
            message: String(error?.message ?? error),
            ...(error?.tool_error ? {tool_error: error.tool_error} : {})};
        }
      }
      (progress.observations ??= []).push(record);
      const failure = outcomes.find(outcome => outcome.status === 'rejected');
      if (failure) throw failure.reason;
      record.pull_request = contributionPR(outcomes[0].value, spec);
      const ref = outcomes[1].value;
      if (ref.ref !== 'refs/heads/' + spec.branch_name || ref.object?.type !== 'commit') {
        throw new Error('The reference response does not identify the existing branch');
      }
      record.ref_sha = sha(ref.object.sha, 'Contribution branch ref');
      record.base_changed = record.pull_request.base_sha !== spec.expected_base_sha;
      return record;
    };
    if (!readOnly) {
      progress.stage = 'read_pull_request';
      progress.pull_request = contributionPR(await fetchJSON(prURL), spec);
      requireContributionHead(progress.pull_request, spec);
    }
    progress.stage = 'read_parent';
    const parent = await fetchJSON(api + '/git/commits/' + spec.expected_head_sha);
    if (parent.sha !== spec.expected_head_sha) throw new Error('The contribution parent identity changed');
    const parentTree = sha(parent.tree?.sha, 'Contribution parent tree');
    if (readOnly && parentTree !== progress.parent_tree_sha) throw new Error('Retained contribution parent tree changed');
    progress.parent_tree_sha = parentTree;
    const before = completeContributionTree(await fetchJSON(api + '/git/trees/' + parentTree + '?recursive=1'), parentTree);
    progress.stage = 'check_file_versions';
    progress.files = contributionFiles(spec, before);
    if (readOnly) {
      const retained = new Map(saved.files.map(file => [object(file, 'Retained file').path, file]));
      if (retained.size !== progress.files.length) throw new Error('Retained contribution paths differ');
      for (let index = 0; index < progress.files.length; index++) {
        const file = progress.files[index], source = spec.files[index], old = retained.get(file.path);
        if (!old || ['previous_blob_sha', 'previous_mode', 'mode'].some(key => old[key] !== file[key])
            || (old.expected_new_blob_sha !== undefined && old.expected_new_blob_sha !== source.expected_new_blob_sha)) {
          throw new Error('Retained contribution file or pin changed: ' + file.path);
        }
        if (old.blob_sha !== undefined) file.blob_sha = sha(old.blob_sha, 'Retained contribution blob');
        if (source.encoding === 'base64' || source.expected_new_blob_sha !== undefined) {
          sha(file.blob_sha, 'Retained source identity');
          checkNewBlobPin(file, source);
        }
      }
    }
    await announce();
    if (!readOnly) {
      progress.stage = 'create_blobs';
      for (let index = 0; index < spec.files.length; index++) {
        const source = spec.files[index], file = progress.files[index];
        if (source.encoding === 'utf-8' && source.expected_new_blob_sha === undefined) continue;
        const blob = await call('create_blob', {repository_full_name, content: source.content, encoding: source.encoding});
        file.blob_sha = sha(blob.sha, 'Created contribution blob');
        checkNewBlobPin(file, source);
        await announce();
      }
      const candidates = progress.files.filter(file => file.blob_sha === undefined
        || file.blob_sha !== file.previous_blob_sha || file.mode !== file.previous_mode);
      if (!candidates.length) {
        progress.status = 'no_source_changes'; progress.stage = 'complete';
        await announce(); return progress;
      }
      progress.stage = 'create_tree';
      const sources = new Map(spec.files.map(source => [source.path, source]));
      const tree = await call('create_tree', {repository_full_name, base_tree_sha: parentTree,
        tree_elements: candidates.map(file => ({path: file.path, mode: file.mode, type: 'blob',
          ...(file.blob_sha === undefined ? {content: sources.get(file.path).content} : {sha: file.blob_sha})}))});
      progress.tree_sha = sha(tree.sha, 'Created contribution tree');
      await announce();
      if (progress.tree_sha === parentTree) {
        for (const file of progress.files) file.blob_sha = file.previous_blob_sha;
        progress.status = 'no_source_changes'; progress.stage = 'complete';
        await announce(); return progress;
      }
      progress.stage = 'create_commit';
      const commit = await call('create_commit', {repository_full_name, parent_sha: spec.expected_head_sha,
        tree_sha: progress.tree_sha, message: spec.commit_message});
      progress.commit_sha = sha(commit.sha, 'Created contribution commit');
      await announce();
    }
    progress.stage = 'verify_commit';
    const created = await fetchJSON(api + '/git/commits/' + progress.commit_sha);
    if (created.sha !== progress.commit_sha || created.tree?.sha !== progress.tree_sha
        || !Array.isArray(created.parents) || created.parents.length !== 1
        || created.parents[0].sha !== spec.expected_head_sha || created.message !== spec.commit_message) {
      throw new Error('The prepared commit differs from its sole parent, tree or message');
    }
    const after = completeContributionTree(
      await fetchJSON(api + '/git/trees/' + progress.tree_sha + '?recursive=1'), progress.tree_sha);
    progress.tree_comparison = compareContributionTrees(before, after, progress.files, spec.files);
    progress.commit_verified = true;
    progress.stage = 'readback';
    progress.readback_ref = progress.commit_sha;
    const readBlob = typeof tools?.[bindings.fetch_blob] === 'function'
      ? blob_sha => call('fetch_blob', {repository_full_name, blob_sha}) : undefined;
    const reads = await Promise.allSettled(progress.files.map(async (file, index) => {
      const source = {...spec.files[index], expected_new_blob_sha: file.blob_sha};
      const data = await call('fetch_file', {repository_full_name, path: file.path,
        ref: progress.readback_ref, encoding: source.encoding});
      return resolveReadback(file, source, data, readBlob);
    }));
    progress.readback = reads.map((read, index) => read.status === 'fulfilled' ? read.value
      : {path: progress.files[index].path, matches: false, error: String(read.reason?.message ?? read.reason),
        ...(read.reason?.tool_error ? {tool_error: read.reason.tool_error} : {})});
    progress.readback_status = progress.readback.some(row => row.error_code === 'readback_content_unavailable')
      ? 'content_unavailable' : progress.readback.some(row => !row.matches) ? 'incomplete' : 'complete';
    await announce();
    if (progress.readback_status !== 'complete') {
      throw new Error('Prepared contribution source readback is incomplete; retain this commit without repeating publication');
    }
    if (!readOnly) {
      progress.stage = 'check_current_head';
      const current = await observe(progress.stage);
      requireContributionHead(current.pull_request, spec);
      if (current.ref_sha !== spec.expected_head_sha) throw new Error('The existing contribution branch moved');
      progress.stage = 'update_ref';
      progress.ref_update_state = 'unknown';
      progress.publication_status = 'unknown';
      progress.ref_update_request = {repository_full_name, branch_name: spec.branch_name,
        sha: progress.commit_sha, force: false};
      await announce();
      const updated = await call('update_ref', progress.ref_update_request);
      if (updated.success !== true) throw new Error('The ref writer did not confirm its update; reconcile before any continuation');
      progress.ref_update_state = 'confirmed';
      progress.publication_status = 'update_confirmed';
      await announce();
    }
    progress.stage = 'read_current_head';
    const current = await observe(progress.stage);
    progress.pull_request = current.pull_request;
    if (current.ref_sha === progress.commit_sha && current.pull_request.head_sha === progress.commit_sha) {
      progress.publication_status = 'updated';
      progress.ref_update_state = 'observed_updated';
      progress.status = 'contribution_branch_updated';
    } else if (readOnly && current.ref_sha === spec.expected_head_sha
        && current.pull_request.head_sha === spec.expected_head_sha) {
      progress.publication_status = 'previous_head_observed';
      progress.ref_update_state = 'observed_previous';
      progress.status = 'contribution_branch_not_updated';
    } else {
      progress.ref_update_state = 'not_converged';
      throw new Error('The current branch and PR do not both identify the prepared commit; retain the observations and do not repeat the write');
    }
    progress.stage = 'complete';
    await announce();
    return progress;
  } catch (error) {
    if (error.tool_error) progress.tool_error = error.tool_error;
    await announce();
    const failure = new GitHubPublishError(String(error.message ?? error), progress, error);
    if (error.tool_error) failure.tool_error = error.tool_error;
    failure.response = error.response ?? lastResponse;
    throw failure;
  }
}

/** Add one nonforce, sole-parent commit to the original open contribution PR. */
async function advanceGitHubContribution(tools, change, options = {}) {
  return contributionOperation(tools, change, options, false);
}

/** Read a retained contribution's source and current refs without any writes. */
async function reconcileGitHubContribution(tools, change, previousProgress, options = {}) {
  return contributionOperation(tools, change, options, true, previousProgress);
}


function validateContributionHeadTarget(input) {
  object(input, 'head observation target');
  const keys = ['repository_full_name', 'pull_request_repository_full_name',
    'pull_request_number', 'branch_name', 'base_branch',
    'expected_commit_sha', 'expected_base_sha'];
  for (const key of Object.keys(input)) {
    if (!keys.includes(key)) throw new TypeError('Unsupported head observation field: ' + key);
  }
  const result = {};
  for (const key of ['repository_full_name', 'pull_request_repository_full_name']) {
    const value = text(input[key], key);
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(value)
        || value.split('/').some(part => part === '.' || part === '..')) {
      throw new TypeError(key + ' must be owner/repository');
    }
    result[key] = value;
  }
  if (!Number.isSafeInteger(input.pull_request_number) || input.pull_request_number < 1) {
    throw new TypeError('pull_request_number must identify the existing pull request');
  }
  return {...result, pull_request_number: input.pull_request_number,
    branch_name: branch(input.branch_name, 'branch_name'),
    base_branch: branch(input.base_branch, 'base_branch'),
    expected_commit_sha: sha(input.expected_commit_sha, 'expected_commit_sha'),
    expected_base_sha: sha(input.expected_base_sha, 'expected_base_sha')};
}

/** Observe two current head resources; never verify source or repeat a write. */
async function observeGitHubContributionHead(tools, target, options = {}) {
  const progress = {operation: 'contribution_head_observation', status: 'incomplete',
    stage: 'validate', source_verification: 'not_performed',
    publication_verification: 'not_performed', snapshot: false, writes: 0,
    calls: {}, requests: {}, responses: {}, observations: {}, errors: {},
    expected_head_observed: null, heads_agree: null, base_changed: null,
    progress_callback_errors: []};
  let announce = async () => {};
  try {
    const spec = validateContributionHeadTarget(target);
    object(options, 'head observation options');
    for (const key of Object.keys(options)) {
      if (!['bindings', 'onProgress'].includes(key)) {
        throw new TypeError('Unsupported head observation option: ' + key);
      }
    }
    if (options.bindings !== undefined) {
      object(options.bindings, 'head observation bindings');
      for (const key of Object.keys(options.bindings)) {
        if (key !== 'fetch') throw new TypeError('Only the fetch binding is used for head observation');
      }
    }
    const binding = text(options.bindings?.fetch ?? 'mcp__codex_apps__github_fetch', 'fetch binding');
    if (typeof tools?.[binding] !== 'function') {
      throw new Error('Binding not present: ' + binding + '. Repeat discovery alongside independent work.');
    }
    if (options.onProgress !== undefined && typeof options.onProgress !== 'function') {
      throw new TypeError('onProgress must be a function');
    }
    progress.target = spec;
    announce = async () => {
      if (options.onProgress === undefined) return;
      try { await options.onProgress(JSON.parse(JSON.stringify(progress))); }
      catch (error) { progress.progress_callback_errors.push(String(error.message ?? error)); }
    };
    progress.requests.pull_request = {url: 'https://api.github.com/repos/'
      + spec.pull_request_repository_full_name + '/pulls/' + spec.pull_request_number};
    progress.requests.branch_ref = {url: 'https://api.github.com/repos/'
      + spec.repository_full_name + '/git/ref/heads/'
      + spec.branch_name.split('/').map(encodeURIComponent).join('/')};
    progress.stage = 'read_current_head';
    await announce();
    const names = ['pull_request', 'branch_ref'];
    const outcomes = await Promise.allSettled(names.map(async name => {
      progress.calls.fetch = (progress.calls.fetch ?? 0) + 1;
      const response = await tools[binding](progress.requests[name]);
      progress.responses[name] = response;
      const payload = unpack(response, 'fetch');
      const data = typeof payload.content === 'string'
        ? object(JSON.parse(payload.content), 'GitHub resource') : object(payload, 'GitHub resource');
      if (name === 'pull_request') return contributionPR(data, spec);
      if (data.ref !== 'refs/heads/' + spec.branch_name || data.object?.type !== 'commit') {
        throw new Error('The reference response does not identify the requested branch');
      }
      return {ref: data.ref, type: 'commit', sha: sha(data.object.sha, 'Contribution branch ref')};
    }));
    for (let index = 0; index < outcomes.length; index++) {
      const name = names[index], outcome = outcomes[index];
      if (outcome.status === 'fulfilled') {
        progress.observations[name] = outcome.value;
      } else {
        const error = outcome.reason;
        progress.errors[name] = {message: String(error?.message ?? error),
          ...(error?.tool_error ? {tool_error: error.tool_error} : {})};
      }
    }
    if (progress.observations.pull_request) {
      progress.base_changed = progress.observations.pull_request.base_sha !== spec.expected_base_sha;
    }
    if (Object.keys(progress.errors).length === 0) {
      const pr = progress.observations.pull_request;
      const ref = progress.observations.branch_ref;
      progress.heads_agree = pr.head_sha === ref.sha;
      progress.expected_head_observed = pr.head_sha === spec.expected_commit_sha
        && ref.sha === spec.expected_commit_sha;
      progress.status = progress.expected_head_observed ? 'expected_head_observed' : 'not_converged';
    }
    progress.stage = 'complete';
    await announce();
    return progress;
  } catch (error) {
    progress.error = String(error.message ?? error);
    await announce();
    throw new GitHubPublishError(progress.error, progress, error);
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {GitHubPublishError, publishGitHubChange, continueGitHubMerge,
    advanceGitHubContribution, reconcileGitHubContribution, observeGitHubContributionHead,
    inspectReadback, resolveReadback, inspectToolError};
}
