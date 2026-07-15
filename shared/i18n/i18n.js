/** Client-side i18n for Income Agent desktop app (22 languages). */
let _locales = null;
let _languages = null;
let _lang = localStorage.getItem("income_agent_lang") || "ru";

const SUPPORTED = [
  "en","ru","zh","es","hi","ar","pt","bn","ja","de","fr","ko","it","tr","vi","pl","uk","id","nl","th","he","sv",
];

export function normalizeLang(code) {
  if (!code) return "ru";
  const c = String(code).toLowerCase().split("-")[0];
  return SUPPORTED.includes(c) ? c : "ru";
}

export async function loadI18n() {
  if (_locales) return;
  const [locRes, langRes] = await Promise.all([
    fetch("../shared/i18n/locales.json"),
    fetch("../shared/i18n/languages.json"),
  ]);
  _locales = await locRes.json();
  _languages = await langRes.json();
}

export function getLang() {
  return normalizeLang(_lang);
}

export function setLang(code) {
  _lang = normalizeLang(code);
  localStorage.setItem("income_agent_lang", _lang);
}

export function t(key, params = {}) {
  const bucket = (_locales && _locales[key]) || {};
  const lang = getLang();
  let text = bucket[lang] || bucket.en || bucket.ru || key;
  for (const [k, v] of Object.entries(params)) {
    text = text.replaceAll(`{${k}}`, String(v));
  }
  return text;
}

export function languageList() {
  return SUPPORTED.map((code) => ({ code, name: (_languages && _languages[code]) || code }));
}

export function applyDom() {
  const map = {
    "h1.title": "desktop_title",
    "p.subtitle": "desktop_subtitle",
    "h2.mission": "desktop_mission",
    "h2.orders": "desktop_orders",
    "h2.telegram": "desktop_telegram",
    "h3.dispatch": "desktop_dispatch",
    "p.env-hint": "desktop_env_hint",
    "footer": "desktop_footer",
    "#btnHunt": "desktop_hunt",
    "#btnRefresh": "desktop_refresh",
    "#btnDash": "desktop_kpi",
    "#btnSheet": "desktop_sheet",
    "#btnLang": "desktop_lang",
    "#btnGrok": "btn_grok",
    "#btnCodex": "btn_codex",
    "#btnApprove": "btn_approve",
    "#btnReject": "btn_reject",
    "#btnEdit": "btn_edit",
    "#btnProject": "btn_create_project",
    "#btnManual": "btn_manual",
  };
  for (const [sel, key] of Object.entries(map)) {
    const el = sel.startsWith("#") ? document.querySelector(sel) : document.querySelector(sel);
    if (el) el.textContent = t(key);
  }
}