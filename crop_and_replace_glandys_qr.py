import hashlib
import io
import zipfile
from pathlib import Path

from PIL import Image


ROOT = Path('/Users/pyen/OpusFormosa/festival_planning/logistics')
SOURCE = Path('/var/folders/64/y4m8r3fj3f5020hryd4sq5mh0000gp/T/codex-clipboard-ee427d0f-bf5a-493e-acf7-eef4f297e04a.png')
QR = Path('/private/tmp/glandys_whatsapp_qr.png')


source_bytes = SOURCE.read_bytes()
source_digest = hashlib.sha256(source_bytes).hexdigest()
image = Image.open(io.BytesIO(source_bytes)).convert('RGB')
# Crop the white QR panel, excluding the dark WhatsApp profile background.
crop = image.crop((235, 430, 910, 1135))
crop.save(QR, format='PNG', optimize=True)
replacement = QR.read_bytes()

for path in sorted(ROOT.glob('*.docx')):
    with zipfile.ZipFile(path, 'r') as archive:
        members = [(info, archive.read(info.filename)) for info in archive.infolist()]
    replaced = 0
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for info, data in members:
            if info.filename.startswith('word/media/') and hashlib.sha256(data).hexdigest() == source_digest:
                data = replacement
                replaced += 1
            archive.writestr(info, data)
    if replaced != 1:
        raise RuntimeError(f'{path.name}: expected one Glandys image, replaced {replaced}')
print('Replaced the QR image in all logistics manuals.')
