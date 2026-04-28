# 座位圖工具使用說明

本文件說明如何使用座位圖定價工具，以及每次新音樂會的操作步驟。

---

## 工具網址

### 定價工具（助理操作）

| 場館 | 網址 |
|------|------|
| 國家兩廳院音樂廳 | `https://opusformosa.org/seatmap/nch/editor-nch.html` |
| 國家兩廳院演奏廳 | `https://opusformosa.org/seatmap/nrh/editor-nrh.html` |
| 衛武營音樂廳 | `https://opusformosa.org/seatmap/wwy/editor-wwy.html` |
| 臺中國家歌劇院大劇場 | `https://opusformosa.org/seatmap/tct/editor-tct.html` |

### 觀眾瀏覽版（對外公開）

| 場館 | 網址 |
|------|------|
| 國家兩廳院音樂廳 | `https://opusformosa.org/seatmap/nch/nch.html` |
| 國家兩廳院演奏廳 | `https://opusformosa.org/seatmap/nrh/nrh.html` |
| 衛武營音樂廳 | `https://opusformosa.org/seatmap/wwy/wwy.html` |
| 臺中國家歌劇院大劇場 | `https://opusformosa.org/seatmap/tct/tct.html` |

---

## 每次新音樂會流程

### 第一步：助理填寫定價

1. 將定價工具網址傳給助理（見上表）
2. 助理在網頁上操作：
   - 滑鼠拖拉框選一區座位
   - 輸入票價數字 → 按「套用」
   - 重複直到所有可售座位都定完價
3. 助理點「⬇ 下載 CSV」，得到例如 `NCH定價-2026-04-03.csv`
4. 助理把 CSV 傳回給你

**定價工具操作快捷鍵：**
- 單擊 = 選取單一座位
- Shift/Ctrl + 點擊 = 加選/取消選取
- 拖拉空白區域 = 框選多個座位
- 點右側圖例中的票價 = 選取所有該票價座位

### 第二步：更新觀眾版座位圖

收到 CSV 後，在終端機執行：

```bash
cd /Users/pyen/OpusFormosa/website/seatmap/_dev/nch
python3 apply-pricing.py NCH定價-2026-04-03.csv
```

（替換為對應場館的目錄和 CSV 檔名）

這會將 `nch/nch.html` 中的座位顏色和票價標籤更新為 CSV 中的定價。

### 第三步：部署

```bash
cd /Users/pyen/OpusFormosa/website
./deploy.sh
```

---

## 注意事項

- **定價工具有自動存檔**：助理關掉瀏覽器再開，進度不會遺失（存在 localStorage）
- **不同場館 CSV 不可混用**：CSV 第一行有場地驗證，匯入時若場地不符會報錯
- **灰色/陰影座位**：觀眾版中灰色座位表示「未定價」，不是已售出
- **特殊席**：工作席（紅）、錄影席（灰藍）、樂池席（灰）無法在定價工具中選取

---

## 開發者說明

詳細的工具設計、特殊席配置、修改方式，請參閱：

```
website/seatmap/_dev/WORKFLOW.md
```
