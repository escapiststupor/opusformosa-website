from pathlib import Path

import re


source = Path('/Users/pyen/.codex/attachments/b7cac920-823e-4123-89b1-d4a5912967d8/pasted-text.txt')
html = source.read_text()
date_labels = re.findall(r'<span class="css-(?:7vjk4e|l4b320)">(\d+) 日</span>', html)
day_segments = [
    segment for segment in re.split(r'<div class="css-1oj2c65">', html)
    if 'css-1mh3b3q' in segment
]

print(f'day_groups={len(day_segments)} date_labels={len(date_labels)}')
for index, day in enumerate(day_segments):
    for session in re.split(r'<div class="css-1mh3b3q">', day)[1:]:
        session_match = re.search(r'<span class="css-1lwx6bl">([^<]+)</span>', session)
        session_name = session_match.group(1) if session_match else '?'
        room_blocks = re.split(r'<div class="css-cu77lo">', session)[1:]
        for room in room_blocks:
            room_match = re.search(r'<span class="css-(?:1l59wtg|w08uyg)">([^<]+)</span>', room)
            title_match = re.search(r'<button title="Opus 室內樂系列 II《異鄉之憶》"', room)
            if title_match:
                print({
                    'day_index': index,
                    'date_label': date_labels[index] if index < len(date_labels) else None,
                    'session': session_name,
                    'room': room_match.group(1) if room_match else None,
                    'cancel_count': room.count('>取消<'),
                })
