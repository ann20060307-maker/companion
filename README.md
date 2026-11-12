# Companion 全端網站

繁體中文、響應式的全球住宿 B2B 合作平台。包含公開網站、合作洽詢表單、SQLite 資料庫與管理後台。

## 本機啟動

```bash
python -m venv .venv
pip install -r requirements.txt
python app.py
```

## 部署環境變數

正式部署務必設定 `SECRET_KEY`、`ADMIN_USERNAME`、`ADMIN_PASSWORD` 與 `DATABASE_PATH`。SQLite 資料庫應放在持久化磁碟。

## 頁面

- `/` 首頁
- `/about` 關於我們
- `/services` 合作服務
- `/contact` 合作洽詢
- `/supplier/register` 供應商註冊
- `/supplier/login` 供應商登入
- `/supplier` 供應商會員中心
- `/api/properties` 已核准房源 API
- `/admin/login` 管理員登入
- `/admin` 管理後台
- `/health` 健康檢查

本專案為 Companion 的獨立原創實作。上線前仍需補齊品牌資料、隱私權政策、CSRF 防護、登入限速及備份流程。
