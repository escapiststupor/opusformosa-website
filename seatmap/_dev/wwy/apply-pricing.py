#!/usr/bin/env python3
"""
根據定價 CSV 更新 wwy.html（觀眾瀏覽版）
用法: python3 apply-pricing.py <csv檔案>
範例: python3 apply-pricing.py WWY定價-2026-04-03.csv

CSV 格式（由 editor-wwy.html 匯出）：
  section,row,seat,type,price
  1樓1號門,1,1,regular,2500
  2樓7號門輪椅席,B3,1,wheelchair,1200
  ...
"""

import re, csv, sys
from pathlib import Path

# ─── 特殊席顏色（與 editor 相同）────────────────────────────────────
TYPE_COLOR_HEX = {
    'staff':      '#c0392b',
    'console':    '#e67e22',
    'chorus':     '#546e7a',
    'reserved':   '#8e44ad',
    'wheelchair': '#0088cc',
    'companion':  '#66b3e0',
    'obstructed': '#b5895a',
}
TYPE_LABEL = {
    'staff':      '工作席（不販售）',
    'console':    '控台區',
    'chorus':     '合唱席（不販售）',
    'reserved':   '保留席（不販售）',
    'wheelchair': '輪椅席',
    'companion':  '輪椅陪同席',
    'obstructed': '視線不良席',
    'regular':    '一般席',
}
# 不販售席：固定顯示類型色，不接受票價
NON_SALE    = {'staff', 'chorus', 'reserved'}
# 固定色席：有票價也顯示類型色（不改為票價色）
FIXED_COLOR = {'staff', 'chorus', 'reserved', 'wheelchair', 'companion', 'console', 'obstructed'}

# 票價自動配色（照票價由高到低）
PRICE_PALETTE = [
    '#ff6b6b','#ffd43b','#4da6ff','#51cf66','#f783ac',
    '#ff922b','#74c0fc','#a9e34b','#cc5de8','#20c997',
]

def hex_to_rgb(h):
    h = h.lstrip('#')
    return f'rgb({int(h[0:2],16)}, {int(h[2:4],16)}, {int(h[4:6],16)})'


def main(csv_path):
    # ── 讀 CSV ────────────────────────────────────────────────────────
    pricing = {}   # (section, row, seat) → (type, price|None)
    prices  = set()
    with open(csv_path, encoding='utf-8-sig', newline='') as f:
        lines = (l for l in f if not l.lstrip('﻿').startswith('#'))
        for row in csv.DictReader(lines):
            key   = (row['section'], row['row'], row['seat'])
            price = int(row['price']) if row.get('price') else None
            pricing[key] = (row.get('type', 'regular'), price)
            if price:
                prices.add(price)

    # 按票價高→低分配顏色
    price_color_hex = {
        p: PRICE_PALETTE[i % len(PRICE_PALETTE)]
        for i, p in enumerate(sorted(prices, reverse=True))
    }

    # ── 讀 wwy.html（已含 data 屬性的 SVG）────────────────────────────
    out_path = Path('../../wwy/wwy.html')
    with open(out_path, encoding='utf-8') as f:
        content = f.read()

    # ── Enrich：按 CSV 覆寫 data-price 與顏色 ───────────────────────
    def recolor(m):
        tag = m.group(0)
        if 'class="seat"' not in tag:
            return tag
        id_m = re.search(r'[\s\n]id="([^"]+)"', tag)
        if not id_m:
            return tag
        parts = id_m.group(1).rsplit('-', 2)
        if len(parts) != 3:
            return tag
        section, row, seat = parts

        key = (section, row, seat)
        seat_type, price = pricing.get(key, ('regular', None))

        # 決定顏色
        if seat_type in FIXED_COLOR:
            color = hex_to_rgb(TYPE_COLOR_HEX[seat_type])
        elif price and price in price_color_hex:
            color = hex_to_rgb(price_color_hex[price])
        else:
            color = 'rgb(204, 204, 204)'  # 未定價灰

        # 票價標籤
        if seat_type in NON_SALE:
            label = TYPE_LABEL.get(seat_type, seat_type)
        elif seat_type in TYPE_LABEL and seat_type != 'regular':
            label = f'{TYPE_LABEL[seat_type]}　NT${price:,}' if price else TYPE_LABEL[seat_type]
        elif price:
            label = f'NT${price:,}'
        else:
            label = ''

        # 更新 data-price 與 fill
        tag = re.sub(r'\s+data-price="[^"]*"', '', tag)
        tag = tag.replace('class="seat"', f'class="seat" data-price="{label}"', 1)
        tag = re.sub(r'(style="[^"]*fill:\s*)rgb\([^)]+\)', rf'\1{color}', tag)
        return tag

    content = re.sub(r'<circle\b.*?</circle>', recolor, content, flags=re.DOTALL)

    # ── 計算票房 ────────────────────────────────────────────────────
    price_counts = {}
    for _, price in pricing.values():
        if price:
            price_counts[price] = price_counts.get(price, 0) + 1
    total_priced  = sum(price_counts.values())
    total_revenue = sum(p * c for p, c in price_counts.items())

    # ── 更新圖例（右側 legend）──────────────────────────────────────
    legend_prices = ''.join(
        f'<div class="li"><span class="dot" style="background:{price_color_hex[p]}"></span>'
        f'NT${p:,} 元 <span style="margin-left:auto;color:#aaa;font-size:10px">{price_counts.get(p,0)}席</span></div>'
        for p in sorted(prices, reverse=True)
    )
    legend_special = ''.join(
        f'<div class="li"><span class="dot" style="background:{c}"></span>{TYPE_LABEL.get(t,t)}</div>'
        for t, c in TYPE_COLOR_HEX.items()
        if any(v[0]==t for v in pricing.values())
    )
    legend_stats = (
        f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #f0f0f0">'
        f'<div class="li">已定價 {total_priced} 席</div>'
        f'<div class="li" style="font-weight:700;color:#e94560">票房上限 NT${total_revenue:,}</div>'
        f'</div>'
    )
    legend_html = f'<div id="side"><h2>票價圖例</h2>{legend_prices}{legend_special}{legend_stats}</div>'

    # 深度感知替換，正確處理巢狀 div
    start = content.find('<div id="side">')
    if start != -1:
        depth, i = 0, start
        while i < len(content):
            if content[i:i+4] == '<div':
                depth += 1
            elif content[i:i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    content = content[:start] + legend_html + content[i+6:]
                    break
            i += 1

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'Done. Updated {out_path}')
    print(f'  已定價：{total_priced} 席')
    print(f'  票房上限：NT${total_revenue:,}')
    print(f'  票價級距：{sorted(prices, reverse=True)}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python3 apply-pricing.py <csv檔案>')
        sys.exit(1)
    main(sys.argv[1])
