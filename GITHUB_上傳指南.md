# GitHub 上傳指南

## 📋 前置準備

### 1. 安裝 Git（如果還沒安裝）

下載並安裝 Git for Windows：
- 官方網站：https://git-scm.com/download/win
- 安裝完成後，重新啟動命令提示字元或 PowerShell

驗證安裝：
```bash
git --version
```

### 2. 設置 Git 用戶資訊（首次使用需要）

```bash
git config --global user.name "您的名字"
git config --global user.email "your_email@example.com"
```

### 3. 登入 GitHub

1. 前往 https://github.com
2. 登入您的帳號（如果沒有帳號，請先註冊）
3. 點擊右上角的 `+` → `New repository`

---

## 🚀 上傳步驟

### 步驟 1：在 GitHub 上創建新倉庫

1. 在 GitHub 上點擊 `New repository`
2. 填寫倉庫資訊：
   - **Repository name**: `javdb-magnet-crawler` （或您喜歡的名稱）
   - **Description**: `JavDB 磁力鏈接專用工具`
   - **Visibility**: 選擇 `Public` 或 `Private`
   - **⚠️ 重要**：**不要**勾選 "Initialize this repository with a README"
3. 點擊 `Create repository`

### 步驟 2：在本地初始化 Git 倉庫

打開 PowerShell 或命令提示字元，進入專案目錄：

```bash
cd "您的專案路徑"
```

例如：
```bash
cd "C:\Users\YourUsername\YourProject\JM"
```

初始化 Git 倉庫：

```bash
git init
```

### 步驟 3：添加檔案到 Git

```bash
# 添加所有檔案（.gitignore 會自動排除敏感檔案）
git add .

# 檢查將要提交的檔案（確認沒有敏感資訊）
git status
```

**⚠️ 確認事項**：
- 確認 `config.env` **沒有**在列表中（已在 .gitignore 中）
- 確認 `javdb_top30_magnets_*.txt` 和 `magnet/` 目錄**沒有**在列表中

### 步驟 4：提交檔案

```bash
git commit -m "Initial commit: JavDB magnet link crawler"
```

### 步驟 5：連接到 GitHub 遠端倉庫

在 GitHub 創建倉庫後，您會看到一個網址，類似：
```
https://github.com/您的用戶名/javdb-magnet-crawler.git
```

添加遠端倉庫（**請替換為您的實際網址**）：

```bash
git remote add origin https://github.com/您的用戶名/javdb-magnet-crawler.git
```

### 步驟 6：上傳到 GitHub

```bash
# 設定主分支名稱
git branch -M main

# 上傳到 GitHub
git push -u origin main
```

如果要求輸入帳號密碼：
- **用戶名**：您的 GitHub 用戶名
- **密碼**：需要使用 **Personal Access Token**（不是 GitHub 密碼）

---

## 🔐 生成 Personal Access Token（如果需要）

1. 前往 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 點擊 `Generate new token (classic)`
3. 設定：
   - **Note**: `My Computer`
   - **Expiration**: 選擇過期時間
   - **Select scopes**: 勾選 `repo`（完整權限）
4. 點擊 `Generate token`
5. **複製 token**（只會顯示一次，請妥善保存）
6. 使用 token 作為密碼進行登入

---

## ✅ 上傳後確認

1. 前往您的 GitHub 倉庫頁面
2. 確認以下檔案**有**在倉庫中：
   - ✅ `README.md`
   - ✅ `requirements.txt`
   - ✅ 所有 `.py` 檔案
   - ✅ `config.env.example`
   - ✅ `.gitignore`

3. 確認以下檔案**沒有**在倉庫中：
   - ❌ `config.env`（含敏感配置）
   - ❌ `javdb_top30_magnets_*.txt`（輸出檔案）
   - ❌ `magnet/` 目錄（輸出檔案）

---

## 📝 快速命令摘要

```bash
# 1. 初始化
git init

# 2. 添加檔案
git add .

# 3. 提交
git commit -m "Initial commit: JavDB magnet link crawler"

# 4. 添加遠端（替換為您的網址）
git remote add origin https://github.com/您的用戶名/javdb-magnet-crawler.git

# 5. 上傳
git branch -M main
git push -u origin main
```

---

## 🔄 之後的更新

如果您之後修改了程式碼並想更新到 GitHub：

```bash
git add .
git commit -m "更新說明"
git push
```

---

## ❓ 常見問題

### Q: 如果上傳時出現錯誤怎麼辦？

A: 常見錯誤及解決方法：

1. **認證失敗**
   - 使用 Personal Access Token 而不是密碼

2. **遠端倉庫已存在**
   ```bash
   git remote remove origin
   git remote add origin https://github.com/您的用戶名/倉庫名.git
   ```

3. **分支衝突**
   ```bash
   git pull origin main --allow-unrelated-histories
   git push -u origin main
   ```

---

## 🛡️ 安全檢查清單

上傳前請確認：

- [ ] `config.env` 不在 Git 追蹤中
- [ ] 所有輸出檔案（`.txt`、`magnet/`）不在 Git 追蹤中
- [ ] `__pycache__/` 目錄不在 Git 追蹤中
- [ ] 沒有硬編碼的密碼或 API 金鑰

---

祝您上傳順利！🎉

