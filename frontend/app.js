/* ═══════════════ Z.AI BNPL Advisory — Frontend App ═══════════════ */

const state = { companyId: null };
const el = (id) => document.getElementById(id);
const formatRM = (n) =>
  new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR", maximumFractionDigits: 0 }).format(n ?? 0);

async function api(path, options) {
  const res = await fetch(`/api/v1${path}`, options);
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

/* ═══ PAGE TITLES ═══ */
const pageTitles = {
  overview: "Dashboard",
  evaluator: "BNPL Evaluator",
  upload: "Upload Data",
  transactions: "Transactions",
  forecast: "Forecast",
  benchmarks: "Benchmarks",
};

/* ═══ NAVIGATION ═══ */
function initNavigation() {
  const btns = [...document.querySelectorAll(".nav-btn")];
  const views = [...document.querySelectorAll(".view")];
  btns.forEach((btn) => {
    btn.addEventListener("click", () => {
      btns.forEach((x) => x.classList.remove("active"));
      views.forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      const viewId = btn.dataset.view;
      el(viewId).classList.add("active");
      el("page-title").textContent = pageTitles[viewId] || viewId;
    });
  });
}

/* ═══ BOOTSTRAP ═══ */
async function bootstrap() {
  try {
    const boot = await api("/dashboard/bootstrap");
    state.companyId = boot.company_id;
    el("company-chip").textContent = `${boot.company_name} · ${boot.industry}`;
  } catch (e) {
    el("company-chip").textContent = "Offline";
    console.error("Bootstrap failed:", e);
  }
}

/* ═══ DASHBOARD OVERVIEW ═══ */
async function loadOverview() {
  if (!state.companyId) return;
  try {
    const data = await api(`/dashboard/${state.companyId}/overview`);
    el("health-summary").textContent = data.health_summary.summary;
    el("health-score-badge").textContent = data.health_summary.health_score ?? "--";
    el("kpi-revenue").textContent = formatRM(data.kpis.total_revenue_mtd);
    el("kpi-cash").textContent = formatRM(data.kpis.operating_cash_flow);
    el("kpi-margin").textContent = `${data.kpis.net_profit_margin_percent.toFixed(1)}%`;
    el("kpi-eapr").textContent = `${data.kpis.effective_annual_rate_percent.toFixed(1)}%`;
  } catch (e) {
    console.error("Overview failed:", e);
  }
}

/* ═══ TRANSACTIONS ═══ */
async function loadTransactions() {
  if (!state.companyId) return;
  try {
    const data = await api(`/dashboard/${state.companyId}/transactions?days_back=120&limit=40`);
    const items = data.items || [];
    const spend = items
      .filter((tx) => ["purchase", "payment"].includes((tx.transaction_type || "").toLowerCase()))
      .reduce((a, tx) => a + (tx.amount || 0), 0);
    const monthlyEst = spend / 4;

    el("tx-total-spend").textContent = formatRM(spend);
    el("tx-upcoming").textContent = formatRM(monthlyEst);
    el("tx-credit").textContent = formatRM(Math.max(0, 50000 - monthlyEst));

    if (items.length === 0) {
      el("tx-empty")?.classList.remove("hidden");
    } else {
      el("tx-empty")?.classList.add("hidden");
    }

    el("tx-rows").innerHTML = items
      .map((tx) => {
        const type = (tx.transaction_type || "").toLowerCase();
        return `<tr>
          <td>${(tx.transaction_date || "").slice(0, 10)}</td>
          <td>${tx.description || "—"}</td>
          <td>${tx.category || "—"}</td>
          <td><span class="type-badge ${type}">${tx.transaction_type}</span></td>
          <td>${formatRM(tx.amount)}</td>
        </tr>`;
      })
      .join("");
  } catch (e) {
    console.error("Transactions failed:", e);
  }
}

/* ═══ BENCHMARKS ═══ */
async function loadBenchmarks() {
  if (!state.companyId) return;
  try {
    const data = await api(`/dashboard/${state.companyId}/benchmarks`);
    el("benchmark-rows").innerHTML = data.providers
      .map(
        (p) => `<tr>
          <td><strong>${p.provider}</strong></td>
          <td>${p.monthly_rate_percent.toFixed(1)}%</td>
          <td>${p.eapr_percent.toFixed(1)}%</td>
          <td>${formatRM(p.late_fee_rm)}</td>
          <td>${formatRM(p.typical_limit_rm)}</td>
          <td>${p.fit}</td>
        </tr>`
      )
      .join("");
  } catch (e) {
    console.error("Benchmarks failed:", e);
  }
}

/* ═══ FORECAST ═══ */
function renderForecast(series, projectedNet, monthlyPmt) {
  const bars = el("forecast-bars");
  const maxVal = Math.max(...series.map((s) => Math.max(s.revenue, s.expenses_plus_debt)), 1);
  bars.innerHTML = series
    .flatMap((s) => {
      const revH = Math.max(8, Math.round((s.revenue / maxVal) * 220));
      const expH = Math.max(6, Math.round((s.expenses_plus_debt / maxVal) * 220));
      return [
        `<div class="bar exp" style="height:${expH}px" data-month="${s.month}"></div>`,
        `<div class="bar rev" style="height:${revH}px"></div>`,
      ];
    })
    .join("");
  bars.style.gridTemplateColumns = `repeat(${series.length * 2}, minmax(8px, 1fr))`;

  el("net-income").textContent = formatRM(projectedNet);
  el("monthly-payment").textContent = formatRM(monthlyPmt);

  const avgProfit = series.reduce((a, m) => a + (m.profit || 0), 0) / Math.max(series.length, 1);
  const risk = avgProfit < 1000 ? "elevated" : avgProfit < 2500 ? "moderate" : "controlled";
  el("insight-health").textContent = `Average monthly profit is ${formatRM(avgProfit)}. Operating margins appear ${risk === "controlled" ? "stable" : "tight"}.`;
  el("insight-risk").textContent = `Risk level: ${risk}. ${risk === "elevated" ? "Consider reducing loan amount or extending term." : "Cash buffer is adequate."}`;
  el("insight-action").textContent = `Monthly payment is ${formatRM(monthlyPmt)}. ${avgProfit < monthlyPmt ? "Warning: payment exceeds average profit." : "Payment is within sustainable range."}`;
}

async function runForecast(formData) {
  const payload = Object.fromEntries(formData.entries());
  Object.keys(payload).forEach((k) => (payload[k] = Number(payload[k])));
  try {
    const result = await api(`/dashboard/${state.companyId}/forecast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderForecast(result.series, result.projected_net_income, result.monthly_payment);
  } catch (e) {
    console.error("Forecast failed:", e);
  }
}

/* ═══ BNPL EVALUATOR (Core AI Feature) ═══ */
async function evaluatePurchase(formData) {
  const placeholder = el("result-placeholder");
  const content = el("result-content");
  const loading = el("result-loading");
  const btn = el("btn-evaluate");

  placeholder.classList.add("hidden");
  content.classList.add("hidden");
  loading.classList.remove("hidden");
  btn.disabled = true;
  btn.textContent = "Analyzing...";

  const payload = {};
  for (const [k, v] of formData.entries()) {
    payload[k] = ["company_name", "industry", "purchase_purpose"].includes(k) ? v : Number(v);
  }

  try {
    const result = await api("/advisor/evaluate-purchase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    // Decision
    const decision = result.decision || "review";
    el("decision-value").textContent = decision;
    const icon = el("decision-icon");
    if (decision.toLowerCase().includes("approve") || decision.toLowerCase().includes("bnpl")) {
      icon.textContent = "✓"; icon.className = "decision-icon";
    } else if (decision.toLowerCase().includes("reject") || decision.toLowerCase().includes("defer")) {
      icon.textContent = "✕"; icon.className = "decision-icon danger";
    } else {
      icon.textContent = "?"; icon.className = "decision-icon warn";
    }

    // Confidence
    const conf = (result.confidence_score || 0.7) * 100;
    el("confidence-fill").style.width = `${conf}%`;
    el("confidence-value").textContent = `${conf.toFixed(0)}%`;

    // Explanation
    el("result-explanation").textContent = result.explanation || "No explanation provided.";

    // Impact
    const impact = result.quantifiable_impact || result.impact_metrics || {};
    el("metric-cash-preserved").textContent = formatRM(impact.cash_flow_preserved || impact.projected_cashflow_change_rm || 0);
    el("metric-roi").textContent = impact.projected_roi_increase || impact.estimated_roi_percent || "—";

    // Actions
    const actions = result.action_recommendations || [];
    el("action-list").innerHTML = actions.length > 0
      ? actions.map((a) => `<li>${a}</li>`).join("")
      : "<li>Review the recommendation and consult your financial advisor.</li>";

    // Show & hide
    if (el("result-actions")) {
      el("result-actions").classList.toggle("hidden", actions.length === 0);
    }
    loading.classList.add("hidden");
    content.classList.remove("hidden");
  } catch (e) {
    loading.classList.add("hidden");
    placeholder.classList.remove("hidden");
    el("result-placeholder").querySelector("p").textContent =
      `Analysis failed: ${e.message}. Make sure the backend is running and the Z.AI API key is configured.`;
    console.error("Evaluation failed:", e);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547Z"/></svg> Evaluate with Z.AI`;
  }
}

/* ═══ FILE UPLOAD ═══ */
function initUpload() {
  const zone = el("upload-zone");
  const input = el("file-input");
  const browse = el("btn-browse");

  browse.addEventListener("click", (e) => { e.stopPropagation(); input.click(); });
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault(); zone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
  });
  input.addEventListener("change", () => { if (input.files.length) uploadFiles(input.files); });
}

async function uploadFiles(files) {
  if (!state.companyId) { alert("No company loaded. Please wait for bootstrap."); return; }
  const formData = new FormData();
  let hasStructured = false;

  for (const f of files) {
    const name = f.name.toLowerCase();
    if (name.endsWith(".csv") || name.endsWith(".json")) {
      formData.append("structured_file", f);
      hasStructured = true;
    } else if (name.endsWith(".pdf")) {
      formData.append("unstructured_files", f);
    }
  }

  if (!hasStructured && !formData.has("unstructured_files")) {
    alert("Please upload CSV, JSON, or PDF files."); return;
  }

  try {
    const result = await api(`/sme/${state.companyId}/upload-financials`, { method: "POST", body: formData });
    const resultDiv = el("upload-result");
    resultDiv.classList.remove("hidden");
    el("upload-summary").innerHTML = `
      <p style="color:var(--green);font-weight:600;margin-bottom:8px;">✓ Upload Successful</p>
      <p>Transactions inserted: <strong>${result.records_stored?.transactions_inserted || 0}</strong></p>
      <p>Documents processed: <strong>${result.records_stored?.documents_processed || 0}</strong></p>
    `;
    if (result.health_assessment && result.health_assessment.health_score) {
      el("upload-metrics").innerHTML = `
        <div style="margin-top:12px;padding:12px;background:rgba(34,197,94,0.08);border-radius:8px;border:1px solid rgba(34,197,94,0.2);">
          <p style="font-size:0.8rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;">Health Score</p>
          <p style="font-size:1.6rem;font-weight:700;color:var(--green);">${result.health_assessment.health_score}/100</p>
          <p style="font-size:0.85rem;color:var(--text-secondary);">Classification: ${result.health_assessment.classification || "—"}</p>
        </div>
      `;
    }
    await loadTransactions();
    await loadOverview();
  } catch (e) {
    alert(`Upload failed: ${e.message}`);
    console.error("Upload failed:", e);
  }
}

/* ═══ INIT ═══ */
async function init() {
  initNavigation();
  initUpload();
  await bootstrap();
  await Promise.all([loadOverview(), loadTransactions(), loadBenchmarks()]);

  // Forecast form
  const fForm = el("forecast-form");
  fForm.addEventListener("submit", async (e) => { e.preventDefault(); await runForecast(new FormData(fForm)); });
  await runForecast(new FormData(fForm));

  // Evaluator form
  const eForm = el("evaluator-form");
  eForm.addEventListener("submit", async (e) => { e.preventDefault(); await evaluatePurchase(new FormData(eForm)); });
}

init().catch((err) => {
  console.error("Init failed:", err);
  el("health-summary").textContent = "Failed to connect to backend. Start the server first.";
});
