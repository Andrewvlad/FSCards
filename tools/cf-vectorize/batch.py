"""Trace every native CF cell in native/ to SVG under the repo's USPA set dirs,
then QA each against its source at native size (mean-abs-error screen)."""
from multiprocessing import Pool
from pathlib import Path
from PIL import Image
import numpy as np
import cairosvg, io

from trace import descrumb, trace

HERE = Path(__file__).resolve().parent
SRC = HERE / 'native'
DST = HERE.parent.parent / 'assets/diagrams'

jobs = []
for disc in ('2-way-cf', '4-way-cf'):
    for webp in sorted((SRC / disc).rglob('*.webp')):
        rel = webp.relative_to(SRC / disc)               # e.g. figures/A.webp
        out = DST / disc / 'USPA' / rel.with_suffix('.svg')
        out.parent.mkdir(parents=True, exist_ok=True)
        jobs.append((str(webp), str(out)))


def run(job):
    src, dst = job
    trace(src, dst)
    orig = descrumb(Image.open(src).convert('L'))
    png = Image.open(io.BytesIO(cairosvg.svg2png(url=dst, output_width=orig.width, output_height=orig.height)))
    # The SVGs are background-free; composite onto white to compare against the cells
    back = Image.alpha_composite(Image.new('RGBA', png.size, 'white'), png.convert('RGBA')).convert('L')
    mae = np.abs(np.asarray(orig, float) - np.asarray(back, float)).mean()
    return dst, mae, Path(dst).stat().st_size


if __name__ == '__main__':
    results = Pool(8).map(run, jobs)
    worst = sorted(results, key=lambda r: -r[1])[:5]
    total = sum(r[2] for r in results)
    print(f'{len(results)} traced, {total / 1024:.0f} KB total')
    for dst, mae, size in worst:
        print(f'  worst MAE {mae:.2f}  {size / 1024:.0f}KB  {dst}')
