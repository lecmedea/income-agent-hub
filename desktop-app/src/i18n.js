/** Client-side i18n for Income Agent desktop app (22 languages). */
window.I18N = (function () {
  const SUPPORTED = [
    "en","ru","zh","es","hi","ar","pt","bn","ja","de","fr","ko","it","tr","vi","pl","uk","id","nl","th","he","sv",
  ];
  let locales = null;
  let languages = null;
  let lang = localStorage.getItem("income_agent_lang") || "ru";

  function normalizeLang(code) {
    if (!code) return "ru";
    const c = String(code).toLowerCase().split("-")[0];
    return SUPPORTED.includes(c) ? c : "ru";
  }

  async function load() {
    if (locales) return;
    const base = pathToShared();
    const [locRes, langRes] = await Promise.all([
      fetch(`${base}/locales.json`),
      fetch(`${base}/languages.json`),
    ]);
    locales = await locRes.json();
    languages = await langRes.json();
  }

  function pathToShared() {
    return "i18n-data";
  }

  function getLang() {
    return normalizeLang(lang);
  }

  function setLang(code) {
    lang = normalizeLang(code);
    localStorage.setItem("income_agent_lang", lang);
  }

  function t(key, params) {
    params = params || {};
    const bucket = (locales && locales[key]) || {};
    const l = getLang();
    let text = bucket[l] || bucket.en || bucket.ru || key;
    Object.keys(params).forEach((k) => {
      text = text.split(`{${k}}`).join(String(params[k]));
    });
    return text;
  }

  function languageList() {
    return SUPPORTED.map((code) => ({ code, name: (languages && languages[code]) || code }));
  }

  function applyDom() {
    const set = (id, key) => {
      const el = document.getElementById(id);
      if (el) el.textContent = t(key);
    };
    set("titleMain", "desktop_title");
    set("subtitleMain", "desktop_subtitle");
    set("hMission", "desktop_mission");
    set("hOrders", "desktop_orders");
    set("hTelegram", "desktop_telegram");
    set("hDispatch", "desktop_dispatch");
    set("envHint", "desktop_env_hint");
    set("footerText", "desktop_footer");
    set("btnHunt", "desktop_hunt");
    set("btnRefresh", "desktop_refresh");
    set("btnDash", "desktop_kpi");
    set("btnSheet", "desktop_sheet");
    set("btnLang", "desktop_lang");
    set("btnGrok", "btn_grok");
    set("btnCodex", "btn_codex");
    set("btnApprove", "btn_approve");
    set("btnReject", "btn_reject");
    set("btnEdit", "btn_edit");
    set("btnProject", "btn_create_project");
    set("btnManual", "btn_manual");
  }

  return { SUPPORTED, load, getLang, setLang, t, languageList, applyDom };
})();