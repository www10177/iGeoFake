# iGeoFake (iOS Location Simulator)

這是一個基於 `pymobiledevice3` 與 `NiceGUI` 的 iOS 定位模擬器，專為 Windows 10/11 設計。
本工具允許開發者透過圖形介面輕鬆模擬 iOS 裝置的 GPS 定位。

## ⚠️ 重要提示

**本應用程式必須以「系統管理員身分」執行。**
因為底層需要建立虛擬網卡 (Tunnel)，若無管理員權限將無法運作。

## 系統需求

* Windows 10 或 Windows 11
* Python 3.12+
* [uv](https://github.com/astral-sh/uv) 套件管理器
* iTunes 或 Apple Drivers (確保 Windows 能識別 iOS 裝置)

## 安裝與設定

1. **安裝 uv (若尚未安裝)**:
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **初始化與同步依賴**:
   在專案目錄下開啟終端機 (Terminal) 並執行：
   ```powershell
   uv sync
   ```

## 啟動方式

1. **以「系統管理員身分」開啟 PowerShell 或 Command Prompt**。
   * 在開始選單搜尋 PowerShell -> 右鍵 -> 以系統管理員身分執行。

2. **進入專案目錄**。

3. **執行程式**:
   ```powershell
   uv run main.py
   ```

4. 瀏覽器應會自動開啟，顯示 iGeoFake 操作介面。

## 封裝成 Windows 執行檔 (.exe)

若需要將此專案封裝成無需安裝 Python 的獨立執行檔：

1. 確保已安裝依賴：
   ```powershell
   uv sync
   ```
2. 執行封裝腳本：
   ```powershell
   uv run build.py
   ```
3. 完成後，執行檔將位於 `dist/iGeoFake/iGeoFake.exe`。
   * 請將整個 `dist/iGeoFake` 資料夾複製到目標電腦使用，切勿只複製 exe 檔案。

## 操作說明

### 1. 啟動服務 (Start Services)
* 點擊 **Start Services** 按鈕。
* 程式會依序啟動 `remote tunneld` 與 `lockdown start-tunnel`。
* 請留意 Log 視窗，等待出現 **"Connected (RSD Found)"** 的綠色狀態。這表示已成功連線到裝置。

### 2. 設定定位 (Set Location)
* 在 **Latitude** (緯度) 與 **Longitude** (經度) 欄位輸入目標座標。
* 點擊 **Set Location** 按鈕。
* 狀態將變為 **"Simulating..."**，此時 iOS 裝置的定位應已改變。

### 3. 清除定位 (Clear Location)
* 若要停止模擬並恢復真實定位，點擊 **Clear Location**。

### 4. 停止服務 (Stop Services)
* 點擊 **Stop Services** 會終止所有背景連線與模擬進程。

## 常見問題

* **Error: Must run as Administrator**
  * 請關閉程式，並確保終端機是以管理員權限開啟的。

* **Log 顯示連線失敗**
  * 請確認 iOS 裝置已解鎖並信任此電腦。
  * 請確認 iTunes 可以偵測到裝置。

## 開發者資訊

* **Backend**: Python `asyncio` + `pymobiledevice3`
* **Frontend**: NiceGUI
* **Process Management**: 使用 `taskkill` 確保無殭屍進程殘留。
