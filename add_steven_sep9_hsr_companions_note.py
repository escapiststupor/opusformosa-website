from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Steven_Lin.docx"
NEW_LINE = "Sep 9, Kaohsiung: Steven Lin, Jinjoo Cho, and Edgar Moreau."
ANCHOR = "Sep 13, Taichung: Steven Lin and Edgar Moreau."

document = Document(PATH)
paragraphs = document.paragraphs
anchor_index = next(
    index for index, paragraph in enumerate(paragraphs)
    if paragraph.text.strip() == ANCHOR
)

if any(paragraph.text.strip() == NEW_LINE for paragraph in paragraphs):
    raise RuntimeError("Sep 9 HSR companion note already exists")

anchor = paragraphs[anchor_index]
new_paragraph = anchor.insert_paragraph_before(NEW_LINE)
new_paragraph.style = anchor.style

document.save(PATH)
print("Added Sep 9 HSR companion note.")
