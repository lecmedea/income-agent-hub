const logEl = document.getElementById("log");
const ordersEl = document.getElementById("orders");
const orderPick = document.getElementById("orderPick");
const statusEl = document.getElementById("status");
const tgInfo = document.getElementById("tgInfo");

let orders = [];

function log(msg) {
  logEl.textContent = `[${new Date().toLocaleTimeString()}] ${msg}\n` + logEl.textContent;
}

async function refreshOrders() {
  orders = await window.agent007.hub("GET", "/orders");
  ordersEl.innerHTML = orders
    .slice(0, 12)
    .map(
      (o, i) => `<div class="card"><b>${i + 1}. [${o.score}/10] ${o.stage}</b>${o.title}<small>${o.url || ""}</small></div>`
    )
    .join("");
  orderPick.innerHTML = orders
    .map((o, i) => `<option value="${i}">${i + 1}. ${o.title.slice(0, 60)}</option>`)
    .join("");
}

async function init() {
  const env = await window.agent007.env();
  tgInfo.textContent = `Bot: @Agent00AI_bot · Chat ID: ${env.INCOME_AGENT_TG_CHAT_ID || "—"}`;
  try {
    await window.agent007.hub("GET", "/health");
    statusEl.textContent = "HUB ONLINE";
    statusEl.style.borderColor = "#2d6a4f";
    await refreshOrders();
  } catch (e) {
    statusEl.textContent = "HUB OFFLINE — run start-hub.sh";
    statusEl.style.borderColor = "#8b2635";
    log(String(e));
  }
}

document.getElementById("btnHunt").onclick = async () => {
  log("Hunt started…");
  const res = await window.agent007.hub("POST", "/hunt?telegram=0");
  log(`Imported ${res.imported} leads`);
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

async function dispatch(agent) {
  const idx = Number(orderPick.value);
  const o = orders[idx];
  if (!o) return log("No order selected");
  const task = `Подготовь отклик и план сдачи: ${o.title} ${o.url}`;
  const res = await window.agent007.hub("POST", `/orders/${o.id}/dispatch`, { agent, task });
  log(`${agent.toUpperCase()} queued: ${res.task_file}`);
  await refreshOrders();
}

document.getElementById("btnGrok").onclick = () => dispatch("grok");
document.getElementById("btnCodex").onclick = () => dispatch("codex");
document.getElementById("btnApprove").onclick = async () => {
  const idx = Number(orderPick.value);
  const o = orders[idx];
  if (!o) return;
  await window.agent007.hub("PATCH", `/orders/${o.id}/stage`, { stage: "approved", notes: "Desktop approve" });
  log(`Approved: ${o.title}`);
  await refreshOrders();
};

init();