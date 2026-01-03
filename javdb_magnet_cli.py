"""
JavDB 磁力鏈接專用CLI工具
專門用於獲取有碼月榜前30的磁力鏈接下載位置
"""
import argparse
import json
import csv
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm

from javdb_magnet_crawler import JavDBMagnetManager, MagnetLink

class JavDBMagnetCLI:
    """JavDB 磁力鏈接命令行界面"""
    
    def __init__(self):
        self.console = Console()
        self.manager = JavDBMagnetManager()
    
    def run(self):
        """運行CLI"""
        parser = argparse.ArgumentParser(
            description="JavDB 磁力鏈接專用工具 - 獲取有碼月榜前30的磁力鏈接",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例用法:
  python javdb_magnet_cli.py top30 --export txt --output magnets.txt
  python javdb_magnet_cli.py top30 --filter 高清,中文 --export json
  python javdb_magnet_cli.py code SSIS-001 --filter 高清
  python javdb_magnet_cli.py interactive
            """
        )
        
        subparsers = parser.add_subparsers(dest='command', help='可用命令')
        
        # 前30命令
        top30_parser = subparsers.add_parser('top30', help='獲取有碼月榜前30的磁力鏈接')
        top30_parser.add_argument('--filter', '-f', help='過濾標籤 (用逗號分隔，如: 高清,中文)')
        top30_parser.add_argument('--export', '-e', choices=['txt', 'json', 'csv'], 
                                help='導出格式（需配合 --output 指定文件名）')
        top30_parser.add_argument('--output', '-o', help='輸出文件名（使用 --export 時必填）')
        top30_parser.add_argument('--rank-type', default='monthly', choices=['monthly'],
                                help='排行榜類型: monthly (月榜)，默認為 monthly')
        
        # 番號命令
        code_parser = subparsers.add_parser('code', help='根據番號獲取磁力鏈接')
        code_parser.add_argument('movie_code', help='影片番號')
        code_parser.add_argument('--filter', '-f', help='過濾標籤')
        code_parser.add_argument('--export', '-e', choices=['txt', 'json', 'csv'], 
                               help='導出格式（需配合 --output 指定文件名）')
        code_parser.add_argument('--output', '-o', help='輸出文件名（使用 --export 時必填）')
        
        # 交互模式
        interactive_parser = subparsers.add_parser('interactive', help='交互模式')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        try:
            if args.command == 'top30':
                self.handle_top30(args)
            elif args.command == 'code':
                self.handle_code(args)
            elif args.command == 'interactive':
                self.handle_interactive()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]操作已取消[/yellow]")
        except Exception as e:
            self.console.print(f"[red]錯誤: {e}[/red]")
    
    def handle_top30(self, args):
        """處理前30命令"""
        # 檢查統計信息
        stats = self.manager.tracker.get_statistics()
        if stats['total_scraped'] > 0:
            self.console.print(f"[cyan]已記錄 {stats['total_scraped']} 部影片，將自動跳過重複[/cyan]")
        
        rank_type = getattr(args, 'rank_type', 'monthly')
        rank_name = "月榜"
        self.console.print(f"[blue]正在獲取有碼{rank_name}前30的磁力鏈接...[/blue]")
        
        # 解析過濾標籤
        filter_tags = []
        if args.filter:
            filter_tags = [tag.strip() for tag in args.filter.split(',')]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("爬取中...", total=30)
            
            # 獲取前30的磁力鏈接（默認會跳過重複）
            results = self.manager.get_top30_magnets(rank_type=rank_type)
            
            # 應用過濾器
            if filter_tags:
                results = self._apply_filter_to_results(results, filter_tags)
            
            progress.update(task, completed=30)
        
        if not results:
            self.console.print("[yellow]沒有新影片需要處理（所有影片都已經爬取過）[/yellow]")
            return
        
        # 顯示結果
        self._display_results(results)
        
        # 顯示統計信息
        stats = self.manager.get_summary_stats(results)
        self._display_stats(stats)
        
        # 導出（只在明確指定時才導出）
        if args.export:
            if not args.output:
                # 如果指定了導出格式但沒指定文件名，提示用戶
                self.console.print("[yellow]請使用 --output 參數指定輸出文件名，或移除 --export 參數僅在螢幕顯示結果[/yellow]")
            else:
                self._export_results(results, args.export, args.output)
    
    def handle_code(self, args):
        """處理番號命令"""
        self.console.print(f"[blue]正在獲取番號 {args.movie_code} 的磁力鏈接...[/blue]")
        
        # 解析過濾標籤
        filter_tags = []
        if args.filter:
            filter_tags = [tag.strip() for tag in args.filter.split(',')]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("爬取中...", total=None)
            
            # 獲取磁力鏈接
            magnet_links = self.manager.get_magnets_by_code(args.movie_code)
            
            # 應用過濾器
            if filter_tags:
                magnet_links = self._filter_magnets(magnet_links, filter_tags)
        
        if not magnet_links:
            self.console.print("[yellow]沒有找到磁力鏈接[/yellow]")
            return
        
        # 顯示結果
        self._display_magnet_links(magnet_links, args.movie_code)
        
        # 導出（只在明確指定時才導出）
        if args.export:
            if not args.output:
                self.console.print("[yellow]請使用 --output 參數指定輸出文件名，或移除 --export 參數僅在螢幕顯示結果[/yellow]")
            else:
                self._export_magnet_links(magnet_links, args.movie_code, args.export, args.output)
    
    def handle_interactive(self):
        """處理交互模式"""
        self.console.print(Panel.fit(
            "[bold blue]JavDB 磁力鏈接工具 - 交互模式[/bold blue]\n"
            "專門用於獲取有碼月榜前30的磁力鏈接\n"
            "輸入 'help' 查看可用命令\n"
            "輸入 'quit' 退出",
            title="歡迎"
        ))
        
        while True:
            try:
                command = Prompt.ask("\n[cyan]javdb-magnet[/cyan]")
                
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                elif command.lower() == 'help':
                    self._show_interactive_help()
                elif command == 'top30':
                    self._handle_interactive_top30()
                elif command.startswith('code '):
                    movie_code = command[5:].strip()
                    self._handle_interactive_code(movie_code)
                else:
                    self.console.print("[yellow]未知命令，輸入 'help' 查看幫助[/yellow]")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]錯誤: {e}[/red]")
        
        self.console.print("[green]再見！[/green]")
    
    def _display_results(self, results: List[Dict[str, Any]]):
        """顯示結果"""
        if not results:
            self.console.print("[yellow]沒有找到結果[/yellow]")
            return
        
        # 創建表格
        table = Table(title=f"有碼月榜前30磁力鏈接 - 共 {len(results)} 部影片")
        table.add_column("排名", style="cyan", width=6)
        table.add_column("番號", style="green", width=12)
        table.add_column("標題", style="yellow", max_width=30)
        table.add_column("評分", style="red", width=8)
        
        for result in results:
            movie = result['movie']
            
            # 處理標題長度（處理空值）
            display_title = movie.get('title', '') or ''
            if len(display_title) > 27:
                display_title = display_title[:27] + "..."
            
            table.add_row(
                str(result['rank']),
                movie.get('code', ''),
                display_title,
                f"{movie.get('score', 0):.1f}" if movie.get('score', 0) > 0 else "-"
            )
        
        self.console.print(table)
    
    def _display_magnet_links(self, magnet_links: List[MagnetLink], movie_code: str):
        """顯示磁力鏈接"""
        if not magnet_links:
            self.console.print("[yellow]沒有找到磁力鏈接[/yellow]")
            return
        
        table = Table(title=f"番號 {movie_code} 的磁力鏈接 - 共 {len(magnet_links)} 個")
        table.add_column("標題", style="cyan", max_width=30)
        table.add_column("大小", style="green", width=12)
        table.add_column("標籤", style="yellow", width=15)
        table.add_column("文件數", style="magenta", width=8)
        table.add_column("日期", style="blue", width=12)
        table.add_column("下載鏈接", style="red", max_width=50)
        
        for magnet in magnet_links:
            # 處理標題長度
            display_title = magnet.title
            if len(display_title) > 27:
                display_title = display_title[:27] + "..."
            
            # 處理下載鏈接長度
            download_link = magnet.copy_url or magnet.magnet_url
            if len(download_link) > 47:
                download_link = download_link[:47] + "..."
            
            table.add_row(
                display_title,
                magnet.size,
                ", ".join(magnet.tags),
                str(magnet.file_count),
                magnet.date,
                download_link
            )
        
        self.console.print(table)
    
    def _display_stats(self, stats: Dict[str, Any]):
        """顯示統計信息"""
        stats_table = Table(title="統計信息")
        stats_table.add_column("項目", style="cyan")
        stats_table.add_column("數值", style="magenta")
        
        stats_table.add_row("總影片數", str(stats['total_movies']))
        stats_table.add_row("有磁力鏈接的影片數", str(stats['movies_with_magnets']))
        stats_table.add_row("成功率", f"{stats['success_rate']:.1%}")
        
        self.console.print(stats_table)
    
    def _export_results(self, results: List[Dict[str, Any]], format_type: str, filename: str):
        """導出結果"""
        if not filename:
            self.console.print("[red]錯誤: 必須指定輸出文件名（使用 --output 參數）[/red]")
            return
        
        # 確保文件擴展名匹配格式
        if not filename.endswith(f'.{format_type}'):
            filename = f"{filename}.{format_type}"
        
        if format_type == 'txt':
            self.manager.export_magnets_to_file(results, filename)
        elif format_type == 'json':
            self._export_to_json(results, filename)
        elif format_type == 'csv':
            self._export_to_csv(results, filename)
        
        self.console.print(f"[green]已導出到: {filename}[/green]")
    
    def _export_magnet_links(self, magnet_links: List[MagnetLink], movie_code: str, 
                           format_type: str, filename: str):
        """導出磁力鏈接"""
        if not filename:
            self.console.print("[red]錯誤: 必須指定輸出文件名（使用 --output 參數）[/red]")
            return
        
        # 確保文件擴展名匹配格式
        if not filename.endswith(f'.{format_type}'):
            filename = f"{filename}.{format_type}"
        
        if format_type == 'txt':
            self._export_magnets_to_txt(magnet_links, movie_code, filename)
        elif format_type == 'json':
            self._export_magnets_to_json(magnet_links, movie_code, filename)
        elif format_type == 'csv':
            self._export_magnets_to_csv(magnet_links, movie_code, filename)
        
        self.console.print(f"[green]已導出到: {filename}[/green]")
    
    def _export_to_json(self, results: List[Dict[str, Any]], filename: str):
        """導出為JSON格式"""
        data = []
        for result in results:
            movie = result['movie']
            movie_data = {
                'rank': result['rank'],
                'movie': {
                    'code': movie['code'],
                    'title': movie['title'],
                    'actors': movie['actors'],
                    'score': movie['score'],
                    'tags': movie['tags']
                },
                'magnet_links': [
                    {
                        'title': magnet.title,
                        'size': magnet.size,
                        'tags': magnet.tags,
                        'file_count': magnet.file_count,
                        'download_url': magnet.copy_url or magnet.magnet_url,
                        'date': magnet.date
                    }
                    for magnet in result['magnet_links']
                ],
                'total_magnets': result['total_magnets'],
                'filtered_magnets': result['filtered_magnets']
            }
            data.append(movie_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _export_to_csv(self, results: List[Dict[str, Any]], filename: str):
        """導出為CSV格式"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['排名', '番號', '標題', '演員', '評分', '磁力鏈接標題', '大小', '標籤', '下載鏈接', '日期'])
            
            for result in results:
                movie = result['movie']
                for magnet in result['magnet_links']:
                    writer.writerow([
                        result['rank'],
                        movie['code'],
                        movie['title'],
                        ', '.join(movie['actors']),
                        movie['score'],
                        magnet.title,
                        magnet.size,
                        ', '.join(magnet.tags),
                        magnet.copy_url or magnet.magnet_url,
                        magnet.date
                    ])
    
    def _export_magnets_to_txt(self, magnet_links: List[MagnetLink], movie_code: str, filename: str):
        """導出磁力鏈接為文本格式"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"番號 {movie_code} 的磁力鏈接\n")
            f.write("=" * 50 + "\n\n")
            
            for i, magnet in enumerate(magnet_links, 1):
                f.write(f"{i}. {magnet.title}\n")
                f.write(f"   大小: {magnet.size}\n")
                f.write(f"   標籤: {', '.join(magnet.tags)}\n")
                f.write(f"   文件數: {magnet.file_count}\n")
                f.write(f"   下載鏈接: {magnet.copy_url or magnet.magnet_url}\n")
                f.write(f"   日期: {magnet.date}\n")
                f.write("-" * 80 + "\n")
    
    def _export_magnets_to_json(self, magnet_links: List[MagnetLink], movie_code: str, filename: str):
        """導出磁力鏈接為JSON格式"""
        data = {
            'movie_code': movie_code,
            'magnet_links': [
                {
                    'title': magnet.title,
                    'size': magnet.size,
                    'tags': magnet.tags,
                    'file_count': magnet.file_count,
                    'download_url': magnet.copy_url or magnet.magnet_url,
                    'date': magnet.date
                }
                for magnet in magnet_links
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _export_magnets_to_csv(self, magnet_links: List[MagnetLink], movie_code: str, filename: str):
        """導出磁力鏈接為CSV格式"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['番號', '標題', '大小', '標籤', '文件數', '下載鏈接', '日期'])
            
            for magnet in magnet_links:
                writer.writerow([
                    movie_code,
                    magnet.title,
                    magnet.size,
                    ', '.join(magnet.tags),
                    magnet.file_count,
                    magnet.copy_url or magnet.magnet_url,
                    magnet.date
                ])
    
    def _apply_priority_filter_to_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """對結果應用優先順序過濾器"""
        filtered_results = []
        
        for result in results:
            if result['magnet_links']:
                # 使用優先順序邏輯
                filtered_magnets = self._apply_priority_logic(result['magnet_links'])
                result['magnet_links'] = filtered_magnets
                result['filtered_magnets'] = len(filtered_magnets)
                filtered_results.append(result)
        
        return filtered_results
    
    def _filter_magnets(self, magnet_links: List[MagnetLink], filter_tags: List[str]) -> List[MagnetLink]:
        """過濾磁力鏈接"""
        if not filter_tags or not magnet_links:
            return magnet_links
        
        filtered = []
        for magnet in magnet_links:
            magnet_tags_str = ','.join(magnet.tags)
            if any(tag in magnet_tags_str for tag in filter_tags):
                filtered.append(magnet)
        
        return filtered
    
    def _apply_filter_to_results(self, results: List[Dict[str, Any]], filter_tags: List[str]) -> List[Dict[str, Any]]:
        """對結果應用標籤過濾"""
        if not filter_tags:
            return results
        
        filtered_results = []
        for result in results:
            # 檢查磁力鏈接標籤
            filtered_magnets = []
            for magnet in result.get('magnet_links', []):
                if any(tag in ','.join(magnet.tags) for tag in filter_tags):
                    filtered_magnets.append(magnet)
            
            if filtered_magnets:
                result['magnet_links'] = filtered_magnets
                result['filtered_magnets'] = len(filtered_magnets)
                filtered_results.append(result)
        
        return filtered_results
    
    def _apply_priority_logic(self, magnet_links: List[MagnetLink]) -> List[MagnetLink]:
        """應用優先順序邏輯：1.高清 2.中文 3.第一個（每部影片只選一個）"""
        if not magnet_links:
            return []
        
        # 優先順序：1.高清 2.中文 3.第一個
        high_quality = []
        chinese = []
        
        for magnet in magnet_links:
            has_high_quality = any(tag in magnet.tags for tag in ['高清', 'HD', '4K', '1080p', '720p'])
            has_chinese = any(tag in magnet.tags for tag in ['中文', 'Chinese'])
            
            if has_high_quality:
                high_quality.append(magnet)
            elif has_chinese:
                chinese.append(magnet)
        
        # 按優先順序返回一個最佳選擇
        if high_quality:
            return [high_quality[0]]  # 只返回第一個高清
        elif chinese:
            return [chinese[0]]  # 只返回第一個中文
        else:
            return [magnet_links[0]]  # 只返回第一個
    
    def _show_interactive_help(self):
        """顯示交互模式幫助"""
        help_text = """
可用命令:
  top30                    - 獲取有碼月榜前30的磁力鏈接
  code <番號>              - 根據番號獲取磁力鏈接
  help                     - 顯示此幫助
  quit                     - 退出程序

示例:
  top30
  code SSIS-001
  code JUR-496
        """
        self.console.print(Panel(help_text, title="幫助"))
    
    def _handle_interactive_top30(self):
        """處理交互模式前30"""
        args = argparse.Namespace()
        args.filter = None
        args.export = 'txt'
        args.output = None
        args.rank_type = 'monthly'  # 默認使用月榜
        
        self.handle_top30(args)
    
    def _handle_interactive_code(self, movie_code: str):
        """處理交互模式番號"""
        args = argparse.Namespace()
        args.movie_code = movie_code
        args.filter = None
        args.export = 'txt'
        args.output = None
        
        self.handle_code(args)

def main():
    """主函數"""
    # 創建CLI實例
    cli = JavDBMagnetCLI()
    
    # 運行CLI
    cli.run()

if __name__ == "__main__":
    main()

