from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Opus_Formosa_2026_Da_Zong_Guan_Handbook.docx"

document = Document(PATH)
for index in range(5, 20):
    print(f"--- TABLE {index}")
    for row in document.tables[index].rows[1:]:
        print(" || ".join(cell.text.replace("\n", " / ") for cell in row.cells))
