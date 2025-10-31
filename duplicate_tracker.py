"""
重複追蹤系統
用於記錄已爬取的影片，避免重複保存
"""
import json
import os
from typing import List, Dict, Any, Set
from datetime import datetime
from pathlib import Path


class DuplicateTracker:
    """重複追蹤器"""
    
    def __init__(self, db_file: str = "scraped_movies.json"):
        self.db_file = db_file
        self.scraped_data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """載入已爬取的數據"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 載入後檢查並清理舊記錄
                    if 'scraped_movies' in data:
                        scraped_count = len(data['scraped_movies'])
                        if scraped_count > 300:
                            # 按照時間排序並保留最新300筆
                            sorted_items = sorted(
                                data['scraped_movies'].items(),
                                key=lambda x: x[1]
                            )
                            data['scraped_movies'] = dict(sorted_items[-300:])
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
        self.scraped_data['last_update'] = datetime.now().isoformat()
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
    
    def is_already_scraped(self, movie_code: str) -> bool:
        """檢查影片是否已經爬取過"""
        return movie_code in self.scraped_data.get('scraped_movies', {})
    
    def mark_as_scraped(self, movie_code: str, scraped_date: str = None):
        """標記影片為已爬取"""
        if scraped_date is None:
            scraped_date = datetime.now().isoformat()
        
        if 'scraped_movies' not in self.scraped_data:
            self.scraped_data['scraped_movies'] = {}
        
        self.scraped_data['scraped_movies'][movie_code] = scraped_date
    
    def get_new_movies(self, movies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """過濾出新影片（未爬取過的）"""
        new_movies = []
        scraped_count = 0
        
        for movie in movies:
            movie_code = movie.get('code', '')
            if movie_code and not self.is_already_scraped(movie_code):
                new_movies.append(movie)
            else:
                scraped_count += 1
        
        return new_movies, scraped_count
    
    def batch_mark_as_scraped(self, movies: List[Dict[str, Any]]):
        """批量標記影片為已爬取"""
        for movie in movies:
            movie_code = movie.get('code', '')
            if movie_code:
                self.mark_as_scraped(movie_code)
        
        # 保存數據
        self.save_data()
        
        # 檢查並清理舊記錄（保持最多300筆）
        self._auto_cleanup(max_records=300)
    
    def _auto_cleanup(self, max_records: int = 300):
        """自動清理舊記錄，保持最多指定數量"""
        if 'scraped_movies' not in self.scraped_data:
            return
        
        scraped_movies = self.scraped_data['scraped_movies']
        total_count = len(scraped_movies)
        
        if total_count <= max_records:
            return  # 不需要清理
        
        # 按照時間排序（舊的在前）
        sorted_items = sorted(
            scraped_movies.items(),
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
        
        # 輸出清理信息（這會在下次載入時被看到）
        import logging
        logging.info(f"自動清理記錄：刪除了 {deleted_count} 筆舊記錄，保留最新 {max_records} 筆")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        scraped_movies = self.scraped_data.get('scraped_movies', {})
        return {
            'total_scraped': len(scraped_movies),
            'last_update': self.scraped_data.get('last_update'),
            'recent_scraped': list(scraped_movies.keys())[-10:] if scraped_movies else [],
            'max_records': 300  # 最大記錄數
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

