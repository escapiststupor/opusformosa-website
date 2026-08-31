from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw


def make_sheets(input_dir, output_dir, per_sheet=4):
    pages = sorted(Path(input_dir).glob('page-*.png'), key=lambda path: int(path.stem.split('-')[1]))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for sheet_number in range(ceil(len(pages) / per_sheet)):
        batch = pages[sheet_number * per_sheet:(sheet_number + 1) * per_sheet]
        thumbs = []
        for page in batch:
            image = Image.open(page).convert('RGB')
            image.thumbnail((500, 700))
            thumbs.append((page.name, image.copy()))
        canvas = Image.new('RGB', (1040, 1460), 'white')
        draw = ImageDraw.Draw(canvas)
        for i, (name, image) in enumerate(thumbs):
            x = 10 + (i % 2) * 520
            y = 10 + (i // 2) * 730
            draw.text((x, y), name, fill='black')
            canvas.paste(image, (x, y + 24))
        canvas.save(output / f'contact-{sheet_number + 1}.png')


make_sheets('/private/tmp/kyu_personal_render', '/private/tmp/kyu_personal_contacts')
make_sheets('/private/tmp/kyu_handbook_render', '/private/tmp/kyu_handbook_contacts')
