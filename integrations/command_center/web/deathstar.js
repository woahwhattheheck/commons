'use strict';
(() => {
  const root = document.querySelector('#view-focus .main-column');
  if (!root) return;
  const card = document.createElement('article'); card.className = 'panel'; card.id = 'deathstar-summary';
  const heading = document.createElement('h2'); heading.textContent = 'Deathstar · operation pulse';
  const status = document.createElement('p'); status.className = 'field-help'; status.setAttribute('role', 'status');
  const body = document.createElement('div');
  const button = document.createElement('button'); button.type = 'button'; button.className = 'text-button'; button.textContent = 'Refresh shared view';
  card.append(heading, status, body, button); root.prepend(card);
  let busy = false, timer;
  const line = (title, detail) => {
    const row = document.createElement('p'); row.className = 'work-next';
    const label = document.createElement('strong'); label.textContent = title + ' ';
    row.append(label, document.createTextNode(detail)); return row;
  };
  async function refresh() {
    if (busy || document.visibilityState === 'hidden') return;
    busy = true; button.disabled = true;
    const abort = new AbortController(), timeout = setTimeout(() => abort.abort(), 10000);
    try {
      const response = await fetch('/api/summary', {signal: abort.signal});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const s = await response.json(), w = s.work, src = s.sources;
      const nextBody = document.createElement('div');
      nextBody.append(line('Work:', w.open.fresh + ' current open; ' + (w.open.retained + w.open.stale + w.open.unknown) + ' retained / stale / unknown.'));
      nextBody.append(line('Coverage:', src.fresh + ' fresh sources of ' + src.total + '; ' + src.coverage_debt_count + ' with coverage to resolve.'));
      nextBody.append(line('Observed merges:', s.throughput.merged_prs['1h'] + ' in 1h; ' + s.throughput.merged_prs['24h'] + ' in 24h. Lower bounds, not complete provider totals.'));
      nextBody.append(line('Workers:', s.workers.explicit_heartbeats ? Object.entries(s.workers.liveness).map(([k,v]) => k + ': ' + v).join(' · ') : 'No explicit heartbeat coverage in this snapshot.'));
      const amounts = s.revenue.observed_amounts || [];
      nextBody.append(line('Money:', amounts.length ? amounts.map(v => v.currency + ' ' + v.amount + ' ' + v.status.replaceAll('_',' ')).join(' · ') : 'No typed payment records loaded. Quoted prices are not counted as cash.'));
      const budget = s.refresh.request_budget || {};
      nextBody.append(line('Provider traffic:', (budget.observed_attempts ?? 'Unknown') + ' observed attempts; ' + (budget.deferred_reads ?? 'unknown') + ' deferred reads in the last collector run.'));
      for (const scope of (budget.scopes || []).filter(v => v.retry_remaining_seconds > 0).slice(0, 4))
        nextBody.append(line(scope.scope + ':', 'Cooldown until ' + scope.retry_not_before + '. Other work can continue.'));
      const rows = s.work.top_attention || [];
      for (const row of rows.slice(0, 4))
        nextBody.append(line(row.title || row.id, row.freshness + ' · ' + row.status + ' · ' + (row.next_action || 'No next action recorded')));
      body.replaceChildren(...nextBody.children);
      status.textContent = 'Shared snapshot ' + new Date(s.generated_at).toLocaleTimeString() + ' · no provider requests for this view · ' + (s.cache.hit ? 'cache hit' : s.telemetry.projection_ms + 'ms projection');
    } catch (error) {
      status.textContent = 'Shared view unavailable (' + error.message + '). Prior displayed observations are retained.';
    } finally {
      clearTimeout(timeout); busy = false; button.disabled = false;
      clearTimeout(timer); timer = setTimeout(refresh, 30000);
    }
  }
  button.addEventListener('click', refresh);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState !== 'hidden') refresh(); });
  refresh();
})();
