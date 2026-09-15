async function refresh() {
  try {
    const response = await fetch('/ready');
    document.querySelector('#readiness').textContent = response.ok ? 'Ready to accept publications.' : 'Not ready. Check the dependencies below.';
    document.querySelector('#status').textContent = JSON.stringify(await response.json(), null, 2);
  } catch (error) { document.querySelector('#readiness').textContent = error.message; }
}
document.querySelector('#refresh').addEventListener('click', refresh);
refresh();
