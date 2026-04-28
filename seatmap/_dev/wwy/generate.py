#!/usr/bin/env python3
"""
衛武營國家藝術文化中心音樂廳 座位圖產生器
用法: python3 generate-wwy.py
輸出: ../weiwuying/index.html

每次新音樂會，只需要修改下方的 CONCERT 和 COLOR_PRICE / SPECIAL_PRICES 兩個區塊。

────────────────────────────────────────────────────────────────────────────
設計說明
────────────────────────────────────────────────────────────────────────────
衛武營音樂廳有 2012 席，分佈在三個樓層：
  1樓  1~2 號門（1F 正廳，最前段）
  2樓  3~8 號門（2F 正廳，中段，含部分輪椅席）
  3樓  9~16 號門（3F 樓上，全灰色，以 2F 有色座位推算）

  特殊席：
    輪椅席  — 以顏色 rgb(174,0,193) 識別（出現在 2F 7/8 號門正廳）
             另有 X號門輪椅席 獨立 section（顏色 rgb(27,129,62)，沿用原色 $800）
    陪同席  — 以顏色 rgb(254,219,181) 識別

來源 SVG 顏色直接對應 OPENTIX 票價區間，
灰色（已售/保留）座位以空間鄰近推算。
來源：衛武營票圖_音樂廳.xlsx
"""

import re
import math
from collections import defaultdict

# ─── 音樂會設定 ────────────────────────────────────────────────────────────────

CONCERT = {
    'name':  'Opus Formosa',
    'venue': '衛武營國家藝術文化中心音樂廳',
}

# ─── 票價對應（每次新音樂會修改這裡）────────────────────────────────────────────
#
# 各顏色代表的區間（來自 OPENTIX）：
#   紅     rgb(248,4,0)     → 最佳區（$2,500 1F正廳前段）
#   淺橘   rgb(252,179,142) → 優良區（$1,200 1F正廳）
#   藍     rgb(0,76,253)    → 良好區（$2,100 2F中央前段）
#   黃     rgb(253,255,0)   → 一般區（$1,800 2F中段）
#   淺藍   rgb(111,206,248) → 上層區（$1,500 2F/3F）
#   深橘   rgb(248,144,18)  → 側邊區（$1,000 2F側邊）
#   紫     rgb(174,0,193)   → 輪椅席（$1,200 2F 7/8號門）
#   淺肉   rgb(254,219,181) → 輪椅陪同席（$1,200）
#   綠     rgb(27,129,62)   → 輪椅席 section 原色（$800）

COLOR_PRICE = {
    'rgb(248, 4, 0)':     '$2,500 元',
    'rgb(0, 76, 253)':    '$2,100 元',
    'rgb(253, 255, 0)':   '$1,800 元',
    'rgb(111, 206, 248)': '$1,500 元',
    'rgb(252, 179, 142)': '$1,200 元',
    'rgb(248, 144, 18)':  '$1,000 元',
    'rgb(27, 129, 62)':   '$800 元',
    # 輪椅相關（以顏色識別，出現在正廳）
    'rgb(174, 0, 193)':   '輪椅席 $1,200 元',
    'rgb(254, 219, 181)': '輪椅陪同席 $1,200 元',
}

# 特殊 section 名稱關鍵字 → 強制標籤（優先於顏色）
# WWY 的輪椅席 section 使用綠色（已在 COLOR_PRICE 對應到 $800），
# 若想改為特殊標籤可在這裡加入：
SPECIAL_PRICES = {
    # 範例：'輪椅席': '輪椅席 $800 元',
}

# ─── 以下為產生邏輯（通常不需要修改）────────────────────────────────────────────

GRAY = 'rgb(235, 235, 235)'

# 3F 全灰色，以 2F 有色座位推算（同屬衛武營上層區域）
# key = section 前綴，value = 推算用的 section 前綴
SECTION_PROXY = {
    '3樓': '2樓',  # 3F sections → use 2F colored seats
}


def parse_seats(content):
    circles = re.findall(r'<circle\b.*?</circle>', content, re.DOTALL)
    seats = []
    for c in circles:
        if 'class="seat"' not in c:
            continue
        id_m   = re.search(r'[\s\n]id="([^"]+)"', c)
        fill_m = re.search(r'fill:\s*(rgb\([^)]+\))', c)
        cx_m   = re.search(r'\bcx="([^"]+)"', c)
        cy_m   = re.search(r'\bcy="([^"]+)"', c)
        tf_m   = re.search(r'transform="matrix\(([^)]+)\)"', c)
        if not (id_m and fill_m):
            continue
        parts = id_m.group(1).rsplit('-', 2)
        if len(parts) != 3:
            continue
        section, row, seat_num = parts[0], parts[1], parts[2]
        cx, cy = float(cx_m.group(1)) if cx_m else 0.0, float(cy_m.group(1)) if cy_m else 0.0
        if tf_m:
            vals = [float(v.strip()) for v in tf_m.group(1).split(',')]
            a, b, c2, d, e, f = vals
            cx, cy = a * cx + c2 * cy + e, b * cx + d * cy + f
        seats.append({'id': id_m.group(1), 'section': section, 'row': row,
                      'seat': seat_num, 'color': fill_m.group(1), 'cx': cx, 'cy': cy})
    return seats


def infer_gray_prices(seats):
    """
    空間距離推算：
    - 3F sections 以 2F 有色座位推算
    - 其他 sections 以同 section 有色座位推算（0.2× 距離偏權）
    """
    colored_by_prefix = defaultdict(list)   # 'X樓' -> [(cx,cy,color), ...]
    colored_by_sec    = defaultdict(list)   # 'section' -> [(cx,cy,color), ...]
    all_colored = []
    for s in seats:
        if s['color'] != GRAY:
            prefix = s['section'][:2]  # '1樓' / '2樓' / '3樓'
            colored_by_prefix[prefix].append((s['cx'], s['cy'], s['color']))
            colored_by_sec[s['section']].append((s['cx'], s['cy'], s['color']))
            all_colored.append((s['cx'], s['cy'], s['color'], s['section']))

    inferred = {}
    for s in seats:
        if s['color'] != GRAY:
            continue
        sec, sx, sy = s['section'], s['cx'], s['cy']
        prefix = sec[:2]  # '1樓' / '2樓' / '3樓'

        # Check if this section's floor uses a proxy
        proxy_prefix = None
        for k, v in SECTION_PROXY.items():
            if prefix == k:
                proxy_prefix = v
                break

        if proxy_prefix:
            pts = colored_by_prefix.get(proxy_prefix, [])
        else:
            pts = colored_by_sec.get(sec, [])

        if pts:
            best_color = min(pts, key=lambda p: math.hypot(p[0]-sx, p[1]-sy))[2]
        else:
            best_color = min(all_colored,
                             key=lambda p: math.hypot(p[0]-sx, p[1]-sy) * (0.2 if p[3]==sec else 1))[2]
        inferred[s['id']] = best_color
    return inferred


def assign_price(section, color, inferred_color):
    for keyword, label in SPECIAL_PRICES.items():
        if keyword in section:
            return label
    c = color if color != GRAY else inferred_color
    return COLOR_PRICE.get(c, '') if c else ''


def enrich_circle(tag, gray_map):
    if 'class="seat"' not in tag:
        return tag
    id_m   = re.search(r'[\s\n]id="([^"]+)"', tag)
    fill_m = re.search(r'fill:\s*(rgb\([^)]+\))', tag)
    if not (id_m and fill_m):
        return tag
    parts = id_m.group(1).rsplit('-', 2)
    if len(parts) != 3:
        return tag
    section, row, seat_num = parts[0], parts[1], parts[2]
    orig_color = fill_m.group(1)
    inferred   = gray_map.get(id_m.group(1))
    label      = assign_price(section, orig_color, inferred)
    display    = orig_color if orig_color != GRAY else (inferred or GRAY)
    attrs = (f' data-section="{section}" data-row="{row}"'
             f' data-seat-num="{seat_num}" data-price="{label}"')
    tag = re.sub(r'\s+data-(?:section|row|seat-num|price)="[^"]*"', '', tag)
    tag = tag.replace('class="seat"', f'class="seat"{attrs}', 1)
    tag = re.sub(r'(style="[^"]*fill:\s*)rgb\([^)]+\)', rf'\1{display}', tag)
    return tag


def main():
    src_path = 'source.html'
    out_path = '../../wwy/wwy.html'

    print(f'Reading {src_path}...')
    with open(src_path, encoding='utf-8') as f:
        content = f.read()

    print('Parsing seats...')
    seats = parse_seats(content)
    gray_count = sum(1 for s in seats if s['color'] == GRAY)
    print(f'  Total: {len(seats)} seats, {gray_count} gray')

    print('Running spatial inference...')
    gray_map = infer_gray_prices(seats)

    # Extract canvas SVG
    canvas_start = content.rfind('<svg', 0, content.find('id="canvas"'))
    depth, svg_end = 0, -1
    for m in re.finditer(r'<svg[\s>]|</svg>', content[canvas_start:]):
        depth += 1 if m.group(0).startswith('<svg') else -1
        if depth == 0:
            svg_end = canvas_start + m.end()
            break
    canvas_svg = content[canvas_start:svg_end]
    canvas_svg = re.sub(r'(<svg\b[^>]*id="canvas"[^>]*)width="[^"]*"',  r'\1width="100%"',  canvas_svg, count=1)
    canvas_svg = re.sub(r'(<svg\b[^>]*id="canvas"[^>]*)height="[^"]*"', r'\1height="auto"', canvas_svg, count=1)

    print('Enriching SVG...')
    count = [0]
    def enricher(m):
        r = enrich_circle(m.group(0), gray_map)
        if 'data-price=' in r: count[0] += 1
        return r
    canvas_svg = re.sub(r'<circle\b.*?</circle>', enricher, canvas_svg, flags=re.DOTALL)

    # Legend
    seen, price_color = [], {}
    for color, label in COLOR_PRICE.items():
        if label not in seen:
            seen.append(label)
            price_color[label] = color
    legend_items = ''.join(
        f'<div class="li"><span class="dot" style="background:{price_color.get(lb,"#aaa")}"></span>{lb}</div>'
        for lb in seen
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{CONCERT['name']} — {CONCERT['venue']} 座位圖</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","微軟正黑體",sans-serif}}
#wrap{{display:flex;flex-direction:column;height:100vh}}
#hdr{{background:#fff;border-bottom:3px solid #e94560;padding:10px 18px;flex-shrink:0}}
#hdr h1{{font-size:15px;font-weight:700;color:#1a1a1a}}
#body{{flex:1;display:flex;overflow:hidden}}
#map{{flex:1;overflow:auto;padding:16px;background:#fafafa;display:flex;align-items:flex-start;justify-content:center}}
#map svg{{display:block;width:100%;max-width:900px}}
#side{{width:210px;background:#fff;border-left:1px solid #eee;padding:14px;overflow-y:auto;flex-shrink:0}}
#side h2{{font-size:13px;font-weight:700;color:#333;margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid #f0f0f0}}
.li{{display:flex;align-items:center;gap:7px;margin:6px 0;font-size:12px;color:#444;line-height:1.4}}
.dot{{width:13px;height:13px;border-radius:50%;flex-shrink:0;display:inline-block}}
#tip{{position:fixed;display:none;background:rgba(10,10,30,.93);color:#eee;border:1px solid #3a5a8f;border-radius:7px;padding:8px 12px;font-size:12px;line-height:1.7;pointer-events:none;z-index:9999;min-width:140px;box-shadow:0 4px 16px rgba(0,0,0,.4)}}
.tl{{color:#8ab;font-size:10px;text-transform:uppercase;letter-spacing:.4px}}
.tv{{color:#fff;font-weight:500}}
.tp{{margin-top:3px;padding-top:3px;border-top:1px solid rgba(255,255,255,.1);color:#ffd700;font-weight:600}}
text.seat{{pointer-events:none}}
</style>
</head>
<body>
<div id="wrap">
<div id="hdr"><h1>{CONCERT['venue']}</h1></div>
<div id="body">
<div id="map">{canvas_svg}</div>
<div id="side"><h2>票價圖例</h2>{legend_items}</div>
</div>
</div>
<div id="tip"></div>
<script>
const tip=document.getElementById('tip');
document.addEventListener('mouseover',e=>{{
  const el=e.target;
  if(!el.classList?.contains('seat')||el.tagName.toLowerCase()!=='circle')return;
  const s=el.getAttribute('data-section')||'',r=el.getAttribute('data-row')||'',n=el.getAttribute('data-seat-num')||'',p=el.getAttribute('data-price')||'';
  if(!s)return;
  tip.innerHTML=`<div class="tl">區域</div><div class="tv">${{s}}</div><div class="tl">排 / 座位</div><div class="tv">第${{r}}排 · 第${{n}}號</div><div class="tp">${{p||'—'}}</div>`;
  tip.style.display='block';posit(e);
}});
document.addEventListener('mousemove',e=>{{if(tip.style.display!=='none')posit(e)}});
document.addEventListener('mouseout',e=>{{if(e.target.classList?.contains('seat'))tip.style.display='none'}});
function posit(e){{
  let x=e.clientX+14,y=e.clientY+14;
  const w=tip.offsetWidth||160,h=tip.offsetHeight||100;
  if(x+w>window.innerWidth-8)x=e.clientX-w-14;
  if(y+h>window.innerHeight-8)y=e.clientY-h-14;
  tip.style.left=x+'px';tip.style.top=y+'px';
}}
</script>
</body></html>"""

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Done. Wrote {out_path} ({count[0]} seats enriched)')


if __name__ == '__main__':
    main()
