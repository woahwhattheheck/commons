(() => {
  'use strict';

  const STORAGE_KEY = 'creator-desk.operator.v1';
  const originalFetch = window.fetch.bind(window);
  let operatorKey = '';
  let lockPanel = null;

  function readKey() {
    if (operatorKey) return operatorKey;
    try { operatorKey = localStorage.getItem(STORAGE_KEY) || ''; } catch (_) {}
    return operatorKey;
  }

  function saveKey(value) {
    operatorKey = value;
    try { localStorage.setItem(STORAGE_KEY, value); } catch (_) {}
  }

  function clearKey() {
    operatorKey = '';
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
  }

  function withAuth(init = {}) {
    const key = readKey();
    if (!key) return init;
    const next = {...init};
    const headers = new Headers(init.headers || {});
    headers.set('Authorization', 'Bearer ' + key);
    next.headers = headers;
    return next;
  }

  function protectedPath(path) {
    return path === '/api/operator' || path === '/api/dashboard' ||
      path === '/workspace.sqlite3' || path.startsWith('/draft.eml') || path === '/api/change';
  }

  window.fetch = async function(input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const local = url.startsWith('/') || url.startsWith(location.origin + '/');
    const response = await originalFetch(input, local ? withAuth(init || {}) : init);
    if (local && protectedPath(new URL(url, location.href).pathname) && response.status === 403 && readKey()) {
      clearKey();
      setLocked(true, 'Operator key was rejected. Paste the current key to restore creator controls.');
    }
    return response;
  };

  function setWorkspaceTab() {
    document.querySelectorAll('.tab').forEach(node => { node.hidden = node.id !== 'creator'; });
    document.querySelectorAll('[data-tab]').forEach(node => {
      node.setAttribute('aria-selected', String(node.dataset.tab === 'creator'));
    });
  }

  function creatorChildren() {
    const creator = document.getElementById('creator');
    if (!creator) return [];
    return Array.from(creator.children).filter(node => node !== lockPanel);
  }

  function setLocked(locked, message = '') {
    if (!lockPanel) return;
    creatorChildren().forEach(node => { node.hidden = locked; });
    lockPanel.hidden = !locked;
    const status = lockPanel.querySelector('[data-operator-status]');
    if (status) status.textContent = message;
  }

  async function verify(candidate) {
    const response = await originalFetch('/api/operator', {
      headers: {'Authorization': 'Bearer ' + candidate}
    });
    if (!response.ok) return false;
    const body = await response.json();
    return body.operator === true;
  }

  async function unlock(candidate, button) {
    button.disabled = true;
    try {
      if (!await verify(candidate)) {
        setLocked(true, 'That operator key was not accepted.');
        return false;
      }
      saveKey(candidate);
      setLocked(false);
      const refresh = document.getElementById('refresh');
      if (refresh) refresh.click();
      return true;
    } finally {
      button.disabled = false;
    }
  }

  function makeLockPanel() {
    const card = document.createElement('section');
    card.className = 'card';
    card.id = 'operator-lock';
    const title = document.createElement('h2');
    title.textContent = 'Unlock creator controls';
    const copy = document.createElement('p');
    copy.className = 'muted';
    copy.textContent = 'Members can use the library and their own delivery preferences without this key. Resource authoring, operator data, draft export, inquiry resolution, and workspace backup require the private operator key.';
    const label = document.createElement('label');
    label.htmlFor = 'operator-key';
    label.textContent = 'Operator key';
    const input = document.createElement('input');
    input.id = 'operator-key';
    input.type = 'password';
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.maxLength = 256;
    const actions = document.createElement('div');
    actions.className = 'form-actions';
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Unlock creator workspace';
    button.addEventListener('click', async () => {
      await unlock(input.value, button);
      if (readKey()) input.value = '';
    });
    const status = document.createElement('p');
    status.className = 'muted';
    status.dataset.operatorStatus = '';
    actions.append(button);
    card.append(title, copy, label, input, actions, status);
    return card;
  }

  async function downloadProtected(anchor) {
    const response = await window.fetch(anchor.href);
    if (!response.ok) {
      let message = 'Protected download failed.';
      try { message = (await response.json()).error || message; } catch (_) {}
      throw new Error(message);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const disposition = response.headers.get('Content-Disposition') || '';
    const quoted = disposition.match(/filename="([^"]+)"/);
    link.download = anchor.getAttribute('download') || (quoted ? quoted[1] : 'creator-desk-download');
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  document.addEventListener('click', event => {
    const tab = event.target.closest && event.target.closest('[data-tab="creator"]');
    if (tab && !readKey()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      setWorkspaceTab();
      setLocked(true, 'Paste the operator key returned by operator_auth.py init or rotate.');
      const input = document.getElementById('operator-key');
      if (input) input.focus();
      return;
    }
    const anchor = event.target.closest && event.target.closest('a[href]');
    if (!anchor) return;
    const url = new URL(anchor.href, location.href);
    if (url.origin !== location.origin || !(url.pathname === '/workspace.sqlite3' || url.pathname === '/draft.eml')) return;
    event.preventDefault();
    if (!readKey()) {
      setWorkspaceTab();
      setLocked(true, 'Unlock creator controls before downloading operator data.');
      return;
    }
    downloadProtected(anchor).catch(error => {
      const status = document.getElementById('status');
      if (status) { status.textContent = error.message; status.className = 'status error'; }
    });
  }, true);

  document.addEventListener('DOMContentLoaded', async () => {
    const creator = document.getElementById('creator');
    if (!creator) return;
    lockPanel = makeLockPanel();
    creator.prepend(lockPanel);

    const header = creator.querySelector('.intro');
    if (header) {
      const lock = document.createElement('button');
      lock.type = 'button';
      lock.className = 'secondary';
      lock.textContent = 'Lock creator controls';
      lock.addEventListener('click', () => {
        clearKey();
        setLocked(true, 'Creator controls are locked on this browser.');
      });
      header.append(lock);
    }

    const key = readKey();
    if (!key) {
      setLocked(true);
      return;
    }
    if (await verify(key)) {
      setLocked(false);
    } else {
      clearKey();
      setLocked(true, 'Stored operator key is no longer valid.');
    }
  });
})();
