from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


path = Path("/Users/pyen/OpusFormosa/festival_planning/logistics/Opus_Formosa_2026_Da_Zong_Guan_Handbook.docx")
document = Document(path)
for table in document.tables:
    if table.rows and table.rows[0].cells[0].text == "日期" and table.rows[0].cells[1].text == "行程／車次":
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:tblHeader")) is None:
            tr_pr.append(OxmlElement("w:tblHeader"))
        for row in table.rows[1:]:
            row_pr = row._tr.get_or_add_trPr()
            if row_pr.find(qn("w:cantSplit")) is None:
                row_pr.append(OxmlElement("w:cantSplit"))
        break
document.save(path)
