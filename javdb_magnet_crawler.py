"""
JavDB 磁力鏈接專用爬蟲
專門用於獲取有碼月榜前30的磁力鏈接下載位置
"""
import time
import random
import re
import os
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
from datetime import datetime

# 使用 curl_cffi 模擬 Chrome TLS 指紋以通過 Cloudflare（requests 會被 403）
try:
    from curl_cffi import requests as cffi_requests
    _USE_CFFI = True
except ImportError:
    import requests as cffi_requests
    _USE_CFFI = False
import requests  # 仍用於 RequestException 等

# 403 時改用 Playwright 真實瀏覽器取得頁面（需 pip install playwright && playwright install chromium）
try:
    from playwright.sync_api import sync_playwright
    _USE_PLAYWRIGHT = True
except ImportError:
    _USE_PLAYWRIGHT = False


class _FakeResponse:
    """供解析用的簡易 response，僅含 .text / .status_code / .url"""
    __slots__ = ("text", "status_code", "url")
    def __init__(self, text: str, status_code: int = 200, url: str = ""):
        self.text = text
        self.status_code = status_code
        self.url = url

# 固定桌面 Chrome UA，避免 Cloudflare 因隨機/行動 UA 回傳 403
FIXED_CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# 年齡驗證：點「是,我已滿18歲」時瀏覽器會請求此 URL，伺服器 302 並設定 cookie
OVER18_URL = "/over18?respond=1"
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
        if _USE_CFFI:
            self.session = cffi_requests.Session(impersonate="chrome")
        else:
            self.session = requests.Session()
        self.logger = setup_logging()
        self._setup_session()
        if _USE_CFFI:
            self.logger.info("使用 curl_cffi 模擬 Chrome TLS（impersonate=chrome）")
        else:
            self.logger.warning("未安裝 curl_cffi，使用 requests，可能遭遇 403，請執行: pip install curl_cffi")
        if _USE_PLAYWRIGHT:
            self.logger.info("Playwright 備援已啟用（403 時將用真實瀏覽器取得頁面）")
        else:
            self.logger.info("若持續 403，可安裝 Playwright 備援: pip install playwright 後執行 playwright install chromium")
    
    def _setup_session(self):
        """設置會話"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://javdb.com/",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "Sec-GPC": "1"
        })
        # JavDB 18 歲確認：直接帶入 over18=1，無需先請求 over18 頁面
        self.session.cookies.set("over18", "1", domain="javdb.com", path="/")
    
    def _fetch_with_playwright(self, full_url: str) -> Optional[_FakeResponse]:
        """403 時用真實瀏覽器取得頁面。需安裝 playwright 並執行 playwright install chromium。"""
        if not _USE_PLAYWRIGHT:
            return None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    locale="zh-TW",
                    viewport={"width": 1280, "height": 720},
                )
                context.add_cookies([{"name": "over18", "value": "1", "domain": "javdb.com", "path": "/"}])
                page = context.new_page()
                page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                # 若有年齡驗證彈窗，點「是,我已滿18歲」
                try:
                    btn = page.get_by_role("button", name="是")
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                html = page.content()
                browser.close()
                return _FakeResponse(html, 200, full_url)
        except Exception as e:
            self.logger.warning(f"Playwright 備援失敗: {e}")
            return None
    
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                     retries: int = 3, skip_ua_rotation: bool = False,
                     extra_headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
        """發送HTTP請求。skip_ua_rotation=True 時不更換 UA（用於先訪首頁再請求排行榜以通過 Cloudflare）。"""
        for attempt in range(retries + 1):
            try:
                # 隨機延遲
                if attempt > 0:
                    random_delay(2, 5)
                
                # 更新User-Agent（若未要求固定 UA）
                if not skip_ua_rotation:
                    self.session.headers['User-Agent'] = get_random_user_agent()
                req_headers = {'Accept-Encoding': 'gzip, deflate'}
                if extra_headers:
                    req_headers.update(extra_headers)
                # 每次請求都明確帶上 over18，確保 curl_cffi 的 cookie jar 有送出
                req_cookies = {"over18": "1"}
                response = self.session.get(
                    url,
                    params=params,
                    timeout=30,
                    allow_redirects=True,
                    headers=req_headers,
                    cookies=req_cookies
                )
                
                response.raise_for_status()
                # 請求間隔 - 增加延遲以降低被封鎖的風險
                random_delay(2, 4)  # 從 1-3秒 增加到 2-4秒
                
                return response
                
            except Exception as e:
                self.logger.warning(f"請求失敗 (嘗試 {attempt + 1}/{retries + 1}): {e}")
                
                if attempt == retries:
                    # 若為 403 且已安裝 Playwright，改用真實瀏覽器取得頁面
                    err_resp = getattr(e, "response", None)
                    if err_resp is not None and err_resp.status_code == 403 and _USE_PLAYWRIGHT:
                        full_url = url + ("?" + urlencode(params)) if params else url
                        self.logger.info("收到 403，嘗試使用 Playwright 真實瀏覽器取得頁面...")
                        pw_resp = self._fetch_with_playwright(full_url)
                        if pw_resp is not None:
                            self.logger.info("Playwright 取得頁面成功")
                            return pw_resp
                    self.logger.error(f"請求最終失敗: {url}")
                    return None
                
                # 指數退避
                time.sleep(2 ** attempt)
        
        return None
    
    def get_monthly_rankings_with_magnets(self, limit: int = 30) -> List[Dict[str, Any]]:
        """獲取有碼月榜前30的影片及其磁力鏈接"""
        self.logger.info(f"開始獲取有碼月榜前{limit}的影片磁力鏈接")
        
        # 直接請求排行榜（已帶 over18=1 cookie 與 Chrome TLS），不再先訪首頁避免觸發 403
        self.session.headers['User-Agent'] = FIXED_CHROME_UA
        # 1. 獲取排行榜頁面
        rankings_url = f"{self.base_url}/rankings/movies"
        params = {
            "p": "monthly",  # 月榜
            "t": "censored",  # 有碼
            "page": 1
        }
        response = self._make_request(
            rankings_url, params,
            skip_ua_rotation=True,
            extra_headers={"Referer": self.base_url + "/"}
        )
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
    
    def search_movie_by_code(self, movie_code: str) -> Optional[str]:
        """通過番號搜索找到正確的影片 URL
        
        Returns:
            找到的影片詳情頁 URL，如果未找到則返回 None
        """
        search_url = f"{self.base_url}/search"
        params = {"q": movie_code}
        
        response = self._make_request(search_url, params)
        if not response:
            self.logger.error(f"無法獲取搜索頁面: {search_url}")
            return None
        
        # 解析搜索結果，找到第一個匹配的影片
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 嘗試多種選擇器來找到影片項目（與排行榜類似）
        movie_items = soup.find_all('div', class_='item')
        if not movie_items:
            movie_items = soup.find_all('div', class_='movie-item')
        if not movie_items:
            movie_items = soup.find_all('div', class_='video-item')
        
        # 遍歷搜索結果，找到包含目標番號的影片
        for item in movie_items:
            link_elem = item.find('a')
            if not link_elem:
                continue
            
            detail_url = urljoin(self.base_url, link_elem.get('href', ''))
            
            # 嘗試解析影片項目獲取番號（如果可用）
            movie_data = self._parse_movie_item(item, 0)
            if movie_data:
                # 檢查標題或代碼是否包含目標番號
                code_in_title = movie_code.upper() in (movie_data.get('code', '') or '').upper()
                code_in_title_text = movie_code.upper() in (movie_data.get('title', '') or '').upper()
                
                # 如果找到匹配的番號，返回該影片的 URL
                if code_in_title or code_in_title_text:
                    self.logger.info(f"通過搜索找到影片: {detail_url} (番號: {movie_data.get('code', '')})")
                    return detail_url
            else:
                # 如果無法解析，至少返回第一個結果的 URL（通常搜索結果的第一個最相關）
                if item == movie_items[0]:
                    self.logger.info(f"返回搜索結果第一個影片: {detail_url}")
                    return detail_url
        
        # 如果沒有找到匹配項，但搜索結果存在，返回第一個結果
        if movie_items:
            link_elem = movie_items[0].find('a')
            if link_elem:
                detail_url = urljoin(self.base_url, link_elem.get('href', ''))
                self.logger.warning(f"未找到精確匹配，返回搜索結果第一個影片: {detail_url}")
                return detail_url
        
        self.logger.warning(f"未找到番號 {movie_code} 的影片")
        return None
    
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
        error_indicators = ['驗證碼', '登錄', '請登入', '需要登錄', 'captcha', 'login', '請稍後再試', '訪問過於頻繁']
        page_text_lower = html_content.lower()
        
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
                if magnet_links:
                    return magnet_links
            
            # 如果還是找不到，嘗試從HTML中直接提取magnet鏈接（使用正則表達式）
            self.logger.warning("未找到磁力鏈接區域和複製按鈕，嘗試從HTML中直接提取")
            magnet_pattern = r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"\s<>]*'
            found_magnets = re.findall(magnet_pattern, html_content)
            if found_magnets:
                self.logger.info(f"從HTML中直接提取到 {len(found_magnets)} 個磁力鏈接")
                for magnet_url in found_magnets[:10]:  # 最多取前10個，避免過多
                    # 創建一個簡單的MagnetLink對象
                    magnet_link = MagnetLink()
                    magnet_link.title = f"磁力鏈接 {len(magnet_links) + 1}"
                    magnet_link.magnet_url = magnet_url
                    magnet_link.copy_url = magnet_url
                    magnet_link.size = "未知"
                    magnet_link.tags = []
                    magnet_link.file_count = 0
                    magnet_link.date = ""
                    magnet_links.append(magnet_link)
                    self.logger.info(f"成功提取磁力鏈接: {magnet_url[:50]}...")
            
            if not magnet_links:
                self.logger.warning("無法從頁面中提取任何磁力鏈接")
                for ind in error_indicators:
                    if ind.lower() in page_text_lower:
                        self.logger.warning(f"頁面可能包含錯誤提示（{ind}），網站可能限制了訪問")
                        break
                return []
            return magnet_links
        
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
        if not magnet_links:
            for ind in error_indicators:
                if ind.lower() in page_text_lower:
                    self.logger.warning(f"頁面可能包含錯誤提示（{ind}），網站可能限制了訪問")
                    break
        return magnet_links
    
    def _parse_magnet_item(self, item) -> Optional[MagnetLink]:
        """解析磁力鏈接項目"""
        magnet = MagnetLink()
        
        # 獲取複製按鈕的鏈接 - 這是重點！優先獲取
        copy_button = item.find('a', class_='copy-btn') or item.find('button', class_='copy') or item.find('a', string='複製') or item.find('a', class_='copy')
        if copy_button:
            magnet.copy_url = copy_button.get('href', '') or copy_button.get('data-url', '') or copy_button.get('data-clipboard-text', '') or copy_button.get('data-clipboard', '')
        
        # 如果沒有找到複製按鈕，嘗試從其他元素獲取磁力鏈接
        if not magnet.copy_url:
            # 查找包含磁力鏈接的元素
            magnet_link_elem = item.find('a', href=lambda x: x and x.startswith('magnet:'))
            if magnet_link_elem:
                magnet.magnet_url = magnet_link_elem.get('href', '')
                magnet.copy_url = magnet.magnet_url
        
        # 如果還是沒有找到，嘗試從文本內容中提取磁力鏈接
        if not magnet.copy_url:
            item_text = item.get_text()
            # 改進正則表達式以匹配完整的磁力鏈接（包括所有參數）
            magnet_match = re.search(r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"\s<>]*', item_text)
            if magnet_match:
                magnet.copy_url = magnet_match.group(0)
                magnet.magnet_url = magnet.copy_url
        
        # 從磁力鏈接中提取標題（從 dn 參數）- 優先提取標題
        if magnet.copy_url:
            # 使用更寬鬆的正則表達式來匹配 dn 參數（可能包含 URL 編碼的特殊字符）
            dn_match = re.search(r'dn=([^&]+)', magnet.copy_url, re.IGNORECASE)
            if not dn_match:
                # 如果第一個正則沒匹配到，嘗試匹配包含更多字符的版本
                dn_match = re.search(r'dn=([^&"\s<>]+)', magnet.copy_url, re.IGNORECASE)
            if dn_match:
                dn_value = dn_match.group(1)
                # URL 解碼
                from urllib.parse import unquote
                try:
                    decoded_dn = unquote(dn_value)
                    # 提取番號（例如：[javdb.com]JUR-496-C.torrent -> JUR-496-C）
                    code_match = re.search(r'\[javdb\.com\]([A-Z0-9\-]+)', decoded_dn, re.IGNORECASE)
                    if code_match:
                        magnet.title = code_match.group(1)
                    else:
                        # 如果沒有 [javdb.com] 前綴，直接使用解碼後的值（去掉 .torrent 等後綴）
                        magnet.title = decoded_dn.replace('.torrent', '').replace('.mkv', '').replace('.mp4', '')
                except Exception as e:
                    magnet.title = dn_value.replace('.torrent', '').replace('.mkv', '').replace('.mp4', '')
        
        # 獲取標題（通常是番號）- 嘗試多種選擇器
        if not magnet.title:
            title_elem = (item.find('span', class_='title') or 
                         item.find('td', class_='title') or 
                         item.find('strong') or
                         item.find('div', class_='title') or
                         item.find('p', class_='title') or
                         item.find('a', class_='title'))
            if title_elem:
                magnet.title = clean_text(title_elem.get_text())
        
        # 獲取大小和文件數量 - 嘗試多種選擇器
        size_elem = (item.find('span', class_='size') or 
                    item.find('td', class_='size') or
                    item.find('div', class_='size') or
                    item.find('span', class_='file-size') or
                    item.find('td', string=re.compile(r'\d+\.?\d*\s*(GB|MB|KB|TB)', re.IGNORECASE)))
        if size_elem:
            size_text = clean_text(size_elem.get_text())
            magnet.size = size_text
            
            # 解析文件數量
            file_count_match = re.search(r'(\d+)個文件', size_text)
            if file_count_match:
                magnet.file_count = int(file_count_match.group(1))
        
        # 如果大小仍然為空，嘗試從文本中提取
        if not magnet.size:
            item_text = item.get_text()
            size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB|KB|TB)', item_text, re.IGNORECASE)
            if size_match:
                magnet.size = f"{size_match.group(1)} {size_match.group(2).upper()}"
        
        # 獲取標籤（高清、字幕等）- 嘗試多種選擇器
        tag_elems = (item.find_all('span', class_='tag') or 
                    item.find_all('span', class_='label') or 
                    item.find_all('span', class_='badge') or
                    item.find_all('div', class_='tag') or
                    item.find_all('a', class_='tag'))
        for tag_elem in tag_elems:
            tag_text = clean_text(tag_elem.get_text())
            if tag_text in ['高清', '字幕', 'HD', 'Subtitle', '4K', '1080p', '720p', '中文', 'Chinese']:
                if tag_text not in magnet.tags:
                    magnet.tags.append(tag_text)
        
        # 如果沒有找到標籤元素，嘗試從文本中識別
        if not magnet.tags:
            item_text = item.get_text()
            if any(keyword in item_text for keyword in ['高清', 'HD', '4K', '1080p', '720p']):
                magnet.tags.append('高清')
            if any(keyword in item_text for keyword in ['字幕', 'Subtitle', '中文', 'Chinese']):
                magnet.tags.append('字幕')
        
        # 獲取下載按鈕的鏈接
        download_button = item.find('a', class_='download-btn') or item.find('button', class_='download') or item.find('a', string='下載')
        if download_button:
            magnet.download_url = download_button.get('href', '') or download_button.get('data-url', '')
        
        # 獲取日期 - 嘗試多種選擇器
        date_elem = (item.find('span', class_='date') or 
                    item.find('td', class_='date') or
                    item.find('div', class_='date') or
                    item.find('time') or
                    item.find('span', class_='time'))
        if date_elem:
            magnet.date = clean_text(date_elem.get_text())
        
        # 解析文件數量（如果還沒解析到）
        if magnet.file_count == 0:
            item_text = item.get_text()
            file_count_match = re.search(r'(\d+)個文件', item_text)
            if file_count_match:
                magnet.file_count = int(file_count_match.group(1))
        
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
    
    def get_top30_magnets(self, skip_duplicates: bool = True, rank_type: str = "monthly", limit: int = None) -> List[Dict[str, Any]]:
        """獲取有碼排行榜前N的磁力鏈接
        
        Args:
            skip_duplicates: 是否跳過已爬取的影片
            rank_type: 排行榜類型 ("monthly" 月榜)
            limit: 下載數量（如果為None，則從配置文件讀取）
        """
        # 只支持月榜
        if rank_type != "monthly":
            rank_type = "monthly"
            self.logger.warning("已將排行榜類型改為月榜（monthly）")
        
        # 從環境變數讀取 limit（如果未提供）
        if limit is None:
            import os
            from dotenv import load_dotenv
            load_dotenv('config.env')
            top_count_raw = os.getenv('TOP_COUNT', '30')
            limit = int(top_count_raw)
        
        return self.get_top30_monthly_with_duplicate_check(limit=limit) if skip_duplicates else self.crawler.get_monthly_rankings_with_magnets(limit)
    
    def get_top30_monthly_with_duplicate_check(self, limit: int = 30) -> List[Dict[str, Any]]:
        """獲取前N月榜，跳過已爬取的影片（共享重複檢測）"""
        # 檢查統計信息
        stats = self.tracker.get_statistics()
        if stats['total_scraped'] > 0:
            self.logger.info(f"📊 已記錄 {stats['total_scraped']} 部影片，將自動跳過重複")
        else:
            # 如果 scraped_movies.json 不存在或為空，清空 written_urls 以確保一致性
            # 這樣可以避免因為舊的 url_list_monthly.txt 導致誤判重複
            self.written_urls.clear()
            self.logger.info("📋 檢測到無歷史記錄，已清空URL重複檢查列表")
        
        self.logger.info(f"開始獲取有碼月榜前{limit}的影片磁力鏈接（檢查重複）")
        
        # 直接請求排行榜（已帶 over18=1 cookie 與 Chrome TLS）
        self.crawler.session.headers['User-Agent'] = FIXED_CHROME_UA
        # 1. 獲取排行榜頁面
        rankings_url = f"{self.crawler.base_url}/rankings/movies"
        params = {
            "p": "monthly",  # 月榜
            "t": "censored",  # 有碼
            "page": 1
        }
        response = self.crawler._make_request(
            rankings_url, params,
            skip_ua_rotation=True,
            extra_headers={"Referer": self.crawler.base_url + "/"}
        )
        if not response:
            self.logger.error("無法獲取排行榜頁面")
            return []
        
        # 2. 解析排行榜，獲取影片列表
        all_movies = self.crawler._parse_rankings_page(response.text, limit)
        self.logger.info(f"從月榜排行榜獲取到 {len(all_movies)} 部影片")
        
        # 3. 過濾出未爬取的影片
        new_movies, skipped_count = self.tracker.get_new_movies(all_movies)
        self.logger.info(f"✓ 跳過 {skipped_count} 部已爬取的影片")
        self.logger.info(f"✓ 剩餘 {len(new_movies)} 部新影片")
        if not new_movies:
            self.logger.info("沒有新影片需要爬取")
            return []
        
        # 4. 使用固定檔名（月榜專用），始終追加模式
        os.makedirs("magnet", exist_ok=True)
        filename = "magnet/url_list_monthly.txt"
        
        # 檢查文件是否存在，如果不存在則需要初始化 written_urls
        # 注意：如果 scraped_movies.json 不存在（已在上方清空 written_urls），
        # 這裡不再從 url_list_monthly.txt 讀取 URL，確保一致性
        if not os.path.exists(filename):
            # 文件不存在，清空 written_urls（新文件）
            self.written_urls.clear()
            self.logger.info(f"創建新文件: {filename}")
        else:
            # 文件已存在，但只有在 scraped_movies.json 也存在時才讀取現有URL
            # 這樣可以避免因為只有 url_list_monthly.txt 而誤判重複
            scraped_movies_exists = os.path.exists(self.tracker.db_file)
            if scraped_movies_exists:
                # 文件已存在，讀取現有URL到 written_urls 中（避免重複）
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        existing_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('20')]  # 過濾掉日期標題行
                        self.written_urls.update(existing_urls)
                    self.logger.info(f"追加到現有文件: {filename} (已有 {len(self.written_urls)} 個URL)")
                except Exception as e:
                    self.logger.warning(f"讀取現有文件失敗: {e}，將繼續追加")
            else:
                # scraped_movies.json 不存在，不清除 written_urls（已在上面清空）
                # 但也不從 url_list_monthly.txt 讀取，確保一致性
                self.logger.info(f"檢測到 {filename} 存在但 scraped_movies.json 不存在，忽略月榜檔中的舊URL以確保一致性")
        
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
                
                # 使用真實番號記錄（如果有），否則使用原始 code
                code_to_record = real_code or movie.get('code', '')
                
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
                    elif url and url in self.written_urls:
                        self.logger.info(f"跳過重複URL: {url}")
                
                # 無論是否有磁力鏈接，只要有有效的番號就記錄為已處理（避免重複爬取）
                # 驗證番號格式，只記錄有效的番號，並立即寫入到 scraped_movies.json
                if code_to_record and self.tracker._is_valid_code(code_to_record):
                    self.tracker.mark_and_save(code_to_record)  # 即時寫入
                    scraped_codes.append(code_to_record)  # 保留用於統計
                    if not filtered_magnets:
                        self.logger.info(f"影片 {code_to_record} 沒有找到磁力鏈接，但已記錄為已處理")
                else:
                    # 如果番號格式異常，記錄警告但繼續處理
                    if code_to_record:
                        self.logger.warning(f"跳過記錄異常格式的番號: {code_to_record} (標題: {movie.get('title', '')})")
                
                f.flush()  # 強制寫入，確保即時保存
                
                # 避免請求過於頻繁 - 增加延遲時間以降低被封鎖的風險（使用模組頂層導入的 random_delay）
                if not filtered_magnets:
                    self.logger.warning(f"影片 {movie.get('title', '')} 未找到磁力鏈接，延遲更長時間...")
                    random_delay(5, 8)  # 延長到5-8秒
                else:
                    random_delay(3, 6)  # 正常情況延遲3-6秒（從2-4秒增加）
        
        self.logger.info(f"磁力鏈接已即時保存到: {filename}")
        
        # 6. 已爬取的影片已通過 mark_and_save 即時寫入，這裡只記錄統計信息
        if scraped_codes:
            self.logger.info(f"已標記 {len(scraped_codes)} 部影片為已爬取（已即時保存到 scraped_movies.json）")
        
        return results
    
    def get_magnets_by_code(self, movie_code: str) -> List[MagnetLink]:
        """根據番號獲取磁力鏈接"""
        # 先通過搜索找到正確的影片 URL（包含正確的 ID）
        movie_url = self.crawler.search_movie_by_code(movie_code)
        
        if not movie_url:
            self.logger.error(f"無法找到番號 {movie_code} 的影片")
            return []
        
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

