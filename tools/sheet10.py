"""Contact sheet of PNG stills: python tools/sheet10.py <dir> -> <dir>/sheet.png (270x480 each)."""
import glob, sys
from PIL import Image
fs = sorted(glob.glob(sys.argv[1] + '/f_*.png'), key=lambda f: float(f.split('_')[-1][:-4]))
s = Image.new('RGB', (270 * len(fs), 480))
for i, f in enumerate(fs): s.paste(Image.open(f).resize((270, 480)), (i * 270, 0))
s.save(sys.argv[1] + '/sheet.png')
