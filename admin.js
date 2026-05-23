const API = '/admin/api';

const fmtMoney = (n) =>
    new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n || 0);

const fmtDate = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const STATUS_LABELS = {
    new: 'Новая',
    contacted: 'На связи',
    bought: 'Выкуплена',
    rejected: 'Отказ',
};

const CATEGORY_LABELS = {
    marketing: 'Реклама',
    salary: 'Зарплата',
    rent: 'Аренда',
    logistics: 'Логистика',
    other: 'Прочее',
};

function categoryLabel(cat) {
    return CATEGORY_LABELS[cat] || cat || '—';
}

function isoToDatetimeLocal(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function datetimeLocalToIso(value) {
    if (!value) return null;
    return new Date(value).toISOString();
}

function dateInputToIso(value) {
    if (!value) return null;
    return new Date(value + 'T12:00:00').toISOString();
}

/** Дата для API без сдвига часового пояса (YYYY-MM-DD) */
function dateForApi(value) {
    if (!value) return null;
    return String(value).trim().slice(0, 10);
}

function showFormError(message) {
    alert(message || 'Не удалось сохранить. Проверьте поля и попробуйте снова.');
}

function apiErrorMessage(err, data) {
    if (data?.detail) {
        return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
    return err?.message || 'Ошибка сервера';
}

function currentLocalMonth() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

function defaultExpenseDate() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const todayStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    if (todayStr.slice(0, 7) === currentMonth) return todayStr;
    return `${currentMonth}-01`;
}

let currentMonth = currentLocalMonth();
let currentTab = 'overview';
let leadsCache = [];
let expensesCache = [];
let expenseFormBound = false;

async function api(path, options = {}) {
    const res = await fetch(API + path, {
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options,
    });
    if (res.status === 401) {
        showLogin();
        throw new Error('unauthorized');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const err = new Error(apiErrorMessage(null, data));
        err.data = data;
        throw err;
    }
    return data;
}

function syncMonthFromDate(dateStr) {
    const month = (dateStr || '').slice(0, 7);
    if (!month || month.length < 7) return;
    currentMonth = month;
    document.getElementById('monthInput').value = month;
}

function showLogin() {
    document.getElementById('loginScreen').classList.remove('admin-hidden');
    document.getElementById('adminApp').classList.add('admin-hidden');
}

function showApp() {
    document.getElementById('loginScreen').classList.add('admin-hidden');
    document.getElementById('adminApp').classList.remove('admin-hidden');
}

async function checkAuth() {
    try {
        await api('/me');
        showApp();
        initApp();
    } catch {
        showLogin();
    }
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('loginError');
    errEl.textContent = '';
    const phrase = document.getElementById('phraseInput').value;
    try {
        const res = await fetch('/admin/login', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phrase }),
        });
        const data = await res.json();
        if (!res.ok) {
            errEl.textContent = data.detail || 'Неверная кодовая фраза';
            return;
        }
        showApp();
        initApp();
    } catch {
        errEl.textContent = 'Ошибка соединения';
    }
});

document.getElementById('logoutBtn').addEventListener('click', async () => {
    await fetch('/admin/logout', { method: 'POST', credentials: 'same-origin' });
    showLogin();
    document.getElementById('phraseInput').value = '';
});

function initApp() {
    const monthInput = document.getElementById('monthInput');
    monthInput.value = currentMonth;
    const expDateEl = document.getElementById('expDate');
    if (expDateEl) expDateEl.value = defaultExpenseDate();

    monthInput.addEventListener('change', () => {
        currentMonth = monthInput.value;
        refreshCurrentTab();
    });

    document.querySelectorAll('.admin-nav-btn[data-tab]').forEach((btn) => {
        btn.addEventListener('click', () => {
            currentTab = btn.dataset.tab;
            document.querySelectorAll('.admin-nav-btn').forEach((b) => b.classList.toggle('active', b === btn));
            document.querySelectorAll('.tab-panel').forEach((p) => p.classList.toggle('admin-hidden', p.dataset.tab !== currentTab));
            document.getElementById('pageTitle').textContent = btn.textContent.trim();
            refreshCurrentTab();
        });
    });
    document.querySelector('.admin-nav-btn[data-tab="overview"]').classList.add('active');
    refreshCurrentTab();
    bindLeadModal();
    bindExpenseForm();
    bindAddLeadForm();
    bindExpenseModal();
}

function refreshCurrentTab() {
    if (currentTab === 'overview') loadOverview();
    else if (currentTab === 'leads') loadLeads();
    else if (currentTab === 'expenses') loadExpenses();
}

async function loadOverview() {
    const data = await api(`/overview?month=${currentMonth}`);
    const s = data.summary;
    document.getElementById('statIncome').textContent = fmtMoney(s.income_actual);
    document.getElementById('statPipeline').textContent = fmtMoney(s.income_pipeline);
    document.getElementById('statExpense').textContent = fmtMoney(s.expense_total);
    const profitEl = document.getElementById('statProfit');
    profitEl.textContent = fmtMoney(s.profit);
    profitEl.style.color = s.profit >= 0 ? 'var(--color-success)' : 'var(--color-danger)';

    const chart = document.getElementById('chartBars');
    chart.innerHTML = '';
    const months = data.months || [];
    const maxVal = Math.max(...months.map((m) => Math.max(m.income, m.expenses, 1)), 1);
    months.forEach((m) => {
        const h = Math.round((Math.max(m.income, m.expenses) / maxVal) * 100);
        const wrap = document.createElement('div');
        wrap.className = 'chart-bar-wrap';
        wrap.innerHTML = `<div class="chart-bar" style="height:${h}px" title="Доход: ${fmtMoney(m.income)}, Расход: ${fmtMoney(m.expenses)}"></div><span>${m.month.slice(5)}</span>`;
        chart.appendChild(wrap);
    });
}

async function loadLeads() {
    const status = document.getElementById('leadStatusFilter').value;
    const data = await api(`/leads?month=${currentMonth}&status=${status}`);
    leadsCache = data.leads || [];
    const tbody = document.getElementById('leadsTableBody');
    tbody.innerHTML = leadsCache
        .map((lead) => {
            const est = lead.estimated_price != null ? fmtMoney(lead.estimated_price) : '—';
            const actual = lead.actual_amount != null ? fmtMoney(lead.actual_amount) : '—';
            const typeBadge =
                lead.type === 'callback'
                    ? '<span class="badge badge-callback">Звонок</span>'
                    : '<span class="badge badge-new">Расчёт</span>';
            const statusClass = `badge-${lead.status}`;
            return `<tr data-id="${lead.id}">
                <td>${fmtDate(lead.created_at)}</td>
                <td>${typeBadge}</td>
                <td><strong>${escapeHtml(lead.name)}</strong><br><small>${escapeHtml(lead.phone)}</small></td>
                <td>${escapeHtml(lead.city || '—')}</td>
                <td>${est}</td>
                <td>${actual}</td>
                <td><span class="badge ${statusClass}">${STATUS_LABELS[lead.status] || lead.status}</span></td>
                <td class="actions-cell">
                    <button type="button" class="btn btn-ghost btn-sm edit-lead">Изменить</button>
                    <button type="button" class="btn btn-ghost btn-sm btn-danger delete-lead">Удалить</button>
                </td>
            </tr>`;
        })
        .join('');

    tbody.querySelectorAll('.edit-lead').forEach((btn) => {
        btn.addEventListener('click', () => {
            const id = btn.closest('tr').dataset.id;
            openLeadModal(leadsCache.find((l) => l.id === id));
        });
    });
    tbody.querySelectorAll('.delete-lead').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const id = btn.closest('tr').dataset.id;
            const lead = leadsCache.find((l) => l.id === id);
            if (!confirm(`Удалить заявку «${lead?.name || ''}»?`)) return;
            await api(`/leads/${id}`, { method: 'DELETE' });
            loadLeads();
            if (currentTab === 'overview') loadOverview();
        });
    });

    if (!leadsCache.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-row">Нет заявок за выбранный месяц</td></tr>';
    }
}

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

function bindLeadModal() {
    document.getElementById('leadModalClose').addEventListener('click', closeLeadModal);
    document.getElementById('leadModalCancel').addEventListener('click', closeLeadModal);
    document.getElementById('leadModalSave').addEventListener('click', saveLeadModal);
    document.getElementById('leadModalDelete').addEventListener('click', deleteLeadModal);
    document.getElementById('leadStatusFilter').addEventListener('change', loadLeads);
}

function bindAddLeadForm() {
    document.getElementById('addLeadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const created_at = datetimeLocalToIso(document.getElementById('newLeadDate').value);
        const closed_at = datetimeLocalToIso(document.getElementById('newLeadClosedDate').value);
        const price = document.getElementById('newLeadPrice').value;
        const status = document.getElementById('newLeadStatus').value;
        const body = {
            type: 'calculate',
            name: document.getElementById('newLeadName').value,
            phone: document.getElementById('newLeadPhone').value,
            city: document.getElementById('newLeadCity').value,
            status,
            estimated_price: price || null,
            actual_amount: price || null,
            notes: document.getElementById('newLeadNotes').value || 'Добавлено вручную',
            created_at,
            closed_at: status === 'bought' ? closed_at : closed_at || null,
        };
        await api('/leads', { method: 'POST', body: JSON.stringify(body) });
        e.target.reset();
        document.getElementById('newLeadStatus').value = 'contacted';
        loadLeads();
        if (currentTab === 'overview') loadOverview();
    });
}

async function deleteLeadModal() {
    const id = document.getElementById('editLeadId').value;
    const name = document.getElementById('editLeadName').value;
    if (!confirm(`Удалить заявку «${name}»?`)) return;
    await api(`/leads/${id}`, { method: 'DELETE' });
    closeLeadModal();
    loadLeads();
    if (currentTab === 'overview') loadOverview();
}

function openLeadModal(lead) {
    if (!lead) return;
    document.getElementById('leadModal').classList.remove('admin-hidden');
    document.getElementById('editLeadId').value = lead.id;
    document.getElementById('editLeadName').value = lead.name || '';
    document.getElementById('editLeadPhone').value = lead.phone || '';
    document.getElementById('editLeadCity').value = lead.city || '';
    document.getElementById('editLeadStatus').value = lead.status || 'new';
    document.getElementById('editLeadEstimated').value = lead.estimated_price ?? '';
    document.getElementById('editLeadActual').value = lead.actual_amount ?? '';
    document.getElementById('editLeadCreatedAt').value = isoToDatetimeLocal(lead.created_at);
    document.getElementById('editLeadClosedAt').value = isoToDatetimeLocal(lead.closed_at);
    document.getElementById('editLeadNotes').value = lead.notes || '';
    const details = document.getElementById('leadModalDetails');
    if (lead.type === 'calculate') {
        details.innerHTML = `Длина: ${escapeHtml(lead.length)}, цвет: ${escapeHtml(lead.color)}, структура: ${escapeHtml(lead.structure)}<br>Фото: ${lead.photo_count || 0}`;
        details.classList.remove('admin-hidden');
    } else {
        details.classList.add('admin-hidden');
    }
}

function closeLeadModal() {
    document.getElementById('leadModal').classList.add('admin-hidden');
}

async function saveLeadModal() {
    const id = document.getElementById('editLeadId').value;
    const body = {
        status: document.getElementById('editLeadStatus').value,
        name: document.getElementById('editLeadName').value,
        phone: document.getElementById('editLeadPhone').value,
        city: document.getElementById('editLeadCity').value,
        estimated_price: document.getElementById('editLeadEstimated').value || null,
        actual_amount: document.getElementById('editLeadActual').value || null,
        created_at: datetimeLocalToIso(document.getElementById('editLeadCreatedAt').value),
        closed_at: datetimeLocalToIso(document.getElementById('editLeadClosedAt').value),
        notes: document.getElementById('editLeadNotes').value,
    };
    await api(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
    closeLeadModal();
    loadLeads();
    if (currentTab === 'overview') loadOverview();
}

function fmtExpenseDate(exp) {
    if (exp.is_recurring) return '—';
    if (!exp.date) return '—';
    const [y, m, d] = exp.date.split('-');
    return `${d}.${m}.${y}`;
}

function expenseMonthKey(exp) {
    if (exp.is_recurring) return null;
    return (exp.date || '').slice(0, 7);
}

async function loadExpenses() {
    const data = await api('/expenses');
    expensesCache = (data.expenses || []).slice().sort((a, b) => {
        if (a.is_recurring && !b.is_recurring) return -1;
        if (!a.is_recurring && b.is_recurring) return 1;
        return (b.date || '').localeCompare(a.date || '');
    });
    const totalInStore = data.total_in_store ?? expensesCache.length;
    const tbody = document.getElementById('expensesTableBody');
    tbody.innerHTML = expensesCache
        .map((exp) => {
            const mKey = expenseMonthKey(exp);
            const rowClass =
                exp.is_recurring || mKey === currentMonth ? 'row-current-month' : 'row-other-month';
            const typeCell = exp.is_recurring
                ? '<span class="badge badge-contacted">Ежемесячный</span>'
                : '<span class="badge badge-new">Разовый</span>';
            return `<tr data-id="${exp.id}" class="${rowClass}">
            <td>${exp.is_recurring ? '—' : escapeHtml(fmtExpenseDate(exp))}</td>
            <td>${escapeHtml(exp.title)}</td>
            <td>${escapeHtml(categoryLabel(exp.category))}</td>
            <td>${fmtMoney(exp.amount)}</td>
            <td>${typeCell}</td>
            <td>${escapeHtml(exp.notes || '')}</td>
            <td class="actions-cell">
                <button type="button" class="btn btn-ghost btn-sm edit-expense">Изменить</button>
                <button type="button" class="btn btn-ghost btn-sm btn-danger delete-expense">Удалить</button>
            </td>
        </tr>`;
        })
        .join('');

    tbody.querySelectorAll('.edit-expense').forEach((btn) => {
        btn.addEventListener('click', () => {
            const id = btn.closest('tr').dataset.id;
            openExpenseModal(expensesCache.find((e) => e.id === id));
        });
    });
    tbody.querySelectorAll('.delete-expense').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!confirm('Удалить расход?')) return;
            const id = btn.closest('tr').dataset.id;
            await api(`/expenses/${id}`, { method: 'DELETE' });
            loadExpenses();
            if (currentTab === 'overview') loadOverview();
        });
    });

    if (!expensesCache.length) {
        tbody.innerHTML =
            '<tr><td colspan="7" class="empty-row">Расходов пока нет. Добавьте первый расход в форме выше.</td></tr>';
    }
}

function bindExpenseModal() {
    document.getElementById('expenseModalCancel').addEventListener('click', closeExpenseModal);
    document.getElementById('expenseModalSave').addEventListener('click', saveExpenseModal);
    document.getElementById('expenseModalDelete').addEventListener('click', deleteExpenseModal);
}

function openExpenseModal(exp) {
    if (!exp) return;
    document.getElementById('expenseModal').classList.remove('admin-hidden');
    document.getElementById('editExpenseId').value = exp.id;
    document.getElementById('editExpTitle').value = exp.title || '';
    document.getElementById('editExpAmount').value = exp.amount ?? '';
    document.getElementById('editExpCategory').value = categoryLabel(exp.category);
    document.getElementById('editExpDate').value = (exp.date || '').slice(0, 10);
    document.getElementById('editExpRecurring').checked = !!exp.is_recurring;
    document.getElementById('editExpNotes').value = exp.notes || '';
}

function closeExpenseModal() {
    document.getElementById('expenseModal').classList.add('admin-hidden');
}

async function saveExpenseModal() {
    const id = document.getElementById('editExpenseId').value;
    const catRaw = document.getElementById('editExpCategory').value.trim();
    const presetKeys = Object.keys(CATEGORY_LABELS);
    let category = 'other';
    let category_custom = '';
    const found = presetKeys.find((k) => CATEGORY_LABELS[k].toLowerCase() === catRaw.toLowerCase());
    if (found) {
        category = found;
    } else if (catRaw) {
        category = 'custom';
        category_custom = catRaw;
    }
    const body = {
        title: document.getElementById('editExpTitle').value,
        amount: document.getElementById('editExpAmount').value,
        category,
        category_custom,
        date: dateForApi(document.getElementById('editExpDate').value),
        is_recurring: document.getElementById('editExpRecurring').checked,
        notes: document.getElementById('editExpNotes').value,
    };
    await api(`/expenses/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
    closeExpenseModal();
    loadExpenses();
    if (currentTab === 'overview') loadOverview();
}

async function deleteExpenseModal() {
    const id = document.getElementById('editExpenseId').value;
    if (!confirm('Удалить расход?')) return;
    await api(`/expenses/${id}`, { method: 'DELETE' });
    closeExpenseModal();
    loadExpenses();
    if (currentTab === 'overview') loadOverview();
}

function bindExpenseForm() {
    if (expenseFormBound) return;
    expenseFormBound = true;

    const catSelect = document.getElementById('expCategory');
    const customWrap = document.getElementById('expCategoryCustomWrap');
    catSelect.addEventListener('change', () => {
        customWrap.classList.toggle('admin-hidden', catSelect.value !== 'custom');
    });

    document.getElementById('expenseForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const expDateVal = document.getElementById('expDate').value || currentMonth + '-01';
        if (catSelect.value === 'custom' && !document.getElementById('expCategoryCustom').value.trim()) {
            showFormError('Укажите название своей категории или выберите другую.');
            return;
        }
        const body = {
            title: document.getElementById('expTitle').value,
            amount: document.getElementById('expAmount').value,
            category: catSelect.value,
            category_custom: document.getElementById('expCategoryCustom').value,
            is_recurring: document.getElementById('expRecurring').checked,
            date: dateForApi(expDateVal),
            notes: document.getElementById('expNotes').value,
        };
        try {
            const data = await api('/expenses', { method: 'POST', body: JSON.stringify(body) });
            const exp = data.expense;
            e.target.reset();
            customWrap.classList.add('admin-hidden');
            document.getElementById('expDate').value = defaultExpenseDate();
            await loadExpenses();
            if (currentTab === 'overview') await loadOverview();
            if (exp) {
                const bookMonth = exp.is_recurring
                    ? 'каждый месяц (в обзоре)'
                    : (exp.date || '').slice(0, 7) || '—';
                alert(
                    `Расход добавлен:\n«${exp.title}» — ${fmtMoney(exp.amount)}\n` +
                        `Дата: ${exp.is_recurring ? 'ежемесячно' : fmtExpenseDate(exp)}\n` +
                        `В «Обзоре» учитывается за: ${bookMonth}`
                );
            }
        } catch (err) {
            showFormError(apiErrorMessage(err, err.data));
        }
    });
}

checkAuth();
