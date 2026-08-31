from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Opus_Formosa_2026_Da_Zong_Guan_Handbook.docx"

document = Document(PATH)
table = document.tables[3]
for row in table.rows[1:]:
    if row.cells[1].text == "Kyu Yeon Kim" and row.cells[2].text == "琴房：平台鋼琴":
        row.cells[0].text = "9月7日 16:00–19:00"
        document.save(PATH)
        print("Corrected Kyu Yeon's Sep 7 special-practice time.")
        break
else:
    raise ValueError("Kyu Yeon Sep 7 special-practice row was not found.")
