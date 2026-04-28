#!/usr/bin/env python3
"""
國家演奏廳 座位圖產生器
用法: python3 generate-nrh.py
輸出: ../nrh/index.html

每次新音樂會，只需要修改下方的 CONCERT 和 PRICING 兩個區塊。
"""

import re

# ─── 場地資料（固定，不需修改）─────────────────────────────────────────────────
# 資料來源：國家兩廳院演奏廳座位圖1150303(多元友善席專用).xlsx
# 總座位 354 席 | 17 排 | 舞台在前（第 1 排最近舞台）
# 座位編號：奇數 = 左側、偶數 = 右側、號碼越小越靠中間
# SVG section: 地下樓BF | id 格式: 地下樓BF-{排}-{號}

NRH_LAYOUT = {
    'rows': {
        1:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21,23],
        2:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23],
        3:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21,23],
        4:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
        5:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23],
        6:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23],
        7:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21,23],
        8:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23],
        9:  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,25],
        # 第 10 排：11,13,15,17 號 = 輪椅席（獨立 section：地下樓BF輪椅席）
        10: [1,2,3,4,5,6,7,8,9,10,12,14,16,18,20],
        # 第 11 排：7 號 = 多元友善陪同席、9 號 = 多元友善席（獨立 section）
        11: [1,2,3,4,5,6,8,10,12,14,16,18],
        # 第 12 排：13,15,17,19 號 = 輪椅陪同席（獨立 section：地下樓BF輪陪席）
        12: [1,2,3,4,5,6,7,8,9,10,11,12,14,16,18,20],
        13: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21],
        14: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
        15: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,19,21,23,25],
        16: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21,23],
        17: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21,23,25,27],
    },
    'special': {
        # 輪椅席 (section: 地下樓BF輪椅席)
        'wheelchair':          {'section': '地下樓BF輪椅席', 'row': 10, 'seats': [11,13,15,17]},
        # 輪椅陪同席 (section: 地下樓BF輪陪席)
        'wheelchairCompanion': {'section': '地下樓BF輪陪席', 'row': 12, 'seats': [13,15,17,19]},
        # 多元友善席 (section: 地下樓BF友善席)
        'accessible':          {'section': '地下樓BF友善席', 'row': 11, 'seats': [9]},
        # 多元友善陪同席 (section: 地下樓BF友陪席)
        'accessibleCompanion': {'section': '地下樓BF友陪席', 'row': 11, 'seats': [7]},
        # 視線不良席（在主 section 地下樓BF 內，以 id 識別）
        'limitedView': [
            {'row': 13, 'seats': [13,15,17,19,21]},
            {'row': 14, 'seats': [11,13,15,17,19,21]},
        ],
    },
}

# ─── 音樂會設定（每次新音樂會修改這裡）──────────────────────────────────────────

CONCERT = {
    'name':  'Opus Formosa',
    'venue': '國家兩廳院演奏廳',
    # 'date': '2026-??-??',  # 選填，會顯示在頁面
}

# 票價區間（由上到下依序判斷，第一個符合的規則勝出）
# rows: [from, to]        排數範圍（包含兩端）
# seats: [from, to]       座位號碼範圍（選填；省略則套用整排）
# seats_set: [...]        精確座位號碼列表（選填；可與 seats 擇一使用）
PRICING = {
    'zones': [
        # 前6排中央區：1–12號 和 13、15號 → $2,300
        {'rows': [1,  6],  'seats':     [1, 12], 'color': 'rgb(248, 4, 0)',    'label': '$2,300 元'},
        {'rows': [1,  6],  'seats_set': [13, 15],'color': 'rgb(248, 4, 0)',    'label': '$2,300 元'},
        {'rows': [1,  10],                        'color': 'rgb(252, 110, 40)', 'label': '$2,000 元'},
        {'rows': [11, 13],                        'color': 'rgb(255, 190, 0)',  'label': '$1,500 元'},
        {'rows': [14, 17],                        'color': 'rgb(27, 129, 62)',  'label': '$1,000 元'},
    ],
    'special': {
        'limitedView':         {'color': 'rgb(180, 170, 0)',  'label': '視線不良席 $1,000 元'},
        'accessible':          {'color': 'rgb(150, 160, 0)',  'label': '多元友善席 $1,000 元'},
        'accessibleCompanion': {'color': 'rgb(230, 160, 80)', 'label': '多元友善陪同席 $1,000 元'},
        'wheelchair':          {'color': 'rgb(0, 100, 220)',  'label': '輪椅席 $1,000 元'},
        'wheelchairCompanion': {'color': 'rgb(0, 50, 165)',   'label': '輪椅陪同席 $1,000 元'},
    },
}

# ─── 以下為產生邏輯（通常不需要修改）────────────────────────────────────────────

def build_seat_color_map():
    """根據 PRICING 建立 seat_id -> (color, label) 的對照表"""
    color_map = {}

    layout = NRH_LAYOUT
    special = layout['special']

    # 視線不良席
    lv_cfg = PRICING['special']['limitedView']
    lv_ids = set()
    for entry in special['limitedView']:
        for s in entry['seats']:
            lv_ids.add(f"地下樓BF-{entry['row']}-{s}")

    # 特殊 section 座位
    for key in ('wheelchair', 'wheelchairCompanion', 'accessible', 'accessibleCompanion'):
        info = special[key]
        cfg = PRICING['special'][key]
        for s in info['seats']:
            sid = f"{info['section']}-{info['row']}-{s}"
            color_map[sid] = (cfg['color'], cfg['label'])

    # 主 section 座位（含視線不良席）
    for row, seats in layout['rows'].items():
        for seat in seats:
            sid = f'地下樓BF-{row}-{seat}'
            if sid in lv_ids:
                color_map[sid] = (lv_cfg['color'], lv_cfg['label'])
                continue
            for zone in PRICING['zones']:
                r1, r2 = zone['rows']
                if r1 <= row <= r2:
                    if 'seats' in zone:
                        s1, s2 = zone['seats']
                        if not (s1 <= seat <= s2):
                            continue
                    if 'seats_set' in zone:
                        if seat not in zone['seats_set']:
                            continue
                    color_map[sid] = (zone['color'], zone['label'])
                    break

    return color_map


def assign_price(section, row, seat):
    """回傳 (color, label)，對應到當前 PRICING 設定"""
    layout = NRH_LAYOUT
    special = layout['special']

    # 特殊 section
    for key in ('wheelchair', 'wheelchairCompanion', 'accessible', 'accessibleCompanion'):
        info = special[key]
        if section == info['section']:
            cfg = PRICING['special'][key]
            return cfg['color'], cfg['label']

    # 視線不良席（在主 section 內）
    lv_cfg = PRICING['special']['limitedView']
    for entry in special['limitedView']:
        if row == entry['row'] and seat in entry['seats']:
            return lv_cfg['color'], lv_cfg['label']

    # 主區票價區間
    for zone in PRICING['zones']:
        r1, r2 = zone['rows']
        if r1 <= row <= r2:
            if 'seats' in zone:
                s1, s2 = zone['seats']
                if not (s1 <= seat <= s2):
                    continue
            if 'seats_set' in zone:
                if seat not in zone['seats_set']:
                    continue
            return zone['color'], zone['label']

    return 'rgb(200, 200, 200)', ''


def enrich_circle(m):
    tag = m.group(0)
    if 'class="seat"' not in tag:
        return tag
    # Parse seat identity from id attribute (whitespace prefix avoids matching data-id)
    id_m = re.search(r'[\s\n]id="([^"]+)"', tag)
    if not id_m:
        return tag
    seat_id = id_m.group(1)
    parts = seat_id.rsplit('-', 2)
    if len(parts) != 3:
        return tag
    section, row, seat = parts[0], int(parts[1]), int(parts[2])

    color, label = assign_price(section, row, seat)
    attrs = (f' data-section="{section}" data-row="{row}"'
             f' data-seat-num="{seat}" data-price="{label}"')
    # Insert data-* after class="seat"
    tag = re.sub(r'\s+data-(?:section|row|seat-num|price)="[^"]*"', '', tag)
    tag = tag.replace('class="seat"', f'class="seat"{attrs}', 1)
    # Update fill color in style attribute
    tag = re.sub(r'(style="[^"]*fill:\s*)rgb\([^)]+\)', rf'\1{color}', tag)
    return tag


def main():
    src_path = 'source.html'
    out_path = '../../nrh/nrh.html'

    print(f'Reading {src_path}...')
    with open(src_path, encoding='utf-8') as f:
        content = f.read()

    # ── Extract canvas SVG ──
    canvas_start = content.rfind('<svg', 0, content.find('id="canvas"'))
    pos, depth, svg_end = canvas_start, 0, -1
    for m in re.finditer(r'<svg[\s>]|</svg>', content[canvas_start:]):
        depth += 1 if m.group(0).startswith('<svg') else -1
        if depth == 0:
            svg_end = canvas_start + m.end()
            break
    canvas_svg = content[canvas_start:svg_end]

    # ── Make responsive ──
    canvas_svg = re.sub(r'(<svg\b[^>]*id="canvas"[^>]*)width="[^"]*"',  r'\1width="100%"',  canvas_svg, count=1)
    canvas_svg = re.sub(r'(<svg\b[^>]*id="canvas"[^>]*)height="[^"]*"', r'\1height="auto"', canvas_svg, count=1)

    # ── Enrich seat circles ──
    canvas_svg = re.sub(r'<circle\b.*?</circle>', enrich_circle, canvas_svg, flags=re.DOTALL)

    # ── Collect unique price tiers for legend ──
    seen = {}
    for zone in PRICING['zones']:
        k = zone['color']
        if k not in seen:
            seen[k] = zone['label']
    for key in ('limitedView', 'accessible', 'accessibleCompanion', 'wheelchair', 'wheelchairCompanion'):
        cfg = PRICING['special'][key]
        k = cfg['color']
        if k not in seen:
            seen[k] = cfg['label']
    legend_items = ''.join(
        f'<div class="li"><span class="dot" style="background:{color}"></span>{label}</div>'
        for color, label in seen.items()
    )

    # ── Assemble HTML ──
    title_text = CONCERT['venue']
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
#map svg{{display:block;width:100%;max-width:700px}}
#side{{width:190px;background:#fff;border-left:1px solid #eee;padding:14px;overflow-y:auto;flex-shrink:0}}
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
<div id="hdr"><h1>{title_text}</h1></div>
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

    # Count enriched seats
    n = len(re.findall(r'data-price=', html))
    print(f'Done. Wrote {out_path} ({n} seats enriched)')


if __name__ == '__main__':
    main()
