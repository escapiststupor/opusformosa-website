from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_NAME = "NotoSansTC"
ASSETS_PATH = Path(__file__).parent / "assets"
pdfmetrics.registerFont(TTFont(FONT_NAME, str(ASSETS_PATH / "fonts" / "NotoSansTC-VF.ttf")))


INCOME_LABELS = {
    "9A_resident": "執行業務所得（9A，居住者）",
    "9A_nonresident": "執行業務所得（9A，非居住者）",
    "9B_resident": "稿費所得（9B，居住者）",
    "9B_nonresident": "稿費所得（9B，非居住者）",
    "50_salary": "薪資所得（50）",
}
INCOME_CODE = {
    "9A_resident": "9A", "9A_nonresident": "9A", "9B_resident": "9B",
    "9B_nonresident": "9B", "50_salary": "50",
}


def money(value: int) -> str:
    return f"{int(value):,}"


def chinese_number(value: int) -> str:
    digits = "零一二三四五六七八九"
    units = ("", "十", "百", "千")

    def under_ten_thousand(number: int) -> str:
        result, pending_zero = "", False
        for index in range(3, -1, -1):
            digit = number // (10**index) % 10
            if digit:
                if pending_zero and result:
                    result += "零"
                result += digits[digit] + units[index]
                pending_zero = False
            elif result:
                pending_zero = True
        return result or "零"

    number = int(value or 0)
    if not number:
        return "零"
    high, low = divmod(number, 10000)
    result = under_ten_thousand(high) + "萬" if high else ""
    if high and low and low < 1000:
        result += "零"
    if low:
        result += under_ten_thousand(low)
    return result.removeprefix("一十")


def paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>"), style)


def markup(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(value, style)


def circle(selected: bool) -> str:
    return "●" if selected else "○"


def residency_choice(person: dict) -> str:
    status = str(person.get("residency_status") or "")
    nationality = str(person.get("nationality") or "")
    if "未達" in status:
        return "f-under"
    if "183" in status:
        return "f183"
    if "未在台" in status:
        return "tw-abroad"
    if "本國" in status or "台灣" in nationality or "臺灣" in nationality:
        return "tw"
    return "f-under" if nationality else "tw"


def render_labor_report_pdf(report: dict, person: dict) -> bytes:
    """Render the labour receipt in the established generator's table layout."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title=f"勞務報酬單_{report['recipient_name']}_{report['work_date']}",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontName=FONT_NAME, fontSize=18, leading=24, alignment=1, spaceAfter=5 * mm)
    text = ParagraphStyle("text", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=9.4, leading=14)
    small = ParagraphStyle("small", parent=text, fontSize=8.3, leading=11)
    label = ParagraphStyle("label", parent=text, fontSize=9, leading=12, alignment=1)
    vertical = ParagraphStyle("vertical", parent=label, leading=12, wordWrap="CJK")
    amount = ParagraphStyle("amount", parent=text, alignment=2, fontSize=10)
    right = ParagraphStyle("right", parent=text, alignment=2)

    income_code = INCOME_CODE.get(str(report["income_category"]), "9A")
    residency = residency_choice(person)
    income_text = "　　".join(
        f"{circle(income_code == code)} {name}"
        for code, name in [("9A", "執行業務所得(9A)"), ("9B", "稿費(9B)"), ("50", "兼職所得(50)"), ("92", "其他所得(92)")]
    )
    residency_text = "<br/>".join(
        f"{circle(residency == code)} {name}"
        for code, name in [("tw", "本國籍"), ("tw-abroad", "本國籍但未在台居住"), ("f183", "外國籍在台滿183天"), ("f-under", "外國籍在台未達183天")]
    )
    gross = int(report["gross_amount"] or 0)
    insurance = int(report["supplemental_health_insurance"] or 0)
    tax = int(report["withholding_tax"] or 0)
    net = int(report["net_amount"] or 0)
    tax_rate = float(report["withholding_rate"] or 0)
    is_nonresident = str(report["income_category"]).endswith("nonresident")
    payment_is_wire = report["payment_method"] == "wire"

    bank_table = Table([
        [paragraph(f"銀行：{report['bank_name'] or ''}", small), paragraph(f"銀行代碼：{report['bank_code'] or ''}", small), paragraph(f"分行：{report['bank_branch'] or ''}", small), paragraph(f"分行代碼：{report['bank_branch_code'] or ''}", small)],
        [paragraph(f"戶名：{report['bank_account_holder'] or ''}", small), "", paragraph(f"帳號：{report['bank_account_number'] or ''}", small), ""],
    ], colWidths=[38 * mm, 30 * mm, 38 * mm, 34 * mm])
    bank_table.setStyle(TableStyle([
        ("SPAN", (0, 1), (1, 1)), ("SPAN", (2, 1), (3, 1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    wire = [paragraph(f"{circle(payment_is_wire)} 匯款", text), Spacer(1, 1.5 * mm), bank_table]
    period = str(report.get("work_period") or report["work_date"])
    id_label = str(report["id_document_type"] or "證件號碼")

    rows = [
        [paragraph("所得類別", label), paragraph(income_text, text), "", "", "", ""],
        [markup("領<br/>款<br/>人<br/>基<br/>本<br/>資<br/>料", vertical), markup(residency_text, text), paragraph("姓名：", text), paragraph(report["recipient_name"], text), "", ""],
        ["", "", paragraph(f"{id_label}：", text), paragraph(report["id_document_number"], text), "", ""],
        ["", "", paragraph("聯絡電話：", text), paragraph(person.get("phone") or "", text), "", ""],
        ["", "", paragraph("戶籍地址：", text), paragraph(person.get("permanent_address") or "", text), "", ""],
        ["", "", paragraph("通訊地址：", text), paragraph(person.get("mailing_address") or "", text), "", ""],
        [paragraph("勞務內容", label), paragraph(report["work_description"], text), "", "", "", ""],
        [paragraph("勞務期間", label), paragraph(period, text), "", "", "", ""],
        [markup("領<br/>款<br/>金<br/>額", vertical), paragraph("應付金額", label), markup("二代健保扣費<br/>2.11%", label), markup(f"所得稅扣繳<br/>{circle(tax_rate == 0.05)} 5%　{circle(tax_rate == 0.10)} 10%", label), markup("所得稅<br/>就源扣繳", label), paragraph("實付金額", label)],
        ["", paragraph(money(gross), amount), paragraph(money(insurance) if insurance else "", amount), paragraph(money(tax) if tax and not is_nonresident else "", amount), paragraph(money(tax) if tax and is_nonresident else "", amount), paragraph(money(net), amount)],
        ["", paragraph(f"新台幣{chinese_number(gross)}元整　→　實付新台幣{chinese_number(net)}元整", small), "", "", "", ""],
        [markup("支<br/>付<br/>方<br/>式", vertical), paragraph(f"{circle(not payment_is_wire)} 現金　　　已確認收到福爾摩沙藝響支付本人之報酬", text), "", "", "", ""],
        ["", wire, "", "", "", ""],
        [[paragraph("上述資料經所得人確認無誤。所得人（簽名或蓋章）：", text), Spacer(1, 9 * mm), paragraph(report["issue_date"], right)], "", "", "", "", ""],
    ]
    table = Table(rows, colWidths=[14 * mm, 40 * mm, 25 * mm, 28 * mm, 31 * mm, 44 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.55, colors.HexColor("#222222")),
        ("SPAN", (1, 0), (5, 0)), ("SPAN", (0, 1), (0, 5)), ("SPAN", (1, 1), (1, 5)),
        ("SPAN", (3, 1), (5, 1)), ("SPAN", (3, 2), (5, 2)), ("SPAN", (3, 3), (5, 3)),
        ("SPAN", (3, 4), (5, 4)), ("SPAN", (3, 5), (5, 5)), ("SPAN", (1, 6), (5, 6)),
        ("SPAN", (1, 7), (5, 7)), ("SPAN", (0, 8), (0, 10)), ("SPAN", (1, 10), (5, 10)),
        ("SPAN", (0, 11), (0, 12)), ("SPAN", (1, 11), (5, 11)), ("SPAN", (1, 12), (5, 12)),
        ("SPAN", (0, 13), (5, 13)),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f5f0e8")),
        ("BACKGROUND", (0, 1), (0, 5), colors.HexColor("#f5f0e8")),
        ("BACKGROUND", (0, 6), (0, 7), colors.HexColor("#f5f0e8")),
        ("BACKGROUND", (0, 8), (0, 10), colors.HexColor("#f5f0e8")),
        ("BACKGROUND", (0, 11), (0, 12), colors.HexColor("#f5f0e8")),
        ("BACKGROUND", (1, 8), (5, 8), colors.HexColor("#f9f6f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (1, 12), (5, 12), 4), ("BOTTOMPADDING", (1, 12), (5, 12), 5),
        ("MINHEIGHT", (0, 6), (-1, 6), 12 * mm), ("MINHEIGHT", (0, 13), (-1, 13), 30 * mm),
    ]))
    personal_stamp = Image(str(ASSETS_PATH / "stamps" / "stamp_personal.png"), width=22 * mm, height=21 * mm)
    org_stamp = Image(str(ASSETS_PATH / "stamps" / "stamp_org.png"), width=31 * mm, height=30 * mm)
    stamps = Table([[personal_stamp, org_stamp]], colWidths=[24 * mm, 33 * mm])
    handler = Table([["", paragraph("經手人：江月萱", right)], ["", stamps]], colWidths=[120 * mm, 62 * mm])
    handler.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    document.build([
        Paragraph("福爾摩沙藝響 勞務報酬單", title), table, Spacer(1, 3 * mm),
        paragraph("另外檢附所得人身分證（居留證／護照）正反面影本。", text),
        Spacer(1, 2 * mm), handler,
    ])
    return buffer.getvalue()
