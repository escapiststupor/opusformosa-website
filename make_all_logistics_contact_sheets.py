from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw


render_root = Path('/private/tmp/glandys_doc_renders')
output_root = Path('/private/tmp/glandys_doc_contacts')
output_root.mkdir(parents=True, exist_ok=True)
pages = []
for directory in sorted(render_root.iterdir()):
    for page in sorted(directory.glob('page-*.png'), key=lambda path: int(path.stem.split('-')[1])):
        pages.append((f'{directory.name}/{page.name}', page))

for sheet_number in range(ceil(len(pages) / 4)):
    canvas = Image.new('RGB', (1040, 1460), 'white')
    draw = ImageDraw.Draw(canvas)
    for i, (label, page) in enumerate(pages[sheet_number * 4:(sheet_number + 1) * 4]):
        image = Image.open(page).convert('RGB')
        image.thumbnail((500, 680))
        x = 10 + (i % 2) * 520
        y = 10 + (i // 2) * 730
        draw.text((x, y), label, fill='black')
        canvas.paste(image, (x, y + 24))
    canvas.save(output_root / f'contact-{sheet_number + 1}.png')
print(f'pages={len(pages)} sheets={ceil(len(pages) / 4)}')
