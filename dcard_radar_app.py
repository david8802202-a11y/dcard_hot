import streamlit as st
import requests
import xml.etree.ElementTree as ET
import json
import os
import re
import hashlib
from datetime import datetime, timedelta

# ==================== 設定 ====================
st.set_page_config(page_title="📡 DcardRadar", page_icon="📡", layout="wide")

DATA_DIR = "dcardradar_data"
os.makedirs(DATA_DIR, exist_ok=True)

# Dcard 看板對照表（英文 alias → 中文名稱）
DCARD_FORUMS = {
    "popular": "即時熱門",
    "trending": "時事",
    "relationship": "感情",
    "mood": "心情",
    "makeup": "美妝",
    "girl": "女孩",
    "boy": "男孩",
    "food": "美食",
    "funny": "有趣",
    "travel": "旅遊",
    "job": "工作",
    "tech_job": "科技業",
    "creditcard": "信用卡",
    "dressup": "穿搭",
    "fitness": "健身",
    "pet": "寵物",
    "movie": "電影",
    "music": "音樂",
    "game": "遊戲",
    "3c": "3C",
    "car": "汽車",
    "house": "買房",
    "stock": "股票",
    "insurance": "保險",
    "skin_care": "護膚",
    "hair": "美髮",
    "teeth": "牙齒矯正",
    "plastic_surgery": "醫美",
    "wedding": "結婚",
    "baby": "寶寶",
    "parenting": "親子",
}

# RSSHub 公開實例列表（可自行增減）
RSSHUB_INSTANCES = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://hub.slarker.me",
    "https://rsshub.pseudoyu.com",
]

# ==================== 資料管理 ====================
def get_user_file(user_id):
    return os.path.join(DATA_DIR, f"{user_id}.json")

def load_user(user_id):
    path = get_user_file(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "keywords": [],
        "tracked_forums": ["popular", "funny", "relationship", "makeup", "food"],
        "alerts": [],
        "scan_history": [],
        "rsshub_instance": RSSHUB_INSTANCES[0],
    }

def save_user(user_id, data):
    with open(get_user_file(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_user_id(username):
    return hashlib.md5(username.encode()).hexdigest()

# ==================== RSS 抓取 ====================
def fetch_dcard_rss(forum_alias, rsshub_instance, post_type="popular"):
    """透過 RSSHub 抓取 Dcard 看板的熱門文章"""
    url = f"{rsshub_instance}/dcard/{forum_alias}/{post_type}"
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        if r.status_code == 200:
            return parse_rss(r.text), None
        else:
            return None, f"HTTP {r.status_code}"
    except requests.exceptions.Timeout:
        return None, "超時"
    except Exception as e:
        return None, str(e)

def parse_rss(xml_text):
    """解析 RSS XML 格式"""
    articles = []
    try:
        root = ET.fromstring(xml_text)
        # RSS 2.0 格式
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                description = item.findtext("description", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                
                # 清理 HTML
                description_clean = re.sub(r'<[^>]+>', '', description)[:200]
                
                if title:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": description_clean,
                        "pub_date": pub_date,
                    })
        
        # Atom 格式 fallback
        if not articles:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                summary = entry.findtext("atom:summary", "", ns).strip()
                published = entry.findtext("atom:published", "", ns).strip()
                
                summary_clean = re.sub(r'<[^>]+>', '', summary)[:200]
                
                if title:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": summary_clean,
                        "pub_date": published,
                    })
    except ET.ParseError:
        pass
    
    return articles

def parse_manual_input(text):
    """解析手動貼上的文字（標題列表）"""
    articles = []
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # 清除開頭的數字編號（如 "1. " "1) " "#1 "）
        cleaned = re.sub(r'^[\d#]+[\.\)\s]+', '', line).strip()
        if cleaned:
            articles.append({
                "title": cleaned,
                "link": "",
                "description": "",
                "pub_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source": "手動輸入",
            })
    return articles

# ==================== 關鍵字比對 ====================
def match_keywords(articles, keywords):
    """比對文章標題是否包含關鍵字"""
    matches = []
    for article in articles:
        title = article.get("title", "")
        matched_kws = []
        for kw in keywords:
            # 支援簡單的 OR 語法（用 | 分隔）
            sub_keywords = [k.strip() for k in kw.split("|")]
            for sub_kw in sub_keywords:
                if sub_kw.lower() in title.lower():
                    matched_kws.append(kw)
                    break
        
        if matched_kws:
            matches.append({
                **article,
                "matched_keywords": matched_kws,
            })
    
    return matches

# ==================== 自訂 CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&display=swap');
* { font-family: 'Noto Sans TC', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 50%, #4ecdc4 100%);
    padding: 2rem;
    border-radius: 16px;
    color: white;
    text-align: center;
    margin-bottom: 1.5rem;
}
.main-header h1 { font-size: 2.2rem; margin: 0; font-weight: 900; }
.main-header p { font-size: 1rem; margin: 0.5rem 0 0 0; opacity: 0.9; }

.match-card {
    background: linear-gradient(135deg, #fff7ed, #fef3c7);
    border-left: 4px solid #f59e0b;
    padding: 1rem 1.2rem;
    border-radius: 0 12px 12px 0;
    margin-bottom: 0.8rem;
}
.match-card .title { font-size: 1.05rem; font-weight: 700; color: #92400e; }
.match-card .kw-tag {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    background: #f59e0b; color: white; font-size: 0.75rem; font-weight: 600; margin: 2px;
}

.no-match-card {
    padding: 0.6rem 1rem;
    background: #f9fafb;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    color: #6b7280;
    font-size: 0.9rem;
}

.alert-banner {
    background: linear-gradient(135deg, #dc2626, #ef4444);
    color: white;
    padding: 1.2rem;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 1rem;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.85; }
}

.stat-card {
    background: linear-gradient(135deg, #1e3a5f, #2d6a9f);
    color: white;
    padding: 1rem;
    border-radius: 12px;
    text-align: center;
}
.stat-card h3 { margin: 0; font-size: 1.6rem; }
.stat-card p { margin: 0.2rem 0 0 0; font-size: 0.8rem; opacity: 0.85; }

.forum-tag {
    display: inline-block; padding: 4px 12px; margin: 3px;
    border-radius: 16px; font-size: 0.85rem; font-weight: 500;
    background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;
}
</style>
""", unsafe_allow_html=True)

# ==================== 登入 ====================
if "user_id" not in st.session_state:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="main-header">
            <h1>📡 DcardRadar</h1>
            <p>Dcard 熱門關鍵字追蹤工具</p>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("👤 輸入用戶名稱", placeholder="例：小王")
        
        if st.button("🚀 開始使用", use_container_width=True, type="primary"):
            if username.strip():
                uid = create_user_id(username.strip())
                st.session_state.user_id = uid
                st.session_state.username = username.strip()
                st.session_state.page = "scan"
                st.rerun()
            else:
                st.error("請輸入名稱")
        
        st.divider()
        st.markdown("""
        **📡 功能一覽**
        - 🔍 追蹤多組關鍵字是否出現在 Dcard 熱門
        - 📋 支援 RSSHub 自動抓取 + 手動貼上
        - 🏷️ 監控多個看板同時掃描
        - 📊 歷史命中紀錄追蹤
        - ⚡ 完全免費，不需 API Key
        """)

else:
    # ==================== 主應用 ====================
    user_id = st.session_state.user_id
    username = st.session_state.username
    user_data = load_user(user_id)
    
    if "page" not in st.session_state:
        st.session_state.page = "scan"
    
    # --- 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 📡 {username}")
        st.caption(f"追蹤 {len(user_data.get('keywords', []))} 組關鍵字")
        st.divider()
        
        pages = {
            "scan": "🔍 掃描熱門",
            "keywords": "🏷️ 關鍵字管理",
            "history": "📊 歷史紀錄",
            "settings": "⚙️ 設定",
        }
        for key, label in pages.items():
            btn_type = "primary" if st.session_state.page == key else "secondary"
            if st.button(label, use_container_width=True, key=f"nav_{key}", type=btn_type):
                st.session_state.page = key
                st.rerun()
        
        st.divider()
        
        # 快速顯示目前追蹤的關鍵字
        kws = user_data.get("keywords", [])
        if kws:
            st.caption("📌 追蹤中的關鍵字：")
            for kw in kws:
                st.markdown(f"<span class='forum-tag'>{kw}</span>", unsafe_allow_html=True)
        
        st.divider()
        if st.button("🚪 登出", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
    
    # ==================== 🔍 掃描熱門 ====================
    if st.session_state.page == "scan":
        st.markdown("""
        <div class="main-header">
            <h1>🔍 掃描 Dcard 熱門</h1>
            <p>檢查你的關鍵字是否出現在各版熱門文章中</p>
        </div>
        """, unsafe_allow_html=True)
        
        keywords = user_data.get("keywords", [])
        
        if not keywords:
            st.warning("⚠️ 你還沒有設定任何關鍵字，請先到「關鍵字管理」頁面新增。")
            if st.button("👉 前往設定關鍵字", type="primary"):
                st.session_state.page = "keywords"
                st.rerun()
        else:
            st.write(f"目前追蹤關鍵字：**{' / '.join(keywords)}**")
            
            # 選擇資料來源
            source_tab1, source_tab2 = st.tabs(["📡 RSSHub 自動抓取", "📋 手動貼上"])
            
            # ---- Tab 1: RSSHub 自動抓取 ----
            with source_tab1:
                st.caption("透過 RSSHub 自動抓取 Dcard 各版熱門文章")
                
                tracked_forums = user_data.get("tracked_forums", ["popular"])
                
                # 選擇要掃描的看板
                selected_forums = st.multiselect(
                    "選擇要掃描的看板",
                    options=list(DCARD_FORUMS.keys()),
                    default=tracked_forums,
                    format_func=lambda x: f"{DCARD_FORUMS.get(x, x)}",
                    key="scan_forums"
                )
                
                if st.button("🚀 開始掃描", use_container_width=True, type="primary", key="btn_rss_scan"):
                    if not selected_forums:
                        st.error("請至少選一個看板")
                    else:
                        instance = user_data.get("rsshub_instance", RSSHUB_INSTANCES[0])
                        all_matches = []
                        all_articles = []
                        
                        progress = st.progress(0, text="開始掃描...")
                        
                        for i, forum in enumerate(selected_forums):
                            forum_name = DCARD_FORUMS.get(forum, forum)
                            progress.progress(
                                (i + 1) / len(selected_forums),
                                text=f"掃描中：{forum_name}..."
                            )
                            
                            articles, error = fetch_dcard_rss(forum, instance)
                            
                            if articles:
                                for a in articles:
                                    a["forum"] = forum_name
                                    a["forum_alias"] = forum
                                all_articles.extend(articles)
                                
                                matches = match_keywords(articles, keywords)
                                all_matches.extend(matches)
                                
                                if matches:
                                    st.success(f"✅ {forum_name}：找到 {len(matches)} 篇命中！")
                                else:
                                    st.caption(f"📋 {forum_name}：{len(articles)} 篇文章，無命中")
                            else:
                                st.warning(f"⚠️ {forum_name}：抓取失敗 ({error})")
                        
                        progress.empty()
                        
                        # 儲存掃描結果
                        st.session_state.scan_results = {
                            "matches": all_matches,
                            "total_articles": len(all_articles),
                            "total_forums": len(selected_forums),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        
                        # 儲存到歷史
                        if all_matches:
                            scan_record = {
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "matches": len(all_matches),
                                "total_articles": len(all_articles),
                                "forums_scanned": len(selected_forums),
                                "matched_titles": [m["title"] for m in all_matches[:10]],
                                "matched_keywords": list(set(
                                    kw for m in all_matches for kw in m.get("matched_keywords", [])
                                )),
                            }
                            user_data.setdefault("scan_history", []).append(scan_record)
                            save_user(user_id, user_data)
            
            # ---- Tab 2: 手動貼上 ----
            with source_tab2:
                st.caption("從 Dcard 網頁複製熱門文章標題，貼到下方")
                st.info("💡 操作方式：到 [Dcard 即時熱門](https://www.dcard.tw/f) 頁面，選取標題文字，複製後貼到下方。每行一個標題。")
                
                manual_text = st.text_area(
                    "貼上文章標題（每行一個）",
                    height=250,
                    placeholder="例：\n有人跟我一樣覺得XX品牌很好用嗎\n推薦一個超讚的保養品\n今天去吃了一家超好吃的店",
                    key="manual_input"
                )
                
                forum_label = st.text_input("這些文章來自哪個看板？（選填）", placeholder="例：美妝、熱門", key="manual_forum")
                
                if st.button("🔍 比對關鍵字", use_container_width=True, type="primary", key="btn_manual_scan"):
                    if not manual_text.strip():
                        st.error("請貼上至少一個標題")
                    else:
                        articles = parse_manual_input(manual_text)
                        for a in articles:
                            a["forum"] = forum_label or "手動輸入"
                        
                        matches = match_keywords(articles, keywords)
                        
                        st.session_state.scan_results = {
                            "matches": matches,
                            "total_articles": len(articles),
                            "total_forums": 1,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        
                        if matches:
                            scan_record = {
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "matches": len(matches),
                                "total_articles": len(articles),
                                "forums_scanned": 1,
                                "matched_titles": [m["title"] for m in matches[:10]],
                                "matched_keywords": list(set(
                                    kw for m in matches for kw in m.get("matched_keywords", [])
                                )),
                            }
                            user_data.setdefault("scan_history", []).append(scan_record)
                            save_user(user_id, user_data)
            
            # ---- 顯示掃描結果 ----
            if "scan_results" in st.session_state:
                results = st.session_state.scan_results
                
                st.divider()
                
                # 統計卡片
                c1, c2, c3 = st.columns(3)
                c1.metric("📋 掃描文章數", results["total_articles"])
                c2.metric("🎯 命中數", len(results["matches"]))
                c3.metric("⏰ 掃描時間", results["timestamp"][-8:])
                
                st.divider()
                
                if results["matches"]:
                    st.markdown("""
                    <div class="alert-banner">
                        <h2 style="margin:0;">🚨 發現命中！</h2>
                        <p style="margin:0.3rem 0 0 0;">以下文章標題包含你追蹤的關鍵字</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for match in results["matches"]:
                        kw_tags = "".join(
                            f'<span class="kw-tag">{kw}</span>'
                            for kw in match.get("matched_keywords", [])
                        )
                        
                        st.markdown(f"""
                        <div class="match-card">
                            <div class="title">{match['title']}</div>
                            <div style="margin-top:6px;">
                                <span style="font-size:0.8rem; color:#b45309;">📌 {match.get('forum', '')}</span>
                                　{kw_tags}
                            </div>
                            {f'<div style="font-size:0.8rem; color:#9ca3af; margin-top:4px;">{match["description"][:100]}</div>' if match.get('description') else ''}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if match.get("link"):
                            st.link_button(f"🔗 查看原文", match["link"], use_container_width=False)
                else:
                    st.info("✅ 目前沒有命中任何關鍵字，一切平靜。")
    
    # ==================== 🏷️ 關鍵字管理 ====================
    elif st.session_state.page == "keywords":
        st.markdown("""
        <div class="main-header">
            <h1>🏷️ 關鍵字管理</h1>
            <p>設定你想追蹤的關鍵字</p>
        </div>
        """, unsafe_allow_html=True)
        
        keywords = user_data.get("keywords", [])
        
        # 新增關鍵字
        st.subheader("➕ 新增關鍵字")
        st.caption("支援 `|` 符號做 OR 搜尋，例如 `品牌A|品牌B` 表示任一出現就算命中")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_kw = st.text_input("輸入關鍵字", placeholder="例：品牌名稱、產品名、競品名", key="new_kw_input")
        with col2:
            st.write("")  # spacing
            st.write("")
            if st.button("➕ 新增", use_container_width=True, type="primary", key="btn_add_kw"):
                if new_kw.strip():
                    if new_kw.strip() not in keywords:
                        keywords.append(new_kw.strip())
                        user_data["keywords"] = keywords
                        save_user(user_id, user_data)
                        st.success(f"✅ 已新增：{new_kw}")
                        st.rerun()
                    else:
                        st.warning("這個關鍵字已經存在了")
                else:
                    st.error("請輸入關鍵字")
        
        # 批次新增
        with st.expander("📦 批次新增（每行一個）"):
            batch_input = st.text_area("每行一個關鍵字", height=120, key="batch_kw")
            if st.button("批次新增", key="btn_batch_add"):
                new_kws = [kw.strip() for kw in batch_input.split("\n") if kw.strip()]
                added = 0
                for kw in new_kws:
                    if kw not in keywords:
                        keywords.append(kw)
                        added += 1
                user_data["keywords"] = keywords
                save_user(user_id, user_data)
                st.success(f"✅ 新增了 {added} 個關鍵字")
                st.rerun()
        
        st.divider()
        
        # 目前的關鍵字列表
        st.subheader(f"📋 目前追蹤的關鍵字（{len(keywords)} 個）")
        
        if keywords:
            for i, kw in enumerate(keywords):
                col_kw, col_del = st.columns([5, 1])
                with col_kw:
                    if "|" in kw:
                        parts = kw.split("|")
                        st.write(f"**{i+1}.** {' 或 '.join(parts)}")
                    else:
                        st.write(f"**{i+1}.** {kw}")
                with col_del:
                    if st.button("🗑️", key=f"del_kw_{i}", help="刪除此關鍵字"):
                        keywords.pop(i)
                        user_data["keywords"] = keywords
                        save_user(user_id, user_data)
                        st.rerun()
            
            st.divider()
            if st.button("🗑️ 清除所有關鍵字", use_container_width=True):
                user_data["keywords"] = []
                save_user(user_id, user_data)
                st.rerun()
        else:
            st.info("還沒有設定任何關鍵字，從上方開始新增吧！")
        
        st.divider()
        
        # 追蹤看板設定
        st.subheader("📌 預設掃描看板")
        tracked = user_data.get("tracked_forums", ["popular"])
        new_tracked = st.multiselect(
            "選擇預設要掃描的看板",
            options=list(DCARD_FORUMS.keys()),
            default=tracked,
            format_func=lambda x: DCARD_FORUMS.get(x, x),
            key="default_forums"
        )
        if new_tracked != tracked:
            user_data["tracked_forums"] = new_tracked
            save_user(user_id, user_data)
            st.success("✅ 看板設定已更新")
    
    # ==================== 📊 歷史紀錄 ====================
    elif st.session_state.page == "history":
        st.markdown("""
        <div class="main-header">
            <h1>📊 歷史掃描紀錄</h1>
            <p>追蹤過去的命中紀錄與趨勢</p>
        </div>
        """, unsafe_allow_html=True)
        
        history = user_data.get("scan_history", [])
        
        if history:
            # 統計
            total_scans = len(history)
            total_matches = sum(h.get("matches", 0) for h in history)
            all_matched_kws = []
            for h in history:
                all_matched_kws.extend(h.get("matched_keywords", []))
            
            c1, c2, c3 = st.columns(3)
            c1.metric("📊 總掃描次數", total_scans)
            c2.metric("🎯 總命中次數", total_matches)
            c3.metric("🏷️ 命中關鍵字種類", len(set(all_matched_kws)))
            
            st.divider()
            
            # 最常命中的關鍵字
            if all_matched_kws:
                st.subheader("🔥 最常命中的關鍵字")
                from collections import Counter
                kw_counter = Counter(all_matched_kws)
                for kw, count in kw_counter.most_common(10):
                    st.write(f"• **{kw}** — 命中 {count} 次")
            
            st.divider()
            
            # 歷史列表
            st.subheader("📝 掃描紀錄（最新在前）")
            for h in reversed(history[-30:]):
                match_emoji = "🎯" if h.get("matches", 0) > 0 else "✅"
                with st.expander(
                    f"{match_emoji} {h.get('date', '')} — 命中 {h.get('matches', 0)} / 掃描 {h.get('total_articles', 0)} 篇"
                ):
                    if h.get("matched_titles"):
                        st.write("**命中標題：**")
                        for title in h["matched_titles"]:
                            st.write(f"• {title}")
                    if h.get("matched_keywords"):
                        st.write(f"**命中關鍵字：** {', '.join(h['matched_keywords'])}")
            
            st.divider()
            if st.button("🗑️ 清除所有紀錄", use_container_width=True):
                user_data["scan_history"] = []
                save_user(user_id, user_data)
                st.rerun()
        else:
            st.info("還沒有掃描紀錄，先去「掃描熱門」頁面試試吧！")
    
    # ==================== ⚙️ 設定 ====================
    elif st.session_state.page == "settings":
        st.markdown("""
        <div class="main-header">
            <h1>⚙️ 設定</h1>
            <p>調整工具設定</p>
        </div>
        """, unsafe_allow_html=True)
        
        # RSSHub 實例選擇
        st.subheader("📡 RSSHub 實例")
        st.caption("如果預設實例抓不到資料，可以切換其他公開實例試試")
        
        current_instance = user_data.get("rsshub_instance", RSSHUB_INSTANCES[0])
        
        selected_instance = st.selectbox(
            "選擇 RSSHub 實例",
            options=RSSHUB_INSTANCES,
            index=RSSHUB_INSTANCES.index(current_instance) if current_instance in RSSHUB_INSTANCES else 0,
            key="rsshub_select"
        )
        
        custom_instance = st.text_input(
            "或輸入自訂實例網址",
            placeholder="https://your-rsshub-instance.com",
            key="custom_rsshub"
        )
        
        if custom_instance.strip():
            selected_instance = custom_instance.strip()
        
        if selected_instance != current_instance:
            user_data["rsshub_instance"] = selected_instance
            save_user(user_id, user_data)
            st.success(f"✅ 已切換到：{selected_instance}")
        
        # 測試連線
        if st.button("🧪 測試連線", use_container_width=True):
            with st.spinner("測試中..."):
                articles, error = fetch_dcard_rss("popular", selected_instance)
                if articles:
                    st.success(f"✅ 連線成功！取得 {len(articles)} 篇熱門文章")
                    for a in articles[:3]:
                        st.caption(f"• {a['title']}")
                else:
                    st.error(f"❌ 連線失敗：{error}")
                    st.info("💡 試試切換其他 RSSHub 實例，或使用「手動貼上」模式")
        
        st.divider()
        
        # 未來功能：LINE Notify
        st.subheader("🔔 自動通知（即將推出）")
        st.info("""
        **Phase 2 規劃中：**
        - 🔔 LINE Notify 自動通知（命中時推播到 LINE）
        - ⏰ GitHub Actions 定時排程（每小時自動掃描）
        - 📧 Email 通知選項
        
        目前可以先用手動掃描，有需要再跟我說加上自動通知功能！
        """)
        
        st.divider()
        
        # 資料管理
        st.subheader("📦 資料管理")
        c1, c2 = st.columns(2)
        c1.metric("追蹤關鍵字", len(user_data.get("keywords", [])))
        c2.metric("掃描紀錄", len(user_data.get("scan_history", [])))
        
        # 匯出設定
        if st.button("📥 匯出設定（JSON）", use_container_width=True):
            export_data = {
                "keywords": user_data.get("keywords", []),
                "tracked_forums": user_data.get("tracked_forums", []),
                "rsshub_instance": user_data.get("rsshub_instance", ""),
            }
            st.json(export_data)
            st.caption("複製以上 JSON 可以備份你的設定")
        
        st.divider()
        st.markdown("""
        **📡 DcardRadar v1.0**
        
        功能清單：
        - ✅ RSSHub 自動抓取 Dcard 各版熱門
        - ✅ 手動貼上模式（RSSHub 失效時的備案）
        - ✅ 多組關鍵字追蹤（支援 OR 語法）
        - ✅ 多看板同時掃描
        - ✅ 歷史命中紀錄 & 統計
        - ✅ 完全免費，不需 API Key
        - 🔜 LINE Notify 自動通知
        - 🔜 GitHub Actions 定時排程
        """)
