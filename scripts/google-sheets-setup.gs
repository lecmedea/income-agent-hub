/**
 * Income Agent — Control Panel setup for Google Sheets
 * Spreadsheet ID: 10wtmzMIgWqPazB0yT1huNLw44W6qsM5qHhwQIYoRcqs
 *
 * Как установить: Extensions → Apps Script → вставить этот файл → Run → setupAll
 */
function setupAll() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  setupSheetOrders_(ss);
  setupSheetKPI_(ss);
  setupSheetFinance_(ss);
  setupSheetPlatforms_(ss);
  setupSheetSkills_(ss);
  setupSheetReports_(ss);
  setupSheetAgentQueue_(ss);
  SpreadsheetApp.flush();
}

function setupSheetOrders_(ss) {
  let sh = ss.getSheetByName('Orders') || ss.insertSheet('Orders');
  sh.clear();
  const headers = [
    'ID', 'Площадка', 'Заказ', 'URL', 'Бюджет', 'Score', 'Стадия',
    'Отклик', 'Дедлайн', 'KPI', 'План ₽', 'Факт ₽', 'Агент', 'Обновлено', 'Заметки'
  ];
  sh.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
  sh.setFrozenRows(1);
  const stages = ['new','review','proposed','approved','in_progress','grok','codex','delivered','invoiced','paid','rejected'];
  const rule = SpreadsheetApp.newDataValidation().requireValueInList(stages, true).build();
  sh.getRange('G2:G5000').setDataValidation(rule);
}

function setupSheetKPI_(ss) {
  let sh = ss.getSheetByName('KPI') || ss.insertSheet('KPI');
  sh.clear();
  sh.getRange('A1:B8').setValues([
    ['Метрика', 'Значение'],
    ['Лидов за неделю', '=COUNTA(Orders!A:A)-1'],
    ['В работе', '=COUNTIF(Orders!G:G,"in_progress")+COUNTIF(Orders!G:G,"grok")+COUNTIF(Orders!G:G,"codex")'],
    ['Сдано', '=COUNTIF(Orders!G:G,"delivered")'],
    ['Оплачено', '=COUNTIF(Orders!G:G,"paid")'],
    ['План выручки ₽', '=SUM(Orders!K:K)'],
    ['Факт выручки ₽', '=SUM(Orders!L:L)'],
    ['Конверсия %', '=IFERROR(COUNTIF(Orders!G:G,"paid")/(COUNTA(Orders!A:A)-1),0)'],
  ]);
}

function setupSheetFinance_(ss) {
  let sh = ss.getSheetByName('Finance') || ss.insertSheet('Finance');
  sh.clear();
  sh.getRange('A1:F1').setValues([['Дата', 'Заказ ID', 'Описание', 'Сумма ₽', 'Статус', 'ЭДО/счёт']]).setFontWeight('bold');
}

function setupSheetPlatforms_(ss) {
  let sh = ss.getSheetByName('Platforms') || ss.insertSheet('Platforms');
  sh.clear();
  const rows = [
    ['Площадка', 'URL профиля', 'Описание профиля', 'Услуги', 'Объявления', 'Последняя проверка', 'Заметки'],
    ['FL.ru', 'https://www.fl.ru/users/lecmedea/', 'AI-креатор, сайты, SMM', 'Сайты, AI-боты, SEO', '', '', 'Проверить отклики'],
    ['Kwork', 'https://kwork.ru/user/lecmedea', 'Нейрокреатор', 'Кворки: сайт, AI', '', '', ''],
    ['hh.ru', 'https://hh.ru/applicant/resumes', 'AI-маркетолог remote', 'Резюме', '', '', ''],
    ['GitHub', 'https://github.com/lecmedea', 'Портфолио репозиториев', 'azimut-medline-site, skills', '', '', ''],
    ['vc.ru', 'https://vc.ru/u/lecmedea', 'Кейсы AI', 'Статьи', '', '', ''],
    ['Telegram @iicnica', 'https://t.me/iicnica', 'Витрина услуг', 'Посты', '', '', ''],
    ['TikTok @iicnica', 'https://www.tiktok.com/@iicnica', 'AI-контент', 'Ролики', '', '', ''],
    ['Азимут Клиник', 'https://azimutclinic.ru', 'Кейс клиники + AI чат', 'Сайт', '', '', ''],
    ['Grillz Customs', 'https://grillzcustoms.ru', 'Премиум лендинг', 'Сайт', '', '', ''],
  ];
  sh.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sh.getRange(1, 1, 1, rows[0].length).setFontWeight('bold');
}

function setupSheetSkills_(ss) {
  let sh = ss.getSheetByName('Skills_GitHub') || ss.insertSheet('Skills_GitHub');
  sh.clear();
  const rows = [
    ['Skill / Repo', 'GitHub URL', 'Описание', 'Триггеры', 'Статус'],
    ['income-agent', 'https://github.com/lecmedea/income-agent-skills', 'Автономный поиск заказов', '/income-agent hunt', 'active'],
    ['income-agent-schedule', 'https://github.com/lecmedea/income-agent-skills', 'Расписание без лишних токенов', 'schedule', 'active'],
    ['russian-marketing-2026', 'https://github.com/lecmedea/income-agent-skills', 'Маркетинг РФ по трендам Чижова', 'маркетинг, SMM', 'active'],
    ['income-agent-autonomy', 'https://github.com/lecmedea/income-agent-skills', 'Легальная автономия заработка', 'заработать', 'active'],
    ['income-agent-hub', 'https://github.com/lecmedea/income-agent-hub', 'Telegram + Desktop пульт', 'Agent00AI', 'active'],
    ['chrome-operator', 'https://github.com/lecmedea/chrome-operator', 'Автономный Chrome для Grok', 'chrome, sheets, github', 'active'],
  ];
  sh.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sh.getRange(1, 1, 1, rows[0].length).setFontWeight('bold');
}

function setupSheetReports_(ss) {
  let sh = ss.getSheetByName('Reports') || ss.insertSheet('Reports');
  sh.clear();
  sh.getRange('A1:D1').setValues([['ID', 'Тип', 'Текст', 'Дата']]).setFontWeight('bold');
}

function setupSheetAgentQueue_(ss) {
  let sh = ss.getSheetByName('AgentQueue') || ss.insertSheet('AgentQueue');
  sh.clear();
  sh.getRange('A1:E1').setValues([['Order ID', 'Агент', 'Файл задачи', 'Задача', 'Дата']]).setFontWeight('bold');
}