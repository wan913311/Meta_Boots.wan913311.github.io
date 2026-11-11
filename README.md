# Meta-Booth 虛擬分身即時拍貼所

學期即時合成特效與互動裝置創作。手機捏 Q 版分身 → 綠棚前 Webcam 即時動補 → 倒數拍貼。

## 檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 主控台（大螢幕）：掃分身票 QR、動作捕捉、拍照存檔 |
| `phone.html` | 手機捏臉頁：選髮型/臉/服裝/配件，產生分身票 QR |
| `avatar-lib.js` | 兩個頁面共用的模型載入器（依參數顯示零件、換色） |
| `metabooth_avatar.glb` | 分身零件模型（Blender 匯出） |
| `blender/metabooth_avatar.blend` | 模型原始檔 |
| `blender/build_avatar.py` | 產生模型的 Blender 腳本 |

## 本機執行

用 WebStorm 開 `index.html` → 右上角瀏覽器圖示（會用 localhost 開，鏡頭才能用）。
直接雙擊開檔時讀不到 .glb，會改用內建模型；可以把 .glb 拖進視窗。

## 主控台按鍵

空白 / → 拍照 · 雙手舉高 1 秒拍照 · N 下一位 · B 換背景 · K 頭部校正 · V 換鏡頭 · D 鏡頭小窗 · C 輸入代碼 · P 像素顆粒 · F 全螢幕

## 模型零件命名規則

- 軸心：`ROOT` / `PIVOT_Upper` / `PIVOT_Head` / `PIVOT_Arm_L|R` / `PIVOT_Eye_L|R` / `PIVOT_Mouth`
- 零件：`hair_0~4`、`eyes_0~3_L|R`、`mouth_0~2`、`mouth_open`、`blush_1`、`outfit_0~3_*`、`acc_1~5`
- 可換色材質：`TINT_HAIR`、`TINT_SKIN`、`TINT_OUTFIT*`
- 匯出：glTF Binary (.glb)、+Y Up、匯出全部物件
