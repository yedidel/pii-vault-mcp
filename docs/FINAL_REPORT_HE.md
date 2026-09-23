# הערות המרה ל-Word (לא חלק מגוף העבודה)

מסמך זה מיועד להמרה לדוח אקדמי ב-Microsoft Word. אין למספר עמודים ידנית.

**עמוד:** A4; שוליים עליון 3.18 ס״מ, תחתון 2.54 ס״מ; שוליים ימין/שמאל לפי תבנית המוסד (פריסת כריכה תואמת RTL).  
**גוף:** עברית David 12pt; אנגלית Arial 12pt; ריווח שורות 1.5.  
**כותרת 1:** 16pt מודגש ממוספר — פרק. **כותרת 2:** 14pt מודגש ממוספר. **כותרת 3:** 12pt מודגש ממוספר.  
**כיוון:** עברית RTL; מזהים טכניים LTR.  
**איורים:** כיתוב מתחת; **טבלאות:** כותרת מעל. לייצר תוכן עניינים, רשימת איורים ורשימת טבלאות אוטומטית מסגנונות.  
**מקור האיורים:** `docs/diagrams/source/*.mmd` — לייצא ל-Word לאחר רינדור.

סיווג חוזר לאורך הדוח:

- **א. ממומש** בזרימת הריצה
- **ב. חלקי**
- **ג. תלות חיצונית**
- **ד. mock / הדגמה**
- **ה. עבודה עתידית**

---

# THE BRIDGE

**A Secure Mediation and Process Orchestration Layer for AI Agents**

שכבת תיווך ואורקסטרציית תהליכים לסוכני בינה מלאכותית

מגישות: אסתר הדס וקנין ודבורה עינב  
מנחה: ידידאל לוק  
בשיתוף: CoralOS

המחלקה להנדסת תוכנה  
מכון טל  
המרכז האקדמי לב  
שנת תשפ״ו

---

# תקציר

סוכני בינה מלאכותית מסוגלים לבצע פעולות בשם משתמשים, אך שילובם במערכות המחזיקות מידע אישי או פיננסי מעלה שתי בעיות חופפות: חשיפת מידע רגיש להקשר של מודל השפה, וניהול תהליכים א-סינכרוניים שאינם מסתיימים בתוך קריאת request–response אחת. כאשר הסוכן מקבל גישה ישירה לסודות, לפרטי תשלום או לממשקי אישור, גדל שטח התקיפה — ובפרט הסיכון לדליפה בעקבות Prompt Injection. במקביל, פעולות כגון אימות אמון, אישור משתמש או מילוי טופס דורשות המתנה חיצונית, והסוכן אינו אמור להחזיק חיבור פתוח לאורך זמן.

פרויקט **The Bridge**, שפותח בשיתוף CoralOS, מציע שכבת תיווך ואורקסטרציה המפרידה בין סביבת קבלת ההחלטות של הסוכן לבין סביבת שמירת הסודות וביצוע הפעולה הרגישה. העיקרון המנחה הוא Context Separation: הסוכן מגדיר *מה* לבצע ומספק הקשר שאינו רגיש; רכיב Backend מתמשך מנהל *כיצד* התהליך מתקדם.

המימוש הוא אב-טיפוס הנדסי מקצה לקצה. **Bridge** ב-Kotlin וב-Spring Boot חושף ממשק gRPC מבוסס Protocol Buffers, שומר `Action` ו-`Workflow` ב-PostgreSQL, ומניע מכונת מצבים באמצעות Apache Kafka. שער HTTP מדבר עם **Guardian**, ושער WebSocket מדבר עם **Vault**. במאגר הקוד עצמו, השירותים הרצים להדגמה הם **guardian-mock** ו-**mock-vault** — כלומר שער האינטגרציה ממומש (סיווג א), ואילו שירותי האמון והכספת המשמשים בהרצה הם עמיתים מדגמיים (סיווג ד) הניתנים להחלפה בשירות חיצוני (סיווג ג).

שכבת **Agent Adapter** ב-Python חושפת לסוכן כלי MCP: `send_action`, `store_pii` ו-`get_action_status`. ה-Adapter ממפה את הקריאה ל-gRPC, שומר מיפוי מקומי של תהליכים ממתינים בזיכרון, ומקבל עם סיום התהליך — במסלול ברירת המחדל — webhook מן ה-Bridge. לאחר מכן הוא מעיר את הפלטפורמה המתאימה: Claude Channel ב-Claude Code, Responses API ב-OpenAI, Interactions API ב-Gemini, או לקוח SDK. לקוחות מקומיים יכולים להאזין ל-SSE. צימוד משתמש–כספת (pairing) ושירות **Install Directory** מומשו כהדגמה אופציונלית.

המערכת מדגימה תרחיש מלא: קבלת בקשה, אימות סוכן, פנייה ל-Vault, התמדת מצב, השלמה והמשך שיחה בלי להחזיר לסוכן את ערכי ה-PII עצמם. התרומה היא ארכיטקטורה מודולרית, בלתי תלויה בספק AI בליבת ה-Bridge, המתאימה לתהליכים ארוכי טווח. הדוח מבחין במפורש בין יכולות ממומשות, יכולות חלקיות (למשל מחבר POLLING בצד Bridge כ-stub, אימות HMAC התלוי בסוג התעבורה, ושחזור Workflow בעת עלייה בלבד) לבין אבטחת ייצור כגון TLS ואימות gRPC, שאינן ממומשות.

**מילות מפתח:** סוכני AI, MCP, gRPC, Workflow, Kafka, Context Separation, Continuation, webhook.

---

# Abstract

AI agents can act on behalf of users, but integrating them with systems that hold personal or financial data creates two coupled problems: sensitive values entering the language-model context, and long-running operations that cannot finish inside a single request–response turn. Direct tool access to secrets and approval APIs enlarges the attack surface, including prompt-injection leakage. User approval, trust checks, and form filling also require waiting on external events, so the agent session should not remain the system of record.

**The Bridge**, developed with CoralOS, is a mediation and orchestration layer guided by Context Separation: the agent states *what* should happen without receiving secrets; a durable backend decides *how* the process advances.

The implementation is a functional end-to-end prototype. A Kotlin / Spring Boot **Bridge** exposes a Protocol Buffers gRPC API, persists actions and workflows in PostgreSQL, and drives a Kafka-backed state machine. HTTP and WebSocket gateways talk to **Guardian** and **Vault**. In this repository the runnable peers used for demonstration are **guardian-mock** and **mock-vault**: the integration gateways are implemented, while the trust and vault *services* used in the lab are mocks and may be replaced by external systems.

A Python **Agent Adapter** exposes MCP tools `send_action`, `store_pii`, and `get_action_status`, maps calls to gRPC, and — by default — receives a completion webhook. It then performs provider-specific continuation (Claude Channel, OpenAI Responses, Gemini Interactions, or an SDK client) and may notify local clients over SSE. Optional user–vault pairing via a mock Install Directory is included.

The prototype demonstrates accept, verify, wait, persist, complete, and resume without returning raw PII to the agent. The contribution is a modular, provider-independent orchestration core. The report distinguishes implemented behaviour from partial paths (Bridge POLLING/THREAD stubs, transport-dependent HMAC, startup-only recovery) and from production controls such as TLS and gRPC authentication, which are not implemented.

**Keywords:** AI agents, MCP, gRPC, workflow, Kafka, context separation, continuation, webhook.

---

# תודות

בראש ובראשונה, ברצוננו להביע את תודתנו למנחה הפרויקט, ידידאל לוק, על הליווי, ההכוונה והמשוב לאורך שלבי המחקר והפיתוח.

תודה לחברת CoralOS על שיתוף הפעולה, האמון והמסגרת שבה נבחנה הארכיטקטורה.

תודה לסגל המחלקה להנדסת תוכנה במרכז האקדמי לב – מכון טל, על הכלים והתמיכה האקדמית.

תודה למשפחותינו, לבני הזוג ולחברים על הסבלנות והעידוד.

---

# תוכן עניינים

*(יווצר אוטומטית ב-Word מכותרות הסגנון.)*

# רשימת איורים

*(יווצר אוטומטית מכיתובי האיורים.)*

# רשימת טבלאות

*(יווצר אוטומטית מכותרות הטבלאות.)*

---

# 1. מבוא

## 1.1 הקשר ומוטיבציה

השימוש בסוכני AI עובר ממענה לשאלות לביצוע פעולות: תשלומים, מילוי טפסים, גישה לשירותים דיגיטליים ועבודה עם נתונים אישיים. ברגע שסוכן פועל בשם המשתמש הוא נכנס לשרשרת אמון הכוללת זהות, הרשאות, סודות ותוצאות בעולם האמיתי. מתן גישה ישירה לכל המידע הדרוש מפשט מימוש, אך מגדיל את שטח התקיפה ואת הנזק האפשרי במקרה של Prompt Injection או התנהגות בלתי אמינה.

בעיה נוספת נובעת מאופיין הזמני של אינטראקציות עם מודלי שפה. פעולות רבות אינן מסתיימות מיד: נדרש אישור משתמש, בדיקת אמון או תגובה ממערכת חיצונית. סוכן במודל request–response אינו אמור להחזיק חיבור פתוח דקות או שעות, ו-polling מתמשך תלוי בכך שהשיחה עדיין פעילה.

## 1.2 הרעיון המרכזי

The Bridge מעביר את אחריות ניהול התהליך מן הסוכן אל שכבת Backend מתמשכת. הסוכן מציין מה ברצונו לבצע; ה-Bridge יוצר Action ו-Workflow, מתאם בין Guardian ל-Vault, שומר מצב וממשיך עם אירועים חיצוניים. כאשר התהליך מסתיים, Adapter מקומי מחזיר תוצאה לסוכן במנגנון המתאים לפלטפורמה. ליבת ה-Bridge אינה מכירה את Claude, OpenAI או Gemini; זהות הספק נשמרת ב-Adapter.

## 1.3 מבנה הדוח

פרק 2 מציג רקע תאורטי. פרק 3 מגדיר בעיה, מטרות וגבולות. פרק 4 מפרט דרישות. פרק 5 דן בחלופות. פרקים 6–11 מתארים ארכיטקטורה ומימוש לפי הקוד הנוכחי. פרק 12 דן באבטחה כפי שמומשה בפועל. פרקים 13–16 מציגים בדיקות, תוצאות, מגבלות, עבודה עתידית וסיכום.

---

# 2. רקע תאורטי ומחקרי

## 2.1 סוכני AI וכלי פעולה

סוכן AI משלב מודל שפה עם קריאה לכלים חיצוניים. המודל מפרש כוונה ומחליט איזה כלי להפעיל; הביצוע מתרחש ברכיב תוכנה נפרד. הפרדה זו מאפשרת ולידציה ורישום, אך אינה פותרת לבדה את חשיפת המידע *בתוך* הקשר המודל אם הכלי מחזיר סודות או אם הסוכן נדרש לספק אותם כפרמטרים.

## 2.2 Prompt Injection והפרדת הקשר

הפרויקט נשען על מחקר של Yedidel Louck, Ariel Stulman ו-Amit Dvir בנושא אבטחת תקשורת בין סוכני AI למערכות חיצוניות [1]. הממצא המנחה הוא שהעברת מידע רגיש להקשר המודל מגדילה סיכון לדליפה כאשר קלט זדוני משפיע על התנהגות הסוכן. **Context Separation** מצמצם סיכון זה בהפרדה בין הקשר ההסקה של הסוכן לבין הקשר שמירת הסודות ושימוש בהם.

## 2.3 Model Context Protocol

MCP הוא פרוטוקול לכלים והקשר בין יישומי מודלים לבין שרתי כלים [2]. במערכת זו MCP הוא ממשק הסוכן מול ה-Adapter, לא מול ה-Bridge. הסוכן רואה כלים ידידותיים; ה-Adapter ממפה ל-gRPC. נתמכים תעבורת stdio ו-Streamable HTTP.

## 2.4 אורקסטרציה וארכיטקטורה מונחית אירועים

אורקסטרציה מרכזת את מחזור החיים של תהליך רב-שלבי. בארכיטקטורה מונחית אירועים, שינוי משמעותי מיוצג כאירוע הנכתב ליומן/תור ונצרך במנותק מהקריאה המקורית [5]. כך קליטת בקשה אינה נחסמת עד סיום Vault, ורכיבים מגיבים בלי coupling סינכרוני מלא.

## 2.5 מכונת מצבים ותהליכים ארוכי טווח

תהליך ארוך טווח חייב לשמור מצב מחוץ לזיכרון התהליך, לדעת באיזה שלב הוא נמצא, ולהמשיך אחרי אירוע או הפעלה מחדש. בפרויקט נשמרת הבחנה בין `StatusType` הנראה לסוכן ב-gRPC לבין `WorkflowState` ו-`WorkflowStep` הפנימיים.

## 2.6 gRPC ו-Protocol Buffers

gRPC מספק RPC טיפוסי מעל HTTP/2, ו-Protocol Buffers מגדירים חוזה שדות [3]. הבחירה מתאימה לגבול Python–Kotlin: קובץ `.proto` אחד מייצר stubs בשתי השפות ומפחית אי-התאמות.

## 2.7 WebSocket ו-Server-Sent Events

WebSocket הוא ערוץ דו-כיווני מעל HTTP, מתאים ללקוח כספת שמתחבר לשרת ומקבל בקשות הערכה [REFERENCE REQUIRED: RFC 6455 או תיעוד Spring WebSocket]. SSE הוא זרם חד-כיווני מהשרת לדפדפן/לקוח [REFERENCE REQUIRED: HTML SSE / WHATWG], ומשמש כאן להודעת לקוחות מקומיים על `workflow.updated`.

## 2.8 תיווך אבטחה

Mediation ממקם נקודת בקרה בין הסוכן למערכות רגישות: ולידציית סוג פעולה, רישום, בדיקת אמון והעברת המשך. זהו עקרון תכנון, לא טענה שכל ערוץ התקשורת מוצפן או מאומת בייצור.

---

# 3. הגדרת הבעיה ומטרות הפרויקט

## 3.1 הגדרת הבעיה

כיצד לאפשר לסוכן AI לבצע פעולה רגישה בשם משתמש, בלי לחשוף לסוכן את המידע האישי או הפיננסי הנדרש לביצוע, ובמקביל לתמוך בתהליך א-סינכרוני שעשוי להמתין לאישור — בלי לאבד את רציפות התהליך או השיחה?

## 3.2 מטרות

1. ניהול מחזור חיים של Action ו-Workflow לאורך זמן.
2. הפרדה בין מצב ציבורי לסוכן לבין מצב פנימי של המנוע.
3. ממשק אחיד שאינו תלוי בספק AI יחיד בליבת ה-Bridge.
4. המשך יזום של שיחת הסוכן לאחר אירוע חיצוני, כאשר webhook הוא המסלול הראשי.
5. הדגמת תרחיש הכולל Guardian, Vault, התמדה והמשך שיחה — גם אם עמיתי ההדגמה הם mocks.

## 3.3 גבולות הפרויקט

**כלול במאגר:** ליבת Bridge (Kotlin/Spring): מנוע Workflow, PostgreSQL, Kafka, שערי Guardian/Vault; Adapter (Python): MCP, gRPC client, webhook, SSE, ספקי wake; Claude Channel; לקוחות OpenAI/Gemini; `bridge-sdk`; מנגנון pairing אופציונלי; Install Directory מדגמי; guardian-mock; mock-vault; demo-forms.

**אינו כלול כייצור:** פריסת ענן, High Availability, TLS, אימות gRPC, חומרה מאובטחת, Guardian/Vault מסחריים. מחברי Bridge מסוג `POLLING` ו-`THREAD` קיימים כ-stub. המערכת היא **אב-טיפוס פונקציונלי** המוכיח היתכנות ארכיטקטונית.

---

# 4. דרישות המערכת

## 4.1 דרישות פונקציונליות

**טבלה 4.1 – דרישות פונקציונליות**

| מזהה | דרישה | מימוש נוכחי |
|---|---|---|
| FR-1 | הסוכן ישלח פעולה ב-MCP `send_action` | א |
| FR-1b | ניתן לאחסן PII מקומית ולהחזיר `vault://` ב-`store_pii` | א (חנות Adapter) |
| FR-2 | ה-Adapter יעביר בקשה ב-gRPC | א, ערוץ insecure ל-localhost |
| FR-3 | Bridge ייצור מזהים וישמור Action ו-Workflow | א |
| FR-4 | בדיקת Guardian ופנייה ל-Vault | א מול mocks בהדגמה |
| FR-5 | שמירת סטטוס, מצב וצעד | א, חלק מהשדות/המצבים אינם בשימוש בזרימה החיה |
| FR-6 | המשך בעקבות Kafka או Vault | א |
| FR-7 | בסיום יישלח webhook כאשר `connector_type=WEBHOOK` | א ברירת מחדל; POLLING ב-Bridge הוא stub |
| FR-8 | Adapter יעיר פלטפורמה ויודיע ללקוח | א לספקים שמומשו |
| FR-9 | קריאת סטטוס ב-`get_action_status` | א, כולל לולאת המתנה קצרה ב-MCP |
| FR-10 | pairing עם QR / PAIRING_REQUIRED | ב+ד, מותנה ב-`INSTALL_DIRECTORY_URL` |
| FR-11 | FILL_FORM עם הפשטת PII ל-`vault://` | א |

## 4.2 דרישות לא-פונקציונליות

**טבלה 4.2 – דרישות לא-פונקציונליות**

| תחום | דרישה | הערה |
|---|---|---|
| אבטחה | מידע רגיש לא ייכנס להקשר הסוכן | מושג ארכיטקטונית; שני מאגרי “vault” — ראו פרק 12 |
| עמידות | מצב Workflow ב-PostgreSQL ושחזור אחרי הפעלה | שחזור בעליית Spring בלבד |
| מודולריות | התאמות ספק ב-Adapter | א |
| חוזה | gRPC/Protobuf כגבול שפות | א |
| הרחבה | Action types, handlers, providers | א בגבולות האב-טיפוס |
| ביצועים | לא נמדדו במסגרת פרויקט זה | אין לטעון מספרי ביצוע |

---

# 5. חלופות ושיקולי תכנון

## 5.1 תקשורת ישירה בין הסוכן למערכות הרגישות

נדחתה: מחייבת את הסוכן לקבל סודות ולוגיקת אינטגרציה, יוצרת coupling, ומנוגדת ל-Context Separation.

## 5.2 request–response ארוך

השארת קריאת MCP/gRPC פתוחה עד אישור פשוטה להבנה, אך חשופה ל-timeouts ומחזיקה משאבים. `SendAction` מחזיר מיד `RECEIVED` והעבודה נמשכת באירועים.

## 5.3 Polling

Polling שימושי כ-POC וככלי סטטוס. ב-MCP, `get_action_status` מבצע לולאת המתנה קצרה (עד כ-20 שניות) כל עוד הסטטוס הוא `RECEIVED` או `IN_PROGRESS`. בנוסף, כאשר `CONNECTOR_TYPE=POLLING`, **PollingWorker ב-Adapter** דוגם את Bridge. עם זאת **מחבר `PollingContinuation` ב-Bridge הוא stub**: ה-Bridge אינו דוחף עדכון במסלול זה. לכן polling אינו המסלול הראשי ואינו “מלא” בשתי השכבות.

## 5.4 Webhook ו-push continuation

נבחר push דו-שלבי: Bridge שולח webhook ל-Adapter עם סיום ה-Workflow; ה-Adapter מכיר platform ו-session ומפעיל provider. כך ה-Bridge נשאר בלתי תלוי בספק.

## 5.5 Adapter מקומי

ה-Adapter הוא שכבת Anti-Corruption: MCP, לקוח gRPC, webhook, מיפוי זמני, wake. הוספת ספק אינה דורשת שינוי במנוע.

## 5.6 gRPC ו-Protocol Buffers

חוזה טיפוסי בין Python ל-Kotlin. `bridge.proto` הוא מקור האמת לממשק הסוכן–Bridge. אין שדה `platform` בפרוטוקול — במכוון.

## 5.7 CHANNEL לעומת THREAD

`CHANNEL` ב-Bridge שולח HTTP POST כללי לכתובת ב-`connector_context`. זרימת Claude בפועל משתמשת בדרך כלל ב-WEBHOOK אל ה-Adapter, ואז ה-Adapter קורא ל-Claude Channel. `THREAD` הוא stub להרחבה עתידית.

## 5.8 PostgreSQL ו-Kafka

PostgreSQL נבחר להתמדת ישויות יחסית פשוטות (`actions`, `workflows`) עם JSONB להקשר. Kafka נבחר להפרדת פרסום אירוע מעיבודו ולאפשר חזרתיות צרכן. זו רציונל תכנון המוצדק ממבנה הקוד, לא ממדד עומס.

## 5.9 WebSocket מול Vault

הכספת מתחברת כלקוח אל ה-Bridge (`/vault-websocket`), מקבלת בקשת הערכה ומחזירה אישור/דחייה. המודל מתאים לרכיב שרץ אצל המשתמש או בשירות נפרד, ואינו דורש מה-Bridge לפתוח חיבור יוצא קבוע אל כל התקנה.

---

# 6. ארכיטקטורת המערכת

**איור 6.1** מציג את השכבות כפי שמומשו. מקור: `docs/diagrams/source/01-architecture.mmd`.

![איור 6.1 – ארכיטקטורת הסוכנים, ה-Adapter, ה-Bridge ועמיתי ההדגמה](diagrams/source/01-architecture.mmd)

## 6.1 רכיבים עיקריים

**טבלה 6.1 – רכיבי המערכת**

| רכיב | טכנולוגיה | אחריות | סיווג |
|---|---|---|---|
| Agent clients | Claude Code / openai-client / gemini-client | MCP והצגת המשך | א |
| Agent Adapter | Python, FastMCP | MCP→gRPC, webhook, wake, SSE, PII מקומי | א |
| Bridge | Kotlin, Spring Boot | Action/Workflow, שערים, Kafka | א |
| Workflow Engine | Kotlin + Kafka | מעברי מצב ופקודות | א |
| PostgreSQL | JPA `ddl-auto=update` | `actions`, `workflows` | א / תשתית מקומית |
| Kafka | topic `workflow-events` | תור אירועים | א / תשתית מקומית |
| Guardian gateway | RestTemplate | GET authenticate | א |
| guardian-mock | FastAPI :8001 | DID לרשימת היתר | ד |
| Vault gateway | WebSocket | בקשות הערכה | א |
| mock-vault | לקוח WS | אישור/דחייה בהדגמה | ד |
| Install Directory | Python :8010 | pairing / user_install_id | ד, אופציונלי |
| demo-forms | HTTP :9000 | יעד FILL_FORM | ד |
| bridge-sdk | Python | צרכן MCP+SSE | א כספריית לקוח; אינו תלות של ה-Adapter |
| Claude Channel | Node `bridge-wake` | `notifications/claude/channel` | א |

אין במערכת רכיב בשם Agent Notification Service.

## 6.2 חלוקת אחריות

הסוכן מבין כוונה; ה-Adapter מתאים פרוטוקולים ופלטפורמות; Bridge מנהל תהליך; Guardian בודק אמון; Vault (החיצוני) מאשר/מבצע פעולה רגישה; חנות PII ב-Adapter מצפינה ערכים מקומיים לפני שליחה ל-Bridge כמזהי ייחוס. חלוקה זו מצמצמת הרשאות ומונעת מרכיב יחיד להחזיק בכל ההקשרים.

## 6.3 Happy Path

**איור 6.2** מתאר את רצף ברירת המחדל WEBHOOK. מקור: `docs/diagrams/source/02-sequence.mmd`.

1. הסוכן קורא `send_action`.
2. ה-Adapter פותר pairing, מסנן PII ב-FILL_FORM, ושומר pending בזיכרון.
3. `SendAction` מחזיר `RECEIVED` מיד.
4. `ActionCreatedEvent` → Guardian → Vault → `ActionResponseReceivedEvent`.
5. עדכון סטטוס, `NotifyAgentCommand`, POST webhook.
6. `WakeDispatcher` מעיר את הספק; SSE ללקוח מקומי במידת הצורך.

---

# 7. תכנון מפורט ומימוש

## 7.1 מבנה ה-Bridge

נקודת הכניסה `bridge.GrpcServerKt` טוענת `agent-adapter/.env` (`EnvLoader`), מפעילה Spring Boot בפורט **8081** (ברירת מחדל) ושרת gRPC בפורט **50051** (קשיח בקוד, ללא TLS). `BridgeServiceImpl` מממש את השירות ומעביר אחריות ל-`ActionService`, `WorkflowInitializationService` ו-repositories.

**טבלה 7.1 – חבילות Bridge**

| חבילה | תפקיד |
|---|---|
| `bridge` | gRPC, ActionService, EnvLoader |
| `bridge.model` / `bridge.repository` | ישויות ו-JPA |
| `bridge.workflow*` | מנוע, handlers, Kafka, recovery |
| `bridge.integration` | Guardian/Vault gateways |
| `bridge.websocket` | `/vault-websocket` |
| `connectors.*` | WEBHOOK/CHANNEL ממשיים; POLLING/THREAD stubs |
| `continuation` | `ConnectorType`, `ContinuationRequest` |

**איור 7.1** (רכיבים): `docs/diagrams/source/05-components.mmd`.

## 7.2 ActionService

מחלקות פעולה מותרות: `PAYMENT`, `TRANSACTION`, `FILL_FORM`. ב-FILL_FORM, אם `email`/`password` אינם ריקים עליהם להתחיל ב-`vault://pii/`. נוצר `requestId`, נשמר `ActionEntity`, וקיים idempotency: בקשה זהה מאותו סוכן ובאותם פרמטרים בחלון **שתי דקות** מחזירה פעולה קיימת. אם כבר קיים Workflow לאותו `request_id`, `SendAction` אינו יוצר שני.

כישלון ולידציה מחזיר `StatusType.FAILED` בלי מזהים. כישלון אתחול Workflow אחרי שמירת Action עלול להשאיר פעולה יתומה — מגבלה ידועה.

## 7.3 WorkflowInitializationService

יוצר `WorkflowEntity` במצב `RECEIVED` ובצעד `ACTION_RECEIVED`, שומר `ActionContext` ב-`context_json`, ומפרסם `ActionCreatedEvent`.

## 7.4 שערים

`GuardianGatewayAdapter.verifyAgent` קורא GET קשיח אל `http://localhost:8001/v1/authenticate/agent?did=`. `status=="verified"` מפרסם `GuardianApprovedEvent`; אחרת או חריגה — `GuardianRejectedEvent`. `trustLevel` אינו משפיע על המעבר. `reportOutcome` ו-`verifyAgentSync` **אינם נקראים** בזרימה.

`VaultGatewayAdapter` שולח דרך `VaultWebSocketHandler`. תשובות `action_approved` / `action_rejected` הופכות ל-`ActionResponseReceivedEvent`. כשל שליחה עשוי להירשם בלוג בלבד ולהשאיר Workflow ב-`WAITING_FOR_VAULT_RESPONSE`.

## 7.5 Recovery

`WorkflowRecoveryScheduler` רץ פעם אחת ב-`ApplicationReadyEvent` (לא scheduler מחזורי). `WorkflowEngine.resume` הוא מצב-מונחה: חוזר על VerifyAgent או על בקשת Vault לפי המצב. ל-`IN_PROGRESS` אין פקודת שחזור, והמצב אינו מושג בזרימה החיה.

## 7.6 Adapter

כניסת התהליך: `adapter.py`. `MCP_TRANSPORT=http` מריץ ASGI אחד עם `/mcp` ונתיבי HTTP. `stdio` מריץ MCP ב-stdio **ו**FastAPI נפרד (`server.py`) ל-webhook/SSE. `main.py` הוא לקוח gRPC בלבד (`localhost:50051` insecure).

---

# 8. מנוע ה-Workflow וניהול מצבים

**איור 8.1** — מצבים בזרימה החיה: `docs/diagrams/source/03-workflow-states.mmd`.

## 8.1 State לעומת Step

`WorkflowState`: `RECEIVED`, `WAITING_FOR_GUARDIAN`, `WAITING_FOR_VAULT_RESPONSE`, `IN_PROGRESS`, `COMPLETED`, `FAILED`.

`WorkflowStep`: `ACTION_RECEIVED`, `VERIFY_AGENT`, `REQUEST_VAULT_EVALUATION`, `WAIT_FOR_VAULT_RESPONSE`, `NOTIFY_AGENT`, `FINISHED`.

**עובדות קוד:** `IN_PROGRESS` מופיע ב-enum וב-validator אך **לא מיושם במעבר חי**. הצעד `WAIT_FOR_VAULT_RESPONSE` **אינו משויך** ב-`TransitionCommand`. במעבר סופי, `WorkflowTransitionService` כופה `FINISHED`.

## 8.2 אירועים

**טבלה 8.1 – אירועי Workflow**

| אירוע | מקור | משמעות | עיבוד חי |
|---|---|---|---|
| ACTION_CREATED | אתחול Workflow | התחלת אימות | כן |
| GUARDIAN_APPROVED | GuardianGatewayAdapter | מעבר ל-Vault | כן |
| GUARDIAN_REJECTED | GuardianGatewayAdapter | כישלון/דחייה | כן |
| ACTION_RESPONSE_RECEIVED | VaultWebSocketHandler | תוצאת Vault | כן |
| WORKFLOW_COMPLETED | handler אחרי הצלחה | אירוע סיכום | מתפרסם אך **נדחה**: ה-validator דורש מצב `IN_PROGRESS` |
| WORKFLOW_FAILED | handler אחרי כישלון | אירוע סיכום | כנ״ל |

ההודעה לסוכן (`NotifyAgentCommand`) מתבצעת כבר ב-handlers של תשובת Vault / דחיית Guardian, ולכן דחיית אירועי הסיכום אינה מונעת webhook במסלול הרגיל — אך היא חוסר עקביות במכונת המצבים.

## 8.3 פקודות

Handlers מחזירים `WorkflowDecision`. `WorkflowCommandExecutor` מבצע `TransitionCommand`, `VerifyAgentCommand`, `RequestVaultEvaluationCommand`, `UpdateActionStatusCommand`, `PublishEventCommand`, `NotifyAgentCommand`. `WorkflowCommandType` ו-`last_executed_command` **אינם בשימוש** — אין idempotency ברמת פקודה.

נושא Kafka: `workflow-events`, groupId של הצרכן `workflow-engine`, retry `FixedBackOff` 2 שניות × 2 (שלושה ניסיונות).

## 8.4 סטטוס לסוכן

`StatusType` ב-proto כולל גם `WAITING_FOR_USER`, `IN_PROGRESS`, `EXPIRED`, `FAILED_APP_NOT_INSTALLED`. בקוד Kotlin נכתבים בפועל בעיקר `RECEIVED`, `COMPLETED`, `REJECTED`, `FAILED`. `GetActionStatus` אינו ממלא `updated_at`.

---

# 9. שכבת הסוכנים והמשך שיחה

## 9.1 תפקידי ה-Adapter

1. כלי MCP: `send_action`, `store_pii`, `get_action_status`.
2. מיפוי ל-`ActionRequest` ושליחת gRPC.
3. `POST /webhook/bridge`.
4. איתור platform/session מ-pending workflows.
5. `ClaudeProvider` / `OpenAIProvider` / `GeminiProvider` / `SdkProvider`.
6. SSE ב-`GET /events`.
7. pairing אופציונלי ו-`PiiVaultStore`.

## 9.2 Claude Code

Claude Code נטען עם `bridge-adapter` ועם `bridge-wake`. ה-Channel רושם URL ב-Adapter (`/continuation/register` במצב HTTP MCP). עם webhook, `ClaudeProvider` שולח POST לכתובת allowlist (localhost). ה-Channel מפיק `notifications/claude/channel`. כלי `get_continuation_context` שייך ל-Channel, לא ל-Adapter.

## 9.3 OpenAI

ה-Adapter משתמש במזהה conversation וקורא ל-Responses API. הלקוח המקומי מאזין ל-SSE ומעדכן תצוגה. נדרש `OPENAI_API_KEY` (תלות חיצונית).

## 9.4 Gemini

נשמר מזהה interaction; נוצר interaction המשכי עם `previous_interaction_id`. קיימים hooks ל-Gemini CLI, וכן POC נפרד בפורט 8010 שאינו השרת הראשי.

## 9.5 WebhookContinuation

כאשר `connector_type=WEBHOOK`, Bridge שולח JSON `{workflowId, requestId, status, message}`. ברירת המחדל של ה-Adapter: `http://127.0.0.1:8000/webhook/bridge`. שדה `status` הוא **שם מצב ה-Workflow**, לא בהכרח `StatusType`.

## 9.6 Polling

**ב. חלקי.** Adapter: `PollingWorker` כל 2 שניות (ברירת מחדל), timeout 120 שניות, עבור pending עם `POLLING`, ומעביר ל-`ContinuationService`. Bridge: `PollingContinuation` רק כותב ללוג. אין לתאר זאת כתמיכה מלאה בשתי השכבות.

## 9.7 bridge-sdk

ספריית Python חיצונית ל-Adapter. ה-Adapter אינו מייבא אותה; הוא רושם `SdkProvider` ש-wake שלו הוא no-op, והלקוח ממתין ל-SSE/סטטוס.

---

# 10. מודל הנתונים והתמדה

**איור 10.1** — ERD לוגי: `docs/diagrams/source/04-erd.mmd`. אין annotation של JPA `@OneToOne`; הקישור הוא `request_id` ייחודי ב-`workflows`.

## 10.1 ActionEntity

`request_id`, `agent_id`, `user_install_id`, `action_type`, `parameters_json`, `context_json` (**לא מאוכלס ביצירה**), `status`, `result_data`, `created_at`, `updated_at`.

## 10.2 WorkflowEntity

`workflow_id`, `request_id`, `connector_type`, `connector_context`, `current_state`, `current_step`, `context_json`, זמנים, `completed_at`, `last_executed_command` (**לא נכתב**).

## 10.3 מקור אמת

PostgreSQL הוא מקור האמת לתהליך ב-Bridge. Adapter `pending_workflows` בזיכרון בלבד: אתחול Adapter מאבד מיפוי session→request, ו-webhook עלול להחזיר 404. Session registry ל-SSE נשמר ב-SQLite מקומי.

---

# 11. ממשקי תקשורת

## 11.1 gRPC

**טבלה 11.1 – BridgeService**

| RPC | בקשה | תשובה | התנהגות |
|---|---|---|---|
| SendAction | ActionRequest | ActionResponse | שמירה + אתחול או reuse; מחזיר מיד |
| GetActionStatus | StatusRequest | StatusResponse | סטטוס ו-`result_data`; בלי timestamp |

שדות ActionRequest: `agent_id`, `user_install_id`, `action_type`, `parameters`, `connector_type`, `connector_context`.

## 11.2 Protocol Buffers

`src/main/proto/bridge.proto`. יצירת stubs ב-Gradle (Kotlin) ובקוד Python שנוצר (`bridge_pb2*.py`).

## 11.3 MCP

**טבלה 11.2 – כלי MCP ב-`bridge-adapter`**

| כלי | קלט עיקרי | פלט |
|---|---|---|
| send_action | agentId, actionType, parameters, sessionId, platform | requestId, workflowId, status או pairing/error |
| store_pii | fieldType, value | token `vault://pii/...` |
| get_action_status | request_id | status, resultData (לולאה קצרה) |

## 11.4 HTTP, Webhook, SSE, Directory

**טבלה 11.3 – נקודות קצה לפי תהליך**

| Endpoint | תהליך | מטרה | הערה |
|---|---|---|---|
| POST /mcp | Adapter HTTP | MCP | |
| POST /webhook/bridge | Adapter | המשך מ-Bridge | HMAC במצב HTTP MCP; **לא** ב-stdio FastAPI |
| GET /events | Adapter | SSE | דורש token |
| POST /sessions/register | Adapter | session + sseToken | |
| /continuation/* | Adapter HTTP MCP | רישום Claude | חסר ב-stdio FastAPI |
| POST /vault/resolve | Adapter HTTP MCP | פתיחת refs | localhost בלבד |
| POST /wake | Claude Channel | notification | |
| /vault-websocket | Bridge :8081 | Vault | ללא אימות WS |
| /api/pair/* , /pair | Install Directory | צימוד | mock |

---

# 12. אבטחה ופרטיות

פרק זה מתאר **רק מנגנונים שמופיעים בקוד**. אין TLS על gRPC, אין OAuth/JWT, ואין להציג את האב-טיפוס כמערכת ייצור מאובטחת.

## 12.1 Context Separation

הסוכן אינו אמור לקבל כרטיס אשראי או סיסמה בשיחה. ב-FILL_FORM ה-Adapter מחליף ערכים ב-`vault://pii/...` (Fernet לקובץ מקומי). Bridge דוחה פרמטרים רגישים שאינם ייחוס. הכספת החיצונית (בהדגמה: mock-vault) מקבלת את בקשת ההערכה ב-WebSocket. זו הפרדת הקשר, לא הצפנת כל הערוצים.

## 12.2 Mediation

Bridge בודק סוג פעולה, מתעד, מאמת סוכן דרך Guardian ומנהל מעברים. הסוכן אינו קורא ישירות ל-Guardian או ל-Vault.

## 12.3 Least privilege כעקרון תכנון

Adapter מחזיק session וספק; Bridge מחזיק workflow וכתובת continuation; Guardian — אמון סוכן; Vault החיצוני — אישור פעולה. בפועל: WebSocket `allowedOrigins=*`, gRPC פתוח, Guardian ללא כותרות אימות — חריגות מן העקרון באב-טיפוס.

## 12.4 אימות Adapter (חלקי)

`AdapterAuthMiddleware` בודק `Authorization: Bearer` עם `hmac.compare_digest` כאשר `ADAPTER_AUTH_TOKEN` מוגדר. אם אינו מוגדר — האימות **כבוי**. ה-middleware עוטף את אפליקציית **HTTP MCP בלבד**. שרת FastAPI במצב stdio **אינו** מוגן כך. webhook מוחרג מ-Bearer ומוגן (במסלול HTTP) בחתימה.

`SessionRegistry` ב-SQLite מצמיד `(platform, sessionId)` ל-`user_install_id`, מנפיק `sseToken`, ו-`ensure_bound` חוסם שימוש חוצה-משתמש. `GET /events` דורש token תואם.

## 12.5 HMAC ל-webhook (חלקי)

Bridge דורש `WEBHOOK_SECRET` בשליחה (`error` אם חסר). חתימת HMAC-SHA256 על `timestamp.nonce.body`, כותרות `X-Webhook-Signature`, `X-Webhook-Timestamp`, `X-Webhook-Nonce`. Adapter במצב HTTP MCP מאמת, דוחה חלון זמן, ושומר nonce בזיכרון נגד replay. **מצב stdio קורא ל-`process_bridge_webhook` בלי אימות חתימה.**

## 12.6 SSRF — Claude wake

`is_allowed_claude_wake_url` מגביל ל-http על localhost ולנתיבים `/wake` או `/continuation/{uuid}`. זהו מנגנון ממשי להגבלת wake, לא פתרון SSRF כללי לכל HTTP ב-Bridge.

## 12.7 מגבלות משאבים מקומיות

TTL ותקרת pending workflows בזיכרון; תקרת חיבורי SSE ותור אירועים. אלה הגנות אב-טיפוס מפני דליפת זיכרון מקומית, לא מערכת DoS ייצורית.

## 12.8 מה אינו הצפנה

מטען `payment_request` ב-WebSocket מקודד ב-**Base64**. אין לכנות זאת הצפנה. הצפנת Fernet קיימת בחנות PII של ה-Adapter בלבד.

## 12.9 סודות

מפתחות וטוקנים נטענים מ-`.env`. אין לטעון בדוח זה שקובץ מסוים אינו ב-Git בלי בדיקת `.gitignore` בעת ההגשה.

---

# 13. בדיקות והרצות

## 13.1 אסטרטגיה

אין מבחני יחידה ב-Kotlin. ב-Adapter קיימים סקריפטי הרצה ידניים: `test_e2e_sse.py`, `test_polling_e2e.py`, `test_fill_form.py`, התלויים בסטאק חי. `bridge-sdk/tests/run_tests.py` בודק את ה-SDK. **אין בדוח זה תוצאות מספריות שהומצאו, ואין לטעון שעבר CI.**

**טבלה 13.1 – תרחישי אינטגרציה מתוכננים (התנהגות צפויה לפי קוד, לא פרוטוקול הרצה חתום)**

| תרחיש | תוצאה צפויה בקוד |
|---|---|
| send_action תקין | Action+Workflow; RECEIVED |
| בקשה זהה בחלון 2 דקות | reuse |
| Guardian verified | WAITING_FOR_VAULT_RESPONSE |
| Guardian לא verified | REJECTED/FAILED + notify |
| Vault approved | COMPLETED + webhook/polling worker |
| requestId לא ב-pending | webhook 404 |
| Recovery בעלייה | resume לפי מצב; IN_PROGRESS ריק |

## 13.2 תרחיש מקצה לקצה

המשתמש מבקש פעולה → MCP `send_action` → WEBHOOK callback → Bridge שומר ומפרסם אירוע → Guardian → Vault → NotifyAgent → Adapter wake → עדכון בשיחה או ב-SSE.

## 13.3 מדדי הצלחה

הצלחת ההדגמה נמדדת במעבר בין השכבות, בהתמדת מצב בין אירועים, ובהמשך סוכן בלי לחשוף PII. אין מדדי זמן-תגובה מתועדים במאגר.

---

# 14. תוצאות, מגבלות ודיון

## 14.1 תוצאות

הוכחה היתכנות: קבלת פעולה ב-MCP, ניהול workflow מתמשך, שילוב שערים ל-Guardian ול-Vault, התמדה, וחזרה לסוכן ב-push במסלול WEBHOOK. הופרדה ליבת התהליך ממנגנוני ספק. מומשו גם FILL_FORM עם ייחוסי PII, כלי `store_pii`, pairing אופציונלי, SSE ו-SDK.

## 14.2 תרומה הנדסית

1. יישום Context Separation סביב פעולות רגישות באב-טיפוס.
2. מנוע Workflow מתמשך במקום תלות בחיי השיחה.
3. שכבת continuation המפרידה תוצאה מאופן התעוררות.
4. חוזה רב-לשוני Protobuf.
5. מבנה להרחבת handlers ו-providers.

## 14.3 מגבלות

- אב-טיפוס מקומי: כתובות קשיחות, compose לתשתית בלבד.
- Guardian ו-Vault בהדגמה הם mocks.
- HMAC ו-Bearer תלויי תעבורה; gRPC/WS ללא אימות.
- מכונת מצבים: IN_PROGRESS מת, אירועי COMPLETED/FAILED נדחים.
- שחזור חלקי; Adapter pending לא עמיד.
- POLLING/THREAD ב-Bridge stubs.
- היעדר מבחנים אוטומטיים מקיפים.

## 14.4 דיון

העברת Continuation ל-Adapter שומרת על ליבת Bridge נקייה מספקי AI — זה היתרון המרכזי מול דחיפת Claude/OpenAI/Gemini לתוך Kotlin. המחיר הוא רכיב מקומי נוסף, מיפוי sessions, ורגישות לאיבוד זיכרון ה-Adapter.

הבחירה ב-Kafka מוסיפה תשתית לעומת תור בזיכרון, אך מתאימה למטרת ההוראה ולאמינות צרכן עם retry. עבור אב-טיפוס יחיד-צומת זו עלות תפעולית.

הפער בין פרק אבטחה “מלא” לבין פער stdio/HMAC מדגים כלל כללי: בקרות שמומשו בנתיב אחד אינן חלות אוטומטית על כל נקודות הכניסה. דוח אקדמי חייב לציין זאת, אחרת נוצרת תמונת ייצור שאינה קיימת.

ביחס לרקע [1], המערכת מממשת הפרדת הקשר ברמת ארכיטקטורה, לא הוכחת ביטחון פורמלית נגד כל מחלקות Prompt Injection. ביחס ל-MCP [2], הכלים הם משטח צר ומבוקר — זהו יישום של רעיון ה-tool use, לא תחליף למדיניות ארגונית.

---

# 15. עבודה עתידית

1. מימוש `THREAD` כהודעה כללית ל-Adapter, בלי קריאת API של ספק מתוך Bridge.
2. להכריע: לממש `PollingContinuation` ב-Bridge או לתעד רשמית ש-polling הוא Adapter-only.
3. התמדת pending workflows ב-Adapter.
4. TLS ואימות ל-gRPC ול-WebSocket.
5. אימות HMAC גם במסלול stdio, או ביטול המסלול הלא חתום.
6. כתיבת `last_executed_command` ו-idempotency של פקודות.
7. תיקון סף `IN_PROGRESS` מול אירועי COMPLETED/FAILED.
8. חיבור `reportOutcome` של Guardian או הסרתו.
9. ריבוי חיבורי Vault וניקוי session בסגירה.
10. החלפת mocks בשירותי אמון וכספת אמיתיים.
11. מבחני יחידה ואינטגרציה אוטומטיים.
12. תמונות Docker ל-Bridge ול-Adapter.

---

# 16. סיכום

The Bridge מתמודד עם שתי בעיות ב-Agentic AI: צמצום חשיפת מידע רגיש להקשר הסוכן, וניהול תהליך שאינו מסתיים בזמן חיי בקשת MCP. באמצעות Adapter, gRPC, מנוע Workflow, PostgreSQL ו-Kafka מומשה ליבת אורקסטרציה; באמצעות webhook (ברירת מחדל) וספקי wake מוחזרת התוצאה לשיחה.

הפרויקט עבר מתכנון שכלל polling מרכזי ורכיב Notification נפרד, למימוש שבו אין שירות כזה: `NotifyAgentCommand` ו-`WebhookContinuation` ב-Bridge, ו-`ContinuationService` / `WakeDispatcher` / SSE ב-Adapter.

מה שמומש הוא אב-טיפוס עובד מקצה לקצה — לא מערכת ייצור. התרומה היא הוכחת היתכנות ארכיטקטונית מודולרית לשילוב סוכנים בתהליכים רגישים וארוכי טווח, עם הפרדה ברורה בין מה שרץ בקוד לבין מה שנותר stub, mock או עבודה עתידית.

---

# מקורות

[1] Y. Louck, A. Stulman, and A. Dvir, “Proposal for Improving Google A2A Protocol: Safeguarding Sensitive Data in Multi-Agent Systems,” arXiv:2505.12490, 2025. https://arxiv.org/abs/2505.12490

[2] Model Context Protocol, “Specification.” https://modelcontextprotocol.io/specification  
[REFERENCE REQUIRED: לאחד גרסת מפרט ותאריך גישה בעת ההגשה.]

[3] gRPC Authors, “gRPC Documentation.” https://grpc.io/docs/  
Google, “Protocol Buffers Documentation.” https://protobuf.dev/overview/

[4] Spring, “Spring Boot Reference Documentation.” https://docs.spring.io/spring-boot/reference/  
Spring, “Spring Data JPA.” https://docs.spring.io/spring-data/jpa/reference/

[5] Apache Software Foundation, “Apache Kafka Documentation.” https://kafka.apache.org/documentation/

[6] PostgreSQL Global Development Group, “PostgreSQL 15 Documentation.” https://www.postgresql.org/docs/15/

[7] Anthropic, “Channels” / Claude Code documentation. https://code.claude.com/docs/en/channels  
[REFERENCE REQUIRED: לאמת URL יציב בעת ההגשה.]

[8] OpenAI, “Responses API.” https://platform.openai.com/docs/api-reference/responses

[9] Google, “Interactions API,” Gemini API. https://ai.google.dev/gemini-api/docs/interactions-overview

אין להוסיף פריטים שלא צוטטו בגוף. אין להמציא מחברים או DOI.

---

# נספח א׳ — מפת רכיבים ומחלקות

**טבלה א.1 – מחלקות ורכיבים מרכזיים**

| רכיב | אחריות | סיווג |
|---|---|---|
| BridgeServiceImpl | SendAction, GetActionStatus | א |
| ActionService | ולידציה, idempotency | א |
| WorkflowEngine | עיבוד אירועים / resume | א |
| WorkflowCommandExecutor | side effects | א |
| KafkaWorkflowEventPublisher / WorkflowEventConsumer | Kafka | א |
| GuardianGatewayAdapter | HTTP authenticate | א |
| VaultWebSocketHandler | WS | א |
| WebhookContinuation | POST callback | א |
| ChannelContinuation | POST כללי | א |
| PollingContinuation / ThreadContinuation | stub | ה |
| WorkflowRecoveryService | עלייה בלבד | ב |
| ContinuationService / WakeDispatcher | Adapter wake | א |
| SseClientNotifier | SSE | א |
| PiiVaultStore | Fernet מקומי | א/ד |
| PairingService / InstallDirectoryClient | pairing | ב/ד |
| PollingWorker | Adapter polling | א כאשר POLLING |
| SdkProvider | no-op wake | א |
| guardian-mock / mock-vault / demo-forms | עמיתי הדגמה | ד |

---

# נספח ב׳ — מילון מונחים

**טבלה ב.1 – מונחים**

| מונח | הגדרה |
|---|---|
| Action | בקשה עסקית של הסוכן |
| Workflow | מצב פנימי מתמשך ב-Bridge |
| Continuation | החזרת תוצאה לסוכן אחרי אירוע חיצוני |
| Adapter | MCP↔gRPC ו-provider wake |
| Context Separation | הפרדת הקשר הסוכן מהקשר הסודות |
| Guardian | בדיקת אמון סוכן (בהדגמה: mock) |
| Vault (חיצוני) | אישור/ביצוע רגיש דרך WebSocket |
| PiiVaultStore | הצפנת PII מקומית ב-Adapter |
| MCP | פרוטוקול כלים לסוכנים |
| SSE | זרם אירועים ללקוח מקומי |
| user_install_id | מזהה התקנה אחרי pairing או fallback |
| vault:// | ייחוס לערך ב-PiiVaultStore |
| Bridge SDK | לקוח Python של ה-Adapter |

---

# נספח ג׳ — תצורה (מקוצר)

**טבלה ג.1 – משתנים ונתונים קשיחים**

| שם | רכיב | הערה |
|---|---|---|
| PORT | Bridge HTTP | ברירת מחדל 8081 |
| gRPC 50051 | Bridge | קשיח בקוד |
| POSTGRES_* | Bridge | application.properties |
| WEBHOOK_SECRET | Bridge+Adapter | חובה לשליחת webhook |
| ADAPTER_AUTH_TOKEN | Adapter HTTP | אם ריק — אין Bearer |
| MCP_TRANSPORT | Adapter | stdio / http |
| ADAPTER_PORT | Adapter | 8000 |
| CONNECTOR_TYPE | Adapter | ברירת מחדל WEBHOOK |
| CONNECTOR_CONTEXT | Adapter | URL webhook |
| INSTALL_DIRECTORY_URL | Adapter | בלי זה pairing directory כבוי |
| VAULT_STORE_KEY | Adapter | מפתח Fernet |
| OPENAI_API_KEY / GEMINI_* | לקוחות/wake | תלות חיצונית |
| Guardian URL | Kotlin | `localhost:8001` קשיח |

---

# נספח ד׳ — קטעי חוזה נבחרים

שירות gRPC (מקוצר מ-`bridge.proto`):

```text
service BridgeService {
  rpc SendAction(ActionRequest) returns (ActionResponse);
  rpc GetActionStatus(StatusRequest) returns (StatusResponse);
}
```

אין להדביק את כל המאגר בנספח.
