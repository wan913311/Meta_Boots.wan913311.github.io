# Meta-Booth 虛擬分身即時拍貼所

學期即時合成特效與互動裝置創作。手機捏 Q 版分身 → 綠棚前 Webcam 即時動補 → 倒數拍貼。

## 檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 舞台畫面（大螢幕）：掃分身票 QR 登記、最多 2 人同框動作捕捉、拍照存檔 |
| `console.html` | 後端控制台（第二螢幕）：等待區、決定誰上台、綁定狀態、遊玩區設定、紀錄與 CSV 匯出 |
| `phone.html` | 手機捏臉頁：選髮型/臉/服裝/配件，產生分身票 QR |
| `avatar-lib.js` | 兩個頁面共用的模型載入器（依參數顯示零件、換色） |
| `metabooth_avatar.glb` | 分身零件模型（Blender 匯出） |
| `blender/metabooth_avatar.blend` | 模型原始檔 |
| `blender/build_avatar.py` | 產生模型的 Blender 腳本 |

## 現場怎麼開

1. 主控電腦接兩個螢幕：用 Chrome 開 `index.html`（拖到電視、按 F 全螢幕），同一個 Chrome 再開 `console.html` 放在電腦螢幕。
2. 兩個頁面要在**同一台電腦、同一個瀏覽器**才會連線（控制台上方顯示「舞台：連線中」）。
3. 同學在鏡頭前掃分身票 → 控制台等待區出現 → 按「上左／上右」（或打開自動叫下一位）。
4. 沒開控制台時，舞台會自己運作：掃到就直接上台（最多 2 人）。

資料存在這台電腦的瀏覽器裡，換電腦或清除瀏覽資料前記得先匯出 CSV。

## 本機執行

用 WebStorm 開 `index.html` → 右上角瀏覽器圖示（會用 localhost 開，鏡頭才能用）。
直接雙擊開檔時讀不到 .glb，會改用內建模型；可以把 .glb 拖進視窗。

## 動作捕捉

用 MediaPipe Pose 的 3D 座標（worldLandmarks）驅動肩、肘、髖、膝，可以前後左右擺動。腳要拍到全身（人離鏡頭約 2.5～3 公尺）才會動，拍不到就站好不動。網址加 `?demo` 可以看示範動作。

## 主控台按鍵

空白 / → 拍照 · 雙手舉高 1 秒拍照 · N 下一位 · B 換背景 · K 頭部校正 · V 換鏡頭 · D 鏡頭小窗 · C 輸入代碼 · P 像素顆粒 · F 全螢幕

## 模型零件命名規則

- 軸心：`ROOT` / `PIVOT_Upper` / `PIVOT_Head` / `PIVOT_Arm_L|R` / `PIVOT_Eye_L|R` / `PIVOT_Mouth`
- 關節：`PIVOT_Arm` > `PIVOT_Elbow_L|R`（手肘）；`ROOT` > `PIVOT_Leg_L|R`（髖）> `PIVOT_Knee_L|R`（膝蓋）
- 手腳在模型裡要「直直往下」擺放；_L = 角色左手邊 = Blender +X
- 零件：`hair_0~4`、`eyes_0~3_L|R`、`mouth_0~2`、`mouth_open`、`blush_1`、`outfit_0~3_*`、`acc_1~5`
- 可換色材質：`TINT_HAIR`、`TINT_SKIN`、`TINT_OUTFIT*`
- 匯出：glTF Binary (.glb)、+Y Up、匯出全部物件
