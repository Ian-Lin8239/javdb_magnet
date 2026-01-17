# JavDB 磁力鏈接專用工具

專門針對 JavDB 網站的磁力鏈接提取工具，用於獲取有碼月榜前30部影片的磁力鏈接，重點提取標記為"高清"或"中文"的磁力鏈接。

> 💡 **關於本專案**：作者是 Code 新手，此專案是透過 [Cursor](https://cursor.sh/) 協助開發完成的。歡迎大家討論、提出建議或貢獻代碼！

## ✨ 核心功能

- 🎬 自動獲取有碼月榜前30部影片
- 🔍 智能過濾高清/中文標籤的磁力鏈接
- 💾 支持 TXT、JSON、CSV 格式導出
- 🎨 命令行和交互式兩種模式

## 🚀 快速開始

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 配置設置

編輯 `config.env` 文件可以自訂配置參數（可選）

### 快速啟動

```bash
# 方式一：Python 命令
python run_javdb_magnet.py

# 方式二：Windows 批次檔
start.bat

# 方式三：Windows Python Launcher
py run_javdb_magnet.py
```

## 📖 使用方法

### 1. 獲取有碼月榜前30的磁力鏈接

```bash
# 僅在螢幕顯示（不過濾）
python javdb_magnet_cli.py top30

# 過濾並導出為 TXT
python javdb_magnet_cli.py top30 --filter 高清,中文 --export txt --output magnets.txt

# 導出為 JSON
python javdb_magnet_cli.py top30 --filter 高清,中文 --export json --output magnets.json

# 導出為 CSV
python javdb_magnet_cli.py top30 --filter 高清,中文 --export csv --output magnets.csv
```

### 2. 根據番號獲取磁力鏈接

```bash
# 僅在螢幕顯示
python javdb_magnet_cli.py code SSIS-001 --filter 高清,中文

# 導出為文件
python javdb_magnet_cli.py code SSIS-001 --filter 高清,中文 --export txt --output SSIS-001.txt
```

### 3. 交互式模式

```bash
python javdb_magnet_cli.py interactive
```

可用命令：`top30`、`code SSIS-001`、`help`、`quit`

## 🔧 程序化使用

```python
from javdb_magnet_crawler import JavDBMagnetManager

manager = JavDBMagnetManager()
results = manager.get_top30_magnets()

for result in results:
    movie = result['movie']
    print(f"排名: {result['rank']}, 番號: {movie['code']}, 標題: {movie['title']}")
```

## ⚙️ 配置選項

### 過濾標籤

支持的標籤：`高清`、`中文`、`字幕`、`HD`、`Chinese`（可多選，用逗號分隔）

### 導出格式

- **TXT** - 文本格式，包含完整信息
- **JSON** - 結構化數據
- **CSV** - 表格格式

**注意**：使用 `--export` 時必須配合 `--output` 指定文件名

## ⚠️ 注意事項

- 遵守網站使用條款和法律法規
- 工具已內建延遲機制，避免對服務器造成負擔
- 僅供學習和研究使用

## 🔍 故障排除

- **連接超時**：檢查網絡連接或使用代理
- **解析錯誤**：網站結構可能已更改
- **訪問被拒絕**：嘗試更換 User-Agent 或使用代理

---

**重要提醒**：`config.env` 等敏感配置文件不會被提交到版本控制系統。
