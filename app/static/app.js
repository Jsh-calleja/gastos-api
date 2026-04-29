const apiBase = '';

function showResult(elId, data) {
  document.getElementById(elId).textContent = JSON.stringify(data, null, 2);
}

async function getJson(path) {
  const res = await fetch(apiBase + path);
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { status: res.status, text }; }
}

async function postJson(path, body) {
  const res = await fetch(apiBase + path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { status: res.status, text }; }
}

/* Populate selects */
async function loadCategories() {
  const data = await getJson('/categories/');
  const sel = document.getElementById('category-select');
  sel.innerHTML = '<option value="">— select category —</option>';
  if (Array.isArray(data)) {
    data.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = `${c.id} — ${c.name} (${c.type})`;
      sel.appendChild(opt);
    });
  } else {
    // show error in console and keep default option
    console.error('Failed to load categories', data);
  }
}

async function loadAccounts() {
  const data = await getJson('/accounts/');
  const sel = document.getElementById('account-select');
  sel.innerHTML = '<option value="">— select account —</option>';
  if (Array.isArray(data)) {
    data.forEach(a => {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = `${a.id} — ${a.name} (balance: ${a.balance})`;
      sel.appendChild(opt);
    });
  } else {
    console.error('Failed to load accounts', data);
  }
}

/* Initialize selects on page load */
async function initLists() {
  await Promise.all([loadCategories(), loadAccounts()]);
}

/* Forms handlers */
document.getElementById('category-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = { name: fd.get('name'), type: fd.get('type') };
  const data = await postJson('/categories/', body);
  showResult('category-result', data);
  // refresh categories so new one appears in the transaction form
  await loadCategories();
  // reset form
  e.target.reset();
});

document.getElementById('account-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = { name: fd.get('name'), balance: parseFloat(fd.get('balance')) };
  const data = await postJson('/accounts/', body);
  showResult('account-result', data);
  await loadAccounts();
  e.target.reset();
});

document.getElementById('transaction-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    type: fd.get('type'),
    date: fd.get('date'),
    amount: parseFloat(fd.get('amount')),
    category_id: Number(fd.get('category_id')),
    account_id: Number(fd.get('account_id')),
  };
  const data = await postJson('/transactions/', body);
  showResult('transaction-result', data);
  e.target.reset();
});

document.getElementById('run-report').addEventListener('click', async () => {
  const res = await fetch('/transactions/reports/avg-salary-per-month');
  const data = await res.json();
  showResult('report-result', data);
});

/* Run initialization */
initLists().catch(err => {
  console.error('Failed to initialize lists', err);
});
