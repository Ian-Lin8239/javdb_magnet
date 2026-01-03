# JavDB 磁力鏈接專用工具使用說明

## 🎯 工具概述

這是一個專門針對 JavDB 網站的磁力鏈接提取工具，**專門用於獲取有碼月榜前30部影片的磁力鏈接**，重點提取標記為"高清"或"中文"的磁力鏈接的"複製"按鈕下載位置。

## ✨ 核心功能

- 🎬 **有碼月榜前30** - 自動獲取有碼類別月榜前30部影片
- 🔍 **智能過濾** - 自動過濾出標記為"高清"或"中文"的磁力鏈接
- 📋 **複製按鈕** - 重點提取"複製"按鈕的實際下載鏈接
- 💾 **多格式導出** - 支持 TXT、JSON、CSV 格式導出
- 🎨 **友好界面** - 命令行和交互式兩種模式

## 🚀 快速開始

### 安裝依賴
```bash
pip install -r requirements.txt
```

### 快速啟動
```bash
python run_javdb_magnet.py
```

## 📖 使用方法

### 1. 獲取有碼月榜前30的磁力鏈接

#### 只獲取高清/中文標籤的磁力鏈接：
```bash
python javdb_magnet_cli.py top30 --filter 高清,中文 --export txt
```

#### 獲取所有磁力鏈接：
```bash
python javdb_magnet_cli.py top30 --export txt
```

#### 導出為不同格式：
```bash
# TXT格式 (默認)
python javdb_magnet_cli.py top30 --filter 高清,中文 --export txt --output magnets.txt

# JSON格式
python javdb_magnet_cli.py top30 --filter 高清,中文 --export json --output magnets.json

# CSV格式
python javdb_magnet_cli.py top30 --filter 高清,中文 --export csv --output magnets.csv
```

### 2. 根據番號獲取磁力鏈接

```bash
# 獲取指定番號的磁力鏈接
python javdb_magnet_cli.py code SSIS-001 --filter 高清,中文 --export txt

# 獲取所有磁力鏈接
python javdb_magnet_cli.py code JUR-496 --export txt
```

### 3. 交互式模式

```bash
python javdb_magnet_cli.py interactive
```

在交互式模式下可以使用：
- `top30` - 獲取有碼月榜前30的磁力鏈接
- `code SSIS-001` - 根據番號獲取磁力鏈接
- `help` - 顯示幫助
- `quit` - 退出

## 🔧 程序化使用

### 基本用法

```python
from javdb_magnet_crawler import JavDBMagnetManager

# 創建管理器
manager = JavDBMagnetManager()

# 獲取有碼月榜前30的磁力鏈接
results = manager.get_top30_magnets()

# 處理結果
for result in results:
    movie = result['movie']
    print(f"排名: {result['rank']}")
    print(f"番號: {movie['code']}")
    print(f"標題: {movie['title']}")
    print(f"過濾後磁力鏈接: {result['filtered_magnets']} 個")
    
    for magnet in result['magnet_links']:
        print(f"  - {magnet.title}")
        print(f"    大小: {magnet.size}")
        print(f"    標籤: {', '.join(magnet.tags)}")
        print(f"    下載鏈接: {magnet.copy_url or magnet.magnet_url}")
```

### 高級用法

```python
from javdb_magnet_crawler import JavDBMagnetCrawler, MagnetLink

# 直接使用爬蟲
crawler = JavDBMagnetCrawler()

# 獲取特定影片的磁力鏈接
magnet_links = crawler.get_movie_magnet_links("https://javdb.com/v/SSIS-001")

# 過濾磁力鏈接
filtered_magnets = crawler._filter_magnets_by_tags(magnet_links, ['高清', '中文'])

# 獲取下載URL
for magnet in filtered_magnets:
    download_url = crawler.get_magnet_download_url(magnet)
    print(f"下載鏈接: {download_url}")
```

## 📊 數據結構

### MagnetLink 對象

```python
class MagnetLink:
    title = ""              # 磁力鏈接標題
    size = ""               # 文件大小
    file_count = 0          # 文件數量
    tags = []               # 標籤 (高清, 中文等)
    magnet_url = ""         # 磁力鏈接URL
    copy_url = ""           # 複製按鈕的實際下載鏈接 ⭐
    download_url = ""       # 下載按鈕的鏈接
    date = ""               # 上傳日期
    quality = ""            # 質量標識
```

### 結果數據結構

```python
{
    'rank': 1,                    # 排名
    'movie': {                    # 影片信息
        'code': 'SSIS-001',       # 番號
        'title': '影片標題',       # 標題
        'actors': ['演員1'],       # 演員列表
        'score': 8.5,             # 評分
        'tags': ['標籤1']         # 標籤
    },
    'magnet_links': [...],        # 磁力鏈接列表
    'total_magnets': 5,          # 總磁力鏈接數
    'filtered_magnets': 2        # 過濾後磁力鏈接數
}
```

## 📁 輸出文件格式

### TXT 格式示例

```
JavDB 有碼月榜前30磁力鏈接
==================================================

排名: 1
番號: SSIS-001
標題: 三上悠亜の制服コレクション
演員: 三上悠亜
評分: 8.5
總磁力鏈接: 5 個
過濾後磁力鏈接: 2 個
磁力鏈接:
  1. SSIS-001 高清版
     大小: 6.38GB
     標籤: 高清
     下載鏈接: magnet:?xt=urn:btih:...
     日期: 2025-10-24

  2. SSIS-001 中文版
     大小: 6.47GB
     標籤: 中文
     下載鏈接: magnet:?xt=urn:btih:...
     日期: 2025-10-24
```

### JSON 格式示例

```json
[
  {
    "rank": 1,
    "movie": {
      "code": "SSIS-001",
      "title": "三上悠亜の制服コレクション",
      "actors": ["三上悠亜"],
      "score": 8.5
    },
    "magnet_links": [
      {
        "title": "SSIS-001 高清版",
        "size": "6.38GB",
        "tags": ["高清"],
        "download_url": "magnet:?xt=urn:btih:..."
      }
    ]
  }
]
```

## ⚙️ 配置選項

### 過濾標籤

支持的過濾標籤：
- `高清` - 高清晰度版本
- `中文` - 中文字幕版本
- `HD` - 高清英文標識
- `Chinese` - 中文英文標識

### 導出格式

- **TXT** - 人類可讀的文本格式，包含完整信息
- **JSON** - 結構化數據，便於程序處理
- **CSV** - 表格格式，便於Excel打開

## 🛡️ 安全特性

- **隨機延遲** - 避免請求過於頻繁
- **User-Agent 輪換** - 模擬不同瀏覽器
- **錯誤處理** - 完善的異常處理機制
- **重試機制** - 自動重試失敗的請求

## ⚠️ 注意事項

1. **遵守網站使用條款** - 請確保使用符合 JavDB 網站的使用條款
2. **請求頻率** - 工具已內建延遲機制，避免對服務器造成負擔
3. **代理設置** - 如果遇到訪問限制，可以考慮使用代理服務器
4. **數據使用** - 僅用於學習和研究目的，請勿用於商業用途
5. **法律合規** - 請確保使用符合當地法律法規

## 🔍 故障排除

### 常見問題

1. **連接超時**
   - 檢查網絡連接
   - 嘗試使用代理服務器
   - 增加請求延遲時間

2. **解析錯誤**
   - 網站結構可能已更改
   - 檢查 HTML 解析器是否正常工作

3. **訪問被拒絕**
   - 網站可能有反爬蟲機制
   - 嘗試更換 User-Agent
   - 使用代理服務器

4. **沒有找到磁力鏈接**
   - 影片可能沒有磁力鏈接
   - 磁力鏈接可能被網站隱藏
   - 嘗試訪問影片詳情頁面確認

### 調試模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 你的代碼
```

## 📈 性能優化

- **並發控制** - 避免同時發送過多請求
- **緩存機制** - 避免重複請求相同內容
- **增量更新** - 只獲取新增的磁力鏈接

## 🔄 更新日誌

- **v1.0.0** - 初始版本，支持基本磁力鏈接獲取
- **v1.1.0** - 添加過濾功能和導出功能
- **v1.2.0** - 優化解析邏輯和錯誤處理
- **v1.3.0** - 添加複製按鈕鏈接提取功能

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request 來改進這個工具！

## 📄 許可證

本工具僅供學習和研究使用，請遵守相關法律法規。

---

**重點提醒**：這個工具專門用於獲取 JavDB 有碼月榜前30部影片的磁力鏈接，特別是標記為"高清"或"中文"的磁力鏈接的"複製"按鈕下載位置。請合理使用，遵守相關法律法規。











