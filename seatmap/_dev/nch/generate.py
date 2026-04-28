#!/usr/bin/env python3
"""
國家音樂廳 座位圖產生器
用法: python3 generate-nch.py
輸出: ../nch/index.html

每次新音樂會，只需要修改下方的 CONCERT 和 COLOR_PRICE / SPECIAL_PRICES 兩個區塊。

────────────────────────────────────────────────────────────────────────────
設計說明
────────────────────────────────────────────────────────────────────────────
國家音樂廳有 2022 席，分佈在三個樓層：
  2樓 (1150 席)  主廳，32 排 + 特殊席
  3樓 ( 422 席)  包廂走廊（排名：VA, VB, 1B~1E, 排 1~11）
  4樓 ( 436 席)  包廂走廊（排名：2B~2E,    排 1~12）

來源 SVG 的顏色直接對應票價區間（OPENTIX 標準），
所以定價只需要編輯 COLOR_PRICE 裡的文字標籤即可。
灰色（已售出/預留）座位會根據鄰近座位自動推算票價。
"""

import re
import math
from collections import defaultdict

# ─── 音樂會設定 ────────────────────────────────────────────────────────────────

CONCERT = {
    'name':  'Opus Formosa',
    'venue': '國家兩廳院音樂廳',
}

# ─── 票價對應（每次新音樂會修改這裡）────────────────────────────────────────────
#
# KEY   = 來源 SVG 中的原始顏色（代表票價區間，不要修改 key）
# VALUE = 顯示給觀眾的票價文字（依照演出修改即可）
#
# 各顏色代表的區間（來自 OPENTIX）：
#   橘紅 rgb(246,112,61)   → 精華席：2樓 第14排（最佳視野）
#   深藍 rgb(0,92,175)     → 優良席：2樓 中段中央（約第5~18排中間位置）
#   綠   rgb(134,193,102)  → 良好席：2樓 大部分（前/中段）
#   琥珀 rgb(250,174,23)   → 一般席：2樓 兩側 & 3樓前段
#   青綠 rgb(0,167,151)    → 遠距席：3、4樓大部分
#   紫   rgb(186,111,248)  → 後排席：2樓末排 & 3、4樓後段

COLOR_PRICE = {
    'rgb(246, 112, 61)':  '$2,500 元',
    'rgb(0, 92, 175)':    '$2,000 元',
    'rgb(134, 193, 102)': '$1,600 元',
    'rgb(250, 174, 23)':  '$1,200 元',
    'rgb(0, 167, 151)':   '$900 元',
    'rgb(186, 111, 248)': '$600 元',
}

# 特殊席位（以 section 名稱判斷，優先於顏色）
SPECIAL_PRICES = {
    '2樓輪椅席': '輪椅席 $1,200 元',
    '2樓輪陪席': '輪椅陪同席 $1,200 元',
    '2樓友善席': '多元友善席 $1,200 元',
    '2樓友陪席': '多元友善陪同席 $1,200 元',
}

# ─── 以下為產生邏輯（通常不需要修改）────────────────────────────────────────────

GRAY = 'rgb(235, 235, 235)'  # OPENTIX 已售出/保留座位顏色


def parse_seats(content):
    """從 HTML 解析所有 circle.seat，回傳 seat 物件 list"""
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
        seat_id = id_m.group(1)
        parts = seat_id.rsplit('-', 2)
        if len(parts) != 3:
            continue
        section, row, seat_num = parts[0], parts[1], parts[2]
        color = fill_m.group(1)

        # Compute actual screen position for spatial inference
        cx, cy = float(cx_m.group(1)) if cx_m else 0.0, float(cy_m.group(1)) if cy_m else 0.0
        if tf_m:
            vals = [float(v.strip()) for v in tf_m.group(1).split(',')]
            # matrix(a,b,c,d,e,f): x_actual = a*cx + c*cy + e
            a, b, c, d, e, f = vals
            cx, cy = a * cx + c * cy + e, b * cx + d * cy + f

        seats.append({
            'id':      seat_id,
            'section': section,
            'row':     row,
            'seat':    seat_num,
            'color':   color,
            'cx':      cx,
            'cy':      cy,
        })
    return seats


def infer_gray_prices(seats):
    """
    灰色座位票價推算（空間距離法）：
    找最近的有色座位，同 section 距離乘以 0.2 偏權。

    特殊規則：
    - 高價票 ($2,500/$2,000) 不納入推算池，避免少數特殊席擴散
    - 4樓 (全灰色) 以 3樓有色座位推算（同屬樓上包廂區）
    """
    INFERENCE_EXCLUDE = {'rgb(246, 112, 61)', 'rgb(0, 92, 175)'}

    # 4樓全灰，以 3樓有色座位作為推算依據
    SECTION_PROXY = {'4樓': '3樓'}

    # Colored seat points grouped by section
    colored_by_sec = defaultdict(list)
    all_colored = []
    for s in seats:
        if s['color'] != GRAY and s['color'] not in INFERENCE_EXCLUDE:
            colored_by_sec[s['section']].append((s['cx'], s['cy'], s['color']))
            all_colored.append((s['cx'], s['cy'], s['color'], s['section']))

    inferred = {}
    for s in seats:
        if s['color'] != GRAY:
            continue
        sec = s['section']
        proxy_sec = SECTION_PROXY.get(sec, sec)
        sx, sy = s['cx'], s['cy']

        # Use proxy section's colored pts; fall back to same section, then all
        pts = colored_by_sec.get(proxy_sec) or colored_by_sec.get(sec)
        if pts:
            best_color = min(pts, key=lambda p: math.hypot(p[0]-sx, p[1]-sy))[2]
        else:
            # Cross-section with 0.2x bias for same section
            best_color = min(all_colored,
                             key=lambda p: math.hypot(p[0]-sx, p[1]-sy) * (0.2 if p[3]==sec else 1))[2]
        inferred[s['id']] = best_color

    return inferred


def assign_price(section, color, gray_inferred_color):
    """回傳最終顯示的票價標籤"""
    # 1. 特殊 section 優先
    for keyword, label in SPECIAL_PRICES.items():
        if keyword in section:
            return label
    # 2. 原本就有顏色
    if color != GRAY:
        return COLOR_PRICE.get(color, '')
    # 3. 灰色→推算顏色
    if gray_inferred_color:
        return COLOR_PRICE.get(gray_inferred_color, '')
    return ''


def enrich_circle(tag, gray_map):
    if 'class="seat"' not in tag:
        return tag
    id_m   = re.search(r'[\s\n]id="([^"]+)"', tag)
    fill_m = re.search(r'fill:\s*(rgb\([^)]+\))', tag)
    if not (id_m and fill_m):
        return tag
    seat_id = id_m.group(1)
    parts = seat_id.rsplit('-', 2)
    if len(parts) != 3:
        return tag
    section, row, seat_num = parts[0], parts[1], parts[2]

    original_color = fill_m.group(1)
    inferred_color = gray_map.get(seat_id)
    label = assign_price(section, original_color, inferred_color)

    # Choose display color
    if original_color != GRAY:
        display_color = original_color
    elif inferred_color:
        display_color = inferred_color
    else:
        display_color = GRAY

    attrs = (f' data-section="{section}" data-row="{row}"'
             f' data-seat-num="{seat_num}" data-price="{label}"')
    tag = re.sub(r'\s+data-(?:section|row|seat-num|price)="[^"]*"', '', tag)
    tag = tag.replace('class="seat"', f'class="seat"{attrs}', 1)
    tag = re.sub(r'(style="[^"]*fill:\s*)rgb\([^)]+\)', rf'\1{display_color}', tag)
    return tag


def main():
    src_path = 'source.html'
    out_path = '../../nch/nch.html'

    print(f'Reading {src_path}...')
    with open(src_path, encoding='utf-8') as f:
        content = f.read()

    # Parse all seats for spatial inference
    print('Parsing seats for spatial inference...')
    seats = parse_seats(content)
    gray_count = sum(1 for s in seats if s['color'] == GRAY)
    print(f'  Total: {len(seats)} seats, {gray_count} gray (will be inferred)')

    print('Running spatial inference for gray seats...')
    gray_map = infer_gray_prices(seats)

    # Extract canvas SVG
    canvas_start = content.rfind('<svg', 0, content.find('id="canvas"'))
    pos, depth, svg_end = canvas_start, 0, -1
    for m in re.finditer(r'<svg[\s>]|</svg>', content[canvas_start:]):
        depth += 1 if m.group(0).startswith('<svg') else -1
        if depth == 0:
            svg_end = canvas_start + m.end()
            break
    canvas_svg = content[canvas_start:svg_end]

    # Make responsive
    canvas_svg = re.sub(r'(<svg\b[^>]*id="canvas"[^>]*)width="[^"]*"',  r'\1width="100%"',  canvas_svg, count=1)
    canvas_svg = re.sub(r'(<svg\b[^>]*id="canvas"[^>]*)height="[^"]*"', r'\1height="auto"', canvas_svg, count=1)

    # Enrich seat circles
    print('Enriching SVG circles...')
    count = [0]
    def enricher(m):
        result = enrich_circle(m.group(0), gray_map)
        if 'data-price=' in result:
            count[0] += 1
        return result
    canvas_svg = re.sub(r'<circle\b.*?</circle>', enricher, canvas_svg, flags=re.DOTALL)

    # Build legend (unique prices in order: highest first)
    price_order = list(COLOR_PRICE.values()) + list(SPECIAL_PRICES.values())
    price_to_color = {v: k for k, v in COLOR_PRICE.items()}
    # Add special section colors
    special_color_map = {
        '輪椅席 $1,200 元':         'rgb(0, 92, 175)',
        '輪椅陪同席 $1,200 元':      'rgb(0, 50, 165)',
        '多元友善席 $1,200 元':      'rgb(66, 248, 251)',
        '多元友善陪同席 $1,200 元':  'rgb(66, 200, 200)',
    }
    price_to_color.update(special_color_map)

    seen_labels = []
    for label in price_order:
        if label not in seen_labels:
            seen_labels.append(label)

    legend_items = ''.join(
        f'<div class="li"><span class="dot" style="background:{price_to_color.get(label, "#aaa")}"></span>{label}</div>'
        for label in seen_labels
    )

    # Assemble HTML
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
  tip.style.display='block';
  posit(e);
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
