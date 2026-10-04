'use strict';

// Caller supplies the already-discovered native bindings and authorized change.
// No filesystem, network client, credential lookup, ref update, or write retry.
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

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {GitHubPublishError, publishGitHubChange, continueGitHubMerge,
    inspectReadback, resolveReadback, inspectToolError};
}
