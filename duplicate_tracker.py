"""
重複追蹤系統
用於記錄已爬取的影片，避免重複保存
"""
import json
import os
import re
from typing import List, Dict, Any, Set
from datetime import datetime


class DuplicateTracker:
    """重複追蹤器（以基礎番號去重：同一番號的 -C/-UC/-U 等版本視為同一部）"""
    
    def __init__(self, db_file: str = "scraped_movies.json"):
        self.db_file = db_file
        self.max_records = 10000  # 改為 10000 筆
        self.scraped_data = self._load_data()
    
    def _to_base_code(self, code: str) -> str:
        """將番號正規化為基礎番號（同一作品不同版本如 -C/-UC/-U 視為同一部）
        例如：MIDA-348-C、MIDA-348-UC -> MIDA-348；SSIS-886-C -> SSIS-886
        """
        if not code or '-' not in code:
            return code
        parts = code.split('-')
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1]}"
        return code

    def _is_valid_code(self, code: str) -> bool:
        """驗證番號格式是否正確"""
        if not code or len(code) < 4:
            return False
        # 正常番號應該包含連字號，例如：SSIS-886-C, JUR-496, 300MIUM-1273
        # 允許格式：字母或數字字母+連字號+數字（可能還有後綴）
        if '-' in code:
            # 檢查是否符合常見番號格式：XX-XXX 或 XX-XXX-C 或 300MIUM-1273
            parts = code.split('-')
            if len(parts) >= 2:
                # 第一部分應該包含字母（可以是純字母或數字字母），第二部分應該是數字
                first_part = parts[0]
                second_part = parts[1]
                # 檢查：第一部分至少包含一個字母，第二部分至少包含一個數字
                if any(c.isalpha() for c in first_part) and any(c.isdigit() for c in second_part):
                    return True
        # 如果沒有連字號，視為異常格式，返回 False
        # 因為正常番號格式都包含連字號
        return False
    
    def _load_data(self) -> Dict[str, Any]:
        """載入已爬取的數據"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 載入後檢查並清理舊記錄
                    if 'scraped_movies' in data:
                        scraped_movies = data['scraped_movies']
                        
                        # 1. 先過濾掉格式異常的番號，並以「基礎番號」合併（同番號不同版本只保留一筆）
                        valid_movies = {}
                        invalid_codes = []
                        for code, date in scraped_movies.items():
                            if self._is_valid_code(code):
                                base = self._to_base_code(code)
                                # 同一基礎番號保留較新的日期
                                if base not in valid_movies or (date and date > valid_movies.get(base, '')):
                                    valid_movies[base] = date
                            else:
                                invalid_codes.append(code)
                        
                        if invalid_codes:
                            import logging
                            logging.info(f"清理了 {len(invalid_codes)} 個異常格式的番號: {invalid_codes[:10]}")
                        
                        # 2. 檢查數量，如果超過 max_records 則按時間清理
                        if len(valid_movies) > self.max_records:
                            # 按照時間排序並保留最新 max_records 筆
                            sorted_items = sorted(
                                valid_movies.items(),
                                key=lambda x: x[1]
                            )
                            valid_movies = dict(sorted_items[-self.max_records:])
                            import logging
                            logging.info(f"已清理舊記錄，保留最新 {self.max_records} 筆")
                        
                        data['scraped_movies'] = valid_movies
                        # 立即保存清理後的數據
                        with open(self.db_file, 'w', encoding='utf-8') as save_file:
                            json.dump(data, save_file, ensure_ascii=False, indent=2)
                    return data
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return {
            'scraped_movies': {},  # movie_code -> scraped_date
            'last_update': None
        }
    
    def save_data(self):
        """保存數據"""
        try:
            self.scraped_data['last_update'] = datetime.now().isoformat()
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise
    
    def is_already_scraped(self, movie_code: str) -> bool:
        """檢查影片是否已經爬取過（以基礎番號判斷，同一番號不同版本 -C/-UC/-U 視為已爬取）"""
        if not self._is_valid_code(movie_code):
            return False
        base = self._to_base_code(movie_code)
        return base in self.scraped_data.get('scraped_movies', {})
    
    def mark_as_scraped(self, movie_code: str, scraped_date: str = None):
        """標記影片為已爬取（以基礎番號儲存，同一番號不同版本只記一筆）"""
        if not self._is_valid_code(movie_code):
            import logging
            logging.warning(f"跳過記錄異常格式的番號: {movie_code}")
            return
        
        if scraped_date is None:
            scraped_date = datetime.now().isoformat()
        
        if 'scraped_movies' not in self.scraped_data:
            self.scraped_data['scraped_movies'] = {}
        
        base = self._to_base_code(movie_code)
        self.scraped_data['scraped_movies'][base] = scraped_date
    
    def mark_and_save(self, movie_code: str, scraped_date: str = None):
        """標記影片為已爬取並立即保存到文件"""
        self.mark_as_scraped(movie_code, scraped_date)
        self.save_data()
    
    def get_new_movies(self, movies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """過濾出新影片（未爬取過的）"""
        new_movies = []
        scraped_count = 0
        
        for movie in movies:
            movie_code = movie.get('code', '')
            # 只檢查有效格式的番號
            if movie_code and self._is_valid_code(movie_code):
                if not self.is_already_scraped(movie_code):
                    new_movies.append(movie)
                else:
                    scraped_count += 1
            else:
                # 無效格式的番號視為新影片（會嘗試重新提取正確的番號）
                new_movies.append(movie)
        
        return new_movies, scraped_count
    
    def batch_mark_as_scraped(self, movies: List[Dict[str, Any]]):
        """批量標記影片為已爬取"""
        for movie in movies:
            movie_code = movie.get('code', '')
            if movie_code:
                self.mark_as_scraped(movie_code)
        
        # 保存數據
        self.save_data()
        
        # 檢查並清理舊記錄（保持最多 max_records 筆）
        self._auto_cleanup(max_records=self.max_records)
    
    def _auto_cleanup(self, max_records: int = 10000):
        """自動清理舊記錄，保持最多指定數量"""
        if 'scraped_movies' not in self.scraped_data:
            return
        
        scraped_movies = self.scraped_data['scraped_movies']
        
        # 1. 先過濾掉格式異常的番號
        valid_movies = {}
        for code, date in scraped_movies.items():
            if self._is_valid_code(code):
                valid_movies[code] = date
        
        total_count = len(valid_movies)
        invalid_count = len(scraped_movies) - total_count
        
        if invalid_count > 0:
            import logging
            logging.info(f"清理了 {invalid_count} 個異常格式的番號")
        
        # 2. 檢查數量
        if total_count <= max_records:
            # 更新為清理後的數據
            self.scraped_data['scraped_movies'] = valid_movies
            if invalid_count > 0:
                self.save_data()
            return  # 不需要清理
        
        # 按照時間排序（舊的在前）
        sorted_items = sorted(
            valid_movies.items(),
            key=lambda x: x[1]  # 按照日期排序
        )
        
        # 保留最新的 max_records 筆
        items_to_keep = sorted_items[-max_records:]
        
        # 刪除的數量
        deleted_count = total_count - max_records
        
        # 更新數據
        self.scraped_data['scraped_movies'] = dict(items_to_keep)
        
        # 保存
        self.save_data()
        
        # 輸出清理信息
        import logging
        logging.info(f"自動清理記錄：刪除了 {deleted_count} 筆舊記錄，保留最新 {max_records} 筆")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        scraped_movies = self.scraped_data.get('scraped_movies', {})
        # 統計有效和無效的番號
        valid_count = sum(1 for code in scraped_movies.keys() if self._is_valid_code(code))
        invalid_count = len(scraped_movies) - valid_count
        
        return {
            'total_scraped': len(scraped_movies),
            'valid_scraped': valid_count,
            'invalid_scraped': invalid_count,
            'last_update': self.scraped_data.get('last_update'),
            'recent_scraped': list(scraped_movies.keys())[-10:] if scraped_movies else [],
            'max_records': self.max_records
        }
    
    def clear_old_records(self, days: int = 7):
        """清理指定天數之前的記錄"""
        from datetime import timedelta
        
        if 'scraped_movies' not in self.scraped_data:
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        movies_to_delete = []
        for movie_code, scraped_date_str in self.scraped_data['scraped_movies'].items():
            try:
                scraped_date = datetime.fromisoformat(scraped_date_str)
                if scraped_date < cutoff_date:
                    movies_to_delete.append(movie_code)
            except (ValueError, TypeError):
                # 如果有無法解析的日期，也刪除
                movies_to_delete.append(movie_code)
        
        for movie_code in movies_to_delete:
            del self.scraped_data['scraped_movies'][movie_code]
            deleted_count += 1
        
        if deleted_count > 0:
            self.save_data()
        
        return deleted_count

