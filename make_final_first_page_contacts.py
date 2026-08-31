from math import ceil
from pathlib import Path
from PIL import Image, ImageDraw

root = Path('/private/tmp/glandys_doc_renders_final')
out = Path('/private/tmp/glandys_final_first_page_contacts')
out.mkdir(parents=True, exist_ok=True)
pages = [(directory.name, directory / 'page-1.png') for directory in sorted(root.iterdir())]
for number in range(ceil(len(pages) / 4)):
    canvas = Image.new('RGB', (1040, 1460), 'white')
    draw = ImageDraw.Draw(canvas)
    for i, (label, page) in enumerate(pages[number * 4:(number + 1) * 4]):
        image = Image.open(page).convert('RGB')
        image.thumbnail((500, 680))
        x = 10 + (i % 2) * 520
        y = 10 + (i // 2) * 730
        draw.text((x, y), label, fill='black')
        canvas.paste(image, (x, y + 24))
    canvas.save(out / f'contact-{number + 1}.png')
