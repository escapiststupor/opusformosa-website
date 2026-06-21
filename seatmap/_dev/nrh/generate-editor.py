#!/usr/bin/env python3
"""
國家演奏廳 定價編輯器產生器
用法: python3 generate-editor.py
輸出: ../../nrh/editor-nrh.html

每次新音樂會，修改 CONCERT 即可；特殊席配置（SECTION_TYPES / SEAT_TYPES）
除非場館改建，否則不需要更動。
"""

import re
import json
import sys
import csv as _csv

# ─── 音樂會設定 ────────────────────────────────────────────────────────────────

CONCERT = {
    'name':  '2026 音樂會',
    'venue': '國家兩廳院演奏廳',
}

# ─── 特殊席配置（場館固定，通常不需修改）─────────────────────────────────────────

# 整個 section 都是同一種特殊類型
SECTION_TYPES = {
    '地下樓BF輪椅席': 'wheelchair',
    '地下樓BF輪陪席': 'companion',
    '地下樓BF友善席': 'accessible',
    '地下樓BF友陪席': 'accessible_companion',
}

# 個別座位的特殊類型（以 section + row + seat 識別）
SEAT_TYPES = [
    # ── 工作席（2席，不販售）────────────────────────────────────────
    {'section': '地下樓BF', 'row': '6',  'seat': 23, 'type': 'staff'},
    {'section': '地下樓BF', 'row': '15', 'seat': 25, 'type': 'staff'},
    # ── 攝影保留席（不販售）─────────────────────────────────────────
    {'section': '地下樓BF', 'row': '4',  'seat': 20, 'type': 'photography'},
    {'section': '地下樓BF', 'row': '8',  'seat': 23, 'type': 'photography'},
    {'section': '地下樓BF', 'row': '9',  'seat': 25, 'type': 'photography'},
    {'section': '地下樓BF', 'row': '10', 'seat': 20, 'type': 'photography'},
    *[{'section': '地下樓BF', 'row': '16', 'seat': s, 'type': 'photography'} for s in range(1, 5)],
    *[{'section': '地下樓BF', 'row': '17', 'seat': s, 'type': 'photography'} for s in range(1, 7)],
    # ── 視線不良席──────────────────────────────────────────────────
    # 第13排（5席）
    *[{'section': '地下樓BF', 'row': '13', 'seat': s, 'type': 'obstructed'} for s in [13, 15, 17, 19, 21]],
    # 第14排（6席）
    *[{'section': '地下樓BF', 'row': '14', 'seat': s, 'type': 'obstructed'} for s in [11, 13, 15, 17, 19, 21]],
]

# ─── 以下為產生邏輯（通常不需要修改）────────────────────────────────────────────

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","微軟正黑體",sans-serif}
#wrap{display:flex;flex-direction:column;height:100vh}
#hdr{background:#fff;border-bottom:3px solid #e94560;padding:10px 18px;flex-shrink:0;display:flex;align-items:center;gap:12px}
#hdr h1{font-size:15px;font-weight:700;color:#1a1a1a}
#save-ind{font-size:11px;color:#27ae60;margin-left:auto;opacity:0;transition:opacity .3s}
#save-ind.show{opacity:1}
#body{flex:1;display:flex;overflow:hidden}
#map-wrap{flex:1;overflow:auto;padding:16px;background:#fafafa;display:flex;align-items:flex-start;justify-content:center;position:relative;cursor:crosshair}
#map{width:100%;max-width:900px}
#map svg{display:block;width:100%;user-select:none}
#side{width:230px;background:#fff;border-left:1px solid #eee;overflow-y:auto;flex-shrink:0}
.panel{padding:12px 14px;border-bottom:1px solid #f0f0f0}
.pt{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
#sel-info{font-size:12px;color:#444;margin-bottom:8px;min-height:18px}
.row{display:flex;gap:6px;margin-bottom:6px}
#price-input{flex:1;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:13px}
#price-input:focus{outline:none;border-color:#4da6ff}
button{padding:7px 12px;border:none;border-radius:4px;font-size:12px;cursor:pointer;width:100%;margin-bottom:4px}
#apply-btn{background:#4da6ff;color:#fff;flex-shrink:0;width:auto;padding:7px 16px}
#apply-btn:hover{background:#3a94f5}
.btn-sec{background:#f0f0f0;color:#555}
.btn-sec:hover{background:#e0e0e0}
.btn-danger{background:#fff;color:#e74c3c;border:1px solid #e74c3c}
.btn-danger:hover{background:#ffeef0}
.btn-ok{background:#27ae60;color:#fff}
.btn-ok:hover{background:#219a52}
.li{display:flex;align-items:center;gap:7px;margin:4px 0;font-size:11px;color:#444;cursor:pointer;padding:2px 4px;border-radius:3px}
.li:hover{background:#f5f5f5}
.dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}
.li-cnt{margin-left:auto;color:#aaa;font-size:10px}
#stats{font-size:11px;color:#555;line-height:1.9}
#stats strong{color:#1a1a1a}
text.seat{pointer-events:none}
#drag-rect{position:fixed;border:2px solid #4da6ff;background:rgba(77,166,255,.12);display:none;pointer-events:none;z-index:100}
#tip{position:fixed;display:none;background:rgba(10,10,30,.93);color:#eee;border:1px solid #3a5a8f;border-radius:7px;padding:8px 12px;font-size:12px;line-height:1.7;pointer-events:none;z-index:9999;min-width:150px;box-shadow:0 4px 16px rgba(0,0,0,.4)}
.tl{color:#8ab;font-size:10px;text-transform:uppercase;letter-spacing:.4px}
.tv{color:#fff;font-weight:500}
.tp{margin-top:3px;padding-top:3px;border-top:1px solid rgba(255,255,255,.1);color:#ffd700;font-weight:600}
"""

JS = """
// ─── Type display ──────────────────────────────────────────────
const TYPE_COLOR = {
  regular:              '#cccccc',
  staff:                '#c0392b',
  photography:          '#607d8b',
  wheelchair:           '#0088cc',
  companion:            '#66b3e0',
  accessible:           '#44aa44',
  accessible_companion: '#88cc88',
  obstructed:           '#b5895a',
};
const TYPE_LABEL = {
  regular:              '一般席',
  staff:                '工作席（不販售）',
  photography:          '攝影保留席（不販售）',
  wheelchair:           '輪椅席',
  companion:            '輪椅陪同席',
  accessible:           '多元友善席',
  accessible_companion: '多元友善陪同席',
  obstructed:           '視線不良席',
};

// ─── Non-saleable types ────────────────────────────────────────
const NON_SALE = new Set(['staff', 'photography']);

// ─── Price palette ─────────────────────────────────────────────
const PALETTE = ['#ff6b6b','#ffd43b','#4da6ff','#51cf66','#f783ac',
                 '#ff922b','#74c0fc','#a9e34b','#cc5de8','#20c997'];
let palIdx = 0;
const priceColors = {};
function getPriceColor(p) {
  if (!priceColors[p]) { priceColors[p] = PALETTE[palIdx++ % PALETTE.length]; }
  return priceColors[p];
}

// ─── State ─────────────────────────────────────────────────────
const seatEl    = {};   // id → <circle>
const seatType  = {};   // id → type string
const seatPrice = {};   // id → price (number)
const selected  = new Set();
const LS_KEY    = 'nrh_pricing_v1';
const SEED      = {};

// ─── Init ──────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  // Build special-seat lookup
  const specials = {};
  CONFIG.seatTypes.forEach(s => {
    specials[s.section + '-' + s.row + '-' + s.seat] = s.type;
  });

  document.querySelectorAll('circle.seat').forEach(el => {
    const sec = el.dataset.section, row = el.dataset.row, seat = el.dataset.seatNum;
    const id  = sec + '-' + row + '-' + seat;
    seatEl[id]   = el;
    seatType[id] = CONFIG.sectionTypes[sec] || specials[id] || 'regular';

    el.style.fill        = TYPE_COLOR[seatType[id]];
    el.style.stroke      = '';
    el.style.strokeWidth = '';

    if (NON_SALE.has(seatType[id])) {
      el.style.cursor  = 'not-allowed';
      el.style.opacity = '0.45';
      el.addEventListener('mouseover', e => {
        const t = seatType[id];
        tipEl.innerHTML = `<div class="tl">區域</div><div class="tv">${sec}</div>
          <div class="tl">排 / 座位</div><div class="tv">${row}排 · 第${seat}號</div>
          <div class="tp" style="color:#ff9999">${TYPE_LABEL[t]}（不販售）</div>`;
        tipEl.style.display = 'block'; posit(e);
      });
      el.addEventListener('mouseout', () => tipEl.style.display = 'none');
    } else {
      el.style.cursor = 'pointer';
      el.addEventListener('click',     onSeatClick);
      el.addEventListener('mouseover', onHover);
      el.addEventListener('mouseout',  () => tipEl.style.display = 'none');
    }
  });

  loadState();
  setupDrag();
  renderSpecialLegend();
  renderPriceLegend();
  renderStats();

  document.getElementById('price-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') applyPrice();
  });
});

// ─── Color helpers ─────────────────────────────────────────────
function displayColor(id) {
  const t = seatType[id];
  // Non-saleable and specialty seats always show their category color
  if (NON_SALE.has(t) || t === 'wheelchair' || t === 'companion' ||
      t === 'accessible' || t === 'accessible_companion') return TYPE_COLOR[t];
  // Regular and obstructed: show price color if priced
  return seatPrice[id] ? getPriceColor(seatPrice[id]) : TYPE_COLOR[t];
}

function paintSeat(id) {
  const el = seatEl[id]; if (!el) return;
  el.style.fill = displayColor(id);
  if (selected.has(id)) { el.style.stroke = '#ffd700'; el.style.strokeWidth = '3'; }
  else                   { el.style.stroke = '';        el.style.strokeWidth = ''; }
}

function paintAll() { Object.keys(seatEl).forEach(paintSeat); }

// ─── Selection ─────────────────────────────────────────────────
function seatId(el) { return el.dataset.section + '-' + el.dataset.row + '-' + el.dataset.seatNum; }

function onSeatClick(e) {
  e.stopPropagation();
  const id = seatId(e.target);
  if (e.shiftKey || e.metaKey || e.ctrlKey) {
    selected.has(id) ? selected.delete(id) : selected.add(id);
  } else {
    const sole = selected.size === 1 && selected.has(id);
    selected.clear();
    if (!sole) selected.add(id);
  }
  paintSeat(id);
  updateSelInfo();
}

function clearSelection() {
  const ids = [...selected]; selected.clear();
  ids.forEach(paintSeat); updateSelInfo();
}

// ─── Pricing ───────────────────────────────────────────────────
function applyPrice() {
  const price = parseInt(document.getElementById('price-input').value);
  if (!price || price <= 0) { alert('請輸入有效票價'); return; }
  if (!selected.size)       { alert('請先選取座位');   return; }
  selected.forEach(id => { if (!NON_SALE.has(seatType[id])) seatPrice[id] = price; });
  selected.forEach(paintSeat);
  renderPriceLegend(); renderStats(); saveState(); flashSaved();
}

function selectByPrice(price) {
  clearSelection();
  Object.entries(seatPrice).forEach(([id, p]) => { if (p === price) selected.add(id); });
  paintAll(); updateSelInfo();
}

function resetAll() {
  Object.keys(seatPrice).forEach(k => delete seatPrice[k]);
  Object.keys(priceColors).forEach(k => delete priceColors[k]);
  palIdx = 0; selected.clear();
  paintAll(); renderPriceLegend(); renderStats(); saveState();
}

// ─── Tooltip ───────────────────────────────────────────────────
const tipEl = document.getElementById('tip');

function onHover(e) {
  const id  = seatId(e.target);
  const sec = e.target.dataset.section, row = e.target.dataset.row, seat = e.target.dataset.seatNum;
  const t   = seatType[id], p = seatPrice[id];
  const pStr = p ? 'NT$' + p.toLocaleString() : (NON_SALE.has(t) ? '不販售' : '未定價');
  tipEl.innerHTML = `<div class="tl">區域</div><div class="tv">${sec}</div>
    <div class="tl">排 / 座位</div><div class="tv">第${row}排 · 第${seat}號</div>
    <div class="tl">類型</div><div class="tv">${TYPE_LABEL[t] || t}</div>
    <div class="tp">${pStr}</div>`;
  tipEl.style.display = 'block'; posit(e);
}
document.addEventListener('mousemove', e => { if (tipEl.style.display !== 'none') posit(e); });
function posit(e) {
  let x = e.clientX+14, y = e.clientY+14;
  const w = tipEl.offsetWidth||160, h = tipEl.offsetHeight||100;
  if (x+w > window.innerWidth-8)  x = e.clientX-w-14;
  if (y+h > window.innerHeight-8) y = e.clientY-h-14;
  tipEl.style.left = x+'px'; tipEl.style.top = y+'px';
}

// ─── Drag selection ────────────────────────────────────────────
function setupDrag() {
  const wrap = document.getElementById('map-wrap');
  const rect = document.getElementById('drag-rect');
  let drag = false, sx = 0, sy = 0;

  wrap.addEventListener('mousedown', e => {
    if (e.target.classList.contains('seat') || e.button !== 0) return;
    drag = true; sx = e.clientX; sy = e.clientY;
    rect.style.cssText = `left:${sx}px;top:${sy}px;width:0;height:0;display:block`;
  });
  document.addEventListener('mousemove', e => {
    if (!drag) return;
    const x = Math.min(e.clientX, sx), y = Math.min(e.clientY, sy);
    rect.style.left = x+'px'; rect.style.top = y+'px';
    rect.style.width = Math.abs(e.clientX-sx)+'px';
    rect.style.height = Math.abs(e.clientY-sy)+'px';
  });
  document.addEventListener('mouseup', e => {
    if (!drag) return; drag = false; rect.style.display = 'none';
    const x1 = Math.min(e.clientX,sx), y1 = Math.min(e.clientY,sy);
    const x2 = Math.max(e.clientX,sx), y2 = Math.max(e.clientY,sy);
    if (x2-x1 < 5 && y2-y1 < 5) return;
    if (!e.shiftKey && !e.metaKey && !e.ctrlKey) selected.clear();
    Object.entries(seatEl).forEach(([id, el]) => {
      if (NON_SALE.has(seatType[id])) return;
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width/2, cy = r.top + r.height/2;
      if (cx >= x1 && cx <= x2 && cy >= y1 && cy <= y2) selected.add(id);
    });
    paintAll(); updateSelInfo();
  });
}

// ─── Sidebar ───────────────────────────────────────────────────
function renderSpecialLegend() {
  const types = ['wheelchair','companion','accessible','accessible_companion',
                 'obstructed','staff','photography'];
  document.getElementById('legend-special').innerHTML = types.map(t =>
    `<div class="li" style="cursor:default"><span class="dot" style="background:${TYPE_COLOR[t]}"></span>${TYPE_LABEL[t]}</div>`
  ).join('');
}

function renderPriceLegend() {
  const el = document.getElementById('legend-prices');
  const prices = [...new Set(Object.values(seatPrice))].sort((a,b) => b-a);
  if (!prices.length) {
    el.innerHTML = '<div class="li" style="cursor:default;color:#bbb">（尚未設定票價）</div>'; return;
  }
  el.innerHTML = prices.map(p => {
    const cnt = Object.values(seatPrice).filter(v => v === p).length;
    return `<div class="li" onclick="selectByPrice(${p})" title="點擊選取此票價所有座位">
      <span class="dot" style="background:${getPriceColor(p)}"></span>
      NT$${p.toLocaleString()} <span class="li-cnt">${cnt}席</span></div>`;
  }).join('');
}

function updateSelInfo() {
  const el = document.getElementById('sel-info');
  if (!selected.size) { el.textContent = '尚未選取座位'; return; }
  const prices = new Set([...selected].map(id => seatPrice[id]).filter(Boolean));
  let s = `已選 ${selected.size} 席`;
  if (prices.size === 1) s += `・目前 NT$${[...prices][0].toLocaleString()}`;
  else if (prices.size > 1) s += `・混合票價`;
  el.textContent = s;
}

function renderStats() {
  const total    = Object.keys(seatEl).length;
  const nonSale  = Object.values(seatType).filter(t => NON_SALE.has(t)).length;
  const priced   = Object.keys(seatPrice).length;
  const revenue  = Object.values(seatPrice).reduce((s,p) => s+p, 0);
  let html = `總席數：${total}<br>不販售席：${nonSale}<br>已定價：${priced}<br>未定價：${total-nonSale-priced}`;
  if (revenue > 0) html += `<br><strong>票房上限：NT$${revenue.toLocaleString()}</strong>`;
  document.getElementById('stats').innerHTML = html;
}

// ─── Persistence ───────────────────────────────────────────────
function saveState() {
  try { localStorage.setItem(LS_KEY, JSON.stringify(seatPrice)); } catch(e) {}
}
function loadState() {
  try {
    const d = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
    Object.entries(d).forEach(([id, p]) => { if (seatEl[id]) seatPrice[id] = p; });
    paintAll(); renderPriceLegend(); renderStats();
  } catch(e) {}
}
function flashSaved() {
  const el = document.getElementById('save-ind');
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 1800);
}

// ─── Export ────────────────────────────────────────────────────
function exportCSV() {
  const lines = [
    '# venue=' + CONFIG.venue,
    'section,row,seat,type,price',
  ];
  Object.entries(seatEl).forEach(([id, el]) => {
    const sec = el.dataset.section, row = el.dataset.row, seat = el.dataset.seatNum;
    const type = seatType[id], price = seatPrice[id] || '';
    lines.push(`"${sec}","${row}","${seat}","${type}","${price}"`);
  });
  const blob = new Blob(['\\uFEFF' + lines.join('\\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'NRH定價-' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}

// ─── Import ────────────────────────────────────────────────────
function importCSV() {
  const input = document.createElement('input');
  input.type = 'file'; input.accept = '.csv,text/csv';
  input.onchange = e => {
    const file = e.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try { parseAndLoadCSV(ev.target.result); }
      catch(err) { alert('匯入失敗：' + err.message); }
    };
    reader.readAsText(file, 'utf-8');
  };
  input.click();
}

function parseAndLoadCSV(text) {
  // Strip BOM
  text = text.replace(/^\\uFEFF/, '');
  const lines = text.split(/\\r?\\n/).filter(l => l.trim());

  // First line: venue check
  const venueLine = lines[0];
  if (!venueLine.startsWith('# venue=')) {
    throw new Error('找不到場地標記（第一行應為 # venue=...）\\n這個檔案可能不是由本工具匯出的。');
  }
  const csvVenue = venueLine.slice('# venue='.length).trim();
  if (csvVenue !== CONFIG.venue) {
    throw new Error(
      `場地不符\\nCSV：${csvVenue}\\n本工具：${CONFIG.venue}\\n請確認匯入的是正確場地的定價檔案。`
    );
  }

  // Second line: header
  const headerLine = lines[1];
  if (!headerLine || !headerLine.includes('section')) {
    throw new Error('找不到 CSV 標題列（section,row,seat,type,price）');
  }
  const headers = headerLine.split(',').map(h => h.replace(/"/g,'').trim());
  const idx = { section: headers.indexOf('section'), row: headers.indexOf('row'),
                seat: headers.indexOf('seat'), price: headers.indexOf('price') };
  if (idx.section<0 || idx.row<0 || idx.seat<0 || idx.price<0) {
    throw new Error('CSV 格式錯誤：缺少必要欄位（section / row / seat / price）');
  }

  // Parse data rows
  let loaded = 0, skipped = 0;
  const newPrices = {};
  for (let i = 2; i < lines.length; i++) {
    const cols = lines[i].match(/("([^"]*)")|([^,]+)|(?<=,)(?=,)|(?<=,)$/g) || [];
    const get = j => (cols[j] || '').replace(/^"|"$/g,'').trim();
    const sec = get(idx.section), row = get(idx.row),
          seat = get(idx.seat),   priceStr = get(idx.price);
    const id = sec + '-' + row + '-' + seat;
    if (!seatEl[id]) { skipped++; continue; }
    const price = parseInt(priceStr);
    if (price > 0) { newPrices[id] = price; loaded++; }
  }

  if (loaded === 0) {
    throw new Error('CSV 中沒有找到任何有效的定價資料。');
  }

  // Apply — reset then load
  Object.keys(seatPrice).forEach(k => delete seatPrice[k]);
  Object.keys(priceColors).forEach(k => delete priceColors[k]);
  palIdx = 0;
  Object.assign(seatPrice, newPrices);
  selected.clear();
  paintAll(); renderPriceLegend(); renderStats(); saveState(); flashSaved();

  alert(`匯入成功\\n已載入 ${loaded} 個定價${skipped ? `\\n（${skipped} 筆座位 ID 不在本場地，已略過）` : ''}`);
}
"""


def main():
    src_path = '../../nrh/nrh.html'
    out_path = '../../nrh/editor-nrh.html'

    with open(src_path, encoding='utf-8') as f:
        content = f.read()

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
    canvas_svg = re.sub(r'\s+data-price="[^"]*"', '', canvas_svg)

    # Seed pricing from CSV if provided
    seed_data = {}
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding='utf-8-sig', newline='') as f:
            for row in _csv.DictReader(l for l in f if not l.lstrip('﻿').startswith('#')):
                price = row.get('price', '').strip()
                if price:
                    seed_data[f"{row['section']}-{row['row']}-{row['seat']}"] = int(price)

    # Config JS (embedded directly)
    config_js = f"""const CONFIG = {{
  venue: {json.dumps(CONCERT['venue'], ensure_ascii=False)},
  sectionTypes: {json.dumps(SECTION_TYPES, ensure_ascii=False, indent=2)},
  seatTypes: {json.dumps(SEAT_TYPES, ensure_ascii=False)},
}};"""

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>定價工具 — {CONCERT['venue']}</title>
<style>
{CSS}
</style>
</head>
<body>
<div id="wrap">
<div id="hdr">
  <h1>{CONCERT['venue']} · 定價工具</h1>
  <span id="save-ind">已儲存</span>
</div>
<div id="body">
<div id="map-wrap"><div id="map">{canvas_svg}</div></div>
<div id="side">
  <div class="panel">
    <div class="pt">定價</div>
    <div id="sel-info">尚未選取座位</div>
    <div class="row">
      <input type="number" id="price-input" placeholder="票價（元）" min="0" step="100">
      <button id="apply-btn" onclick="applyPrice()">套用</button>
    </div>
    <button class="btn-sec" onclick="clearSelection()">清除選取</button>
  </div>
  <div class="panel">
    <div class="pt">票價圖例 <span style="font-weight:400;color:#aaa">（點擊選取）</span></div>
    <div id="legend-prices"></div>
  </div>
  <div class="panel">
    <div class="pt">特殊席圖例</div>
    <div id="legend-special"></div>
  </div>
  <div class="panel">
    <div class="pt">統計</div>
    <div id="stats"></div>
  </div>
  <div class="panel">
    <button class="btn-sec" onclick="importCSV()">⬆ 匯入 CSV</button>
    <button class="btn-danger" onclick="if(confirm('確定要重設所有定價？'))resetAll()">重設全部定價</button>
    <button class="btn-ok" onclick="exportCSV()">⬇ 下載 CSV</button>
  </div>
</div>
</div>
</div>
<div id="drag-rect"></div>
<div id="tip"></div>
<script>
{config_js}
{JS}
</script>
</body></html>"""

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Done. Wrote {out_path}')


if __name__ == '__main__':
    main()
