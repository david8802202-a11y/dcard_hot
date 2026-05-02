# 📡 DcardRadar — Dcard 熱門關鍵字追蹤工具

追蹤你關心的關鍵字是否出現在 Dcard 各版熱門文章中。

## 功能

- 🔍 多組關鍵字同時追蹤（支援 OR 語法）
- 📡 透過 RSSHub 自動抓取 Dcard 各版熱門
- 📋 手動貼上模式（備援方案）
- 🏷️ 30+ 看板同時掃描
- 📊 歷史命中紀錄與統計
- ⚡ 完全免費，不需 API Key

## 安裝與啟動

```bash
pip install -r requirements.txt
streamlit run dcard_radar_app.py
```

## 部署到 Streamlit Cloud

1. 將檔案推到 GitHub repo
2. 到 share.streamlit.io 部署
3. Main file path：`dcard_radar_app.py`
4. 不需要設定 Secrets（本工具不需 API Key）

## 資料來源說明

本工具透過 RSSHub（開源 RSS 服務）間接取得 Dcard 文章列表。
如果 RSSHub 抓取失敗，可切換到「手動貼上」模式。
