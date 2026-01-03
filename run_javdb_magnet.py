"""
JavDB 磁力鏈接工具快速啟動腳本
專門用於獲取有碼月榜前30的磁力鏈接
"""
import sys
import os
import subprocess
from pathlib import Path

# 強制無緩衝輸出
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

# 確保立即輸出
print("正在啟動腳本...", flush=True)
sys.stdout.flush()

def check_dependencies():
    """檢查依賴"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import rich
        print("✅ 所有依賴已安裝")
        return True
    except ImportError as e:
        print(f"❌ 缺少依賴: {e}")
        print("請運行: pip install -r requirements.txt")
        return False

def run_command(cmd_args):
    """執行命令並顯示輸出"""
    try:
        # 使用當前Python解釋器執行
        python_exec = sys.executable
        full_cmd = [python_exec] + cmd_args
        
        # 執行命令，實時顯示輸出
        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )
        
        # 實時輸出
        for line in process.stdout:
            print(line, end='', flush=True)
        
        process.wait()
        return process.returncode == 0
    except Exception as e:
        print(f"❌ 執行命令失敗: {e}")
        return False

def main():
    """主函數"""
    print("JavDB 磁力鏈接工具")
    print("=" * 50)
    print("自動獲取有碼月榜前30的磁力鏈接")
    print("重點：獲取標記為'高清'或'字幕'的磁力鏈接")
    print("=" * 50)
    
    # 檢查依賴
    if not check_dependencies():
        return
    
    # 自動執行月榜
    print("\n開始自動執行...")
    print("=" * 50)
    
    # 執行月榜
    print("\n正在獲取有碼月榜前30的磁力鏈接...")
    print("這可能需要幾分鐘時間，請耐心等待...\n")
    cmd_args = ['javdb_magnet_cli.py', 'top30', '--rank-type', 'monthly', '--filter', '高清,字幕']
    success = run_command(cmd_args)
    
    if success:
        print("\n✅ 月榜完成！")
    else:
        print("\n❌ 月榜執行失敗")
    
    print("\n" + "=" * 50)
    print("\n✅ 全部完成！")
    print("月榜的磁力鏈接已保存")

if __name__ == "__main__":
    try:
        print("進入主程序...", flush=True)
        sys.stdout.flush()
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用戶中斷操作", flush=True)
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
    finally:
        sys.stdout.flush()
