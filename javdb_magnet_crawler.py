"""
JavDB 磁力鏈接專用爬蟲
專門用於獲取有碼月榜前30的磁力鏈接下載位置
"""
import requests
import time
import random
import re
import os
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from utils import (
    get_random_user_agent, random_delay, clean_text, setup_logging
)
from duplicate_tracker import DuplicateTracker

class MagnetLink:
    """磁力鏈接數據模型"""
    def __init__(self):
        self.title = ""  # 磁力鏈接標題
        self.size = ""  # 文件大小
        self.file_count = 0  # 文件數量
        self.tags = []  # 標籤 (高清, 字幕等)
        self.magnet_url = ""  # 磁力鏈接URL
        self.copy_url = ""  # 複製按鈕的實際下載鏈接
        self.download_url = ""  # 下載按鈕的鏈接
        self.date = ""  # 上傳日期
        self.quality = ""  # 質量標識

class JavDBMagnetCrawler:
    """JavDB 磁力鏈接專用爬蟲"""
    
    def __init__(self):
        self.base_url = "https://javdb.com"
        self.session = requests.Session()
        self.logger = setup_logging()
        self._setup_session()
    
    def _setup_session(self):
        """設置會話"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "Sec-GPC": "1"
        })
    
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                     retries: int = 3) -> Optional[requests.Response]:
        """發送HTTP請求"""
        for attempt in range(retries + 1):
            try:
                # 隨機延遲
                if attempt > 0:
                    random_delay(2, 5)
                
                # 更新User-Agent
                self.session.headers['User-Agent'] = get_random_user_agent()
                
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=30,
                    allow_redirects=True,
                    headers={'Accept-Encoding': 'gzip, deflate'}
                )
                
                response.raise_for_status()
                
                # 請求間隔
                random_delay(1, 3)
                
                return response
                
            except requests.RequestException as e:
                self.logger.warning(f"請求失敗 (嘗試 {attempt + 1}/{retries + 1}): {e}")
                
                if attempt == retries:
                    self.logger.error(f"請求最終失敗: {url}")
                    return None
                
                # 指數退避
                time.sleep(2 ** attempt)
        
        return None
    
    def get_monthly_rankings_with_magnets(self, limit: int = 30) -> List[Dict[str, Any]]:
        """獲取有碼月榜前30的影片及其磁力鏈接"""
        self.logger.info(f"開始獲取有碼月榜前{limit}的影片磁力鏈接")
        
        # 1. 獲取排行榜頁面
        rankings_url = f"{self.base_url}/rankings/movies"
        params = {
            "p": "monthly",  # 月榜
            "t": "censored",  # 有碼
            "page": 1
        }
        
        response = self._make_request(rankings_url, params)
        if not response:
            self.logger.error("無法獲取排行榜頁面")
            return []
        
        # 2. 解析排行榜，獲取影片列表
        movies = self._parse_rankings_page(response.text, limit)
        self.logger.info(f"從排行榜獲取到 {len(movies)} 部影片")
        
        # 3. 創建即時寫入文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"magnet/javdb_monthly_magnets_{timestamp}.txt"
        os.makedirs("magnet", exist_ok=True)
        
        # 4. 為每部影片獲取磁力鏈接並即時寫入
        results = []
        with open(filename, 'w', encoding='utf-8') as f:
            # 寫入文件頭
            f.write("JavDB 有碼月榜前30磁力鏈接\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            f.write("磁力鏈接列表（即時更新）\n")
            f.write("=" * 80 + "\n\n")
            f.flush()  # 強制寫入
            
            for i, movie in enumerate(movies, 1):
                self.logger.info(f"處理第 {i}/{len(movies)} 部影片: {movie['title']}")
                
                # 獲取磁力鏈接
                magnet_links = self.get_movie_magnet_links(movie['detail_url'])
                
                # 根據優先順序過濾磁力鏈接
                filtered_magnets = self._filter_magnets_by_priority(magnet_links)
                
                result = {
                    'rank': i,
                    'movie': movie,
                    'magnet_links': filtered_magnets,
                    'total_magnets': len(magnet_links),
                    'filtered_magnets': len(filtered_magnets)
                }
                
                # 嘗試從磁力鏈接中提取真實番號
                if filtered_magnets and (not movie['code'] or len(movie['code']) < 5):
                    magnet = filtered_magnets[0]
                    real_code = self._extract_real_code_from_magnet(magnet.copy_url or magnet.magnet_url)
                    if real_code:
                        movie['code'] = real_code
                
                results.append(result)
                
                # 即時寫入到文件
                f.write(f"排名: {i}\n")
                f.write(f"番號: {movie['code']}\n")
                f.write(f"標題: {movie['title']}\n")
                f.write(f"演員: {', '.join(movie['actors'])}\n")
                f.write(f"評分: {movie['score']}\n")
                f.write(f"總磁力鏈接: {len(magnet_links)} 個\n")
                f.write(f"選擇磁力鏈接: {len(filtered_magnets)} 個\n")
                
                if filtered_magnets:
                    magnet = filtered_magnets[0]  # 只取第一個（最佳選擇）
                    f.write(f"磁力鏈接: {magnet.copy_url or magnet.magnet_url}\n")
                    f.write(f"大小: {magnet.size}\n")
                    f.write(f"標籤: {', '.join(magnet.tags)}\n")
                    f.write(f"日期: {magnet.date}\n")
                else:
                    f.write("無符合條件的磁力鏈接\n")
                
                f.write("-" * 80 + "\n\n")
                f.flush()  # 強制寫入，確保即時保存
                
                # 避免請求過於頻繁
                random_delay(2, 4)
            
            # 寫入統計信息
            total_magnets = sum(result['total_magnets'] for result in results)
            filtered_magnets = sum(result['filtered_magnets'] for result in results)
            
            f.write("=" * 80 + "\n")
            f.write("統計信息\n")
            f.write("=" * 80 + "\n")
            f.write(f"總影片數: {len(results)}\n")
            f.write(f"總磁力鏈接數: {total_magnets}\n")
            f.write(f"選擇磁力鏈接數: {filtered_magnets}\n")
            f.write(f"成功率: {filtered_magnets/total_magnets*100:.1f}%\n")
            f.write(f"完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.logger.info(f"磁力鏈接已即時保存到: {filename}")
        return results
    
    def _parse_rankings_page(self, html_content: str, limit: int) -> List[Dict[str, Any]]:
        """解析排行榜頁面"""
        soup = BeautifulSoup(html_content, 'html.parser')
        movies = []
        
        # 調試：檢查頁面內容
        self.logger.info(f"頁面內容長度: {len(html_content)}")
        
        # 查找電影列表容器
        movie_items = soup.find_all('div', class_='item')
        self.logger.info(f"找到 {len(movie_items)} 個電影項目")
        
        # 如果沒有找到，嘗試其他選擇器
        if not movie_items:
            movie_items = soup.find_all('div', class_='movie-item')
            self.logger.info(f"使用 movie-item 找到 {len(movie_items)} 個項目")
        
        if not movie_items:
            movie_items = soup.find_all('div', class_='video-item')
            self.logger.info(f"使用 video-item 找到 {len(movie_items)} 個項目")
        
        # 調試：保存頁面內容
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.info("已保存調試頁面到 debug_page.html")
        
        for index, item in enumerate(movie_items[:limit]):
            try:
                movie = self._parse_movie_item(item, index + 1)
                if movie:
                    movies.append(movie)
            except Exception as e:
                self.logger.warning(f"解析電影項目失敗: {e}")
                continue
        
        return movies
    
    def _parse_movie_item(self, item, rank: int) -> Optional[Dict[str, Any]]:
        """解析電影項目"""
        movie = {
            'rank': rank,
            'code': '',
            'title': '',
            'detail_url': '',
            'cover_url': '',
            'score': 0.0,
            'actors': [],
            'tags': []
        }
        
        # 獲取電影鏈接
        link_elem = item.find('a')
        if not link_elem:
            return None
        
        movie['detail_url'] = urljoin(self.base_url, link_elem.get('href', ''))
        
        # 從URL提取番號（這是JavDB的短代碼，不是真實番號）
        url_parts = movie['detail_url'].split('/')
        if len(url_parts) > 1:
            movie['code'] = url_parts[-1]  # 短代碼，後續會嘗試從磁力鏈接提取真實番號
        
        # 獲取封面圖片
        img_elem = item.find('img')
        if img_elem:
            movie['cover_url'] = urljoin(self.base_url, img_elem.get('src', ''))
        
        # 獲取標題 - 嘗試多種選擇器
        title_elem = item.find('div', class_='video-title')
        if not title_elem:
            title_elem = item.find('div', class_='title')
        if not title_elem:
            title_elem = item.find('strong')
        if not title_elem:
            # 嘗試從鏈接文本獲取
            title_elem = link_elem
        
        if title_elem:
            if title_elem.name == 'a':
                title_text = title_elem.get('title', '') or title_elem.get_text()
            else:
                title_link = title_elem.find('a')
                if title_link:
                    title_text = title_link.get('title', '') or title_link.get_text()
                else:
                    title_text = title_elem.get_text()
            
            if title_text:
                movie['title'] = clean_text(title_text)
        
        # 獲取評分 - 嘗試多種選擇器
        score_elem = item.find('span', class_='score')
        if not score_elem:
            score_elem = item.find('span', class_='rating')
        if not score_elem:
            score_elem = item.find('div', class_='score')
        if not score_elem:
            score_elem = item.find('span', class_='value')
        if score_elem:
            try:
                score_text = score_elem.get_text().strip()
                # 移除可能的非數字字符，只保留數字和小數點
                score_text = re.sub(r'[^\d.]', '', score_text)
                if score_text:
                    movie['score'] = float(score_text)
            except (ValueError, AttributeError):
                pass
        
        # 獲取標籤
        tags_elem = item.find('div', class_='tags')
        if not tags_elem:
            tags_elem = item.find('div', class_='tag-list')
        if tags_elem:
            tag_links = tags_elem.find_all('a')
            movie['tags'] = [clean_text(tag.get_text()) for tag in tag_links]
        
        # 獲取演員 - 嘗試多種選擇器
        actors_elem = item.find('div', class_='actors')
        if not actors_elem:
            actors_elem = item.find('div', class_='actor-list')
        if not actors_elem:
            actors_elem = item.find('div', class_='performers')
        if not actors_elem:
            # 嘗試查找包含"演員"或"主演"文字的div
            for div in item.find_all('div'):
                div_text = div.get_text()
                if '演員' in div_text or '主演' in div_text:
                    actors_elem = div
                    break
        
        if actors_elem:
            actor_links = actors_elem.find_all('a')
            if actor_links:
                movie['actors'] = [clean_text(actor.get_text()) for actor in actor_links]
            else:
                # 如果沒有鏈接，嘗試直接獲取文本並分割
                actor_text = actors_elem.get_text().strip()
                if actor_text:
                    # 移除"演員："等前綴
                    actor_text = re.sub(r'^[演員主演：:]+', '', actor_text)
                    if actor_text:
                        movie['actors'] = [clean_text(a.strip()) for a in actor_text.split(',') if a.strip()]
        
        return movie
    
    def get_movie_magnet_links(self, movie_url: str) -> List[MagnetLink]:
        """獲取影片的磁力鏈接"""
        self.logger.info(f"獲取磁力鏈接: {movie_url}")
        
        response = self._make_request(movie_url)
        if not response:
            self.logger.error(f"無法獲取影片詳情頁面: {movie_url}")
            return []
        
        return self._parse_magnet_links_page(response.text, movie_url)
    
    def _parse_magnet_links_page(self, html_content: str, movie_url: str) -> List[MagnetLink]:
        """解析磁力鏈接頁面"""
        soup = BeautifulSoup(html_content, 'html.parser')
        magnet_links = []
        
        # 調試：保存頁面內容
        with open('magnet_debug.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.info("已保存磁力鏈接頁面到 magnet_debug.html")
        
        # 查找磁力鏈接區域 - 嘗試多種選擇器
        magnet_section = None
        
        # 嘗試不同的選擇器
        selectors = [
            'div.magnet-links',
            'div#magnet-links', 
            'div.links',
            'div.magnet-list',
            'div.torrent-list',
            'div[class*="magnet"]',
            'div[class*="torrent"]'
        ]
        
        for selector in selectors:
            magnet_section = soup.select_one(selector)
            if magnet_section:
                self.logger.info(f"找到磁力鏈接區域: {selector}")
                break
        
        if not magnet_section:
            # 如果找不到專門的磁力鏈接區域，查找包含"複製"按鈕的區域
            copy_buttons = soup.find_all('a', string='複製')
            if copy_buttons:
                self.logger.info(f"找到 {len(copy_buttons)} 個複製按鈕")
                # 從複製按鈕向上查找父容器
                for button in copy_buttons:
                    parent = button.find_parent('div') or button.find_parent('tr')
                    if parent:
                        magnet_link = self._parse_magnet_item(parent)
                        if magnet_link:
                            magnet_links.append(magnet_link)
                return magnet_links
            else:
                self.logger.warning("未找到磁力鏈接區域和複製按鈕")
                return []
        
        # 查找磁力鏈接項目
        magnet_items = []
        
        # 嘗試不同的項目選擇器
        item_selectors = [
            'div.magnet-item',
            'div.link-item', 
            'tr',
            'div[class*="item"]',
            'div[class*="link"]'
        ]
        
        for selector in item_selectors:
            items = magnet_section.select(selector)
            if items:
                magnet_items = items
                self.logger.info(f"使用選擇器 {selector} 找到 {len(items)} 個項目")
                break
        
        if not magnet_items:
            # 如果還是找不到，查找所有包含"複製"或"下載"按鈕的div
            magnet_items = magnet_section.find_all('div', string=lambda text: text and ('複製' in text or '下載' in text))
            if not magnet_items:
                magnet_items = magnet_section.find_all('div')
        
        self.logger.info(f"開始解析 {len(magnet_items)} 個磁力鏈接項目")
        
        for i, item in enumerate(magnet_items):
            try:
                magnet_link = self._parse_magnet_item(item)
                if magnet_link:
                    magnet_links.append(magnet_link)
                    self.logger.info(f"成功解析第 {i+1} 個磁力鏈接: {magnet_link.title}")
                else:
                    self.logger.debug(f"第 {i+1} 個項目解析失敗")
            except Exception as e:
                self.logger.warning(f"解析磁力鏈接項目失敗: {e}")
                continue
        
        self.logger.info(f"總共解析出 {len(magnet_links)} 個磁力鏈接")
        return magnet_links
    
    def _parse_magnet_item(self, item) -> Optional[MagnetLink]:
        """解析磁力鏈接項目"""
        magnet = MagnetLink()
        
        # 獲取標題（通常是番號）
        title_elem = item.find('span', class_='title') or item.find('td', class_='title') or item.find('strong')
        if title_elem:
            magnet.title = clean_text(title_elem.get_text())
        
        # 獲取大小和文件數量
        size_elem = item.find('span', class_='size') or item.find('td', class_='size')
        if size_elem:
            size_text = clean_text(size_elem.get_text())
            magnet.size = size_text
            
            # 解析文件數量
            file_count_match = re.search(r'(\d+)個文件', size_text)
            if file_count_match:
                magnet.file_count = int(file_count_match.group(1))
        
        # 獲取標籤（高清、字幕等）
        tag_elem = item.find('span', class_='tag') or item.find('span', class_='label') or item.find('span', class_='badge')
        if tag_elem:
            tag_text = clean_text(tag_elem.get_text())
            if tag_text in ['高清', '字幕', 'HD', 'Subtitle', '4K', '1080p', '720p']:
                magnet.tags.append(tag_text)
        
        # 獲取複製按鈕的鏈接 - 這是重點！
        copy_button = item.find('a', class_='copy-btn') or item.find('button', class_='copy') or item.find('a', string='複製')
        if copy_button:
            magnet.copy_url = copy_button.get('href', '') or copy_button.get('data-url', '') or copy_button.get('data-clipboard-text', '')
        
        # 獲取下載按鈕的鏈接
        download_button = item.find('a', class_='download-btn') or item.find('button', class_='download') or item.find('a', string='下載')
        if download_button:
            magnet.download_url = download_button.get('href', '') or download_button.get('data-url', '')
        
        # 獲取日期
        date_elem = item.find('span', class_='date') or item.find('td', class_='date')
        if date_elem:
            magnet.date = clean_text(date_elem.get_text())
        
        # 如果沒有找到複製按鈕，嘗試從其他元素獲取磁力鏈接
        if not magnet.copy_url:
            # 查找包含磁力鏈接的元素
            magnet_link_elem = item.find('a', href=lambda x: x and x.startswith('magnet:'))
            if magnet_link_elem:
                magnet.magnet_url = magnet_link_elem.get('href', '')
                magnet.copy_url = magnet.magnet_url
        
        # 調試信息
        self.logger.info(f"解析磁力鏈接項目: 標題={magnet.title}, 大小={magnet.size}, 標籤={magnet.tags}, 複製鏈接={magnet.copy_url}")
        
        return magnet if magnet.copy_url or magnet.magnet_url else None
    
    def _extract_real_code_from_magnet(self, magnet_url: str) -> str:
        """從磁力鏈接URL中提取真實番號"""
        if not magnet_url:
            return ""
        
        # 從磁力鏈接URL中提取番號（格式：[javdb.com]ONSG-098）
        code_match = re.search(r'\[javdb\.com\]([A-Z0-9\-]+)', magnet_url)
        if code_match:
            return code_match.group(1)
        
        return ""
    
    def _filter_magnets_by_priority(self, magnet_links: List[MagnetLink]) -> List[MagnetLink]:
        """根據優先順序選擇一個最佳磁力鏈接"""
        if not magnet_links:
            return []
        
        # 優先順序：1.高清 2.字幕 3.第一個
        high_quality = []
        subtitle = []
        
        for magnet in magnet_links:
            has_high_quality = any(tag in magnet.tags for tag in ['高清', 'HD', '4K', '1080p', '720p'])
            has_subtitle = any(tag in magnet.tags for tag in ['字幕', 'Subtitle'])
            
            if has_high_quality:
                high_quality.append(magnet)
            elif has_subtitle:
                subtitle.append(magnet)
        
        # 按優先順序返回一個最佳選擇
        if high_quality:
            self.logger.info(f"選擇高清磁力鏈接: {high_quality[0].copy_url}")
            return [high_quality[0]]  # 只返回第一個高清
        elif subtitle:
            self.logger.info(f"選擇字幕磁力鏈接: {subtitle[0].copy_url}")
            return [subtitle[0]]  # 只返回第一個字幕
        else:
            self.logger.info(f"選擇第一個磁力鏈接: {magnet_links[0].copy_url}")
            return [magnet_links[0]]  # 只返回第一個
    
    def get_magnet_download_url(self, magnet_link: MagnetLink) -> Optional[str]:
        """獲取磁力鏈接的實際下載URL"""
        if magnet_link.copy_url:
            # 如果複製按鈕有直接的URL
            if magnet_link.copy_url.startswith('magnet:'):
                return magnet_link.copy_url
            
            # 如果是相對URL，轉換為絕對URL
            if not magnet_link.copy_url.startswith('http'):
                return urljoin(self.base_url, magnet_link.copy_url)
            
            return magnet_link.copy_url
        
        return magnet_link.magnet_url

class JavDBMagnetManager:
    """JavDB 磁力鏈接管理器"""
    
    def __init__(self):
        self.crawler = JavDBMagnetCrawler()
        self.logger = setup_logging()
        self.tracker = DuplicateTracker()
        self.written_urls = set()  # 用於跟踪已寫入的URL，避免重複
    
    def get_top30_magnets(self, skip_duplicates: bool = True, rank_type: str = "monthly") -> List[Dict[str, Any]]:
        """獲取有碼排行榜前30的磁力鏈接
        
        Args:
            skip_duplicates: 是否跳過已爬取的影片
            rank_type: 排行榜類型 ("monthly" 月榜)
        """
        # 只支持月榜
        if rank_type != "monthly":
            rank_type = "monthly"
            self.logger.warning("已將排行榜類型改為月榜（monthly）")
        
        return self.get_top30_monthly_with_duplicate_check() if skip_duplicates else self.crawler.get_monthly_rankings_with_magnets(30)
    
    def get_top30_monthly_with_duplicate_check(self) -> List[Dict[str, Any]]:
        """獲取前30月榜，跳過已爬取的影片（共享重複檢測）"""
        # 檢查統計信息
        stats = self.tracker.get_statistics()
        if stats['total_scraped'] > 0:
            self.logger.info(f"📊 已記錄 {stats['total_scraped']} 部影片，將自動跳過重複")
        
        self.logger.info("開始獲取有碼月榜前30的影片磁力鏈接（檢查重複）")
        
        # 1. 獲取排行榜頁面
        rankings_url = f"{self.crawler.base_url}/rankings/movies"
        params = {
            "p": "monthly",  # 月榜
            "t": "censored",  # 有碼
            "page": 1
        }
        
        response = self.crawler._make_request(rankings_url, params)
        if not response:
            self.logger.error("無法獲取排行榜頁面")
            return []
        
        # 2. 解析排行榜，獲取影片列表
        all_movies = self.crawler._parse_rankings_page(response.text, 30)
        self.logger.info(f"從月榜排行榜獲取到 {len(all_movies)} 部影片")
        
        # 3. 過濾出未爬取的影片
        new_movies, skipped_count = self.tracker.get_new_movies(all_movies)
        self.logger.info(f"✓ 跳過 {skipped_count} 部已爬取的影片")
        self.logger.info(f"✓ 剩餘 {len(new_movies)} 部新影片")
        
        if not new_movies:
            self.logger.info("沒有新影片需要爬取")
            return []
        
        # 4. 使用固定檔名，始終追加模式
        os.makedirs("magnet", exist_ok=True)
        filename = "magnet/Url List.txt"  # 固定檔名
        
        # 檢查文件是否存在，如果不存在則需要初始化 written_urls
        if not os.path.exists(filename):
            # 文件不存在，清空 written_urls（新文件）
            self.written_urls.clear()
            self.logger.info(f"創建新文件: {filename}")
        else:
            # 文件已存在，讀取現有URL到 written_urls 中（避免重複）
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_urls = [line.strip() for line in f if line.strip()]
                    self.written_urls.update(existing_urls)
                self.logger.info(f"追加到現有文件: {filename} (已有 {len(self.written_urls)} 個URL)")
            except Exception as e:
                self.logger.warning(f"讀取現有文件失敗: {e}，將繼續追加")
        
        file_mode = 'a'  # 始終使用追加模式
        
        # 檢查文件最後一行是否為今天的日期標題
        current_date = datetime.now().strftime('%Y/%m/%d')
        needs_date_header = True
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                with open(filename, 'r', encoding='utf-8') as check_file:
                    lines = check_file.readlines()
                    if lines:
                        # 從後往前找最後一個非空行
                        for line in reversed(lines):
                            last_line = line.strip()
                            if last_line:
                                # 檢查是否為今天的日期格式 YYYY/MM/DD
                                if last_line == current_date:
                                    needs_date_header = False
                                break
            except Exception:
                pass
        
        # 5. 為每部新影片獲取磁力鏈接並即時寫入
        results = []
        scraped_codes = []  # 記錄成功爬取的番號
        
        with open(filename, file_mode, encoding='utf-8') as f:
            # 如果需要，寫入日期標題
            if needs_date_header:
                f.write(f"\n{current_date}\n")
            
            for i, movie in enumerate(new_movies, 1):
                self.logger.info(f"處理第 {i}/{len(new_movies)} 部新影片: {movie['title']}")
                
                # 獲取磁力鏈接
                magnet_links = self.crawler.get_movie_magnet_links(movie['detail_url'])
                
                # 根據優先順序過濾磁力鏈接
                filtered_magnets = self.crawler._filter_magnets_by_priority(magnet_links)
                
                # 嘗試從磁力鏈接中提取真實番號
                real_code = None
                if filtered_magnets:
                    magnet = filtered_magnets[0]
                    real_code = self.crawler._extract_real_code_from_magnet(magnet.copy_url or magnet.magnet_url)
                    if real_code:
                        movie['code'] = real_code  # 更新為真實番號
                    elif not movie.get('code') or len(movie.get('code', '')) < 5:
                        # 如果沒有提取到真實番號，嘗試從標題提取
                        title = movie.get('title', '')
                        code_match = re.search(r'([A-Z]{2,6}-\d{3,5})', title)
                        if code_match:
                            extracted_code = code_match.group(1)
                            movie['code'] = extracted_code
                            real_code = extracted_code
                
                result = {
                    'rank': i,
                    'movie': movie,
                    'magnet_links': filtered_magnets,
                    'total_magnets': len(magnet_links),
                    'filtered_magnets': len(filtered_magnets)
                }
                
                results.append(result)
                
                # 即時寫入到文件（只保存URL，檢查重複）
                if filtered_magnets:
                    magnet = filtered_magnets[0]  # 只取第一個（最佳選擇）
                    url = magnet.copy_url or magnet.magnet_url
                    # 標準化URL（去除首尾空格）
                    if url:
                        url = url.strip()
                    # 檢查URL是否已經寫入過（避免重複）
                    if url and url not in self.written_urls:
                        f.write(f"{url}\n")
                        self.written_urls.add(url)  # 記錄已寫入的URL
                        # 使用真實番號記錄（如果有），否則使用原始 code
                        code_to_record = real_code or movie.get('code', '')
                        # 驗證番號格式，只記錄有效的番號
                        if code_to_record and self.tracker._is_valid_code(code_to_record):
                            scraped_codes.append(code_to_record)
                        else:
                            # 如果番號格式異常，記錄警告但繼續處理
                            if code_to_record:
                                self.logger.warning(f"跳過記錄異常格式的番號: {code_to_record} (標題: {movie.get('title', '')})")
                    elif url and url in self.written_urls:
                        self.logger.info(f"跳過重複URL: {url}")
                
                f.flush()  # 強制寫入，確保即時保存
                
                # 避免請求過於頻繁
                from utils import random_delay
                random_delay(2, 4)
        
        self.logger.info(f"磁力鏈接已即時保存到: {filename}")
        
        # 6. 標記已爬取的影片
        if scraped_codes:
            self.tracker.batch_mark_as_scraped([{'code': code} for code in scraped_codes])
            self.logger.info(f"已標記 {len(scraped_codes)} 部影片為已爬取")
        
        return results
    
    def get_magnets_by_code(self, movie_code: str) -> List[MagnetLink]:
        """根據番號獲取磁力鏈接"""
        movie_url = f"{self.crawler.base_url}/v/{movie_code}"
        return self.crawler.get_movie_magnet_links(movie_url)
    
    def export_magnets_to_file(self, results: List[Dict[str, Any]], 
                              filename: str = None) -> str:
        """導出磁力鏈接到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"magnet/javdb_magnets_{timestamp}.txt"
        
        # 確保 magnet 資料夾存在
        os.makedirs("magnet", exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("JavDB 有碼月榜前30磁力鏈接\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            # 統計信息
            total_movies = len(results)
            total_magnets = sum(result['total_magnets'] for result in results)
            filtered_magnets = sum(result['filtered_magnets'] for result in results)
            
            f.write(f"統計信息:\n")
            f.write(f"總影片數: {total_movies}\n")
            f.write(f"總磁力鏈接數: {total_magnets}\n")
            f.write(f"過濾後磁力鏈接數: {filtered_magnets}\n")
            f.write(f"成功率: {filtered_magnets/total_magnets*100:.1f}%\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("磁力鏈接列表\n")
            f.write("=" * 80 + "\n\n")
            
            for result in results:
                movie = result['movie']
                f.write(f"排名: {result['rank']}\n")
                f.write(f"番號: {movie['code']}\n")
                f.write(f"標題: {movie['title']}\n")
                f.write(f"演員: {', '.join(movie['actors'])}\n")
                f.write(f"評分: {movie['score']}\n")
                f.write(f"總磁力鏈接: {result['total_magnets']} 個\n")
                f.write(f"過濾後磁力鏈接: {result['filtered_magnets']} 個\n")
                
                if result['magnet_links']:
                    f.write("磁力鏈接:\n")
                    for i, magnet in enumerate(result['magnet_links'], 1):
                        f.write(f"  {i}. {magnet.title}\n")
                        f.write(f"     大小: {magnet.size}\n")
                        f.write(f"     標籤: {', '.join(magnet.tags)}\n")
                        f.write(f"     下載鏈接: {magnet.copy_url or magnet.magnet_url}\n")
                        f.write(f"     日期: {magnet.date}\n")
                        f.write("\n")
                else:
                    f.write("無符合條件的磁力鏈接\n")
                
                f.write("-" * 80 + "\n\n")
            
            # 在文件末尾添加純磁力鏈接列表
            f.write("=" * 80 + "\n")
            f.write("純磁力鏈接列表（方便複製）\n")
            f.write("=" * 80 + "\n\n")
            
            magnet_count = 0
            for result in results:
                if result['magnet_links']:
                    for magnet in result['magnet_links']:
                        magnet_count += 1
                        f.write(f"{magnet_count}. {magnet.copy_url or magnet.magnet_url}\n")
            
            f.write(f"\n總共 {magnet_count} 個磁力鏈接\n")
        
        self.logger.info(f"磁力鏈接已導出到: {filename}")
        return filename
    
    def get_summary_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """獲取統計摘要"""
        total_movies = len(results)
        total_magnets = sum(result['total_magnets'] for result in results)
        filtered_magnets = sum(result['filtered_magnets'] for result in results)
        
        movies_with_magnets = sum(1 for result in results if result['filtered_magnets'] > 0)
        
        return {
            'total_movies': total_movies,
            'total_magnets': total_magnets,
            'filtered_magnets': filtered_magnets,
            'movies_with_magnets': movies_with_magnets,
            'success_rate': movies_with_magnets / total_movies if total_movies > 0 else 0
        }

