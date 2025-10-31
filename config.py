"""
BT網站爬蟲工具 - 核心配置模塊
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 加載環境變量
load_dotenv()

@dataclass
class SiteConfig:
    """BT網站配置"""
    name: str
    base_url: str
    search_url: str
    browse_url: str
    headers: Dict[str, str]
    search_params: Dict[str, str]
    enabled: bool = True

class Config:
    """全局配置類"""
    
    # 請求配置
    REQUEST_DELAY = (1, 3)  # 隨機延遲範圍（秒）
    MAX_RETRIES = 3
    TIMEOUT = 30
    
    # 數據庫配置
    DATABASE_PATH = "bt_torrents.db"
    
    # 日誌配置
    LOG_LEVEL = "INFO"
    LOG_FILE = "bt_crawler.log"
    
    # 支持的BT網站配置
    SITES = {
        "piratebay": SiteConfig(
            name="The Pirate Bay",
            base_url="https://thepiratebay.org",
            search_url="https://thepiratebay.org/search.php",
            browse_url="https://thepiratebay.org/browse.php",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            search_params={
                "q": "",
                "cat": "",
                "page": 0,
                "orderby": 99,  # 按種子數量排序
            }
        ),
        "1337x": SiteConfig(
            name="1337x",
            base_url="https://1337x.to",
            search_url="https://1337x.to/search",
            browse_url="https://1337x.to/category",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            search_params={
                "q": "",
                "cat": "",
                "page": 1,
                "sort": "seeders",
                "order": "desc"
            }
        ),
        "rarbg": SiteConfig(
            name="RARBG",
            base_url="https://rarbg.to",
            search_url="https://rarbg.to/torrents.php",
            browse_url="https://rarbg.to/torrents.php",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            search_params={
                "search": "",
                "category": "",
                "page": 1,
                "order": "seeders",
                "by": "DESC"
            }
        )
    }
    
    # 類別映射
    CATEGORIES = {
        "movies": {
            "piratebay": "200",  # Video > Movies
            "1337x": "Movies",
            "rarbg": "4"  # XXX
        },
        "tv": {
            "piratebay": "500",  # Video > TV shows
            "1337x": "TV",
            "rarbg": "18"  # TV Episodes
        },
        "music": {
            "piratebay": "100",  # Audio > Music
            "1337x": "Music",
            "rarbg": "23"  # Music
        },
        "games": {
            "piratebay": "400",  # Applications > Games
            "1337x": "Games",
            "rarbg": "27"  # Games
        },
        "software": {
            "piratebay": "300",  # Applications
            "1337x": "Applications",
            "rarbg": "33"  # Software
        },
        "books": {
            "piratebay": "600",  # Other > E-books
            "1337x": "Books",
            "rarbg": "35"  # E-books
        }
    }
    
    @classmethod
    def get_site_config(cls, site_name: str) -> Optional[SiteConfig]:
        """獲取指定網站的配置"""
        return cls.SITES.get(site_name)
    
    @classmethod
    def get_enabled_sites(cls) -> List[str]:
        """獲取啟用的網站列表"""
        return [name for name, config in cls.SITES.items() if config.enabled]
    
    @classmethod
    def get_category_id(cls, category: str, site: str) -> Optional[str]:
        """獲取指定網站的類別ID"""
        return cls.CATEGORIES.get(category, {}).get(site)


