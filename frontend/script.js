// =========================
// PAGE NAVIGATION
// =========================
const API_BASE = "https://vensim-ai-web-vr.onrender.com";
const homeSection = document.getElementById("homeSection");
const appSection = document.getElementById("appSection");
const chartRegistry = {};

const dashboardState = {
  chartOrder: [],
  chartsMeta: {},
  parametersMeta: {},
  debounceTimer: null,
  isRunning: false,
  pendingRun: false,
  isInitialized: false,
  scenarioOverrides: {
    parameters: {},
    variables: {},
    initial_values: {},
  },
};

function showHome() {
  homeSection?.classList.remove("hidden-page");
  homeSection?.classList.add("active-page");
  appSection?.classList.remove("active-page");
  appSection?.classList.add("hidden-page");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showResults() {
  homeSection?.classList.remove("active-page");
  homeSection?.classList.add("hidden-page");
  appSection?.classList.remove("hidden-page");
  appSection?.classList.add("active-page");
  window.scrollTo({ top: 0, behavior: "smooth" });

  setTimeout(() => {
    Object.values(chartRegistry).forEach((chart) => {
      if (chart) {
        chart.resize();
        chart.update();
      }
    });
  }, 150);
}

document.getElementById("startBtn")?.addEventListener("click", showResults);
document.getElementById("navToAppBtn")?.addEventListener("click", showResults);
document.getElementById("navHomeBtn")?.addEventListener("click", showHome);
document.getElementById("navResultBtn")?.addEventListener("click", showResults);

// =========================
// CHAT SESSION
// =========================
const CHAT_SESSION_KEY = "vensim_ai_chat_session_id";
const CHAT_GREETING_DISMISSED_KEY = "vensim_chat_greeting_dismissed";

function getSessionId() {
  let sessionId = localStorage.getItem(CHAT_SESSION_KEY);
  if (!sessionId) {
    sessionId = "sess_" + Math.random().toString(36).slice(2) + "_" + Date.now();
    localStorage.setItem(CHAT_SESSION_KEY, sessionId);
  }
  return sessionId;
}

// =========================
// CHAT UI
// =========================
const chatWidget = document.getElementById("chatWidget");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSendBtn = document.getElementById("chatSendBtn");
const chatToggleBtn = document.getElementById("chatToggleBtn");
const chatCloseBtn = document.getElementById("chatCloseBtn");
const chatClearBtn = document.getElementById("chatClearBtn");
const chatGreetingPreview = document.getElementById("chatGreetingPreview");
const chatGreetingCloseBtn = document.getElementById("chatGreetingCloseBtn");
const INITIAL_CHAT_HTML = chatMessages ? chatMessages.innerHTML : "";

function scrollChatToBottom() {
  if (!chatMessages) return;
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addBubble(content, from = "bot", asHtml = false) {
  if (!chatMessages) return null;
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${from}`;
  if (asHtml) {
    bubble.innerHTML = content;
  } else {
    bubble.textContent = content;
  }
  chatMessages.appendChild(bubble);
  scrollChatToBottom();
  return bubble;
}

function createBotBubbleContainer() {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble bot";
  bubble.style.maxWidth = "92%";
  bubble.style.width = "92%";
  bubble.style.padding = "14px 15px";
  chatMessages?.appendChild(bubble);
  scrollChatToBottom();
  return bubble;
}

function hideGreetingPreview(savePreference = false) {
  chatGreetingPreview?.classList.add("hidden-preview");
  if (savePreference) {
    localStorage.setItem(CHAT_GREETING_DISMISSED_KEY, "1");
  }
}

function maybeShowGreetingPreview() {
  const dismissed = localStorage.getItem(CHAT_GREETING_DISMISSED_KEY) === "1";
  const chatHidden = chatWidget?.classList.contains("hidden-chat");
  if (!dismissed && chatHidden) {
    chatGreetingPreview?.classList.remove("hidden-preview");
  } else {
    chatGreetingPreview?.classList.add("hidden-preview");
  }
}

function toggleChat() {
  if (!chatWidget) return;
  chatWidget.classList.toggle("hidden-chat");
  if (chatWidget.classList.contains("hidden-chat")) {
    maybeShowGreetingPreview();
  } else {
    hideGreetingPreview(true);
    chatInput?.focus();
  }
}

function closeChat() {
  chatWidget?.classList.add("hidden-chat");
  maybeShowGreetingPreview();
}

function clearChatHistory() {
  if (!chatMessages) return;
  chatMessages.innerHTML = INITIAL_CHAT_HTML;
  if (chatInput) chatInput.value = "";
  scrollChatToBottom();
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatAnswerToHtml(text) {
  if (!text) return "";

  let html = escapeHtml(text);
  html = html.replace(/^###\s+(.*)$/gm, '<h4 style="margin:0 0 8px;color:#fff;font-size:15px;">$1</h4>');
  html = html.replace(/^##\s+(.*)$/gm, '<h3 style="margin:0 0 8px;color:#fff;font-size:16px;">$1</h3>');
  html = html.replace(/^#\s+(.*)$/gm, '<h2 style="margin:0 0 8px;color:#fff;font-size:17px;">$1</h2>');
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  const lines = html.split("\n");
  let inList = false;
  const out = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (/^[-•]\s+/.test(line)) {
      if (!inList) {
        out.push('<ul style="margin:6px 0 10px 18px;padding:0;">');
        inList = true;
      }
      out.push(`<li style="margin:4px 0;line-height:1.6;">${line.replace(/^[-•]\s+/, "")}</li>`);
    } else {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }

      if (line === "") {
        out.push('<div style="height:6px;"></div>');
      } else if (!/^<h[234]/.test(line)) {
        out.push(`<p style="margin:0 0 8px;line-height:1.7;">${line}</p>`);
      } else {
        out.push(line);
      }
    }
  }

  if (inList) out.push("</ul>");
  return out.join("");
}

function createSectionTitle(text) {
  const div = document.createElement("div");
  div.style.marginTop = "14px";
  div.style.marginBottom = "8px";
  div.style.fontWeight = "800";
  div.style.color = "#ffffff";
  div.style.fontSize = "13px";
  div.textContent = text;
  return div;
}

function createActionButton(text, variant = "default") {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = text;
  btn.style.border = "1px solid rgba(255,255,255,.10)";
  btn.style.background = variant === "primary" ? "rgba(0,224,160,.14)" : "rgba(255,255,255,.06)";
  btn.style.color = variant === "primary" ? "#7ef2ca" : "#eef2fa";
  btn.style.borderRadius = "10px";
  btn.style.padding = "8px 10px";
  btn.style.fontSize = "12px";
  btn.style.cursor = "pointer";
  btn.style.transition = "all .2s";
  btn.onmouseenter = () => {
    btn.style.background = variant === "primary" ? "rgba(0,224,160,.22)" : "rgba(255,255,255,.10)";
  };
  btn.onmouseleave = () => {
    btn.style.background = variant === "primary" ? "rgba(0,224,160,.14)" : "rgba(255,255,255,.06)";
  };
  return btn;
}

function createButtonRow() {
  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.flexWrap = "wrap";
  row.style.gap = "8px";
  row.style.marginTop = "10px";
  return row;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  return num.toLocaleString("en-US", { maximumFractionDigits: digits });
}

function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return `${num.toFixed(digits)}%`;
}

function createInfoCard(title, value, subtitle = "", color = "#00e0a0") {
  const card = document.createElement("div");
  card.style.flex = "1 1 140px";
  card.style.minWidth = "130px";
  card.style.background = "rgba(255,255,255,.04)";
  card.style.border = "1px solid rgba(255,255,255,.08)";
  card.style.borderRadius = "12px";
  card.style.padding = "12px";

  const titleEl = document.createElement("div");
  titleEl.textContent = title;
  titleEl.style.fontSize = "11px";
  titleEl.style.color = "#9fb0c9";
  titleEl.style.marginBottom = "6px";

  const valueEl = document.createElement("div");
  valueEl.textContent = value;
  valueEl.style.fontSize = "20px";
  valueEl.style.fontWeight = "800";
  valueEl.style.color = color;
  valueEl.style.lineHeight = "1.2";

  const subEl = document.createElement("div");
  subEl.textContent = subtitle;
  subEl.style.fontSize = "11px";
  subEl.style.color = "#d4deee";
  subEl.style.lineHeight = "1.5";
  subEl.style.marginTop = "6px";

  card.appendChild(titleEl);
  card.appendChild(valueEl);
  if (subtitle) card.appendChild(subEl);
  return card;
}

function createScrollableTable(records) {
  const wrap = document.createElement("div");
  wrap.style.overflowX = "auto";
  wrap.style.marginTop = "8px";
  wrap.style.border = "1px solid rgba(255,255,255,.08)";
  wrap.style.borderRadius = "12px";
  wrap.style.background = "rgba(255,255,255,.03)";

  const table = document.createElement("table");
  table.style.width = "100%";
  table.style.minWidth = "560px";
  table.style.borderCollapse = "collapse";
  table.style.fontSize = "12px";

  const headers = Object.keys(records[0] || {});
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");

  headers.forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    th.style.textAlign = "left";
    th.style.padding = "8px 10px";
    th.style.color = "#d8e2f0";
    th.style.borderBottom = "1px solid rgba(255,255,255,.10)";
    th.style.background = "rgba(255,255,255,.04)";
    th.style.whiteSpace = "nowrap";
    headRow.appendChild(th);
  });

  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  records.forEach((row) => {
    const tr = document.createElement("tr");
    headers.forEach((h) => {
      const td = document.createElement("td");
      td.textContent = row[h] === null || row[h] === undefined ? "" : String(row[h]);
      td.style.padding = "8px 10px";
      td.style.color = "#eef2fa";
      td.style.borderBottom = "1px solid rgba(255,255,255,.05)";
      td.style.verticalAlign = "top";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

function createSuggestions(suggestions = []) {
  const wrap = createButtonRow();
  suggestions.forEach((item) => {
    const btn = createActionButton(item.label || item.prompt || "Санал", "primary");
    btn.addEventListener("click", async () => {
      const text = item.prompt || item.label || "";
      if (chatInput) chatInput.value = text;
      await sendChat(text);
    });
    wrap.appendChild(btn);
  });
  return wrap;
}

function createResponseStyleButtons() {
  const wrap = createButtonRow();
  const styles = [
    { label: "Хураангуй", prompt: "Дээрх хариултыг хураангуйл." },
    { label: "Дэлгэрэнгүй", prompt: "Дээрх хариултыг дэлгэрэнгүй тайлбарла." },
    { label: "Зөвхөн тоо", prompt: "Дээрх хариултыг зөвхөн тоон утгаар гарга." },
    { label: "Тайлбартай", prompt: "Дээрх хариултыг илүү ойлгомжтой тайлбартай болгож өг." },
  ];

  styles.forEach((item) => {
    const btn = createActionButton(item.label);
    btn.addEventListener("click", async () => {
      if (chatInput) chatInput.value = item.prompt;
      await sendChat(item.prompt);
    });
    wrap.appendChild(btn);
  });

  return wrap;
}

function normalizeStatRow(row = {}) {
  const normalized = {};
  Object.keys(row).forEach((key) => {
    normalized[String(key).trim().toLowerCase()] = row[key];
  });
  return normalized;
}

function extractSummaryData(data) {
  const statRowRaw = Array.isArray(data.stats) && data.stats.length > 0 ? data.stats[0] : null;
  if (!statRowRaw) return null;

  const row = normalizeStatRow(statRowRaw);
  const metricName = row["kpi"] || row["metric"] || row["real_name"] || "KPI";
  const baselineEnd = row["baseline_end"];
  const scenarioEnd = row["scenario_end"];
  const endPctChange = row["end_%change"] ?? row["end_%_change"] ?? row["end_change_pct"];

  return { metricName, baselineEnd, scenarioEnd, endPctChange };
}

// =========================
// DASHBOARD HELPERS
// =========================
function showLoading(show, text = "Симуляци тооцоолж байна...") {
  const loadingEl = document.getElementById("dashboardLoadingStatus");
  if (!loadingEl) return;
  loadingEl.textContent = text;
  loadingEl.classList.toggle("show", Boolean(show));
}

function showError(message = "Симуляци амжилтгүй.") {
  const errorEl = document.getElementById("dashboardErrorStatus");
  if (!errorEl) return;
  errorEl.textContent = message;
  errorEl.classList.add("show");
}

function hideError() {
  const errorEl = document.getElementById("dashboardErrorStatus");
  if (!errorEl) return;
  errorEl.classList.remove("show");
}

function formatDisplayValue(value, format) {
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value ?? "-");
  if (format === "integer") return String(Math.round(num));
  if (format === "decimal_2") return num.toFixed(2);
  return String(num);
}

function formatAxisValue(value, unit = "") {
  const num = Number(value);
  if (!Number.isFinite(num)) return value ?? "-";
  if (unit === "индекс") return num.toFixed(2);
  if (Math.abs(num) >= 1000) return num.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (Math.abs(num) < 10 && !Number.isInteger(num)) return num.toFixed(2);
  return num.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function normalizeNumericValue(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : value;
}

function mergeOverrideValues(target, values) {
  if (!values || typeof values !== "object") return 0;
  let count = 0;
  Object.entries(values).forEach(([key, value]) => {
    target[key] = normalizeNumericValue(value);
    count += 1;
  });
  return count;
}

function getCurrentParameterValues() {
  const payload = {};
  Object.keys(dashboardState.parametersMeta).forEach((key) => {
    const slider = document.getElementById(key);
    if (!slider) return;
    payload[key] = Number(slider.value);
  });
  return payload;
}

function getCurrentScenarioPayload() {
  return {
    parameters: getCurrentParameterValues(),
    variables: { ...dashboardState.scenarioOverrides.variables },
    initial_values: { ...dashboardState.scenarioOverrides.initial_values },
  };
}

function describeDashboardSync(syncPayload) {
  if (!syncPayload || typeof syncPayload !== "object") return "";
  const parts = [];

  const paramCount = Object.keys(syncPayload.parameters || {}).length;
  const variableCount = Object.keys(syncPayload.variables || {}).length;
  const initialCount = Object.keys(syncPayload.initial_values || {}).length;

  if (paramCount) parts.push(`${paramCount} параметр`);
  if (variableCount) parts.push(`${variableCount} хувьсагч`);
  if (initialCount) parts.push(`${initialCount} анхны утга`);

  return parts.join(", ");
}

function getGradient(ctx, r, g, b, height = 200) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, `rgba(${r},${g},${b},.22)`);
  gradient.addColorStop(1, `rgba(${r},${g},${b},.01)`);
  return gradient;
}

function createChart(metricKey, meta) {
  const canvas = document.getElementById(meta.canvas_id);
  if (!canvas) return null;
  const ctx = canvas.getContext("2d");
  const baselineFill = getGradient(ctx, 0, 224, 160);
  const scenarioFill = getGradient(ctx, 255, 95, 173);

  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Суурь хувилбар",
          data: [],
          borderColor: "#00e0a0",
          backgroundColor: baselineFill,
          fill: true,
          borderWidth: 2,
          tension: 0.38,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
        {
          label: "Дэвшүүлж буй хувилбар",
          data: [],
          borderColor: "#ff5fad",
          backgroundColor: scenarioFill,
          fill: true,
          borderWidth: 2,
          tension: 0.38,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 380, easing: "easeOutQuart" },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: {
            color: "#6b7a95",
            usePointStyle: true,
            boxWidth: 7,
            boxHeight: 7,
            padding: 14,
            font: { family: "'DM Sans'", size: 11, weight: 600 },
          },
        },
        tooltip: {
          backgroundColor: "rgba(6,10,16,.97)",
          titleColor: "#eef2fa",
          bodyColor: "#6b7a95",
          borderColor: "rgba(0,224,160,.15)",
          borderWidth: 1,
          padding: 12,
          callbacks: {
            title: (items) => `Хугацаа: ${items[0].label}`,
            label: (ctx) => ` ${ctx.dataset.label}: ${formatAxisValue(ctx.parsed.y, meta.unit)} ${meta.unit || ""}`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: "#4a5568", autoSkip: true, maxTicksLimit: 8, font: { family: "'DM Sans'", size: 10 } },
          grid: { color: "rgba(255,255,255,.03)" },
        },
        y: {
          ticks: { color: "#4a5568", font: { family: "'DM Sans'", size: 10 } },
          grid: { color: "rgba(255,255,255,.04)" },
        },
      },
    },
  });
}

function ensureCharts(chartsPayload) {
  Object.entries(chartsPayload).forEach(([metricKey, meta]) => {
    dashboardState.chartsMeta[metricKey] = meta;
    if (!chartRegistry[metricKey]) {
      chartRegistry[metricKey] = createChart(metricKey, meta);
    }
  });
}

function updateCharts(chartsPayload) {
  ensureCharts(chartsPayload);
  Object.entries(chartsPayload).forEach(([metricKey, series]) => {
    const chart = chartRegistry[metricKey];
    if (!chart) return;
    chart.data.labels = series.labels || [];
    chart.data.datasets[0].data = series.baseline || [];
    chart.data.datasets[1].data = series.scenario || [];
    chart.update();
  });
}

function applyParameterMeta(parameters) {
  parameters.forEach((meta) => {
    dashboardState.parametersMeta[meta.key] = meta;
    const slider = document.getElementById(meta.key);
    const valueEl = document.getElementById(`val_${meta.key}`);
    if (!slider || !valueEl) return;

    slider.min = meta.min;
    slider.max = meta.max;
    slider.step = meta.step;
    slider.value = meta.value;
    valueEl.textContent = formatDisplayValue(meta.value, meta.value_format);

    const card = slider.closest(".param-card");
    if (card) {
      const labelEl = card.querySelector(".param-label");
      const unitEl = card.querySelector(".param-unit");
      if (labelEl) labelEl.textContent = meta.label;
      if (unitEl) unitEl.textContent = String(meta.unit || "").toUpperCase();
    }
  });
}

function wireParameterEvents() {
  Object.keys(dashboardState.parametersMeta).forEach((key) => {
    const slider = document.getElementById(key);
    const meta = dashboardState.parametersMeta[key];
    if (!slider || slider.dataset.bound === "true") return;

    slider.dataset.bound = "true";
    slider.addEventListener("input", () => {
      const valueEl = document.getElementById(`val_${key}`);
      if (valueEl) valueEl.textContent = formatDisplayValue(slider.value, meta.value_format);

      dashboardState.scenarioOverrides.parameters[key] = Number(slider.value);

      showLoading(true, "Симуляци тооцоолж байна...");
      hideError();

      if (dashboardState.debounceTimer) {
        clearTimeout(dashboardState.debounceTimer);
      }
      dashboardState.debounceTimer = setTimeout(runScenarioSimulation, 350);
    });
  });
}

function setSliderValuesToDefault() {
  dashboardState.scenarioOverrides.parameters = {};
  dashboardState.scenarioOverrides.variables = {};
  dashboardState.scenarioOverrides.initial_values = {};

  Object.values(dashboardState.parametersMeta).forEach((meta) => {
    const slider = document.getElementById(meta.key);
    const valueEl = document.getElementById(`val_${meta.key}`);
    if (!slider) return;

    slider.value = meta.default;
    if (valueEl) {
      valueEl.textContent = formatDisplayValue(meta.default, meta.value_format);
    }
  });
}

document.getElementById("resetParamsBtn")?.addEventListener("click", () => {
  setSliderValuesToDefault();
  showLoading(true, "Симуляци тооцоолж байна...");
  hideError();
  runScenarioSimulation();
});
async function initializeDashboard() {
  showLoading(true, "Суурь симуляци уншиж байна...");
  hideError();

  try {
    const res = await fetch(`${API_BASE}/api/dashboard/init`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Dashboard эхлүүлэхэд алдаа гарлаа.");

    dashboardState.chartOrder = data.chart_order || [];
    applyParameterMeta(data.parameters || []);

    dashboardState.scenarioOverrides.parameters = {};
    dashboardState.scenarioOverrides.variables = {};
    dashboardState.scenarioOverrides.initial_values = {};

    wireParameterEvents();
    updateCharts(data.charts || {});
    dashboardState.isInitialized = true;
  } catch (error) {
    showError(error.message || "Симуляци амжилтгүй.");
  } finally {
    showLoading(false);
  }
}

async function runScenarioSimulation() {
  if (dashboardState.isRunning) {
    dashboardState.pendingRun = true;
    return;
  }

  dashboardState.isRunning = true;
  dashboardState.pendingRun = false;
  showLoading(true, "Симуляци тооцоолж байна...");
  hideError();

  try {
    const res = await fetch(`${API_BASE}/api/dashboard/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getCurrentScenarioPayload()),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Симуляци амжилтгүй.");

    updateCharts(data.charts || {});
  } catch (error) {
    showError(error.message || "Симуляци амжилтгүй.");
  } finally {
    dashboardState.isRunning = false;
    showLoading(false);

    if (dashboardState.pendingRun) {
      dashboardState.pendingRun = false;
      runScenarioSimulation();
    }
  }
}

function applyDashboardSyncToState(syncPayload) {
  if (!syncPayload || typeof syncPayload !== "object") return false;

  let changed = 0;

  const incomingParameters = syncPayload.parameters || {};
  Object.entries(incomingParameters).forEach(([key, value]) => {
    const slider = document.getElementById(key);
    const meta = dashboardState.parametersMeta[key];
    if (!slider || !meta) return;

    slider.value = value;
    dashboardState.scenarioOverrides.parameters[key] = Number(value);

    const valueEl = document.getElementById(`val_${key}`);
    if (valueEl) {
      valueEl.textContent = formatDisplayValue(value, meta.value_format);
    }
    changed += 1;
  });

  changed += mergeOverrideValues(
    dashboardState.scenarioOverrides.variables,
    syncPayload.variables || {}
  );

  changed += mergeOverrideValues(
    dashboardState.scenarioOverrides.initial_values,
    syncPayload.initial_values || {}
  );

  return changed > 0;
}

async function syncDashboardFromChat(syncPayload, showResultsPage = true) {
  const changed = applyDashboardSyncToState(syncPayload);
  if (!changed) return false;

  if (showResultsPage) {
    showResults();
  }

  await runScenarioSimulation();

  const description = describeDashboardSync(syncPayload);
  if (description) {
    addBubble(
      `Чатботын simulation-ийн дагуу dashboard дээр ${description} шинэчлэгдэж, "Дэвшүүлж буй хувилбар" дахин тооцоологдлоо.`,
      "bot"
    );
  }

  return true;
}

// =========================
// CHAT RENDER
// =========================
function renderChatResult(data) {
  const wrapper = createBotBubbleContainer();

  const answerBlock = document.createElement("div");
  answerBlock.innerHTML = formatAnswerToHtml(data.answer || "Хариулт хоосон ирлээ.");
  wrapper.appendChild(answerBlock);

  const summary = extractSummaryData(data);
  if (summary) {
    wrapper.appendChild(createSectionTitle("Товч үр дүн"));

    const cardRow = document.createElement("div");
    cardRow.style.display = "flex";
    cardRow.style.flexWrap = "wrap";
    cardRow.style.gap = "10px";

    cardRow.appendChild(createInfoCard("Үзүүлэлт", summary.metricName, "Сонгосон KPI", "#ffffff"));
    cardRow.appendChild(createInfoCard("Суурь хувилбар", formatNumber(summary.baselineEnd), "Сүүлийн жилийн утга", "#00e0a0"));
    cardRow.appendChild(createInfoCard("Дэвшүүлж буй хувилбар", formatNumber(summary.scenarioEnd), "Сүүлийн жилийн утга", "#ff5fad"));
    cardRow.appendChild(createInfoCard("Өөрчлөлт", formatPercent(summary.endPctChange), "Суурьтай харьцуулсан зөрүү", "#8fb8ff"));

    wrapper.appendChild(cardRow);
  }

  if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
    wrapper.appendChild(createSectionTitle("Санал болгож буй сонголтууд"));
    wrapper.appendChild(createSuggestions(data.suggestions));
  } else {
    wrapper.appendChild(createSectionTitle("Хариултын хэлбэр"));
    wrapper.appendChild(createResponseStyleButtons());
  }

  const utilityRow = createButtonRow();

  const copyBtn = createActionButton("Хуулах");
  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(data.answer || "");
      copyBtn.textContent = "Хуулагдлаа";
      setTimeout(() => {
        copyBtn.textContent = "Хуулах";
      }, 1200);
    } catch (_) {}
  });
  utilityRow.appendChild(copyBtn);

  if (data.dashboard_sync) {
    const syncBtn = createActionButton("Параметрт тусгах", "primary");
    syncBtn.addEventListener("click", async () => {
      const applied = await syncDashboardFromChat(data.dashboard_sync, true);
      if (!applied) {
        addBubble("Dashboard параметртэй холбож чадсангүй.", "bot");
      }
    });
    utilityRow.appendChild(syncBtn);
  }

  wrapper.appendChild(utilityRow);

  if (Array.isArray(data.table_preview) && data.table_preview.length > 0) {
    wrapper.appendChild(createSectionTitle("Жагсаалт / хүснэгт"));
    wrapper.appendChild(createScrollableTable(data.table_preview.slice(0, 20)));
  }

  scrollChatToBottom();
}

async function sendChat(forcedText = null) {
  const message = forcedText !== null ? String(forcedText).trim() : chatInput?.value.trim();
  if (!message) return;

  addBubble(message, "user");
  if (forcedText === null && chatInput) chatInput.value = "";

  const loadingBubble = addBubble("Хариулт боловсруулж байна...", "bot");

  if (chatInput) chatInput.disabled = true;
  if (chatSendBtn) chatSendBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: getSessionId() }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Чатбот алдаа өглөө.");

    loadingBubble?.remove();
    renderChatResult(data);

    if (data.dashboard_sync) {
      await syncDashboardFromChat(data.dashboard_sync, false);
    }
  } catch (error) {
    if (loadingBubble) {
      loadingBubble.textContent = error.message || "Чатботтой холбогдож чадсангүй.";
    } else {
      addBubble(error.message || "Чатботтой холбогдож чадсангүй.", "bot");
    }
  } finally {
    if (chatInput) {
      chatInput.disabled = false;
      chatInput.focus();
    }
    if (chatSendBtn) chatSendBtn.disabled = false;
  }
}

chatToggleBtn?.addEventListener("click", toggleChat);
chatCloseBtn?.addEventListener("click", closeChat);
chatClearBtn?.addEventListener("click", clearChatHistory);
chatGreetingCloseBtn?.addEventListener("click", () => hideGreetingPreview(true));
chatSendBtn?.addEventListener("click", () => sendChat());
chatInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});
maybeShowGreetingPreview();

// =========================
// HERO MINI CHART
// =========================
function initHeroChart() {
  const canvas = document.getElementById("heroMiniChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, 140);
  gradient.addColorStop(0, "rgba(0,224,160,.2)");
  gradient.addColorStop(1, "rgba(0,224,160,.0)");

  new Chart(ctx, {
    type: "line",
    data: {
      labels: Array.from({ length: 12 }, (_, i) => i + 1),
      datasets: [
        {
          data: [125, 132, 128, 140, 138, 150, 145, 162, 170, 165, 178, 190],
          borderColor: "#00e0a0",
          backgroundColor: gradient,
          fill: true,
          borderWidth: 2,
          tension: 0.45,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } },
    },
  });
}

initHeroChart();
initializeDashboard();
