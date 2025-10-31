import sys
print(f"Python 版本: {sys.version}")
print(f"Python 路徑: {sys.executable}")

try:
    import json
    print("✅ json 模塊正常")
except ImportError as e:
    print(f"❌ json 模塊錯誤: {e}")

try:
    import os
    print("✅ os 模塊正常")
except ImportError as e:
    print(f"❌ os 模塊錯誤: {e}")

try:
    import requests
    print("✅ requests 模塊正常")
except ImportError as e:
    print(f"❌ requests 模塊錯誤: {e}")

try:
    from bs4 import BeautifulSoup
    print("✅ beautifulsoup4 模塊正常")
except ImportError as e:
    print(f"❌ beautifulsoup4 模塊錯誤: {e}")

try:
    import rich
    print("✅ rich 模塊正常")
except ImportError as e:
    print(f"❌ rich 模塊錯誤: {e}")

print("\n基本模塊檢查完成")


