// ---------------------------------------------------------------------------
// AI Stock Screener - Dashboard client
// ---------------------------------------------------------------------------

let allRows = [];
let longTermRows = [];
let sortKey = "symbol";
let sortDir = 1;
let currentPage = 1;
const PAGE_SIZE = 15;

const el = (id) => document.getElementById(id);

// ---------- WebSocket ----------
function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/dashboard`);

  ws.onopen = () => setLive(true);
  ws.onclose = () => { setLive(false); setTimeout(connectWS, 2000); };
  ws.onerror = () => ws.close();

  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.type === "screen_update") {
      allRows = data.rows || [];
      longTermRows = data.long_term_picks || [];
      updateSummary();
      renderScreenerTable();
      renderLongTermTable();
      el("lastUpdated").textContent = "Last updated: " + new Date(data.timestamp * 1000).toLocaleTimeString();
    }
  };
}

function setLive(isLive) {
  el("liveIndicator").style.background = isLive ? "#22c55e" : "#ef4444";
}

// ---------- Summary cards ----------
function updateSummary() {
  el("cardTotal").textContent = allRows.length;
  el("cardBuy").textContent = allRows.filter(r => r.action === "BUY").length;
  el("cardSell").textContent = allRows.filter(r => r.action === "SELL").length;
  el("cardLongTerm").textContent = longTermRows.length;
}

// ---------- Filtering / sorting / pagination ----------
function getFilteredRows() {
  const q = el("searchBox").value.trim().toUpperCase();
  const action = el("actionFilter").value;

  let rows = allRows.filter(r => {
    if (q && !r.symbol.includes(q)) return false;
    if (action && r.action !== action) return false;
    return true;
  });

  rows.sort((a, b) => {
    const va = a[sortKey], vb = b[sortKey];
    if (typeof va === "string") return va.localeCompare(vb) * sortDir;
    return ((va ?? 0) - (vb ?? 0)) * sortDir;
  });

  return rows;
}

function actionBadge(action) {
  const cls = action === "BUY" ? "badge-buy" : action === "SELL" ? "badge-sell" : "badge-avoid";
  return `<span class="badge ${cls}">${action}</span>`;
}

function riskBadge(risk) {
  const cls = "risk-badge-" + risk.toLowerCase();
  return `<span class="badge ${cls}">${risk}</span>`;
}

function trendLabel(trend) {
  const cls = trend === "Uptrend" ? "trend-up" : "trend-down";
  const arrow = trend === "Uptrend" ? "▲" : "▼";
  return `<span class="${cls}">${arrow} ${trend}</span>`;
}

function stars(rating) {
  const full = Math.round(rating);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

function renderScreenerTable() {
  const rows = getFilteredRows();
  el("rowCountLabel").textContent = `${rows.length} stocks match filters`;

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  if (currentPage > totalPages) currentPage = totalPages;
  const pageRows = rows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const tbody = el("screenerBody");
  tbody.innerHTML = "";

  pageRows.forEach(r => {
    const tr = document.createElement("tr");
    const rowCls = r.action === "BUY" ? "row-buy" : r.action === "SELL" ? "row-sell" : "row-avoid";
    tr.className = `stock-row ${rowCls}`;
    tr.innerHTML = `
      <td class="expand-toggle">▸</td>
      <td><b>${r.symbol}</b></td>
      <td class="mono">₹${r.ltp.toFixed(2)}</td>
      <td>${actionBadge(r.action)}</td>
      <td>
        <div class="progress" style="height:5px;width:70px;display:inline-block;vertical-align:middle;margin-right:6px;">
          <div class="progress-bar bg-info" style="width:${r.ai_confidence}%"></div>
        </div><span class="mono">${r.ai_confidence.toFixed(1)}%</span>
      </td>
      <td>${riskBadge(r.risk)}</td>
      <td>${trendLabel(r.trend)}</td>
      <td class="mono">${r.smma_fast ?? "-"}</td>
      <td class="mono">${r.smma_slow ?? "-"}</td>
      <td class="mono">${(r.bid_qty ?? 0).toLocaleString()}</td>
      <td class="mono">${(r.ask_qty ?? 0).toLocaleString()}</td>
      <td class="mono">${(r.traded_qty_60m ?? 0).toLocaleString()}</td>
    `;

    const detailTr = buildDetailRow(r);

    tr.addEventListener("click", () => {
      const isHidden = detailTr.classList.contains("d-none");
      detailTr.classList.toggle("d-none");
      tr.querySelector(".expand-toggle").textContent = isHidden ? "▾" : "▸";
    });

    tbody.appendChild(tr);
    tbody.appendChild(detailTr);
  });

  renderPagination(totalPages);
}

function buildDetailRow(r) {
  const tpl = el("detailTemplate").content.cloneNode(true);
  const tr = tpl.querySelector("tr");

  const metrics = tr.querySelectorAll(".detail-metric");
  const setMetric = (idx, value, pct) => {
    const m = metrics[idx];
    m.querySelector(".val").textContent = value;
    const bar = m.querySelector(".progress-bar");
    if (bar) bar.style.width = (pct ?? 0) + "%";
  };

  setMetric(0, r.ai_confidence.toFixed(1) + "%", r.ai_confidence);
  setMetric(1, r.trade_quality.toFixed(1) + "%", r.trade_quality);
  setMetric(2, r.momentum.toFixed(2) + "%");
  setMetric(3, r.buying_pressure.toFixed(1) + "%", r.buying_pressure);
  setMetric(4, r.selling_pressure.toFixed(1) + "%", r.selling_pressure);
  setMetric(5, r.liquidity_score.toFixed(1) + "%", r.liquidity_score);
  setMetric(6, stars(r.opportunity_rating));
  setMetric(7, r.confluence_score.toFixed(1) + "%", r.confluence_score);

  tr.querySelector(".bidp").textContent = "₹" + (r.bid_price ?? "-");
  tr.querySelector(".bidq").textContent = (r.bid_qty ?? 0).toLocaleString();
  tr.querySelector(".askp").textContent = "₹" + (r.ask_price ?? "-");
  tr.querySelector(".askq").textContent = (r.ask_qty ?? 0).toLocaleString();
  tr.querySelector(".avg20").textContent = "₹" + r.avg_ltp_20m;
  tr.querySelector(".avg60").textContent = "₹" + r.avg_ltp_60m;
  tr.querySelector(".tq5").textContent = (r.traded_qty_5m ?? 0).toLocaleString();
  tr.querySelector(".tq20").textContent = (r.traded_qty_20m ?? 0).toLocaleString();

  return tr;
}

function renderPagination(totalPages) {
  const controls = el("paginationControls");
  controls.innerHTML = "";
  el("paginationLabel").textContent = `Page ${currentPage} of ${totalPages}`;

  const addBtn = (label, page, disabled, active) => {
    const li = document.createElement("li");
    li.className = "page-item" + (disabled ? " disabled" : "") + (active ? " active" : "");
    li.innerHTML = `<button class="page-link">${label}</button>`;
    li.addEventListener("click", () => { if (!disabled) { currentPage = page; renderScreenerTable(); } });
    controls.appendChild(li);
  };

  addBtn("«", currentPage - 1, currentPage === 1, false);
  for (let p = 1; p <= totalPages; p++) addBtn(p, p, false, p === currentPage);
  addBtn("»", currentPage + 1, currentPage === totalPages, false);
}

// ---------- Long-term picks table ----------
function renderLongTermTable() {
  const tbody = el("longTermBody");
  tbody.innerHTML = "";

  if (longTermRows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted py-4">No stocks are currently well positioned for the long term.</td></tr>`;
    return;
  }

  longTermRows.forEach(r => {
    const tr = document.createElement("tr");
    tr.className = "stock-row";

    tr.innerHTML = `
      <td><b>${r.symbol}</b></td>
      <td><span class="badge badge-approved">WELL POSITIONED</span></td>
      <td class="mono">₹${r.ltp.toFixed(2)}</td>
      <td>${actionBadge(r.action)}</td>
      <td>
        <div class="progress" style="height:5px;width:70px;display:inline-block;vertical-align:middle;margin-right:6px;">
          <div class="progress-bar bg-info" style="width:${r.ai_confidence}%"></div>
        </div><span class="mono">${r.ai_confidence.toFixed(1)}%</span>
      </td>
      <td>${riskBadge(r.risk)}</td>
      <td>${trendLabel(r.trend)}</td>
      <td class="mono">${r.momentum.toFixed(2)}%</td>
      <td class="mono">₹${r.avg_ltp_20m.toFixed(2)}</td>
      <td class="mono">${(r.traded_qty_60m ?? 0).toLocaleString()}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ---------- Sorting ----------
document.addEventListener("click", (e) => {
  const th = e.target.closest("th[data-sort]");
  if (!th) return;
  const key = th.dataset.sort;
  if (sortKey === key) { sortDir *= -1; } else { sortKey = key; sortDir = 1; }
  renderScreenerTable();
});

// ---------- Search / filter ----------
el("searchBox").addEventListener("input", () => { currentPage = 1; renderScreenerTable(); });
el("actionFilter").addEventListener("change", () => { currentPage = 1; renderScreenerTable(); });

// ---------- Tabs ----------
document.querySelectorAll("#mainTabs .nav-link").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#mainTabs .nav-link").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.add("d-none"));
    el("tab-" + btn.dataset.tab).classList.remove("d-none");
  });
});

// ---------- Theme toggle ----------
el("themeToggle").addEventListener("click", () => {
  const html = document.documentElement;
  const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
  html.setAttribute("data-theme", next);
});

// ---------- Init ----------
connectWS();
