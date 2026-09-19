(() => {
  'use strict';
  const model = JSON.parse(document.getElementById('comparison-data').textContent);
  const groups = ['ESS', 'RIS', 'IAM'];
  const roles = [['support_ids', 'Support'], ['dissent_ids', 'Dissent'], ['limitation_ids', 'Limitations'], ['mechanism_source_ids', 'Mechanism support']];
  const $ = id => document.getElementById(id);
  const node = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined && text !== null) item.textContent = String(text);
    if (className) item.className = className;
    return item;
  };
  const readable = value => value.replaceAll('_', ' ');
  const selectedGroups = () => [...document.querySelectorAll('input[name=group]:checked')].map(input => input.value);
  function lensMatch(finding) {
    const lens = $('lens').value;
    if (lens === 'all') return true;
    if (lens === 'shared_gap' || lens === 'local_gap') return finding.state === 'gap' && finding.topology === lens.split('_')[0];
    return finding.state === lens;
  }
  function visibleRows() {
    const chosen = selectedGroups();
    const query = $('query').value.trim().toLocaleLowerCase('en');
    return model.rows.filter(row => {
      if ($('dimension').value !== 'all' && row.dimension !== $('dimension').value) return false;
      const findings = row.findings.filter(finding => chosen.includes(finding.group));
      if (!chosen.length || ($('lens').value !== 'all' && !findings.some(lensMatch))) return false;
      const evidence = findings.flatMap(finding => roles.flatMap(([role]) => finding[role].map(id => model.sources[id])));
      return !query || JSON.stringify([row.practice_key, row.dimension, row.window_start, row.window_end, findings, evidence]).toLocaleLowerCase('en').includes(query);
    });
  }
  function addEvidence(parent, finding) {
    const count = new Set(roles.flatMap(([role]) => finding[role])).size;
    const details = node('details'); details.append(node('summary', `Evidence: ${count} distinct source ID${count === 1 ? '' : 's'}`));
    for (const [role, label] of roles) {
      if (!finding[role].length) continue;
      const section = node('div', null, `evidence ${role === 'dissent_ids' ? 'dissent' : ''}`);
      section.append(node('h3', label));
      for (const id of finding[role]) {
        const source = model.sources[id];
        section.append(node('p', `${id} · ${source.evidence_kind} · version ${source.version}`, 'record-id'));
        section.append(node('blockquote', source.excerpt));
        section.append(node('p', `Locator: ${source.locator}`));
        section.append(node('p', `Declared origin: ${source.origin_id || 'not supplied'}`));
        let url;
        try { url = new URL(source.source_ref); } catch (_) { url = null; }
        if (url && ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) {
          const link = node('a', source.source_ref); link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; section.append(link);
        } else section.append(node('p', source.source_ref, 'record-id'));
      }
      details.append(section);
    }
    if (!count) details.append(node('p', 'No evidence reference supplied for this record. This is not evidence that the practice is absent.'));
    parent.append(details);
  }
  function findingCard(finding) {
    const card = node('article', null, 'finding'); card.dataset.finding = finding.finding_id;
    const tags = node('div', null, 'tags');
    tags.append(node('span', readable(finding.state).toUpperCase(), `tag state-${finding.state}`));
    tags.append(node('span', `Basis: ${finding.basis}`, 'tag'));
    tags.append(node('span', `Topology: ${finding.topology}`, 'tag'));
    card.append(tags, node('p', `${finding.finding_id} · ${finding.service_id}`, 'record-id'), node('p', finding.statement), node('p', finding.context, 'context'));
    card.append(node('p', `Dependency: ${finding.dependency_id || 'not supplied'} · Mechanism: ${finding.mechanism_id || 'not supplied'} (${finding.mechanism_basis || 'not supplied'})`, 'record-id'));
    if (finding.rationale) card.append(node('p', finding.rationale, 'rationale'));
    addEvidence(card, finding); return card;
  }
  function render() {
    const chosen = selectedGroups(), rows = visibleRows();
    $('head').replaceChildren(); $('body').replaceChildren();
    const head = node('tr'); head.append(node('th', 'PRACTICE / WINDOW'));
    for (const group of chosen) { const th = node('th', group); th.scope = 'col'; head.append(th); }
    $('head').append(head);
    for (const row of rows) {
      const tr = node('tr'); tr.dataset.practice = row.practice_key;
      const heading = node('th'); heading.scope = 'row';
      heading.append(node('h2', row.practice_key.replaceAll('-', ' ')), node('p', `${row.dimension} · ${row.window_start} → ${row.window_end}`));
      const findings = row.findings.filter(finding => chosen.includes(finding.group));
      const support = new Set(findings.flatMap(finding => finding.support_ids));
      const all = new Set(findings.flatMap(finding => roles.flatMap(([role]) => finding[role])));
      heading.append(node('p', `${findings.length} supplied records · ${support.size} distinct support source IDs · ${all.size} source IDs across all evidence roles`));
      heading.append(node('p', 'Distinct source IDs are not proof of independent corroboration.'));
      tr.append(heading);
      for (const group of chosen) {
        const cell = node('td'); cell.dataset.group = group;
        const items = row.findings.filter(finding => finding.group === group);
        if (!items.length) cell.append(node('p', 'NOT SUPPLIED — no record for this group and exact window. Not a finding of absence.', 'missing'));
        for (const finding of items) cell.append(findingCard(finding));
        tr.append(cell);
      }
      $('body').append(tr);
    }
    const count = rows.reduce((sum, row) => sum + row.findings.filter(finding => chosen.includes(finding.group)).length, 0);
    $('counts').textContent = `${rows.length} of ${model.rows.length} comparison rows · ${count} supplied records · ${chosen.length} visible groups`;
    $('empty').hidden = rows.length !== 0;
    $('csv').disabled = rows.length === 0;
    $('expand').textContent = 'Expand evidence';
  }
  function cell(value) {
    let result = String(value ?? '');
    if (/^[\t\r\n]/.test(result) || /^\s*[=+@-]/u.test(result)) result = "'" + result;
    return '"' + result.replaceAll('"', '""') + '"';
  }
  function csv() {
    const lines = [model.columns.map(cell).join(',')];
    for (const row of visibleRows()) for (const group of selectedGroups()) {
      const items = row.findings.filter(finding => finding.group === group);
      for (const finding of items.length ? items : [{state:'NOT_SUPPLIED', rationale:'No record supplied; not a finding of absence.'}]) {
        const record = {...finding, dataset_id:model.dataset_id, data_status:model.data_status, input_sha256:model.input_sha256,
          dimension:row.dimension, practice_key:row.practice_key, window_start:row.window_start, window_end:row.window_end, group};
        roles.forEach(([role], index) => { record[model.columns[model.columns.length - 4 + index]] = JSON.stringify((finding[role] || []).map(id => model.sources[id])); });
        lines.push(model.columns.map(column => cell(record[column])).join(','));
      }
    }
    return lines.join('\n') + '\n';
  }
  function download(data, name, type) {
    const url = URL.createObjectURL(new Blob([data], {type}));
    const link = node('a'); link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('provenance').textContent = model.data_status === 'synthetic' ? 'SYNTHETIC EXAMPLE — NOT UNIVERSITY FINDINGS' : `SUPPLIED PROVENANCE: ${model.data_status}`;
  $('dataset').textContent = model.dataset_id; $('source-hash').textContent = model.input_sha256;
  ['dimension', 'lens'].forEach(id => $(id).addEventListener('change', render));
  $('query').addEventListener('input', render);
  document.querySelectorAll('input[name=group]').forEach(input => input.addEventListener('change', render));
  $('reset').addEventListener('click', () => {
    $('dimension').value = 'all'; $('lens').value = 'all'; $('query').value = '';
    document.querySelectorAll('input[name=group]').forEach(input => { input.checked = true; }); render();
  });
  $('expand').addEventListener('click', () => {
    const details = [...document.querySelectorAll('tbody details')]; const open = details.some(item => !item.open);
    details.forEach(item => { item.open = open; }); $('expand').textContent = open ? 'Collapse evidence' : 'Expand evidence';
  });
  $('csv').addEventListener('click', () => download(csv(), 'comparison-visible.csv', 'text/csv;charset=utf-8'));
  $('json').addEventListener('click', () => download(Uint8Array.from(atob(model.original_base64), char => char.charCodeAt(0)), 'assessment-original.json', 'application/json'));
  render();
})();
