from docx import Document


PATH = "/Users/pyen/OpusFormosa/festival_planning/logistics/Opus_Formosa_2026_Da_Zong_Guan_Handbook.docx"
DATES = {
    4: "9/2", 5: "9/3", 6: "9/4", 7: "9/5", 8: "9/6", 9: "9/7",
    10: "9/8", 11: "9/9", 12: "9/10", 13: "9/11", 14: "9/12",
    15: "9/13", 16: "9/14", 17: "9/15", 18: "9/16", 19: "9/17",
}
NTCH_VENUES = {"CHR1", "CHR2", "CHR3", "CHR4", "國家音樂廳", "國家演奏廳"}

document = Document(PATH)
first = {}
all_entries = []

for table_index, date in DATES.items():
    for row in document.tables[table_index].rows[1:]:
        time, people, activity, venue, _ = [cell.text for cell in row.cells]
        if venue not in NTCH_VENUES:
            continue
        for person in [name.strip() for name in people.split(";") if name.strip()]:
            first.setdefault(person, (date, time, activity, venue))
            all_entries.append((date, time, person, activity, venue))

print("FIRST NTCH/CHR ENTRY")
for person, detail in first.items():
    print(person, "|", " | ".join(detail))

print("\nALL NTCH/CHR ENTRIES")
for entry in all_entries:
    print(" | ".join(entry))
