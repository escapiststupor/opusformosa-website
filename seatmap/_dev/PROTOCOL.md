# Seat-Map Protocol

This document describes the canonical bridge between three representations of venue seating:

1. **SVG seatmap** — the interactive viewer shown to the public (`seatmap/{venue}/{venue}.html`)
2. **Pricing CSV** — the source of truth for seat types and prices, edited in the browser editor
3. **Excel seating chart** — the physical seat chart handed to venue staff

The protocol ensures all three stay in sync without manual re-mapping every time prices change.

---

## Core Idea

Each seat has a stable identity: `{section}-{row}-{seat}` (e.g., `演奏廳-10-14`). This ID appears in:
- the SVG element's `id` attribute
- the pricing CSV's `section`, `row`, `seat` columns
- the seat-map CSV that maps Excel cell coordinates to the same identity

The seat-map CSV is the **durable bridge** between Excel and CSV. Once generated, it never needs to change unless the Excel layout itself changes.

---

## File Roles

| File | Role | Changes when |
|------|------|--------------|
| `{venue}-seat-map.csv` | Maps Excel row/col → seat ID | Excel layout changes (rare) |
| `{VENUE}定價-{date}.csv` | Seat types and prices | Prices change |
| `apply-excel.py` | Colors Excel from the two CSVs above | Bug fixes / new price tiers |
| `generate-seat-map.py` | Generates seat-map CSV from blank Excel | One-time setup per venue |

---

## Seat-Map CSV Format

```
excel_row,col,section,row,seat
5,3,演奏廳,1,1
5,5,演奏廳,1,2
...
```

- `excel_row` / `col` — 1-indexed Excel cell coordinates (matching openpyxl convention)
- `section`, `row`, `seat` — the seat's canonical identity (must match the pricing CSV exactly)

Generated once per venue by `generate-seat-map.py`. Stored at:
- `nrh/nrh-seat-map.csv` (354 rows)
- `nch/nch-seat-map.csv` (2022 rows)

---

## Pricing CSV Format

```
# venue=國家兩廳院演奏廳
section,row,seat,type,price
演奏廳,1,1,regular,2800
演奏廳,10,14,regular,1800
地下樓BF,15,25,staff,
...
```

- UTF-8 with BOM (`utf-8-sig`)
- Lines starting with `#` are metadata (venue name)
- `price` is blank for non-sellable seats (staff, chorus, reserved, etc.)
- Exported/imported by the browser editor at `seatmap/editor-{venue}.html`

---

## apply-excel.py — Generic Coloring Engine

```
python3 apply-excel.py <seat-map.csv> <pricing.csv> <blank.xlsx> <output.xlsx>
```

**What it does:**
1. Reads the seat-map CSV to know which Excel cell = which seat
2. Reads the pricing CSV to know each seat's type and price
3. Colors each cell:
   - If the type has a fixed color (staff, wheelchair, obstructed, etc.) → use type color
   - Else if the price has a known color → use price color
   - Else → light gray `FFCCCCCC`
4. Writes output xlsx (never modifies the blank source)

**Does not** write legend cells — that is left to the venue-specific wrapper script.

### Price color palette (apply-excel.py)

| Price | Color | ARGB |
|-------|-------|------|
| 5000 | red | FFFF6B6B |
| 3600 | yellow | FFFFD43B |
| 3300 | red | FFFF6B6B |
| 2800 | blue | FF4DA6FF |
| 2500 | green | FF51CF66 |
| 2200 | yellow | FFFFD43B |
| 2100 | pink | FFF783AC |
| 1800 | orange | FFFF922B |
| 1500 | light blue | FF74C0FC |
| 1200 | lime | FFA9E34B |
| 1000 | pink | FFF783AC |
| 790 | purple | FFCC5DE8 |
| 640 | teal | FF20C997 |
| 300 | gray | FFADB5BD |

### Type color palette (apply-excel.py)

| Type | Color | ARGB |
|------|-------|------|
| staff | gold | FFFFC000 |
| wheelchair | sky blue | FF00B0F0 |
| companion | dark blue | FF0070C0 |
| accessible | dark green | FF76923C |
| accessible_companion | light green | FFC2D69B |
| obstructed | gray | FF7F7F7F |
| organ_obstructed | peach | FFFBD4B4 |
| uncomfortable_obstructed | dark red | FF953734 |
| vip_box | pink | FFFF99CC |
| chorus | charcoal | FF595959 |
| reserved | purple | FF8E44AD |
| console | burnt orange | FFE67E22 |
| photography | gold | FFFFC000 |

---

## Venue-Specific Wrapper Scripts

Each venue has a wrapper script that:
1. Calls `apply-excel.py` for seat coloring
2. Adds venue-specific legend cells on top of the colored output
3. Copies the result to other date folders if needed

### NRH — `ticketing/2026/0910NRH/color-seating-chart.py`

- Sheet: `空白座位圖`
- Legend columns: AD (col 30) for color swatch, AE (col 31) for text
- Type legend: rows 7–12
- Price legend: rows 14+
- NRH price colors (override for legend display):
  - 2800 → FFFF6B6B, 2200 → FFFFD43B, 1800 → FF4DA6FF, 1500 → FF51CF66, 1000 → FFF783AC
- Copies output to `0912NRH/` with the same filename

### NCH — `ticketing/2026/0904NCH/color_nch.py`

- Multi-floor layout: 2樓 (main floor), 3樓 galleries, 4樓 upper, VA/VB boxes
- 2樓: uses column Q (col 17) for row numbers
- 3樓: fixed column pairs (left 10/12/14, right 65/67/69)
- 4樓: fixed column pairs (left 5/7, right 73/75)
- VA/VB: Excel rows 64–65
- Sheet: `空白座位圖`
- 2022 seats total

---

## How to Generate a Seat-Map CSV (one-time setup)

Each venue needs a `generate-seat-map.py` that reads the blank Excel and outputs the seat-map CSV. The script must:

1. Open the blank Excel and identify the correct sheet
2. Determine which column holds row numbers (often column Q = col 17)
3. For each seat cell, determine `section`, `row`, `seat` from context (nearby labels, column offsets, etc.)
4. Output rows: `excel_row,col,section,row,seat`

See `nrh/generate-seat-map.py` and `nch/generate-seat-map.py` as references.

**Key challenge per venue:**
- NRH: straightforward single-floor layout; col Q = row number
- NCH: multi-floor with non-numeric row labels (1E, 1D, 1C...); galleries use fixed column pairs
- WWY: complex multi-section layout with ~290 rows × 120 cols; seat-map not yet generated (manual coloring may be faster)

---

## Workflow for Updating Prices

When a new pricing CSV arrives:

```bash
# 1. Deploy updated pricing to seatmap viewer
cd seatmap/_dev/{venue}
python3 apply-pricing.py {VENUE}定價-{date}.csv
# (for NRH/NCH, apply-pricing.py reads the CSV and updates the .html file)

# 2. Re-color the Excel seating chart
cd ticketing/2026/{date}{VENUE}
python3 color-seating-chart.py     # NRH
# or
python3 color_nch.py               # NCH
```

The seat-map CSV does not need to change — only the pricing CSV changes.

---

## File Locations Quick Reference

```
website/
  seatmap/
    _dev/
      apply-excel.py              ← generic coloring engine
      nrh/
        generate-seat-map.py      ← generates nrh-seat-map.csv
        nrh-seat-map.csv          ← Excel cell → seat ID (354 rows)
        NRH定價-{date}.csv        ← current pricing
        apply-pricing.py          ← updates nrh.html
      nch/
        generate-seat-map.py      ← generates nch-seat-map.csv
        nch-seat-map.csv          ← Excel cell → seat ID (2022 rows)
        NCH定價-{date}.csv        ← current pricing
        apply-pricing.py          ← updates nch.html
      wwy/
        WWY定價-{date}.csv        ← current pricing
        apply-pricing.py          ← updates wwy.html
        (no seat-map yet)
    nrh/nrh.html                  ← deployed viewer
    nch/nch.html                  ← deployed viewer
    wwy/wwy.html                  ← deployed viewer

ticketing/2026/
  0910NRH/
    color-seating-chart.py        ← NRH wrapper (also writes 0912NRH)
    國家兩廳院演奏廳座位圖...xlsx       ← blank source
    國家兩廳院演奏廳座位圖...-已填寫.xlsx ← colored output
  0912NRH/
    國家兩廳院演奏廳座位圖...-已填寫.xlsx ← copy from 0910NRH
  0904NCH/
    color_nch.py                  ← NCH wrapper
    國家音樂廳座位圖...-已填寫.xlsx      ← colored output
```
