"""
BT網站爬蟲工具 - 工具函數
"""
import re
import time
import random
import logging
import sys
import io
from typing import Optional, List, Dict, Any
from datetime import datetime
from fake_useragent import UserAgent

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """設置日誌記錄"""
    # 確保控制台支持 UTF-8 編碼
    try:
        if sys.platform == 'win32':
            # Windows 上設置控制台代碼頁為 UTF-8
            import os
            os.system('chcp 65001 >nul 2>&1')
        
        # 重新配置 stdout/stderr 為 UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass  # 如果設置失敗，繼續執行
    
    logger = logging.getLogger("bt_crawler")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除現有的處理器
    logger.handlers.clear()
    
    # 創建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台處理器 - 確保使用 UTF-8 編碼輸出
    class UTF8StreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                # 確保編碼正確
                if hasattr(stream, 'buffer'):
                    stream.buffer.write(msg.encode('utf-8', errors='replace'))
                    stream.buffer.write(b'\n')
                    stream.buffer.flush()
                else:
                    stream.write(msg)
                    stream.write('\n')
                    stream.flush()
            except Exception:
                self.handleError(record)
    
    console_handler = UTF8StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件處理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_random_user_agent() -> str:
    """獲取隨機User-Agent"""
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        # 備用User-Agent列表
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        return random.choice(user_agents)

def random_delay(min_delay: float = 1.0, max_delay: float = 3.0) -> None:
    """隨機延遲"""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)

def parse_size(size_str: str) -> Optional[int]:
    """解析文件大小字符串為字節數"""
    if not size_str:
        return None
    
    # 清理字符串
    size_str = size_str.strip().upper()
    
    # 大小單位映射
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4
    }
    
    # 正則表達式匹配數字和單位
    pattern = r'([\d,]+\.?\d*)\s*([A-Z]+)'
    match = re.search(pattern, size_str)
    
    if match:
        try:
            number = float(match.group(1).replace(',', ''))
            unit = match.group(2)
            
            if unit in units:
                return int(number * units[unit])
        except ValueError:
            pass
    
    return None

def format_size(size_bytes: Optional[int]) -> str:
    """格式化字節數為可讀大小"""
    if size_bytes is None:
        return "Unknown"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def parse_date(date_str: str) -> Optional[datetime]:
    """解析日期字符串"""
    if not date_str:
        return None
    
    # 常見日期格式
    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %H:%M:%S.%f"
    ]
    
    # 清理字符串
    date_str = date_str.strip()
    
    # 處理相對時間（如 "2 hours ago", "1 day ago"）
    relative_patterns = {
        r'(\d+)\s*minute[s]?\s*ago': lambda m: datetime.now().replace(minute=datetime.now().minute - int(m.group(1))),
        r'(\d+)\s*hour[s]?\s*ago': lambda m: datetime.now().replace(hour=datetime.now().hour - int(m.group(1))),
        r'(\d+)\s*day[s]?\s*ago': lambda m: datetime.now().replace(day=datetime.now().day - int(m.group(1))),
        r'(\d+)\s*week[s]?\s*ago': lambda m: datetime.now().replace(day=datetime.now().day - int(m.group(1)) * 7),
        r'(\d+)\s*month[s]?\s*ago': lambda m: datetime.now().replace(month=datetime.now().month - int(m.group(1))),
        r'(\d+)\s*year[s]?\s*ago': lambda m: datetime.now().replace(year=datetime.now().year - int(m.group(1)))
    }
    
    for pattern, func in relative_patterns.items():
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                return func(match)
            except ValueError:
                continue
    
    # 嘗試標準格式
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def clean_text(text: str) -> str:
    """清理文本"""
    if not text:
        return ""
    
    # 移除多餘的空白字符
    text = re.sub(r'\s+', ' ', text.strip())
    
    # 移除特殊字符
    text = re.sub(r'[^\w\s\-.,!?()]', '', text)
    
    return text

def extract_magnet_link(html_content: str) -> Optional[str]:
    """從HTML內容中提取磁力鏈接"""
    magnet_pattern = r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"\s]*'
    match = re.search(magnet_pattern, html_content)
    return match.group(0) if match else None

def extract_torrent_url(html_content: str, base_url: str) -> Optional[str]:
    """從HTML內容中提取種子文件URL"""
    # 查找.torrent文件鏈接
    torrent_pattern = r'href=["\']([^"\']*\.torrent)["\']'
    match = re.search(torrent_pattern, html_content)
    
    if match:
        torrent_path = match.group(1)
        if torrent_path.startswith('http'):
            return torrent_path
        elif torrent_path.startswith('/'):
            return base_url + torrent_path
        else:
            return base_url + '/' + torrent_path
    
    return None

def validate_magnet_link(magnet_link: str) -> bool:
    """驗證磁力鏈接格式"""
    if not magnet_link:
        return False
    
    magnet_pattern = r'^magnet:\?xt=urn:btih:[a-zA-Z0-9]+'
    return bool(re.match(magnet_pattern, magnet_link))

def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    if not filename:
        return "unknown"
    
    # 移除或替換非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename.strip('._')
    
    # 限制長度
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename or "unknown"







