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
/* ---------- Toolbar behavior ---------- */

function setBulkDeleteEnabled(enabled) {
  document.getElementById('btn-bulk-delete').disabled = !enabled;
}

function getSelectedTransactionIds() {
  return Array.from(document.querySelectorAll('#transactions-table tbody input[type="checkbox"]:checked'))
    .map(cb => Number(cb.dataset.id));
}

/* Render transactions rows with selection checkbox */
function renderTransactions(items) {
  const tbody = document.querySelector('#transactions-table tbody');
  tbody.innerHTML = '';
  items.forEach(tx => {
    const tr = document.createElement('tr');
    tr.dataset.id = tx.id;
    tr.innerHTML = `
      <td><input type="checkbox" data-id="${tx.id}" class="tx-select" /></td>
      <td>${tx.id}</td>
      <td>${tx.date}</td>
      <td>${tx.type}</td>
      <td>${tx.amount}</td>
      <td>${tx.category_id ?? ''}</td>
      <td>${tx.account_id ?? ''}</td>
      <td>
        <button data-action="edit" data-id="${tx.id}">Edit</button>
        <button data-action="delete" data-id="${tx.id}">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
  // wire selection change
  document.querySelectorAll('.tx-select').forEach(cb => {
    cb.addEventListener('change', () => {
      const any = document.querySelectorAll('#transactions-table tbody input[type="checkbox"]:checked').length > 0;
      setBulkDeleteEnabled(any);
      // highlight row
      const row = cb.closest('tr');
      if (cb.checked) row.classList.add('selected'); else row.classList.remove('selected');
    });
  });
  // reset select-all
  document.getElementById('select-all').checked = false;
  setBulkDeleteEnabled(false);
}

/* Select all checkbox */
document.getElementById('select-all').addEventListener('change', (e) => {
  const checked = e.target.checked;
  document.querySelectorAll('#transactions-table tbody input[type="checkbox"]').forEach(cb => {
    cb.checked = checked;
    const row = cb.closest('tr');
    if (checked) row.classList.add('selected'); else row.classList.remove('selected');
  });
  setBulkDeleteEnabled(checked);
});

/* Bulk delete */
document.getElementById('btn-bulk-delete').addEventListener('click', async () => {
  const ids = getSelectedTransactionIds();
  if (!ids.length) return;
  if (!confirm(`Delete ${ids.length} transactions?`)) return;
  // delete sequentially (or implement batch endpoint)
  for (const id of ids) {
    await fetch(`/transactions/${id}`, { method: 'DELETE' });
  }
  await loadTransactions();
});

/* Refresh button */
document.getElementById('btn-refresh').addEventListener('click', async () => {
  await loadTransactions();
});

/* Toggle view (example toggles a CSS class on table card) */
let compactView = false;
document.getElementById('btn-toggle-view').addEventListener('click', () => {
  compactView = !compactView;
  document.getElementById('transactions-table').classList.toggle('compact', compactView);
});

/* Filter and sort */
document.getElementById('filter-type').addEventListener('change', async (e) => {
  await loadTransactions(); // load and apply filter in client
});
document.getElementById('sort-by').addEventListener('change', async (e) => {
  await loadTransactions();
});

/* Apply client-side filter/sort after fetching */
async function loadTransactions() {
  const data = await getJson('/transactions/');
  if (!Array.isArray(data)) return renderTransactions([]);
  // client-side filter
  const typeFilter = document.getElementById('filter-type').value;
  let items = data;
  if (typeFilter) items = items.filter(i => i.type === typeFilter);
  // client-side sort
  const sort = document.getElementById('sort-by').value;
  if (sort === 'date_desc') items.sort((a,b) => b.date.localeCompare(a.date));
  if (sort === 'date_asc') items.sort((a,b) => a.date.localeCompare(b.date));
  if (sort === 'amount_desc') items.sort((a,b) => b.amount - a.amount);
  if (sort === 'amount_asc') items.sort((a,b) => a.amount - b.amount);
  renderTransactions(items);
}

/* Quick new-item shortcuts */
document.getElementById('btn-new-category').addEventListener('click', () => {
  document.getElementById('category-form').scrollIntoView({behavior:'smooth'});
});
document.getElementById('btn-new-account').addEventListener('click', () => {
  document.getElementById('account-form').scrollIntoView({behavior:'smooth'});
});
document.getElementById('btn-new-transaction').addEventListener('click', () => {
  document.getElementById('transaction-form').scrollIntoView({behavior:'smooth'});
});

/* Wire initial load */
initLists().then(() => loadTransactions()).catch(console.error);
