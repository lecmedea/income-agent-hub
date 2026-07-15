const logEl = document.getElementById("log");
const ordersEl = document.getElementById("orders");
const orderPick = document.getElementById("orderPick");
const statusEl = document.getElementById("status");
const tgInfo = document.getElementById("tgInfo");
const langPick = document.getElementById("langPick");

let orders = [];

function log(msg) {
  logEl.textContent = `[${new Date().toLocaleTimeString()}] ${msg}\n` + logEl.textContent;
}

function tr(key, params) {
  return window.I18N.t(key, params);
}

async function refreshOrders() {
  orders = await window.agent007.hub("GET", "/orders");
  ordersEl.innerHTML = orders
    .slice(0, 12)
    .map(
      (o, i) =>
        `<div class="card" data-idx="${i}"><b>${i + 1}. [${o.score}/10] ${o.stage}</b>${o.title}<small>${o.url || ""}</small></div>`
    )
    .join("");
  orderPick.innerHTML = orders
    .map((o, i) => `<option value="${i}">${i + 1}. ${o.title.slice(0, 60)}</option>`)
    .join("");
}

function setupLangPicker() {
  langPick.innerHTML = window.I18N.languageList()
    .map((l) => `<option value="${l.code}">${l.name}</option>`)
    .join("");
  langPick.value = window.I18N.getLang();
  langPick.onchange = () => {
    window.I18N.setLang(langPick.value);
    window.I18N.applyDom();
    log(tr("lang_set", { name: langPick.options[langPick.selectedIndex].text }));
  };
}

async function init() {
  await window.I18N.load();
  window.I18N.applyDom();
  setupLangPicker();

  const env = await window.agent007.env();
  tgInfo.textContent = `Bot: @Agent00AI_bot · Chat ID: ${env.INCOME_AGENT_TG_CHAT_ID || "—"}`;
  try {
    await window.agent007.hub("GET", "/health");
    statusEl.textContent = tr("desktop_hub_online");
    statusEl.style.borderColor = "#2d6a4f";
    await refreshOrders();
  } catch (e) {
    statusEl.textContent = tr("desktop_hub_offline");
    statusEl.style.borderColor = "#8b2635";
    log(String(e));
  }
}

document.getElementById("btnHunt").onclick = async () => {
  log(tr("hunt_start"));
  const res = await window.agent007.hub("POST", "/hunt?telegram=0");
  log(tr("hunt_ok", { count: res.imported, stdout: "" }).split("\n")[0]);
  await refreshOrders();
};

document.getElementById("btnRefresh").onclick = () => refreshOrders();

document.getElementById("btnDash").onclick = async () => {
  const d = await window.agent007.hub("GET", "/dashboard");
  log(JSON.stringify(d, null, 2));
};

document.getElementById("btnSheet").onclick = async () => {
  const d = await window.agent007.hub("GET", "/dashboard");
  window.open(d.sheet_url, "_blank");
};

document.getElementById("btnLang").onclick = () => langPick.focus();

async function patchStage(stage, notes) {
  const idx = Number(orderPick.value);
  const o = orders[idx];
  if (!o) return log(tr("no_orders"));
  await window.agent007.hub("PATCH", `/orders/${o.id}/stage`, { stage, notes });
  log(`${stage}: ${o.title}`);
  await refreshOrders();
}

async function dispatch(agent) {
  const idx = Number(orderPick.value);
  const o = orders[idx];
  if (!o) return log(tr("no_orders"));
  const task = `Подготовь отклик и план сдачи: ${o.title} ${o.url}`;
  const res = await window.agent007.hub("POST", `/orders/${o.id}/dispatch`, { agent, task });
  log(tr("dispatched", { agent: agent.toUpperCase(), file: res.task_file }));
  await refreshOrders();
}

document.getElementById("btnGrok").onclick = () => dispatch("grok");
document.getElementById("btnCodex").onclick = () => dispatch("codex");
document.getElementById("btnApprove").onclick = () => patchStage("approved", "Desktop approve");
document.getElementById("btnReject").onclick = () => patchStage("rejected", "Desktop reject");
document.getElementById("btnEdit").onclick = async () => {
  const note = prompt(tr("edit_prompt", { n: Number(orderPick.value) + 1 }));
  if (note) await patchStage("review", note);
};
document.getElementById("btnProject").onclick = () => patchStage("in_progress", "Project created from desktop");
document.getElementById("btnManual").onclick = () => patchStage("in_progress", "Manual execution");

init();