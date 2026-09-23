#!/usr/bin/env python3
"""Surgical edits to the original academic DOCX. Does not rewrite from Markdown."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor
from docx.text.paragraph import Paragraph

SRC = Path("/Users/yhd/Downloads/עותק של The_Bridge_Final_Report_HE_Polished.docx")
DST = Path("/Users/yhd/Downloads/The_Bridge_Final_Report_READY_FOR_SUBMISSION.docx")
RENDERED = Path("/Users/yhd/pii-vault-mcp/docs/diagrams/rendered")

HE = "David"
EN = "Arial"


def qn_w(tag: str) -> str:
    return qn(f"w:{tag}")


def set_val(el, name: str, value: str) -> None:
    el.set(qn(f"w:{name}"), value)


def delete_paragraph(paragraph: Paragraph) -> None:
    el = paragraph._element
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def insert_paragraph_after(paragraph: Paragraph, style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style:
        new_para.style = style
    return new_para


def set_run_fonts(run, *, size=12, bold=None, italic=None, cs=HE, ascii_font=EN, rtl=None):
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    run.font.size = Pt(size)
    rPr = run._r.get_or_add_rPr()
    for child in list(rPr):
        if child.tag == qn_w("rFonts"):
            rPr.remove(child)
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:cs"), cs)
    rFonts.set(qn("w:eastAsia"), ascii_font)
    rPr.insert(0, rFonts)
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "en-US")
    lang.set(qn("w:bidi"), "he-IL")
    rPr.append(lang)
    sz = OxmlElement("w:sz")
    set_val(sz, "val", str(int(size * 2)))
    rPr.append(sz)
    szCs = OxmlElement("w:szCs")
    set_val(szCs, "val", str(int(size * 2)))
    rPr.append(szCs)
    if rtl is not None:
        rtl_el = OxmlElement("w:rtl")
        set_val(rtl_el, "val", "1" if rtl else "0")
        rPr.append(rtl_el)


def set_para_bidi(p: Paragraph, rtl: bool) -> None:
    pPr = p._p.get_or_add_pPr()
    for child in list(pPr):
        if child.tag == qn_w("bidi"):
            pPr.remove(child)
    bidi = OxmlElement("w:bidi")
    set_val(bidi, "val", "1" if rtl else "0")
    pPr.append(bidi)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl else WD_ALIGN_PARAGRAPH.LEFT


def rewrite(p: Paragraph, text: str, *, rtl=True, size=12, bold=False, style=None) -> None:
    if style:
        p.style = style
    for child in list(p._p):
        if child.tag != qn_w("pPr"):
            p._p.remove(child)
    run = p.add_run(text)
    set_run_fonts(run, size=size, bold=bold, rtl=rtl)
    set_para_bidi(p, rtl)
    p.paragraph_format.line_spacing = 1.5


def add_field(paragraph: Paragraph, instruction: str, placeholder: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    set_val(begin, "fldCharType", "begin")
    run._r.append(begin)
    run2 = paragraph.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    run2._r.append(instr)
    run3 = paragraph.add_run()
    sep = OxmlElement("w:fldChar")
    set_val(sep, "fldCharType", "separate")
    run3._r.append(sep)
    run4 = paragraph.add_run(placeholder)
    set_run_fonts(run4, size=11, italic=True, rtl=True)
    run5 = paragraph.add_run()
    end = OxmlElement("w:fldChar")
    set_val(end, "fldCharType", "end")
    run5._r.append(end)


def apply_style_defaults(doc: Document) -> None:
    styles = doc.styles
    def tune(name, size, bold, rtl=True, before=0, after=8, line=1.5):
        st = styles[name]
        st.font.size = Pt(size)
        st.font.bold = bold
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.font.name = EN
        rPr = st.element.get_or_add_rPr()
        rFonts = rPr.find(qn_w("rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:ascii"), EN)
        rFonts.set(qn("w:hAnsi"), EN)
        rFonts.set(qn("w:cs"), HE)
        pPr = st.element.get_or_add_pPr()
        bidi = pPr.find(qn_w("bidi"))
        if bidi is None:
            bidi = OxmlElement("w:bidi")
            pPr.append(bidi)
        set_val(bidi, "val", "1" if rtl else "0")
        st.paragraph_format.line_spacing = line
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)

    tune("Normal", 12, False, after=8)
    tune("Heading 1", 16, True, before=12, after=10)
    tune("Heading 2", 14, True, before=12, after=8)
    tune("Heading 3", 12, True, before=10, after=6)

    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Cm(3.18)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
    sectPr = section._sectPr
    bidi = sectPr.find(qn_w("bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        sectPr.append(bidi)
    set_val(bidi, "val", "1")

    settings = doc.settings.element
    update = settings.find(qn_w("updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    set_val(update, "val", "true")


def find_all(doc: Document, pred):
    return [p for p in doc.paragraphs if pred(p)]


def find_one(doc: Document, start: str, occurrence=0) -> Paragraph:
    hits = [p for p in doc.paragraphs if p.text.strip().startswith(start)]
    return hits[occurrence]


def set_cell(cell, text: str) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    rewrite(p, text, size=10)


def add_row(table, values: list[str]) -> None:
    row = table.add_row()
    for i, val in enumerate(values):
        set_cell(row.cells[i], val)


def paragraph_has_drawing(p: Paragraph) -> bool:
    return "w:drawing" in p._p.xml or "w:pict" in p._p.xml


def main() -> None:
    shutil.copy2(SRC, DST)
    doc = Document(str(DST))
    apply_style_defaults(doc)

    # --- Duplicate cover: keep the first, drop the second (includes black image) ---
    covers = [i for i, p in enumerate(doc.paragraphs) if p.text.strip() == "THE BRIDGE"]
    if len(covers) >= 2:
        start = covers[1]
        end = None
        for i, p in enumerate(doc.paragraphs):
            if p.style.name == "Heading 1" and p.text.strip() == "תקציר":
                end = i
                break
        if end:
            for p in list(doc.paragraphs[start:end]):
                delete_paragraph(p)

    # --- Page break before major Heading 1 chapters ---
    chapter_starts = {
        "תקציר",
        "Abstract",
        "תודות",
        "תוכן עניינים",
        "רשימת איורים",
        "רשימת טבלאות",
        "1. מבוא",
        "2. רקע תאורטי ומחקרי",
        "3. הגדרת הבעיה ומטרות הפרויקט",
        "4. דרישות המערכת",
        "5. חלופות ושיקולי תכנון",
        "6. ארכיטקטורת המערכת",
        "7. תכנון מפורט ומימוש",
        "8. מנוע ה-Workflow וניהול מצבים",
        "9. שכבת הסוכנים והמשך שיחה",
        "10. מודל הנתונים ושמירתם",
        "11. ממשקי תקשורת",
        "12. אבטחה ופרטיות",
        "13. בדיקות והרצות",
        "14. תוצאות, מגבלות ודיון",
        "15. עבודה עתידית",
        "16. סיכום",
        "מקורות",
    }
    for p in doc.paragraphs:
        t = p.text.strip()
        if p.style.name == "Heading 1" and (
            t in chapter_starts or t.startswith("נספח")
        ):
            p.paragraph_format.page_break_before = True
            p.paragraph_format.keep_with_next = True

    # --- TOC: replace typed lists with Word fields ---
    toc_h = find_one(doc, "תוכן עניינים")
    # delete following normal items until רשימת איורים
    nxt = toc_h._p.getnext()
    while nxt is not None:
        text = "".join(nxt.itertext()).strip()
        style = nxt.find(qn_w("pPr"))
        style_val = ""
        if style is not None:
            pstyle = style.find(qn_w("pStyle"))
            if pstyle is not None:
                style_val = pstyle.get(qn("w:val") ) or ""
        if text.startswith("רשימת איורים") or style_val in {"Heading1", "1"}:
            break
        following = nxt.getnext()
        if nxt.tag == qn_w("p") and text in {
            "1. מבוא",
            "2. רקע תאורטי ומחקרי",
            "3. הגדרת הבעיה ומטרות הפרויקט",
            "4. דרישות המערכת",
            "5. חלופות ושיקולי תכנון",
            "6. ארכיטקטורת המערכת",
            "7. תכנון מפורט ומימוש",
            "8. מנוע ה-Workflow וניהול מצבים",
            "9. שכבת הסוכנים והמשך שיחה",
            "10. מודל הנתונים והתמדה",
            "11. ממשקי תקשורת",
            "12. אבטחה ופרטיות",
            "13. בדיקות והרצות",
            "14. תוצאות, מגבלות ודיון",
            "15. עבודה עתידית",
            "16. סיכום",
            "מקורות",
            "נספחים",
        } or text == "":
            # only delete the known TOC lines, keep a couple blanks
            if text:
                parent = nxt.getparent()
                parent.remove(nxt)
        nxt = following
        if text.startswith("רשימת"):
            break

    # Simpler: insert TOC field immediately after heading
    field_p = insert_paragraph_after(toc_h)
    set_para_bidi(field_p, True)
    note = insert_paragraph_after(toc_h)
    rewrite(
        note,
        "יש לעדכן שדה זה ב-Microsoft Word: לחיצה ימנית על תוכן העניינים → Update Field → Update entire table.",
        size=10,
    )
    # rewrite() doesn't take italic kw for para - fix note run
    for r in note.runs:
        r.italic = True
    add_field(
        field_p,
        r'TOC \o "1-3" \h \z \u',
        "תוכן העניינים יתעדכן אוטומטית ב-Word.",
    )

    # List of figures/tables: clear stale page-number tables (first two tables)
    if len(doc.tables) >= 2:
        fig_h = find_one(doc, "רשימת איורים")
        tab_h = find_one(doc, "רשימת טבלאות")
        # delete table 0 and 1 xml
        for tbl in list(doc.tables[:2]):
            tbl._tbl.getparent().remove(tbl._tbl)
        fp = insert_paragraph_after(fig_h)
        set_para_bidi(fp, True)
        add_field(fp, r'TOC \h \z \t "Caption,1"', "רשימת האיורים תתעדכן ב-Word.")
        n1 = insert_paragraph_after(fig_h)
        rewrite(n1, "עדכון שדה: Update Field / Update entire table.", size=10)
        tp = insert_paragraph_after(tab_h)
        set_para_bidi(tp, True)
        add_field(tp, r'TOC \h \z \c "טבלה"', "רשימת הטבלאות תתעדכן ב-Word.")
        # Also a style-based LOF/LOT using Caption if present
        n2 = insert_paragraph_after(tab_h)
        rewrite(n2, "עדכון שדה: Update Field / Update entire table.", size=10)

    # ========== Factual paragraph edits ==========
    rewrite(
        find_one(doc, "סוכני בינה מלאכותית מסוגלים לבצע פעולות מורכבות"),
        "סוכני בינה מלאכותית מסוגלים לבצע פעולות מורכבות בשם משתמשים, אך שילובם במערכות המחזיקות מידע אישי או פיננסי יוצר שתי בעיות מרכזיות: חשיפת מידע רגיש לסוכן, וקושי בניהול תהליכים א-סינכרוניים ארוכי טווח שאינם מסתיימים במסגרת בקשת request-response אחת. פרויקט The Bridge מציע שכבת תיווך ואורקסטרציה המפרידה בין סביבת קבלת ההחלטות של הסוכן לבין סביבת שמירת הסודות וביצוע הפעולות. המימוש הנוכחי הוא אב-טיפוס מקומי: שערי האינטגרציה ממומשים, ומנגנוני האבטחה הם חלקיים ואינם כוללים TLS או אימות gRPC.",
    )
    rewrite(
        find_one(doc, "המערכת פותחה בשיתוף CoralOS"),
        "המערכת פותחה בשיתוף CoralOS ובהשראת עקרון Context Separation: הסוכן מגדיר את הפעולה המבוקשת אך אינו מקבל גישה ישירה לפרטי התשלום, לזהויות או לנתונים הרגישים. רכיב Bridge מרכזי מנהל את מחזור החיים של הפעולה, מתאם בין שער Guardian לבדיקת אמון לבין שער Vault, שומר מצב מתמשך במסד נתונים ומניע את התהליך באמצעות אירועים. בהדגמה במאגר זה, העמיתים הרצים הם guardian-mock ו-mock-vault, הניתנים להחלפה בשירות חיצוני.",
    )
    rewrite(
        find_one(doc, "המימוש כולל Bridge ב-Kotlin"),
        "המימוש כולל Bridge ב-Kotlin וב-Spring Boot, ממשק gRPC מבוסס Protocol Buffers, מנוע Workflow מונחה מצבים, PostgreSQL, Apache Kafka, חיבור WebSocket ל-Vault ושכבת Agent Adapter מקומית ב-Python. הסוכן מפעיל כלי MCP על גבי ה-Adapter, ובהם send_action, store_pii ו-get_action_status. ה-Adapter מתרגם את הבקשה ל-gRPC ושולח אותה ל-Bridge. עם השלמת התהליך, במסלול ברירת המחדל ה-Bridge שולח webhook ל-Adapter; ה-Adapter מפעיל מנגנון המשך ייעודי לספק. ב-Claude Code ההמשך מבוצע באמצעות Claude Channel והודעת notifications/claude/channel, וב-OpenAI וב-Gemini באמצעות ממשקי ה-API שלהם והודעת SSE ללקוח המקומי.",
    )

    rewrite(
        find_one(doc, "The Bridge is a secure mediation"),
        "The Bridge is a mediation and process-orchestration layer developed in collaboration with CoralOS. It applies the Context Separation principle by separating the agent’s decision-making environment from the environment that stores secrets and executes sensitive operations. The Bridge coordinates Guardian and Vault gateways, persists workflow state, and resumes execution when external events arrive. In this repository the runnable Guardian and Vault peers used for demonstration are mock services.",
        rtl=False,
        size=12,
    )
    rewrite(
        find_one(doc, "The implementation combines Kotlin"),
        "The implementation combines Kotlin and Spring Boot, gRPC and Protocol Buffers, PostgreSQL, Apache Kafka, a WebSocket integration with the Vault, and a local Python Agent Adapter. Agents invoke MCP tools on the Adapter (send_action, store_pii, get_action_status), which forwards typed gRPC requests to the Bridge. When a workflow reaches a terminal state, the Bridge by default sends a webhook to the Adapter. The Adapter then uses a provider-specific continuation mechanism: Claude Channel notifications for Claude Code, and provider APIs with SSE client notification for OpenAI and Gemini. The system is a functional local prototype; TLS and gRPC authentication are not implemented.",
        rtl=False,
    )

    rewrite(
        find_one(doc, "Model Context Protocol משמש"),
        "Model Context Protocol משמש במערכת כממשק אחיד בין הסוכן לבין ה-Adapter. במקום שכל ספק AI יכיר את ה-API הפנימי של Bridge, הסוכן רואה שלושה כלים: send_action, store_pii ו-get_action_status. ה-Adapter מקבל אובייקטים ידידותיים לסוכן, מבצע מיפוי ל-Protocol Buffers ומעביר אותם ל-Bridge.",
    )

    rewrite(
        find_one(doc, "גבולות האחריות ההנדסית"),
        "גבולות האחריות ההנדסית של הפרויקט תוחמו כדי להתמקד בליבת התיווך, ניהול התהליכים והאבטחה של תהליכי הסוכנים. הפרויקט כולל את ליבת ה-Bridge ב-Kotlin וב-Spring Boot — מנוע ה-Workflow, PostgreSQL ו-Kafka — לצד Agent Adapter ב-Python התומך ב-MCP. מנגנוני ההתעוררות הממומשים הם בעיקר webhook ו-SSE; Polling ממומש ב-Adapter (PollingWorker) אך מחבר POLLING ב-Bridge הוא stub. צימוד משתמש–כספת, Install Directory ו-Pairing Watcher מומשו באב-טיפוס והם פעילים רק כאשר INSTALL_DIRECTORY_URL מוגדר. Guardian ו-Vault הם שירותים חיצוניים לליבת ה-Bridge; שערי HTTP ו-WebSocket ממומשים ב-Bridge, ובמאגר הקוד קיימים גם עמיתי הדגמה (guardian-mock, mock-vault) שאינם שירותי ייצור. המערכת היא אב-טיפוס פונקציונלי מקצה לקצה. פריסת ענן, High Availability, TLS ואימות gRPC הוגדרו כעבודה עתידית.",
    )

    p54 = find_one(doc, "5.4 Webhook")
    rewrite(p54, "5.4 Webhook ו-Push Continuation", style="Heading 2", size=14, bold=True)

    rewrite(
        find_one(doc, "Polling היה שימושי"),
        "Polling היה שימושי בשלב POC, ובכלי get_action_status קיימת לולאת המתנה קצרה. כאשר CONNECTOR_TYPE=POLLING, PollingWorker ב-Adapter דוגם את GetActionStatus. עם זאת זה אינו המסלול העיקרי, ומחבר PollingContinuation ב-Bridge הוא stub שרק כותב ללוג. Polling יוצר בקשות מיותרות, תלוי בחיי הסשן, ואינו מאפשר ל-Bridge עצמו ליזום המשך.",
    )

    rewrite(
        find_one(doc, "Bridge הוא יישום Spring Boot"),
        "Bridge הוא יישום Spring Boot. נקודת הכניסה מפעילה ApplicationContext, שרת HTTP בפורט 8081 (ברירת מחדל) ואת שרת ה-gRPC בפורט 50051 (קשיח בקוד, ללא TLS). BridgeServiceImpl מממש את השירות המוגדר ב-Proto ומעביר אחריות ל-ActionService, WorkflowInitializationService ול-repositories.",
    )

    rewrite(
        find_one(doc, "GuardianGatewayAdapter מבצע"),
        "GuardianGatewayAdapter מבצע קריאת HTTP GET אל http://localhost:8001/v1/authenticate/agent ומפרסם GuardianApprovedEvent או GuardianRejectedEvent. המתודה reportOutcome אינה נקראת בזרימה החיה. VaultGatewayAdapter שולח בקשה דרך VaultWebSocketHandler. התגובה מן ה-Vault מתורגמת לאירוע ActionResponseReceivedEvent. מטען payment_request מקודד ב-Base64 ואינו הצפנה.",
    )

    rewrite(
        find_one(doc, "בקוד קיימים WorkflowRecoveryService"),
        "בקוד קיימים WorkflowRecoveryService ו-WorkflowRecoveryScheduler. השחזור רץ פעם אחת ב-ApplicationReadyEvent לאחר עליית Spring, ולא באופן מחזורי. הוא מזהה workflows במצבים שאינם סופיים ומנסה resume לפי המצב. למצב IN_PROGRESS אין פקודת שחזור, והזרימה החיה אינה נכנסת למצב זה. התמדת PostgreSQL מונעת תלות בזיכרון תהליך ה-Bridge, אך מיפוי pending_workflows ב-Adapter נשאר בזיכרון בלבד.",
    )

    # Stray H1 inside chapter 8
    stray = [p for p in doc.paragraphs if p.style.name == "Heading 1" and p.text.strip() == "10. מודל הנתונים והתמדה"]
    for p in stray:
        delete_paragraph(p)

    rewrite(
        find_one(doc, "איור 1:"),
        "איור 6.1: ארכיטקטורת שכבת הסוכנים, ה-Adapter וה-Bridge",
    )
    rewrite(
        find_one(doc, "איור 2:"),
        "איור 6.2: תרשים רצף — שליחת פעולה, Workflow והמשך הסוכן",
    )
    rewrite(
        find_one(doc, "איור 3:"),
        "איור 8.1: מצבי Workflow בזרימה החיה",
    )
    rewrite(
        find_one(doc, "איור 4:"),
        "איור 10.1: ERD — טבלאות actions ו-workflows",
    )

    rewrite(
        find_one(doc, "6.3"),
        "6.3 Happy Path",
        style="Heading 2",
        size=14,
        bold=True,
    )

    # Workflow states note
    rewrite(
        find_one(doc, "RECEIVED, WAITING_FOR_GUARDIAN"),
        "RECEIVED, WAITING_FOR_GUARDIAN, WAITING_FOR_VAULT_RESPONSE, IN_PROGRESS, COMPLETED או FAILED. ערך IN_PROGRESS קיים ב-enum וב-validator, אך handlers בזרימה החיה אינם מעבירים אליו.",
    )
    rewrite(
        find_one(doc, "ACTION_RECEIVED"),
        "ACTION_RECEIVED, VERIFY_AGENT, REQUEST_VAULT_EVALUATION, WAIT_FOR_VAULT_RESPONSE, NOTIFY_AGENT ו-FINISHED. הצעד WAIT_FOR_VAULT_RESPONSE מוגדר אך אינו משויך ב-TransitionCommand של הזרימה החיה; במעבר סופי הצעד נשמר כ-FINISHED.",
    )

    rewrite(
        find_one(doc, "StatusType המוחזר"),
        "StatusType המוחזר ב-gRPC אינו זהה ל-WorkflowState. הסוכן מקבל סטטוס ציבורי; בקוד Kotlin נכתבים בפועל בעיקר RECEIVED (התחלתי), COMPLETED, REJECTED ו-FAILED. ערכים נוספים קיימים ב-proto (למשל IN_PROGRESS, EXPIRED) אך אינם נכתבים בזרימה החיה. GetActionStatus אינו ממלא את שדה updated_at. ההפרדה מונעת חשיפת פרטי מימוש פנימיים.",
    )

    rewrite(
        find_one(doc, "חשיפת כלי MCP send_action ו-get_action_status"),
        "חשיפת כלי MCP send_action, store_pii ו-get_action_status.",
    )

    # Duplicate OpenAI/Gemini: keep first of each, delete second; add H2 9.3/9.4
    openai_paras = [p for p in doc.paragraphs if p.text.startswith("עבור OpenAI")]
    gemini_paras = [p for p in doc.paragraphs if p.text.startswith("עבור Gemini")]
    if len(openai_paras) >= 2:
        h = insert_paragraph_after(openai_paras[0])
        # insert heading BEFORE openai body: do it on previous
        prev = openai_paras[0]
        heading = Paragraph(OxmlElement("w:p"), prev._parent)
        prev._p.addprevious(heading._p)
        rewrite(heading, "9.3 OpenAI", style="Heading 2", size=14, bold=True)
        delete_paragraph(openai_paras[1])
    if len(gemini_paras) >= 2:
        prev = gemini_paras[0]
        heading = Paragraph(OxmlElement("w:p"), prev._parent)
        prev._p.addprevious(heading._p)
        rewrite(heading, "9.4 Gemini", style="Heading 2", size=14, bold=True)
        delete_paragraph(gemini_paras[1])

    rewrite(
        find_one(doc, "המערכת כוללת תמיכה מלאה במנגנון Polling"),
        "Polling הוא מסלול חלופי חלקי. ב-Adapter, PollingWorker דוגם את Bridge GetActionStatus כל 2 שניות כברירת מחדל (timeout 120 שניות) עבור workflows עם CONNECTOR_TYPE=POLLING, ומעביר את התוצאה ל-ContinuationService לצורך Wake ו-SSE. ב-Bridge, PollingContinuation הוא stub (TODO) שאינו שולח עדכון. לכן אין לתאר את polling כתמיכה מלאה בשתי השכבות, והמסלול הראשי נשאר webhook.",
    )

    rewrite(
        find_one(doc, "WorkflowEntity מייצגת"),
        "WorkflowEntity מייצגת את מצב התהליך. היא כוללת workflow_id, request_id ייחודי, connector_type, connector_context, current_state, current_step, context_json, זמני יצירה ועדכון, completed_at ו-last_executed_command. השדה last_executed_command אינו נכתב בזרימה הנוכחית. הקשר בין הטבלאות הוא לוגי 1:1 באמצעות request_id; אין annotation של JPA OneToOne. בשדה ActionEntity.context_json אינו מאוכלס בעת יצירת הפעולה.",
    )

    rewrite(
        find_one(doc, "bridge.proto מגדיר"),
        "bridge.proto מגדיר את BridgeService ואת הודעות ActionRequest, ActionResponse, StatusRequest ו-StatusResponse. הוא כולל מזהי סוכן והתקנה, סוג פעולה, parameters, connector type/context, status, result data ו-timestamp. שדה updated_at קיים ב-proto אך GetActionStatus אינו ממלא אותו. יצירת stubs אוטומטית ב-Kotlin וב-Python מבטיחה תאימות טיפוסים.",
    )

    rewrite(
        find_one(doc, "הסוכן אינו מקבל את פרטי האשראי"),
        "הסוכן אינו מקבל את פרטי האשראי או המידע הפרטי עצמו. הוא מעביר בקשה ופרמטרים שאינם דורשים חשיפת המידע הפרטי. יש להבחין בין שני רכיבים שונים: PiiVaultStore ב-Adapter מצפין ערכי PII מקומית ב-Fernet ומחזיר ייחוסי vault://; ה-Vault החיצוני (בהדגמה: mock-vault) מתחבר ב-WebSocket ל-Bridge לצורך אישור או דחיית פעולה. הפרדת ההקשר מפחיתה את כמות המידע שנכנסת למודל.",
    )

    # Promote 12.4–12.7 to Heading 2
    for title in (
        "12.4 אימות ובקרת גישה",
        "12.5 שלמות הודעות ומניעת שידור חוזר",
        "12.6 בידוד כתובות ומניעת SSRF",
        "12.7 הגנה על משאבים ומניעת דליפות זיכרון",
    ):
        p = find_one(doc, title)
        rewrite(p, p.text.strip(), style="Heading 2", size=14, bold=True)

    for title in (
        "12.4.1 ",
        "12.4.2 ",
        "12.4.3 ",
        "12.5.1 ",
        "12.5.2 ",
        "12.6.1 ",
        "12.7.1 ",
        "12.7.2 ",
        "12.7.3 ",
    ):
        p = find_one(doc, title)
        rewrite(p, p.text.strip(), style="Heading 3", size=12, bold=True)

    rewrite(
        find_one(doc, "12.4.1 שכבת תיווך לאימות"),
        "12.4.1 שכבת תיווך לאימות (AdapterAuthMiddleware): במצב MCP_TRANSPORT=http, בקשות HTTP לאפליקציית ה-Adapter עוברות Middleware הבודק Authorization: Bearer כאשר ADAPTER_AUTH_TOKEN מוגדר. אם הטוקן אינו מוגדר, האימות כבוי. במצב stdio, שרת FastAPI הנפרד (webhook/events) אינו עוטף ב-AdapterAuthMiddleware. האימות בנתיבים רגישים (MCP ו-POST /sessions/register) משתמש ב-hmac.compare_digest. נתיבים ציבוריים נבחרים אינם דורשים Bearer: דף השורש, POST /webhook/bridge (מוגן בחתימה במסלול HTTP MCP), ו-/vault/resolve החסום ל-localhost.",
        style="Heading 3",
        size=12,
        bold=True,
    )
    # Heading 3 with long body is awkward; split: heading short + body
    # Re-do 12.4.1 as heading only then following para already exists as the long text - we overwrote the long para to include heading number. That's OK for this document since original had number inside body.

    rewrite(
        find_one(doc, "12.5.1 חתימה קריפטוגרפית"),
        "12.5.1 חתימה קריפטוגרפית (HMAC-SHA256): במסלול WEBHOOK, Bridge דורש WEBHOOK_SECRET וחותם את {timestamp}.{nonce}.{body} בכותרת X-Webhook-Signature. Adapter במצב HTTP MCP מאמת את החתימה ודוחה אי-התאמה ב-401. במצב stdio, נקודת POST /webhook/bridge קוראת לעיבוד ללא אימות HMAC. אין להציג את המנגנון כחובה בכל נקודות הכניסה.",
        style="Heading 3",
        size=12,
        bold=True,
    )

    # Chapter 13 heading
    p13 = [p for p in doc.paragraphs if p.text.strip() == "בדיקות והרצות"]
    if p13:
        rewrite(p13[0], "13. בדיקות והרצות", style="Heading 1", size=16, bold=True)
        p13[0].paragraph_format.page_break_before = True

    rewrite(
        find_one(doc, "הבדיקות בפרויקט התמקדו"),
        "הבדיקות בפרויקט התמקדו בהרצות אינטגרציה מקצה לקצה ובאימות המעברים בין הרכיבים. במאגר קיימים סקריפטי הרצה ידניים ב-Adapter (למשל test_e2e_sse.py) ואין מבחני יחידה ב-Kotlin. אין בדוח זה מדדי ביצוע מספריים או תוצאות CI חתומות.",
    )

    rewrite(
        find_one(doc, "הצלחת ההדגמה נמדדה"),
        "הצלחת ההדגמה נמדדה בכך שהבקשה עברה את כל השכבות, מצב התהליך נשמר בין האירועים, רכיב חיצוני יכול היה להשלים את התהליך, והסוכן קיבל המשך במסלול webhook בלי לולאת polling כמסלול ראשי. כלי get_action_status עדיין כולל לולאת המתנה קצרה, ו-PollingWorker זמין כמסלול חלופי.",
    )

    rewrite(
        find_one(doc, "המימוש מוכיח היתכנות"),
        "המימוש מוכיח היתכנות הנדסית של שכבת תיווך לסוכנים: ניתן לקבל בקשת פעולה בממשק MCP, לנהל אותה במנוע workflow מתמשך, לערב שערי Guardian ו-Vault, לשמור מצב ולחזור לסוכן באירוע push. הארכיטקטורה מפרידה בהצלחה בין ליבת התהליך לבין מנגנוני ההמשך של פלטפורמות שונות. ההדגמה נשענת על mocks מקומיים ואינה שקולה לפריסת ייצור.",
    )

    # 14.3 limitations before 14.4
    p144 = find_one(doc, "14.4 דיון")
    lim_h = Paragraph(OxmlElement("w:p"), p144._parent)
    p144._p.addprevious(lim_h._p)
    rewrite(lim_h, "14.3 מגבלות", style="Heading 2", size=14, bold=True)
    lim_b = Paragraph(OxmlElement("w:p"), p144._parent)
    p144._p.addprevious(lim_b._p)
    rewrite(
        lim_b,
        "המערכת היא אב-טיפוס מקומי. מחברי POLLING ו-THREAD ב-Bridge הם stubs. שחזור ה-Workflow הוא בעלייה בלבד. HMAC ו-Bearer תלויים בסוג התעבורה. אין TLS ואימות gRPC. pending workflows ב-Adapter אינם עמידים לאתחול. אירועי WORKFLOW_COMPLETED ו-WORKFLOW_FAILED מתפרסמים אך נדחים על ידי validator הדורש מצב IN_PROGRESS שאינו מושג בזרימה החיה. Guardian ו-Vault בהדגמה הם mocks.",
    )

    # Chapter 15 heading before 15.1
    p151 = find_one(doc, "15.1 הצעה למימוש THREAD")
    h15 = Paragraph(OxmlElement("w:p"), p151._parent)
    p151._p.addprevious(h15._p)
    rewrite(h15, "15. עבודה עתידית", style="Heading 1", size=16, bold=True)
    h15.paragraph_format.page_break_before = True
    intro15 = Paragraph(OxmlElement("w:p"), p151._parent)
    p151._p.addprevious(intro15._p)
    rewrite(
        intro15,
        "פרק זה מציג כיוונים שטרם מומשו במלואם. אין לראות בהם חלק מהמימוש הנוכחי.",
    )

    h152 = insert_paragraph_after(find_one(doc, "מימוש עתידי לא צריך"))
    rewrite(h152, "15.2 כיוונים נוספים", style="Heading 2", size=14, bold=True)
    b152 = insert_paragraph_after(h152)
    rewrite(
        b152,
        "מימוש או תיעוד רשמי של Polling כ-Adapter-only; התמדת pending workflows; TLS ואימות ל-gRPC ול-WebSocket; אימות HMAC גם במסלול stdio; כתיבת last_executed_command; תיקון סף IN_PROGRESS מול אירועי הסיום; חיבור reportOutcome או הסרתו; מבחנים אוטומטיים; והחלפת mocks בשירותי Guardian ו-Vault אמיתיים.",
    )

    rewrite(
        find_one(doc, "The Bridge פותר שתי בעיות"),
        "The Bridge מתמודד עם שתי בעיות ב-Agentic AI: צמצום חשיפת מידע רגיש להקשר הסוכן, וניהול תהליך שאינו מסתיים בזמן חיי בקשת הסוכן. באמצעות Context Separation הסוכן אינו מקבל את ערכי ה-PII עצמם; באמצעות Workflow Engine, PostgreSQL ו-Kafka התהליך נשמר וממשיך על בסיס אירועים; ובאמצעות Agent Adapter ו-webhook continuation ניתן להחזיר תוצאה לפלטפורמות AI שונות. זהו אב-טיפוס עובד מקצה לקצה, לא מערכת ייצור.",
    )

    rewrite(
        find_one(doc, "1] Y. Louck"),
        "[1] Y. Louck, A. Stulman, and A. Dvir, “Proposal for Improving Google A2A Protocol: Safeguarding Sensitive Data in Multi-Agent Systems,” arXiv preprint arXiv:2505.12490, 2025. Accessed: Aug. 4, 2026. https://arxiv.org/abs/2505.12490",
    )

    # ========== Tables (indices shift after deleting first two TOC tables) ==========
    # Re-open mapping: originally 2=FR, 3=NFR, 4=components, 5=packages, 6=events, 7=grpc, 8=mcp, 9=http, 10=tests, 11=classes, 12=glossary, 13=env
    # After removing tables 0 and 1: subtract 2
    tables = doc.tables
    # FR
    fr = tables[0]
    add_row(fr, ["FR-1b", "הסוכן יוכל לאחסן ערך רגיש מקומית באמצעות store_pii ולקבל ייחוס vault://."])
    set_cell(fr.rows[7].cells[1], "בסיום התהליך יישלח webhook ל-Adapter כאשר connector_type=WEBHOOK (ברירת המחדל).")
    set_cell(fr.rows[10].cells[1], "המערכת תתמוך בצימוד (Pairing) באמצעות Install Directory כאשר INSTALL_DIRECTORY_URL מוגדר, ותחזיר PAIRING_REQUIRED בהיעדר כספת רשומה.")

    nfr = tables[1]
    set_cell(nfr.rows[1].cells[1], "מידע רגיש לא יועבר להקשר הסוכן: PII מקומי ב-PiiVaultStore (Fernet) וייחוסי vault://; אישור פעולה ב-Vault החיצוני (בהדגמה mock).")
    set_cell(nfr.rows[2].cells[1], "מצב Workflow יישמר ב-PostgreSQL; שחזור מתבצע בעליית Bridge בלבד.")
    set_cell(nfr.rows[4].cells[1], "חוזה gRPC/Protobuf כגבול בין Python ל-Kotlin (ללא מדדי ביצוע שנמדדו).")

    comp = tables[2]
    set_cell(comp.rows[5].cells[1], "HTTP; בהדגמה guardian-mock במאגר")
    set_cell(comp.rows[5].cells[2], "בדיקת אמון של הסוכן (שער ממומש; שירות ההדגמה הוא mock).")
    set_cell(comp.rows[6].cells[1], "WebSocket client; בהדגמה mock-vault")
    set_cell(comp.rows[6].cells[2], "אישור משתמש וביצוע רגיש (שער ממומש; שירות ההדגמה הוא mock).")
    set_cell(comp.rows[9].cells[1], "Python, mock directory")
    set_cell(comp.rows[9].cells[2], "רישום user_install_id ל-Vault URL באמצעות pairing/QR; אופציונלי לפי INSTALL_DIRECTORY_URL.")
    add_row(comp, ["PiiVaultStore", "Adapter, Fernet", "הצפנת PII מקומית והנפקת ייחוסי vault:// — שונה מה-Vault החיצוני."])
    add_row(comp, ["bridge-sdk", "Python", "לקוח MCP+SSE של ה-Adapter; אינו מיובא על ידי ה-Adapter."])

    ev = tables[4]
    set_cell(ev.rows[5].cells[2], "אירוע סיכום שמתפרסם אך נדחה בזרימה החיה (validator דורש IN_PROGRESS).")
    set_cell(ev.rows[6].cells[2], "אירוע כישלון שמתפרסם אך נדחה בזרימה החיה מאותה סיבה.")

    mcp = tables[6]
    set_cell(mcp.rows[2].cells[2], "status, resultData (updated_at אינו מגיע מ-Bridge)")
    add_row(mcp, ["store_pii", "fieldType, value", "token מסוג vault://pii/..."])

    tests = tables[8]
    set_cell(tests.rows[9].cells[2], "ApplicationReadyEvent טוען workflows לא-סופיים ומריץ resume; IN_PROGRESS ללא פקודה.")

    gloss = tables[10]
    set_cell(gloss.rows[6].cells[1], "רכיב בדיקת אמון; בהדגמה guardian-mock.")
    set_cell(gloss.rows[7].cells[1], "רכיב אישור פעולות דרך WebSocket; בהדגמה mock-vault. שונה מ-PiiVaultStore.")
    add_row(gloss, ["PiiVaultStore", "חנות PII מקומית ב-Adapter עם הצפנת Fernet וייחוסי vault://."])

    env = tables[11]
    add_row(env, ["MCP_TRANSPORT", "Adapter", "stdio או http"])
    add_row(env, ["CONNECTOR_CONTEXT", "Adapter", "כתובת webhook כברירת מחדל"])
    add_row(env, ["PORT", "Bridge", "HTTP 8081; gRPC 50051 קשיח"])

    # packages table connectors row already says stubs - OK

    # Caption style on figure/table captions
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("איור 6.") or t.startswith("איור 8.") or t.startswith("איור 10."):
            try:
                p.style = "Caption"
            except Exception:
                pass
            set_para_bidi(p, True)
            for r in p.runs:
                set_run_fonts(r, size=11, bold=True, rtl=True)

    # Fonts / RTL sweep
    english_starts = (
        "AI agents can perform",
        "The Bridge is a mediation",
        "The implementation combines",
        "The project demonstrates an end-to-end",
        "The Bridge is a secure",  # in case original left
        "Keywords:",
        "Abstract",
        "A Secure Mediation",
        "THE BRIDGE",
    )
    for p in doc.paragraphs:
        t = p.text.strip()
        is_en = t.startswith(english_starts) or p.text.strip() == "Abstract"
        if is_en and t != "THE BRIDGE" and not t.startswith("The Bridge מעביר") and not t.startswith("The Bridge פותר") and not t.startswith("The Bridge מתמודד"):
            if t in {"Abstract", "THE BRIDGE"} or t.startswith("A Secure") or t.startswith("AI agents") or t.startswith("The Bridge is") or t.startswith("The implementation combines") or t.startswith("The project demonstrates"):
                set_para_bidi(p, False)
                for r in p.runs:
                    set_run_fonts(r, size=16 if p.style.name == "Heading 1" else 12, bold=p.style.name.startswith("Heading"), ascii_font=EN, cs=EN, rtl=False)
                continue
        if p.style.name == "Heading 1":
            set_para_bidi(p, True)
            for r in p.runs:
                set_run_fonts(r, size=16, bold=True, rtl=True)
        elif p.style.name == "Heading 2":
            set_para_bidi(p, True)
            for r in p.runs:
                set_run_fonts(r, size=14, bold=True, rtl=True)
        elif p.style.name == "Heading 3":
            set_para_bidi(p, True)
            for r in p.runs:
                set_run_fonts(r, size=12, bold=True, rtl=True)
        elif p.style.name in {"Normal", "Caption"}:
            if t.startswith("AI agents") or t.startswith("The implementation combines") or t.startswith("The project demonstrates") or t.startswith("The Bridge is a"):
                continue
            set_para_bidi(p, True)
            for r in p.runs:
                size = 11 if p.style.name == "Caption" else 12
                set_run_fonts(r, size=size, rtl=True)

    doc.save(str(DST))

    # Replace inaccurate/broken diagrams inside the zip
    replacements = {
        "word/media/image5.png": RENDERED / "01-architecture.png",  # architecture
        "word/media/image1.png": RENDERED / "03-workflow-states.png",  # workflow states
    }
    tmp = DST.with_suffix(".tmp.docx")
    with zipfile.ZipFile(DST, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in replacements and replacements[item.filename].exists():
                data = replacements[item.filename].read_bytes()
            zout.writestr(item, data)
    tmp.replace(DST)
    print("wrote", DST, "size", DST.stat().st_size)


if __name__ == "__main__":
    main()
