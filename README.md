# JavDB 磁力鏈接專用工具

專門針對 JavDB 網站的磁力鏈接提取工具，用於獲取有碼月榜排行榜影片的磁力鏈接。支援自訂下載數量、標籤過濾（如**高清**、**字幕**、**中文**等）和評分過濾。

> 💡 **關於本專案**：作者是 Code 新手，此專案是透過 [Cursor](https://cursor.sh/) 協助開發完成的。歡迎大家討論、提出建議或貢獻代碼！

**[📖 English Documentation](#english-documentation) | [中文說明](#chinese-documentation)**

---

## ✨ 核心功能

* 🎬 **自動獲取**：獲取有碼月榜排行榜影片（預設 30 部，可自訂）。
* 🔍 **智能過濾**：可自訂標籤（如高清、字幕、中文等）與評分門檻。
* 🔐 **TLS 指紋模擬**：內建 `curl_cffi` 支援，模擬 Chrome 瀏覽器環境，大幅降低遭網站 403 封鎖機率。
* 💾 **多格式導出**：支持 TXT、JSON、CSV 格式。
* 🎨 **雙模式操作**：提供命令列和交互式（單部查詢）兩種模式。

---

## 🚀 快速開始

### 1. 安裝依賴

> ⚠️ **必安裝**：為避免爬取 JavDB 時遭遇 **403 Forbidden**，請先安裝 `curl_cffi`。若系統找不到 `pip` 指令，請用下方 Python Launcher 方式。
>
> ```bash
> py -m pip install curl_cffi
> ```
>
> **可選（備援）**：若安裝 `curl_cffi` 後仍出現 403，可再安裝 Playwright 作為備援：`py -m pip install playwright`，然後執行 `playwright install chromium`。

```bash
# 方式一：使用 Python Launcher (Windows 推薦)
py -m pip install -r requirements.txt

# 方式二：直接使用 pip
pip install -r requirements.txt
```

### 2. 配置設置 (可選)

編輯 `config.env` 文件可以自訂爬蟲行為。若無特殊需求，可直接使用預設值：

| 配置項 | 預設值 | 說明 |
| :--- | :--- | :--- |
| `TOP_COUNT` | `30` | 下載排行榜的前 N 部影片 |
| `FILTER_TAGS` | `高清,字幕` | 只抓取包含指定標籤的連結（逗號分隔） |
| `MIN_SCORE` | `4.0` | 只抓取評分 >= N 的影片（0.0 為不過濾） |

> **提示**：支援標籤包括 `高清`、`字幕`、`中文`、`HD`、`Chinese` 等。設定為空則抓取所有磁力連結。

### 3. 快速啟動

> 💡 **懶人模式**：直接執行以下任意方式即可自動獲取月榜連結：

```bash
# 方式一：Windows 批次檔 (最推薦)
start.bat

# 方式二：Python 命令
python run_javdb_magnet.py

# 方式三：Windows Python Launcher
py run_javdb_magnet.py
```

**🎮 互動模式 (查詢指定番號)**：
```bash
python javdb_magnet_cli.py interactive
```

---

## 🛠️ 進階用法

### 命令行參數

如果需要臨時覆蓋 `config.env` 的設定，可以使用命令行參數：

- `--limit` 或 `-l`：覆蓋 TOP_COUNT
- `--filter` 或 `-f`：覆蓋 FILTER_TAGS
- `--min-score`：覆蓋 MIN_SCORE
- `--export`：導出格式（txt、json、csv）

**範例**：
```bash
# 臨時下載前 50 部，且評分需高於 7.5
python javdb_magnet_cli.py top30 --limit 50 --min-score 7.5

# 導出為自訂 TXT 文件
python javdb_magnet_cli.py top30 --export txt --output my_magnets.txt
```

### 導出路徑與格式

* **月榜結果**：`magnet/url_list_monthly.txt`
* **番號查詢**：`magnet/url_list_code.txt`
* **結構化紀錄**：`scraped_movies.json` (自動生成，每處理一部影片即時存檔)

---

## ⚠️ 注意事項

* 請遵守網站使用條款和相關法律法規。
* 工具內建延遲機制 (2-8 秒)，請勿過度頻繁請求以免造成伺服器負擔或遭 IP 封鎖。
* 本專案僅供學習程式開發與網路爬蟲研究使用。

---

## 🔄 更新日誌

### v1.1.4 (2026-02-12)
* 🛡️ **基礎番號去重**：同一番號的 -C/-UC/-U 等版本（如 MIDA-348、MIDA-348-C）合併為一筆記錄，避免 `scraped_movies.json` 重複。
* ✅ **測試修正**：驗證程式邏輯、模組導入、路徑使用；移除未使用的 `pathlib` 導入；載入舊資料時自動合併為基礎番號。

### v1.1.3 (2026-02-06)
* 🔐 **解決 403 Forbidden**：改用 `curl_cffi` 模擬 Chrome TLS 指紋，大幅降低被阻擋機率。
* 📖 **文檔校對**：修正 README 標籤預設值為 `高清,字幕` 以符合程式邏輯。
* 📂 **導出檔名拆分**：月榜結果保存至 `url_list_monthly.txt`，番號查詢保存至 `url_list_code.txt`。

### v1.1.2 (2026-01-19)
* 🧹 **清理代碼**：移除包含絕對路徑的 debug log，提升專案移植性。
* 📦 **依賴優化**：移除未使用的 `pandas` 與 `selenium`，解決 Python 3.14 安裝問題。

### v1.1.1 (2026-01-18)
* 🔍 **修復搜索功能**：解決番號查詢時 URL 構建錯誤的問題。
* 📊 **磁力解析強化**：支援從連結參數提取標題，優化檔案大小與日期提取。
* 🔢 **互動優化**：表格顯示序號，支援選取特定連結保存。

### v1.1 (2026-01-17)
* ✨ **配置支援**：新增 `config.env` 集中管理設定。
* 🛡️ **防重機制**：番號格式驗證，記錄上限提升至 10,000 筆。
* 🔧 **即時存檔**：每處理完一部影片即時更新 JSON 紀錄。

### v1.0.0
* 初始版本，支持基本磁力鏈接獲取。

---

<div id="english-documentation"></div>

# JavDB Magnet Link Tool (English)

A specialized tool for extracting magnet links from JavDB. It automatically fetches monthly rankings and allows filtering by tags (e.g., **HD**, **Subtitles**, **Chinese**) and ratings.

> 💡 **About This Project**: The author is a coding beginner. This project was developed with the assistance of [Cursor](https://cursor.sh/). Contributions and suggestions are welcome!

**[Back to Chinese Documentation ↑](#chinese-documentation)**

---

## ✨ Features

* 🎬 **Auto Ranking**: Fetches top monthly ranking videos (default 30, customizable).
* 🔍 **Smart Filtering**: Custom tag filters (HD, Subtitles, etc.) and minimum score thresholds.
* 🔐 **TLS Simulation**: Built-in `curl_cffi` support to simulate Chrome TLS fingerprints, significantly reducing 403 Forbidden risks.
* 💾 **Multi-format Export**: Supports TXT, JSON, and CSV.
* 🎨 **Dual Modes**: Command-line interface and Interactive (search by code) modes.

---

## 🚀 Quick Start

### 1. Install Dependencies

> ⚠️ **Required**: To avoid **403 Forbidden** errors on JavDB, you **must** install `curl_cffi` first.
>
> ```bash
> py -m pip install curl_cffi
> ```
>
> **Optional (Fallback)**: If 403 errors persist after installing `curl_cffi`, you can install Playwright: `py -m pip install playwright` and run `playwright install chromium`.

```bash
# Method 1: Using Python Launcher (Recommended for Windows)
py -m pip install -r requirements.txt

# Method 2: Direct pip
pip install -r requirements.txt
```

### 2. Configuration (Optional)

Edit `config.env` to customize the crawler's behavior:

| Key | Default | Description |
| :--- | :--- | :--- |
| `TOP_COUNT` | `30` | Number of top movies to fetch from rankings |
| `FILTER_TAGS` | `高清,字幕` | Fetch links with specific tags (comma-separated) |
| `MIN_SCORE` | `4.0` | Minimum rating score (0.0 to disable filter) |

> **Note**: Supported tags include `高清`, `字幕`, `中文`, `HD`, `Chinese`. Leave empty to fetch all links.

### 3. Launch

> 💡 **Lazy Mode**: Run any of these to start fetching monthly rankings automatically:

```bash
# Method 1: Windows Batch File (Recommended)
start.bat

# Method 2: Python Command
python run_javdb_magnet.py
```

**🎮 Interactive Mode (Search by Movie Code)**:
```bash
python javdb_magnet_cli.py interactive
```

---

## 🛠️ Advanced Usage

### Command Line Arguments

Override `config.env` settings on the fly:

```bash
# Fetch top 50 with rating >= 7.5
python javdb_magnet_cli.py top30 --limit 50 --min-score 7.5

# Export to custom TXT file
python javdb_magnet_cli.py top30 --export txt --output my_magnets.txt
```

### Export Paths & Files

* **Monthly Ranking**: `magnet/url_list_monthly.txt`
* **Code Query**: `magnet/url_list_code.txt`
* **Scraping Log**: `scraped_movies.json` (Real-time auto-save)

---

## 🔄 Update Log

### v1.1.4 (2026-02-12)
* 🛡️ **Base Code Deduplication**: Same movie variants (e.g. MIDA-348, MIDA-348-C) now merge into a single record in `scraped_movies.json`.
* ✅ **Testing & Fixes**: Verified program logic, module imports, and path usage; removed unused `pathlib` import; auto-merge legacy data to base codes on load.

### v1.1.3 (2026-02-06)
* 🔐 **Fixed 403 Forbidden**: Integrated `curl_cffi` to simulate Chrome TLS fingerprints, replacing standard `requests`.
* 📖 **Documentation Sync**: Updated README default tags to `高清,字幕` to match source code.
* 📂 **Export File Split**: Separated monthly ranking results (`url_list_monthly.txt`) from code query results (`url_list_code.txt`).

### v1.1.2 (2026-01-19)
* 🧹 **Code Cleanup**: Removed all debug logs containing absolute paths for better portability.
* 📦 **Dependency Optimization**: Removed unused `pandas` and `selenium`; fixed installation issues with Python 3.14.

### v1.1.1 (2026-01-18)
* 🔍 **Fixed Search Function**: Resolved URL construction errors when querying by movie code.
* 📊 **Improved Parsing**: Enhanced extraction for magnet titles from `dn` parameters and optimized size/date detection.
* 🔢 **UI Enhancement**: Added serial numbers to the results table; supports saving selected links by index (e.g., `1,3,4`).

### v1.1 (2026-01-17)
* ✨ **Config Support**: Added `config.env` for centralized setting management.
* 🔧 **Live Saving**: `scraped_movies.json` now updates immediately after processing each movie.
* 🛡️ **Anti-Duplication**: Added code format validation and increased record limit to 10,000 entries.

### v1.0.0
* Initial release with basic magnet link scraping support.

---

<div id="chinese-documentation"></div>
