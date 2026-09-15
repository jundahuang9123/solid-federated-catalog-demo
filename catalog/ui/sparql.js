const editor = document.querySelector('#query');
const examples = document.querySelector('#examples');
const run = document.querySelector('#run');
const message = document.querySelector('#message');
const results = document.querySelector('#results');
try {
  const response = await fetch('/queries.json');
  if (!response.ok) throw new Error('Examples unavailable');
  const queries = await response.json();
  for (const name of Object.keys(queries)) {
    const option = document.createElement('option');
    option.textContent = name;
    examples.append(option);
  }
  const choose = () => { editor.value = queries[examples.value]; };
  examples.addEventListener('change', choose);
  choose();
} catch (error) { message.textContent = error.message; }
run.addEventListener('click', async () => {
  run.disabled = true;
  results.replaceChildren();
  message.textContent = 'Running query…';
  const started = performance.now();
  try {
    const response = await fetch('/sparql', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: editor.value})
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `Query failed (${response.status})`);
    if ('boolean' in payload) {
      results.textContent = payload.boolean ? 'True — a match exists.' : 'False — no match.';
    } else {
      const table = document.createElement('table');
      const head = table.createTHead().insertRow();
      for (const variable of payload.head.vars) {
        const th = document.createElement('th'); th.textContent = variable; head.append(th);
      }
      const body = table.createTBody();
      for (const binding of payload.results.bindings) {
        const row = body.insertRow();
        for (const variable of payload.head.vars) {
          const term = binding[variable];
          const cell = row.insertCell();
          cell.textContent = term ? term.value : '—';
          if (term) cell.title = [term.type, term.datatype, term['xml:lang']].filter(Boolean).join(' · ');
        }
      }
      results.append(table);
      const count = document.createElement('p');
      count.textContent = `${payload.results.bindings.length} row(s). The server applies a result limit.`;
      results.append(count);
    }
    message.textContent = `Completed in ${((performance.now() - started)/1000).toFixed(2)} seconds.`;
  } catch (error) { message.textContent = error.message; }
  finally { run.disabled = false; }
});
