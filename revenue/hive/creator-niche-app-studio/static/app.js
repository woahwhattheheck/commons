'use strict';

const state = { csrf: null, workspaceRevision: null, planRevision: null, planId: null };
const $ = (selector) => document.querySelector(selector);
const rows = $('#item-rows');

function requestKey(prefix) {
  return `${prefix}-${Date.now()}-${crypto.getRandomValues(new Uint32Array(1))[0]}`;
}

function toast(message, error = false) {
  const node = $('#toast');
  node.textContent = message;
  node.className = error ? 'show error' : 'show';
  window.setTimeout(() => { node.className = ''; }, 3200);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) {
    headers['Content-Type'] = 'application/json';
    headers['X-CSRF-Token'] = state.csrf;
  }
  const response = await fetch(path, { ...options, headers });
  const type = response.headers.get('content-type') || '';
  if (!response.ok) {
    const data = type.includes('json') ? await response.json() : { message: await response.text() };
    throw new Error(`${data.error || response.status}: ${data.message || 'request failed'}`);
  }
  return type.includes('json') ? response.json() : response;
}

function itemRow(seed = {}) {
  const tr = document.createElement('tr');
  const mode = seed.mode || 'PER_ATTENDEE_CONSUMABLE';
  tr.innerHTML = `
    <td><input class="name" value="${seed.name || ''}" required><input class="item-id" value="${seed.item_id || ''}" hidden></td>
    <td><select class="mode"><option value="PER_ATTENDEE_CONSUMABLE">Per-attendee consumable</option><option value="SHARED_REUSABLE">Shared/reusable</option></select></td>
    <td><input class="on-hand" type="number" min="0" value="${seed.on_hand_units ?? 0}" required></td>
    <td><input class="reserve" type="number" min="0" value="${seed.reserve_units ?? 0}" required></td>
    <td><input class="pack" type="number" min="1" value="${seed.units_per_pack ?? 1}" required></td>
    <td><input class="target" type="number" min="1" value="${seed.per_attendee_per_session ?? seed.shared_target_units ?? 1}" required><div class="mode-help"></div></td>
    <td><input class="cost" type="number" min="0" value="${seed.estimated_pack_cost_cents ?? ''}" placeholder="optional"></td>`;
  tr.querySelector('.mode').value = mode;
  const sync = () => { tr.querySelector('.mode-help').textContent = tr.querySelector('.mode').value === 'PER_ATTENDEE_CONSUMABLE' ? 'units / attendee / session' : 'fixed shared target'; };
  tr.querySelector('.mode').addEventListener('change', sync);
  sync();
  rows.appendChild(tr);
}

function seedRows() {
  itemRow({ item_id:'clay-lumps', name:'Prepared clay lumps', mode:'PER_ATTENDEE_CONSUMABLE', on_hand_units:30, reserve_units:8, units_per_pack:25, estimated_pack_cost_cents:4200, per_attendee_per_session:1 });
  itemRow({ item_id:'brushes', name:'Glaze brushes', mode:'SHARED_REUSABLE', on_hand_units:12, reserve_units:2, units_per_pack:6, estimated_pack_cost_cents:1800, shared_target_units:18 });
  itemRow({ item_id:'ribs', name:'Pottery ribs', mode:'SHARED_REUSABLE', on_hand_units:16, reserve_units:2, units_per_pack:8, estimated_pack_cost_cents:2400, shared_target_units:20 });
}

function slug(value) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || `item-${rows.children.length + 1}`;
}

function planFromForm(form) {
  const data = new FormData(form);
  const items = [...rows.querySelectorAll('tr')].map((tr, index) => {
    const name = tr.querySelector('.name').value.trim();
    const mode = tr.querySelector('.mode').value;
    const row = {
      item_id: tr.querySelector('.item-id').value || `${slug(name)}-${index + 1}`,
      name,
      mode,
      unit_label: 'units',
      on_hand_units: Number(tr.querySelector('.on-hand').value),
      reserve_units: Number(tr.querySelector('.reserve').value),
      units_per_pack: Number(tr.querySelector('.pack').value),
      estimated_pack_cost_cents: tr.querySelector('.cost').value === '' ? null : Number(tr.querySelector('.cost').value)
    };
    if (mode === 'PER_ATTENDEE_CONSUMABLE') row.per_attendee_per_session = Number(tr.querySelector('.target').value);
    else row.shared_target_units = Number(tr.querySelector('.target').value);
    return row;
  });
  return {
    plan_id: data.get('plan_id'), title: data.get('title'), sessions: Number(data.get('sessions')),
    rostered_count: Number(data.get('rostered_count')), expected_attendees: Number(data.get('expected_attendees')), items
  };
}

function renderPlan(saved) {
  const d = saved.derived;
  const body = d.items.map(item => `<tr><td>${escapeHtml(item.name)}</td><td>${item.mode === 'PER_ATTENDEE_CONSUMABLE' ? 'Consumable' : 'Shared'}</td><td>${item.operational_required_units}</td><td>${item.rostered_reference_units}</td><td>${item.packs_to_acquire}</td><td>${item.projected_remaining_units}</td></tr>`).join('');
  const result = $('#result');
  result.innerHTML = `<strong>Revision ${saved.revision}</strong> · expected ${d.expected_attendees} of ${d.rostered_count} rostered · ${d.sessions} sessions
    <table><thead><tr><th>Supply</th><th>Mode</th><th>Operational</th><th>Roster reference</th><th>Packs</th><th>Remaining</th></tr></thead><tbody>${body}</tbody></table>`;
  result.hidden = false;
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = String(value);
  return div.innerHTML;
}

$('#workspace-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const data = new FormData(event.currentTarget);
    const config = Object.fromEntries(data.entries());
    const result = await api('/api/workspace', { method:'POST', body:JSON.stringify({ config, request_key:requestKey('workspace'), expected_revision:state.workspaceRevision }) });
    state.workspaceRevision = result.revision;
    document.documentElement.style.setProperty('--accent', result.config.accent_color);
    $('#brand-title').textContent = result.config.brand_name;
    $('#brand-tagline').textContent = result.config.tagline;
    $('#workspace-state').textContent = `Saved · revision ${result.revision}`;
    $('#workspace-state').className = 'badge ok';
    toast('Brand saved locally');
  } catch (error) { toast(error.message, true); }
});

$('#plan-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const plan = planFromForm(event.currentTarget);
    const result = await api('/api/plans', { method:'POST', body:JSON.stringify({ plan, request_key:requestKey('plan'), expected_revision:state.planId === plan.plan_id ? state.planRevision : null }) });
    state.planId = plan.plan_id;
    state.planRevision = result.plan.revision;
    $('#plan-state').textContent = `Saved · revision ${state.planRevision}`;
    $('#plan-state').className = 'badge ok';
    renderPlan(result.plan);
    toast('Plan saved and recalculated');
  } catch (error) { toast(error.message, true); }
});

$('#add-consumable').addEventListener('click', () => itemRow({ mode:'PER_ATTENDEE_CONSUMABLE' }));
$('#add-shared').addEventListener('click', () => itemRow({ mode:'SHARED_REUSABLE' }));

$('#download').addEventListener('click', async () => {
  if (!state.planId) return toast('Save a plan first', true);
  try {
    const response = await fetch(`/api/plans/${encodeURIComponent(state.planId)}/export`);
    if (!response.ok) throw new Error('Export failed');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `${state.planId}-supply-plan.zip`; link.click();
    URL.revokeObjectURL(url);
    toast('Deterministic ZIP downloaded');
  } catch (error) { toast(error.message, true); }
});

$('#support').addEventListener('click', async () => {
  try {
    const result = await api('/api/support', { method:'POST', body:JSON.stringify({ request_key:requestKey('support'), support:{ plan_id:state.planId, category:'LAUNCH_REVIEW', description:'Please review this plan before creator handoff.', contact_preference:'LOCAL_OWNER_REVIEW' } }) });
    $('#handoff-output').textContent = JSON.stringify(result.packet, null, 2);
    toast('Local support handoff drafted; nothing was sent');
  } catch (error) { toast(error.message, true); }
});

async function boot() {
  seedRows();
  try {
    const data = await api('/api/bootstrap');
    state.csrf = data.csrf_token;
    if (data.workspace) {
      state.workspaceRevision = data.workspace.revision;
      document.documentElement.style.setProperty('--accent', data.workspace.config.accent_color);
      $('#brand-title').textContent = data.workspace.config.brand_name;
      $('#brand-tagline').textContent = data.workspace.config.tagline;
      $('#workspace-state').textContent = `Saved · revision ${data.workspace.revision}`;
      $('#workspace-state').className = 'badge ok';
    }
    if (data.plans.length) {
      const latest = data.plans[0]; state.planId = latest.plan_id; state.planRevision = latest.revision; renderPlan(latest);
      $('#plan-state').textContent = `Saved · revision ${latest.revision}`; $('#plan-state').className = 'badge ok';
    }
  } catch (error) { toast(error.message, true); }
}

boot();
