// TIDOSZIT Control Center — interface language (English default, Arabic with right-to-left layout).
// Keys are the English texts. Your own data (prompts, playbooks, file names, model names) is never translated.

const KEY = "tidoszit.lang";
const LANGS = { en: { dir: "ltr", name: "English" }, ar: { dir: "rtl", name: "العربية" } };

export const lang = (() => {
  try { const v = localStorage.getItem(KEY); return LANGS[v] ? v : "en"; } catch { return "en"; }
})();

export function setLang(v) {
  try { localStorage.setItem(KEY, v); } catch { /* private mode: this page only */ }
  location.reload(); // the session cookie survives; every panel re-renders in the new language
}

const AR = {
  // ---- login
  "System": "النظام",
  "TIDOS Control Center": "مركز تحكم TIDOS",
  "A Player is trying to access the TIDOS control center. Identity verification is required.": "لاعبٌ يحاول الدخول إلى مركز تحكم TIDOS. يلزم التحقق من الهوية.",
  "1 · GOOGLE IDENTITY": "1 · هوية Google",
  "2 · CONTROL PASSWORD": "2 · كلمة مرور التحكم",
  "Verify identity with Google": "تحقّق من الهوية عبر Google",
  "Only the TIDOS owner's Google account is accepted.": "لا يُقبل إلا حساب Google الخاص بمالك TIDOS.",
  "CONTROL PASSWORD": "كلمة مرور التحكم",
  "Enter": "دخول",
  "Type it here only — never in an AI chat or terminal.": "اكتبها هنا فقط، ولا تكتبها أبدًا في محادثة ذكاء اصطناعي أو في الطرفية.",
  "[FIRST RUN]": "[التشغيل الأول]",
  "No control password exists yet. Set one now. Only its PBKDF2 hash is stored (Firestore, owner-only).": "لا توجد كلمة مرور تحكم بعد. عيّن واحدة الآن. لا يُخزَّن إلا بصمتها PBKDF2 (في Firestore، للمالك فقط).",
  "NEW CONTROL PASSWORD (10+ chars, 3 of: a-z A-Z 0-9 symbols)": "كلمة مرور تحكم جديدة (10 أحرف فأكثر، و3 أنواع من: a-z A-Z 0-9 رموز)",
  "CONFIRM": "تأكيد",
  "Set password & enter": "عيّن كلمة المرور وادخل",
  "Opening Google sign-in…": "جارٍ فتح تسجيل الدخول عبر Google…",
  "Verifying owner identity…": "جارٍ التحقق من هوية المالك…",
  "Verification failed.": "فشل التحقق.",
  "Owner verified. Set your control password.": "تم التحقق من المالك. عيّن كلمة مرور التحكم.",
  "Owner verified.": "تم التحقق من المالك.",
  "Sign-in cancelled.": "أُلغي تسجيل الدخول.",
  "Sign-in error.": "خطأ في تسجيل الدخول.",
  "[LOCKED] Too many wrong passwords. Try again in {t}.": "[مقفل] كلمات مرور خاطئة كثيرة. حاول مجددًا بعد {t}.",
  "Lock lifted. You may try again.": "رُفع القفل. يمكنك المحاولة مجددًا.",
  "{n} attempt(s) left before lockout.": "المحاولات المتبقية قبل القفل: {n}.",
  "Login failed.": "فشل الدخول.",
  "Passwords do not match.": "كلمتا المرور غير متطابقتين.",
  "Control password set. Only its hash is stored.": "عُيّنت كلمة مرور التحكم. لا تُخزَّن إلا بصمتها.",
  "Setup failed.": "فشل الإعداد.",
  "Control center unavailable.": "مركز التحكم غير متاح.",
  // server messages
  "Wrong password.": "كلمة المرور خاطئة.",
  "Current password is wrong.": "كلمة المرور الحالية خاطئة.",
  "Too many wrong passwords. Locked.": "كلمات مرور خاطئة كثيرة. تم القفل.",
  "Sign in with Google first.": "سجّل الدخول عبر Google أولًا.",
  "This Google account is not the TIDOS owner.": "حساب Google هذا ليس مالك TIDOS.",
  "Google sign-in could not be verified.": "تعذّر التحقق من تسجيل الدخول عبر Google.",
  "Setup is only available before a password exists.": "الإعداد متاح فقط قبل وجود كلمة مرور.",
  "Mix at least 3 of: lowercase, uppercase, digits, symbols.": "استخدم 3 أنواع على الأقل من: أحرف صغيرة، أحرف كبيرة، أرقام، رموز.",
  "login required": "يلزم تسجيل الدخول",
  "empty question": "السؤال فارغ",

  // ---- top bar, tabs, ask bar
  "// CONTROL CENTER": "// مركز التحكم",
  "Log out": "خروج",
  "session {t}": "الجلسة {t}",
  "Status": "الحالة",
  "Live Monitor": "المراقبة المباشرة",
  "Security": "الأمان",
  "Dungeons": "الزنزانات",
  "Playbooks": "خطط العمل",
  "🔒 Model Arena": "🔒 ساحة النماذج",
  "Unlocks in Phase 6 — Weak-model driver": "تُفتح في المرحلة 6 — قيادة النماذج الضعيفة",
  "Memory": "الذاكرة",
  "Evolution": "التطوّر",
  "Tool Scout": "كشّاف الأدوات",
  "Ask TIDOS (why did Flutter tasks fail this month?) or search traces, playbooks, memory, evals": "اسأل TIDOS (لماذا فشلت مهام Flutter هذا الشهر؟) أو ابحث في السجلات وخطط العمل والذاكرة والتقييمات",
  "Ask": "اسأل",
  "Search": "بحث",
  "Answer": "الإجابة",
  "Ask TIDOS": "اسأل TIDOS",
  "Thinking over your traces…": "يحلّل سجلاتك…",
  "failed": "فشل",
  "Data TIDOS used (sent to the model)": "البيانات التي استخدمها TIDOS (أُرسلت إلى النموذج)",
  "Data TIDOS used (local only)": "البيانات التي استخدمها TIDOS (محليًا فقط)",
  "No match for: {w}": "لا نتائج لـ: {w}",
  "Welcome back, Player. Control center unlocked.": "مرحبًا بعودتك أيها اللاعب. فُتح مركز التحكم.",
  "Session expired. Verify again.": "انتهت الجلسة. تحقّق مجددًا.",
  "Logged out.": "تم تسجيل الخروج.",

  // ---- status
  "LEVEL": "المستوى",
  "XP · next level at": "XP · المستوى التالي عند",
  "XP = evidence: tasks whose checks passed (bonus when right first time), minus your corrections. Engine: tidos_learn/xp.py.": "XP = أدلة: مهام نجحت فحوصها (مع مكافأة عند النجاح من أول مرة)، ناقص تصحيحاتك. المحرّك: tidos_learn/xp.py.",
  "Stats": "الخصائص",
  "Daily Quests": "المهام اليومية",
  "System Notifications": "إشعارات النظام",
  "Domains": "المجالات",
  "Models": "النماذج",
  "Quest Log": "سجل المهام",
  "Shadow Army — your subagents": "جيش الظلال — وكلاؤك الفرعيون",
  "LEVEL UP!": "ارتفع المستوى!",
  "Level {a} → {b} · Rank {r}": "المستوى {a} ← {b} · الرتبة {r}",
  "Sessions": "الجلسات", "Tasks": "المهام", "Cleared": "المنجزة", "Failed": "الفاشلة",
  "Tokens in": "الرموز الداخلة", "Tokens out": "الرموز الخارجة", "Player": "اللاعب",
  "Intelligence": "الذكاء", "Precision": "الدقة", "Discipline": "الانضباط", "Wisdom": "الحكمة", "Agility": "الرشاقة",
  "success rate of tasks with a clear outcome": "نسبة نجاح المهام ذات النتيجة الواضحة",
  "last test/lint/build run passed": "آخر تشغيل للاختبار أو الفحص أو البناء نجح",
  "tasks that edited code AND ran a verification": "مهام عدّلت الكود وشغّلت تحققًا",
  "answers the user did not have to correct": "إجابات لم يضطر المستخدم إلى تصحيحها",
  "tasks finished without a tool error": "مهام انتهت دون خطأ في الأدوات",
  "Clear 3 verified tasks": "أنجز 3 مهام مُتحقَّق منها",
  "Zero corrections today": "صفر تصحيحات اليوم",
  "Verify every code edit": "تحقّق من كل تعديل في الكود",
  "Quests reset daily (UTC).": "تتجدد المهام يوميًا (UTC).",
  "No domains yet.": "لا مجالات بعد.",
  "{n} tasks": "{n} مهمة",
  "avg {v}": "المتوسط {v}",
  "No models yet.": "لا نماذج بعد.",
  "[QUEST CLEARED]": "[مهمة منجزة]",
  "No cleared quests yet.": "لا مهام منجزة بعد.",
  "Nothing needs your attention.": "لا شيء يحتاج انتباهك.",
  "draft": "مسودة", "active": "نشط",
  "{n} mission(s)": "المهمات: {n}",
  "No subagents yet.": "لا وكلاء فرعيون بعد.",

  // ---- live
  "Active Sessions": "الجلسات النشطة",
  "Recording:": "التسجيل:",
  "· switch it in Security.": "· يُغيَّر من تبويب الأمان.",
  "ON": "مفعّل", "PAUSED": "متوقف",
  "Event Stream": "تدفق الأحداث",
  "TIDOS Session": "جلسة TIDOS",
  "Does GUIDE mode help? (weak models, real work)": "هل يساعد وضع التوجيه؟ (نماذج ضعيفة، عمل حقيقي)",
  "Model": "النموذج", "Guided tasks": "مهام موجَّهة", "Checks passed": "الفحوص الناجحة", "Unguided tasks": "مهام غير موجَّهة",
  "Guided = done within 12 h after a GUIDE-mode START TIDOS in the same project and tool.": "موجَّهة = أُنجزت خلال 12 ساعة بعد START TIDOS بوضع التوجيه في المشروع والأداة نفسيهما.",
  "Recent Tasks": "أحدث المهام",
  "When": "الوقت", "Project": "المشروع", "Task": "المهمة", "Tools": "الأدوات", "Verify": "التحقق", "Score": "التقييم", "Outcome": "النتيجة",
  "Mode": "الوضع", "Tier": "الفئة", "Tool": "الأداة", "Started": "البداية",
  "LEARN": "تعلّم", "GUIDE": "توجيه",
  "No START TIDOS yet.": "لم يُشغَّل START TIDOS بعد.",
  "No weak-model work recorded yet.": "لم يُسجَّل عمل لنماذج ضعيفة بعد.",
  "No live events yet. Install the brain hooks, then use Claude Code — events stream here in real time.": "لا أحداث مباشرة بعد. افتح جلسة Claude Code جديدة (الخطافات مثبّتة) — تظهر الأحداث هنا لحظيًا.",
  "last: {t}": "الأخير: {t}",
  "{n} events": "الأحداث: {n}",
  "{n} errors": "الأخطاء: {n}",
  "{n} err": "{n} خطأ",
  "No session active in the last 10 minutes.": "لا جلسة نشطة خلال آخر 10 دقائق.",
  "pass": "نجح", "fail": "فشل",
  "success": "نجاح", "failure": "فشل", "unknown": "غير معروف", "corrected": "مُصحَّح",

  // ---- dungeons
  "Arena Leaderboard — does TIDOS make models stronger?": "لوحة الصدارة — هل يجعل TIDOS النماذج أقوى؟",
  "Agent": "الوكيل", "Without TIDOS": "بدون TIDOS", "With TIDOS": "مع TIDOS", "TIDOS lift": "تحسين TIDOS", "Cost": "التكلفة",
  "Dungeon Map": "خريطة الزنزانات",
  "Dungeon": "الزنزانة",
  "Run a raid from a terminal:": "شغّل غارة من الطرفية:",
  "· free models:": "· النماذج المجانية:",
  "free": "مجاني", "plain": "عادي", "never": "أبدًا",
  "{n} pts": "{n} نقطة",
  "No raids yet. Run the command below.": "لا غارات بعد. شغّل الأمر أدناه.",
  "{n} dungeons · last raid {w} · lift = pass rate with TIDOS minus without.": "{n} زنزانة · آخر غارة {w} · التحسين = نسبة النجاح مع TIDOS ناقص بدونه.",

  // ---- evolution
  "Evolution Queue — improving TIDOS itself": "طابور التطوّر — تحسين TIDOS نفسه",
  "Proposal": "الاقتراح", "Priority": "الأولوية", "Decide": "القرار",
  "Accepted proposals can be implemented by": "يمكن تنفيذ الاقتراحات المقبولة بواسطة",
  "on a separate branch, gated by all checks, never pushed. You review and merge.": "على فرع منفصل، بعد اجتياز كل الفحوص، ولا يُرفع أبدًا. أنت تراجع وتدمج.",
  "Daily Quest": "المهمة اليومية",
  "Run:": "التشغيل:",
  "Unlocked Drafts": "المسودات المفتوحة",
  "high": "عالية", "medium": "متوسطة", "low": "منخفضة",
  "new": "جديد", "accepted": "مقبول", "rejected": "مرفوض", "implemented": "منفَّذ",
  "Accept": "اقبل", "Reject": "ارفض",
  "No proposals yet. Agents add them with tidos_propose; you with tidos_learn proposals --add.": "لا اقتراحات بعد. يضيفها الوكلاء عبر tidos_propose، وأنت عبر tidos_learn proposals --add.",
  "Proposal #{id} {s}.": "الاقتراح #{id}: {s}.",
  "Last run": "آخر تشغيل", "Result": "النتيجة",
  "Skill drafts": "مسودات المهارات", "Specialist drafts": "مسودات المتخصصين", "Issue drafts": "مسودات القضايا",

  // ---- tool scout
  "Tool Scout — capabilities TIDOS can recommend": "كشّاف الأدوات — قدرات يمكن لـ TIDOS أن يوصي بها",
  "Capability": "القدرة", "Installed": "مثبّتة", "Trust": "الثقة", "Used": "الاستخدام", "Actions": "الإجراءات",
  "Approve a tool, then Install: TIDOS installs only approved catalog tools, pinned to an exact version or a verified download, in your user account (switch tool_install in Security). MCP servers stay manual.": "وافق على الأداة ثم اضغط «ثبّت»: لا يثبّت TIDOS إلا أدوات الكتالوج الموافق عليها، بإصدار محدد أو بتنزيل مُتحقَّق منه، داخل حساب المستخدم فقط (مفتاح tool_install في تبويب الأمان). خوادم MCP تبقى يدوية.",
  "Install": "ثبّت", "Uninstall": "أزل التثبيت",
  "Install {name}?": "تثبيت {name}؟",
  "Uninstall {name}?": "إزالة تثبيت {name}؟",
  "Trust {n}/100. Your user account only, no administrator rights. Logged; Uninstall removes it.": "الثقة {n}/100. داخل حسابك فقط، دون صلاحيات المدير. يُسجَّل في سجل الأمان، ويمكن إزالته بزر «أزل التثبيت».",
  "Installing {name}… (can take a few minutes)": "جارٍ تثبيت {name}… (قد يستغرق بضع دقائق)",
  "installed": "تم التثبيت", "uninstalled": "أُزيل التثبيت",
  "installed, but not detected yet": "ثُبّتت لكن لم تُكتشف بعد",
  "Tool Scout may install a tool you approved when you press Install (pinned version or verified download, your user account only)": "يسمح لكشّاف الأدوات بتثبيت أداة وافقت عليها عند ضغط «ثبّت» (إصدار محدد أو تنزيل مُتحقَّق منه، داخل حسابك فقط)",
  "the tool_install switch is off (Security tab)": "مفتاح tool_install متوقف (تبويب الأمان)",
  "Per project:": "لكل مشروع:",
  "yes": "نعم", "no": "لا",
  "Vet": "افحص", "Approve": "وافق", "Ban": "احظر", "Unban": "ألغِ الحظر",
  "proposed": "مقترحة", "approved": "موافق عليها", "blacklisted": "محظورة", "none": "بلا حالة",

  // ---- memory + playbooks
  "Memory Explorer — private, in ~/.tidos": "مستكشف الذاكرة — خاص، في ‎~/.tidos",
  "File": "الملف", "Kind": "النوع", "Lines": "الأسطر",
  "Read-only. Edit the files themselves; drafts become active only when you move them (see each draft's last line).": "للقراءة فقط. عدّل الملفات نفسها؛ لا تصبح المسودات فعّالة إلا عندما تنقلها أنت (انظر آخر سطر في كل مسودة).",
  "Select a file": "اختر ملفًا",
  "Not found.": "غير موجود.",
  "Memory is empty.": "الذاكرة فارغة.",
  "Playbook Library — what TIDOS learned": "مكتبة خطط العمل — ما تعلّمه TIDOS",
  "Type": "النوع", "Rank": "الرتبة", "Conf.": "الثقة", "Evidence": "الأدلة", "Served": "مرات الاستخدام", "On": "مفعّلة",
  "Select a playbook": "اختر خطة عمل",
  "Nothing learned yet. Work with a strong model, then START TIDOS.": "لم يُتعلَّم شيء بعد. اعمل مع نموذج قوي، ثم شغّل START TIDOS.",
  "{n} playbooks in {dir} · served = times a GUIDE brief gave it to a weaker model · switched off = never served.": "{n} خطة عمل في {dir} · مرات الاستخدام = عدد المرات التي قدّمها موجز التوجيه لنموذج أضعف · الموقوفة لا تُقدَّم أبدًا.",
  "Playbook switched off.": "أُوقفت خطة العمل.",
  "Playbook switched on.": "فُعّلت خطة العمل.",

  // ---- security
  "Kill Switches": "مفاتيح الإيقاف",
  "Session & Lock": "الجلسة والقفل",
  "Change Control Password": "تغيير كلمة مرور التحكم",
  "CURRENT": "الحالية", "NEW": "الجديدة", "CONFIRM NEW": "تأكيد الجديدة",
  "Change password": "غيّر كلمة المرور",
  "Settings — config/framework.md": "الإعدادات — config/framework.md",
  "Brain Backups": "النسخ الاحتياطية للدماغ",
  "Back up now": "انسخ احتياطيًا الآن",
  "Restore is terminal-only (it replaces your brain):": "الاستعادة من الطرفية فقط (لأنها تستبدل دماغك):",
  "Security Log": "سجل الأمان",
  "Time (UTC)": "الوقت (UTC)", "Event": "الحدث", "Detail": "التفاصيل",
  "default": "افتراضي", "changed": "مُعدَّل",
  "Session ends in": "تنتهي الجلسة بعد", "{n} min": "{n} دقيقة",
  "Lock": "القفل", "locked until {w}": "مقفل حتى {w}", "open": "مفتوح",
  "Attempts before lockout": "المحاولات قبل القفل", "Brain": "الدماغ",
  "New passwords do not match.": "كلمتا المرور الجديدتان غير متطابقتين.",
  "Password changed.": "تم تغيير كلمة المرور.",
  "Failed.": "فشل.",
  "Saved {k} = {v}": "حُفظ {k} = {v}",
  "No backups yet.": "لا نسخ احتياطية بعد.",
  "Brain backed up.": "تم نسخ الدماغ احتياطيًا.",
  // kill switches (tidos_brain/control.py)
  "Record Claude Code sessions into the brain": "تسجيل جلسات Claude Code في الدماغ",
  "Run the GitHub update gate on START TIDOS": "تشغيل بوابة التحديث من GitHub عند START TIDOS",
  "Persona factory may commit + push generated personas": "يسمح لمصنع الشخصيات بحفظ الشخصيات المولَّدة ورفعها",
  "Community sync may open upstream pull requests": "يسمح لمزامنة المجتمع بفتح طلبات دمج في المستودع الأصلي",
  "ChatGPT browser relay (experimental, ToS risk)": "وسيط ChatGPT عبر المتصفح (تجريبي، خطر مخالفة شروط الخدمة)",
  "After strong-model sessions, a cheap strong model writes advice notes (max 2 per START, $0.05 each)": "بعد جلسات النماذج القوية، يكتب نموذج قوي رخيص ملاحظات نصح (حتى 2 لكل START، بحد 0.05$ لكل منها)",
  "Require Google sign-in at START TIDOS (the /TIDOSZIT owner login is always on)": "طلب تسجيل الدخول عبر Google عند START TIDOS (دخول المالك إلى /TIDOSZIT مفعّل دائمًا)",
  "Ask TIDOS may send a sanitized digest of your traces to a cheap Claude model ($0.05 cap); off = local search only": "يسمح لـ «اسأل TIDOS» بإرسال ملخص منقّى من سجلاتك إلى نموذج Claude رخيص (بحد 0.05$)؛ الإيقاف = بحث محلي فقط",
  // settings (tidos_dashboard/explore.py)
  "Persona factory may generate new personas": "يسمح لمصنع الشخصيات بتوليد شخصيات جديدة",
  "Factory commits personas on a review branch and opens a PR": "يحفظ المصنع الشخصيات على فرع مراجعة ويفتح طلب دمج",
  "Sessions/sources needed before generating a persona": "عدد الجلسات/المصادر اللازمة قبل توليد شخصية",
  "At most one factory run per START TIDOS": "تشغيل واحد للمصنع على الأكثر لكل START TIDOS",
  "ChatGPT browser relay (also needs the gptid kill switch)": "وسيط ChatGPT عبر المتصفح (يحتاج أيضًا مفتاح gptid)",
  "Relay mode": "وضع الوسيط",
  "Relay connect timeout": "مهلة اتصال الوسيط",
  "Max wait for a ChatGPT answer": "أقصى انتظار لإجابة ChatGPT",
  "Max context sent to ChatGPT": "أقصى سياق يُرسل إلى ChatGPT",
  "Max files attached per request": "أقصى عدد ملفات مرفقة لكل طلب",
};

// Messages built by the server with numbers inside (tidos_dashboard/stats.py notifications).
const AR_PATTERNS = [
  [/^(\d+) new proposal\(s\) to review in Evolution\.$/, "اقتراحات جديدة للمراجعة في تبويب التطوّر: $1."],
  [/^Proposal #(\d+) implemented on branch (\S+) - review and merge if you agree\.$/, "نُفِّذ الاقتراح #$1 على الفرع $2 — راجعه وادمجه إن وافقت."],
  [/^Daily quest (\S+): (.*)$/, "المهمة اليومية $1: $2"],
  [/^Unlocked: (\d+) skill draft\(s\), (\d+) specialist draft\(s\) - see Memory\.$/, "فُتحت: $1 مسودة مهارة و$2 مسودة متخصص — انظر تبويب الذاكرة."],
  [/^No daily quest report yet: (.*)$/, "لا يوجد تقرير للمهمة اليومية بعد: $1"],
  [/^Use at least (\d+) characters\.$/, "استخدم $1 أحرف على الأقل."],
];

/** Translate an interface text. Unknown texts (your data) come back unchanged. */
export function t(text, vars = {}) {
  let out = text;
  if (lang === "ar") {
    if (Object.prototype.hasOwnProperty.call(AR, text)) out = AR[text];
    else for (const [re, rep] of AR_PATTERNS) if (re.test(text)) { out = text.replace(re, rep); break; }
  }
  return out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
}

const norm = (s) => s.replace(/\s+/g, " ").trim();

/** Translate the page's static texts once at load, and set the direction. */
export function applyStatic(root = document.body) {
  document.documentElement.lang = lang;
  document.documentElement.dir = LANGS[lang].dir;
  if (lang === "en") return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (n.parentElement.closest("code, pre, script, style") || !norm(n.nodeValue)
      ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const n of nodes) {
    const key = norm(n.nodeValue);
    if (Object.prototype.hasOwnProperty.call(AR, key)) {
      const lead = /^\s/.test(n.nodeValue) ? " " : "", trail = /\s$/.test(n.nodeValue) ? " " : "";
      n.nodeValue = lead + AR[key] + trail;
    }
  }
  for (const el of root.querySelectorAll("[placeholder], [title]")) {
    for (const attr of ["placeholder", "title"]) {
      const v = el.getAttribute(attr);
      if (v && Object.prototype.hasOwnProperty.call(AR, norm(v))) el.setAttribute(attr, AR[norm(v)]);
    }
  }
  document.title = "TIDOSZIT — " + AR["TIDOS Control Center"];
}

/** The language switch buttons: show the OTHER language's name. */
export function wireSwitches() {
  const other = lang === "ar" ? "en" : "ar";
  document.querySelectorAll(".lang-switch").forEach((b) => {
    b.textContent = LANGS[other].name;
    b.setAttribute("lang", other);
    b.addEventListener("click", () => setLang(other));
  });
}
