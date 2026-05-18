const $ = (sel) => document.querySelector(sel);

function money(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function pct(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${n.toFixed(1)}%`;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function showErr(msg) {
  const e = $("err-banner");
  if (!e) return;
  e.textContent = msg || "";
  e.style.display = msg ? "block" : "none";
}

async function loadDashboard() {
  showErr("");
  setText("status", "Loading…");
  try {
    const r = await fetch("/api/dashboard");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    render(d);
    setText("status", "Updated " + new Date().toLocaleTimeString());
  } catch (e) {
    setText("status", "");
    showErr(e.message || String(e));
  }
}

function render(d) {
  const fin = d.finance || {};
  const src = fin.source || "—";
  setText("finance-source", src);
  setText("finance-path", fin.finance_data_dir || "—");
  setText("db-path", fin.operations_db || "—");
  setText("config-path", fin.config_file || "—");

  const badge = $("finance-badge");
  if (badge) {
    badge.className = "badge" + (fin.all_required_present === false ? " warn" : "");
    badge.textContent =
      fin.all_required_present === false ? "Missing CSVs" : fin.all_required_present ? "Data ready" : "—";
  }

  const inp = $("finance-dir-input");
  if (inp && !inp.dataset.touched) inp.placeholder = fin.finance_data_dir || "";

  const snap = d.snapshot || {};
  setText("m-task", String(snap.open_or_in_progress_tasks ?? "—"));
  setText("m-cust", String(snap.customer_count ?? "—"));
  setText("m-inv", String(snap.inventory_skus_low_stock_le_5 ?? "—"));
  setText("m-exp", money(snap.month_to_date_expenses_usd));

  const salesBody = $("tbl-sales");
  const salesWrap = $("sales-section");
  if (d.sales?.ok && d.sales.data?.monthly) {
    salesWrap.style.display = "block";
    $("sales-err").textContent = "";
    salesBody.innerHTML = d.sales.data.monthly
      .map(
        (row) =>
          `<tr><td>${row.year_month}</td><td class="num">${money(row.revenue_usd)}</td><td class="num">${pct(row.delivery_pct_of_revenue)}</td><td class="num">${row.mom_revenue_pct_change == null ? "—" : row.mom_revenue_pct_change + "%"}</td></tr>`
      )
      .join("");
  } else {
    salesWrap.style.display = d.sales?.ok ? "block" : "block";
    $("sales-err").textContent = d.sales?.error || "";
    if (!d.sales?.ok) salesBody.innerHTML = "";
  }

  const marBody = $("tbl-margins");
  if (d.margins?.ok && d.margins.data?.by_month) {
    $("margins-err").textContent = "";
    marBody.innerHTML = d.margins.data.by_month
      .map(
        (row) =>
          `<tr><td>${row.year_month}</td><td class="num">${money(row.revenue_usd)}</td><td class="num">${pct(row.gross_margin_pct)}</td><td class="num">${pct(row.operating_margin_pct)}</td></tr>`
      )
      .join("");
  } else {
    $("margins-err").textContent = d.margins?.error || "";
    marBody.innerHTML = "";
  }

  const prBody = $("tbl-payroll");
  if (d.payroll?.ok && d.payroll.data?.by_month) {
    $("payroll-err").textContent = "";
    prBody.innerHTML = d.payroll.data.by_month
      .map(
        (row) =>
          `<tr><td>${row.year_month}</td><td class="num">${money(row.revenue_usd)}</td><td class="num">${money(row.payroll_usd)}</td><td class="num">${pct(row.payroll_as_pct_of_revenue)}</td></tr>`
      )
      .join("");
  } else {
    $("payroll-err").textContent = d.payroll?.error || "";
    prBody.innerHTML = "";
  }

  const anBody = $("tbl-anomalies");
  if (d.anomalies?.ok && d.anomalies.data?.anomalies) {
    $("anom-err").textContent = "";
    const rows = d.anomalies.data.anomalies.slice(0, 12);
    anBody.innerHTML = rows
      .map(
        (row) =>
          `<tr><td>${row.year_month}</td><td>${row.metric}</td><td class="num">${money(row.amount_usd)}</td><td class="muted">${(row.reasons || []).join(", ")}</td></tr>`
      )
      .join("");
  } else {
    $("anom-err").textContent = d.anomalies?.error || "";
    anBody.innerHTML = "";
  }
}

async function saveFinanceDir() {
  const inp = $("finance-dir-input");
  const val = inp.value.trim();
  showErr("");
  try {
    const r = await fetch("/api/finance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ directory: val }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    inp.value = "";
    inp.dataset.touched = "";
    await loadDashboard();
  } catch (e) {
    showErr(e.message || String(e));
  }
}

async function clearFinanceDir() {
  const inp = $("finance-dir-input");
  inp.value = "";
  showErr("");
  try {
    const r = await fetch("/api/finance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ directory: "" }),
    });
    if (!r.ok) {
      const j = await r.json();
      throw new Error(j.error || `HTTP ${r.status}`);
    }
    await loadDashboard();
  } catch (e) {
    showErr(e.message || String(e));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("btn-refresh")?.addEventListener("click", loadDashboard);
  $("btn-save")?.addEventListener("click", saveFinanceDir);
  $("btn-clear")?.addEventListener("click", clearFinanceDir);
  $("finance-dir-input")?.addEventListener("input", (e) => {
    e.target.dataset.touched = "1";
  });
  loadDashboard();
});
