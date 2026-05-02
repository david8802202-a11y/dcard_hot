import streamlit as st
import json
import os
import re
import hashlib
from datetime import datetime

# ==================== 設定 ====================
st.set_page_config(page_title="📡 DcardRadar", page_icon="📡", layout="wide")

DATA_DIR = "dcardradar_data"
os.makedirs(DATA_DIR, exist_ok=True)

SHARED_FILE = os.path.join(DATA_DIR, "_shared.json")

DCARD_FORUMS = {
    "popular": "即時熱門", "trending": "時事", "relationship": "感情",
    "mood": "心情", "makeup": "美妝", "girl": "女孩", "boy": "男孩",
    "food": "美食", "funny": "有趣", "travel": "旅遊", "job": "工作",
    "tech_job": "科技業", "creditcard": "信用卡", "dressup": "穿搭",
    "fitness": "健身", "pet": "寵物", "movie": "電影", "music": "音樂",
    "game": "遊戲", "3c": "3C", "car": "汽車", "house": "買房",
    "stock": "股票", "insurance": "保險", "skin_care": "護膚",
    "hair": "美髮", "plastic_surgery": "醫美", "wedding": "結婚",
    "baby": "寶寶", "parenting": "親子",
}

# ==================== 資料管理 ====================
def load_shared():
    """讀取共用資料（關鍵字、追蹤看板、最新掃描結果）"""
    if os.path.exists(SHARED_FILE):
        with open(SHARED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "keywords": [],
        "tracked_forums": ["popular", "funny", "relationship", "makeup", "food"],
        "last_scan": None,
        "scan_log": [],
    }

def save_shared(data):
    with open(SHARED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_file(user_id):
    return os.path.join(DATA_DIR, f"user_{user_id}.json")

def load_user(user_id):
    path = get_user_file(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"my_scan_history": []}

def save_user(user_id, data):
    with open(get_user_file(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_user_id(username):
    return hashlib.md5(username.encode()).hexdigest()

# ==================== 關鍵字比對 ====================
def parse_manual_input(text):
    articles = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r'^[\d#]+[\.\)\s]+', '', line).strip()
        if cleaned:
            articles.append({
                "title": cleaned,
                "link": "",
                "description": "",
                "pub_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
    return articles

def match_keywords(articles, keywords):
    matches = []
    for article in articles:
        title = article.get("title", "")
        matched_kws = []
        for kw in keywords:
            sub_keywords = [k.strip() for k in kw.split("|")]
            for sub_kw in sub_keywords:
                if sub_kw and sub_kw.lower() in title.lower():
                    matched_kws.append(kw)
                    break
        if matched_kws:
            matches.append({**article, "matched_keywords": matched_kws})
    return matches

# ==================== CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&display=swap');
* { font-family: 'Noto Sans TC', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 50%, #4ecdc4 100%);
    padding: 2rem; border-radius: 16px; color: white; text-align: center; margin-bottom: 1.5rem;
}
.main-header h1 { font-size: 2.2rem; margin: 0; font-weight: 900; }
.main-header p { font-size: 1rem; margin: 0.5rem 0 0 0; opacity: 0.9; }

.match-card {
    background: linear-gradient(135deg, #fff7ed, #fef3c7);
    border-left: 4px solid #f59e0b;
    padding: 1rem 1.2rem; border-radius: 0 12px 12px 0; margin-bottom: 0.8rem;
}
.match-card .title { font-size: 1.05rem; font-weight: 700; color: #92400e; }
.match-card .kw-tag {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    background: #f59e0b; color: white; font-size: 0.75rem; font-weight: 600; margin: 2px;
}

.alert-banner {
    background: linear-gradient(135deg, #dc2626, #ef4444);
    color: white; padding: 1.2rem; border-radius: 12px; text-align: center; margin-bottom: 1rem;
}

.forum-tag {
    display: inline-block; padding: 4px 12px; margin: 3px;
    border-radius: 16px; font-size: 0.85rem; font-weight: 500;
    background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;
}

.team-badge {
    display: inline-block; padding: 3px 10px; border-radius: 10px;
    font-size: 0.75rem; font-weight: 600;
    background: #d1fae5; color: #065f46;
}

.scan-entry {
    padding: 0.6rem 1rem; background: #f9fafb; border-radius: 8px;
    margin-bottom: 0.5rem; border-left: 3px solid #2d6a9f;
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
            <p>部門共用 — Dcard 熱門關鍵字追蹤</p>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("👤 輸入你的名字", placeholder="例：小王")

        if st.button("🚀 進入系統", use_container_width=True, type="primary"):
            if username.strip():
                uid = create_user_id(username.strip())
                st.session_state.user_id = uid
                st.session_state.username = username.strip()
                st.session_state.page = "scan"
                st.rerun()
            else:
                st.error("請輸入名字")

        st.divider()
        st.markdown("""
        **📡 部門共用版功能**
        - 🏷️ 關鍵字全部門共用 — 任何人都能新增
        - 📋 掃描結果即時共享 — 一人貼上，大家看
        - 📊 個人掃描紀錄獨立保存
        - ⚡ 完全免費，不需 API Key
        """)

else:
    user_id = st.session_state.user_id
    username = st.session_state.username
    shared = load_shared()
    user_data = load_user(user_id)

    if "page" not in st.session_state:
        st.session_state.page = "scan"

    # --- 側邊欄 ---
    with st.sidebar:
        st.markdown(f"### 📡 {username}")
        st.markdown(f"<span class='team-badge'>👥 部門共用</span>", unsafe_allow_html=True)
        st.caption(f"共用關鍵字：{len(shared.get('keywords', []))} 組")
        st.divider()

        pages = {
            "scan": "🔍 掃描熱門",
            "keywords": "🏷️ 關鍵字管理",
            "history": "📊 我的紀錄",
            "team_log": "📋 團隊掃描記錄",
            "settings": "⚙️ 設定",
        }
        for key, label in pages.items():
            btn_type = "primary" if st.session_state.page == key else "secondary"
            if st.button(label, use_container_width=True, key=f"nav_{key}", type=btn_type):
                st.session_state.page = key
                st.rerun()

        st.divider()
        kws = shared.get("keywords", [])
        if kws:
            st.caption("📌 團隊追蹤中：")
            for kw in kws[:10]:
                st.markdown(f"<span class='forum-tag'>{kw}</span>", unsafe_allow_html=True)
            if len(kws) > 10:
                st.caption(f"...還有 {len(kws) - 10} 個")

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
            <p>從 Dcard 複製熱門文章標題，AI 秒比對關鍵字</p>
        </div>
        """, unsafe_allow_html=True)

        # 重新讀取共用資料（確保最新）
        shared = load_shared()
        keywords = shared.get("keywords", [])

        if not keywords:
            st.warning("⚠️ 團隊還沒有設定任何關鍵字，請先到「關鍵字管理」新增。")
            if st.button("👉 前往設定", type="primary"):
                st.session_state.page = "keywords"
                st.rerun()
        else:
            st.write(f"團隊追蹤關鍵字：**{' / '.join(keywords)}**")
            st.divider()

            # === 操作說明 ===
            with st.expander("📖 怎麼操作？（點我展開）", expanded=False):
                st.markdown("""
                **三步驟：**
                1. 打開 [Dcard 即時熱門](https://www.dcard.tw/f) 或任一看板的熱門頁
                2. 用滑鼠選取文章標題 → 複製（Ctrl+C）
                3. 貼到下方文字框 → 點「比對關鍵字」

                **小技巧：**
                - 可以一次複製多個標題，每行一個
                - 也可以直接複製整段（工具會自動清理格式）
                - 建議每天早上掃一次，追蹤聲量變化
                """)

            # === 輸入區 ===
            forum_source = st.selectbox(
                "這批文章來自哪個看板？",
                options=["即時熱門"] + [DCARD_FORUMS[k] for k in shared.get("tracked_forums", []) if k != "popular"],
                key="forum_source"
            )

            manual_text = st.text_area(
                "📋 貼上文章標題（每行一個）",
                height=250,
                placeholder="從 Dcard 複製標題貼到這裡...\n\n例：\n有人跟我一樣覺得XX品牌很好用嗎\n推薦一個超讚的保養品\n今天去吃了一家超好吃的店",
                key="manual_input"
            )

            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn1:
                scan_clicked = st.button("🔍 比對關鍵字", use_container_width=True, type="primary", key="btn_scan")
            with col_btn2:
                clear_clicked = st.button("🗑️ 清除", use_container_width=True, key="btn_clear")

            if clear_clicked:
                if "scan_results" in st.session_state:
                    del st.session_state.scan_results
                st.rerun()

            if scan_clicked:
                if not manual_text.strip():
                    st.error("請先貼上文章標題")
                else:
                    articles = parse_manual_input(manual_text)

                    if not articles:
                        st.error("沒有偵測到有效的標題，請確認格式")
                    else:
                        for a in articles:
                            a["forum"] = forum_source

                        matches = match_keywords(articles, keywords)

                        scan_result = {
                            "matches": matches,
                            "total_articles": len(articles),
                            "forum": forum_source,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "scanned_by": username,
                        }
                        st.session_state.scan_results = scan_result

                        # 存到個人歷史
                        record = {
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "forum": forum_source,
                            "total_articles": len(articles),
                            "matches": len(matches),
                            "matched_titles": [m["title"] for m in matches[:10]],
                            "matched_keywords": list(set(
                                kw for m in matches for kw in m.get("matched_keywords", [])
                            )),
                        }
                        user_data.setdefault("my_scan_history", []).append(record)
                        save_user(user_id, user_data)

                        # 存到團隊掃描記錄
                        team_record = {**record, "scanned_by": username}
                        shared.setdefault("scan_log", []).append(team_record)
                        shared["last_scan"] = scan_result
                        save_shared(shared)

            # === 顯示結果 ===
            results = st.session_state.get("scan_results") or shared.get("last_scan")

            if results:
                st.divider()

                # 是誰掃描的
                scanned_by = results.get("scanned_by", "未知")
                scan_time = results.get("timestamp", "")
                st.caption(f"📡 由 **{scanned_by}** 於 {scan_time} 掃描")

                c1, c2, c3 = st.columns(3)
                c1.metric("📋 掃描文章", results["total_articles"])
                c2.metric("🎯 命中數", len(results["matches"]))
                c3.metric("📌 看板", results.get("forum", ""))

                st.divider()

                if results["matches"]:
                    st.markdown("""
                    <div class="alert-banner">
                        <h2 style="margin:0;">🚨 發現命中！</h2>
                        <p style="margin:0.3rem 0 0 0;">以下文章標題包含團隊追蹤的關鍵字</p>
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
                        </div>
                        """, unsafe_allow_html=True)

                        if match.get("link"):
                            st.link_button("🔗 查看原文", match["link"])
                else:
                    st.success("✅ 目前沒有命中任何關鍵字，一切平靜。")

    # ==================== 🏷️ 關鍵字管理 ====================
    elif st.session_state.page == "keywords":
        st.markdown("""
        <div class="main-header">
            <h1>🏷️ 團隊關鍵字管理</h1>
            <p>全部門共用 — 任何人都能新增或刪除</p>
        </div>
        """, unsafe_allow_html=True)

        shared = load_shared()
        keywords = shared.get("keywords", [])

        # 新增
        st.subheader("➕ 新增關鍵字")
        st.caption("支援 `|` 做 OR 搜尋，例如 `品牌A|品牌B` 表示任一出現就算命中")

        col1, col2 = st.columns([3, 1])
        with col1:
            new_kw = st.text_input("輸入關鍵字", placeholder="例：品牌名稱、產品名、競品名", key="new_kw")
        with col2:
            st.write("")
            st.write("")
            if st.button("➕ 新增", use_container_width=True, type="primary", key="btn_add"):
                if new_kw.strip():
                    if new_kw.strip() not in keywords:
                        keywords.append(new_kw.strip())
                        shared["keywords"] = keywords
                        save_shared(shared)
                        st.success(f"✅ 已新增：{new_kw}（by {username}）")
                        st.rerun()
                    else:
                        st.warning("這個關鍵字已經存在了")
                else:
                    st.error("請輸入關鍵字")

        # 批次新增
        with st.expander("📦 批次新增（每行一個）"):
            batch = st.text_area("每行一個關鍵字", height=120, key="batch")
            if st.button("批次新增", key="btn_batch"):
                new_kws = [k.strip() for k in batch.split("\n") if k.strip()]
                added = 0
                for kw in new_kws:
                    if kw not in keywords:
                        keywords.append(kw)
                        added += 1
                shared["keywords"] = keywords
                save_shared(shared)
                st.success(f"✅ 新增了 {added} 個關鍵字（by {username}）")
                st.rerun()

        st.divider()

        # 列表
        st.subheader(f"📋 目前團隊追蹤（{len(keywords)} 個）")

        if keywords:
            for i, kw in enumerate(keywords):
                col_kw, col_del = st.columns([5, 1])
                with col_kw:
                    display = f" **或** ".join(kw.split("|")) if "|" in kw else kw
                    st.write(f"**{i+1}.** {display}")
                with col_del:
                    if st.button("🗑️", key=f"del_{i}", help="刪除此關鍵字"):
                        keywords.pop(i)
                        shared["keywords"] = keywords
                        save_shared(shared)
                        st.rerun()

            st.divider()
            if st.button("🗑️ 清除全部關鍵字", use_container_width=True):
                shared["keywords"] = []
                save_shared(shared)
                st.rerun()
        else:
            st.info("團隊還沒有設定任何關鍵字，從上方開始新增吧！")

        st.divider()

        # 看板設定
        st.subheader("📌 預設掃描看板")
        tracked = shared.get("tracked_forums", ["popular"])
        new_tracked = st.multiselect(
            "選擇預設看板（掃描頁面會顯示在下拉選單）",
            options=list(DCARD_FORUMS.keys()),
            default=[f for f in tracked if f in DCARD_FORUMS],
            format_func=lambda x: DCARD_FORUMS.get(x, x),
            key="default_forums"
        )
        if new_tracked != tracked:
            shared["tracked_forums"] = new_tracked
            save_shared(shared)
            st.success("✅ 看板設定已更新")

    # ==================== 📊 我的紀錄 ====================
    elif st.session_state.page == "history":
        st.markdown("""
        <div class="main-header">
            <h1>📊 我的掃描紀錄</h1>
            <p>你個人的掃描歷史與統計</p>
        </div>
        """, unsafe_allow_html=True)

        user_data = load_user(user_id)
        history = user_data.get("my_scan_history", [])

        if history:
            total_scans = len(history)
            total_matches = sum(h.get("matches", 0) for h in history)
            all_kws = []
            for h in history:
                all_kws.extend(h.get("matched_keywords", []))

            c1, c2, c3 = st.columns(3)
            c1.metric("📊 我的掃描次數", total_scans)
            c2.metric("🎯 累計命中", total_matches)
            c3.metric("🏷️ 命中關鍵字種類", len(set(all_kws)))

            st.divider()

            if all_kws:
                st.subheader("🔥 我最常命中的關鍵字")
                from collections import Counter
                for kw, count in Counter(all_kws).most_common(10):
                    st.write(f"• **{kw}** — {count} 次")

            st.divider()
            st.subheader("📝 掃描紀錄")
            for h in reversed(history[-30:]):
                emoji = "🎯" if h.get("matches", 0) > 0 else "✅"
                with st.expander(f"{emoji} {h.get('date', '')} | {h.get('forum', '')} — 命中 {h.get('matches', 0)}"):
                    if h.get("matched_titles"):
                        for t in h["matched_titles"]:
                            st.write(f"• {t}")
                    if h.get("matched_keywords"):
                        st.write(f"**關鍵字：** {', '.join(h['matched_keywords'])}")

            st.divider()
            if st.button("🗑️ 清除我的紀錄", use_container_width=True):
                user_data["my_scan_history"] = []
                save_user(user_id, user_data)
                st.rerun()
        else:
            st.info("你還沒有掃描紀錄，去「掃描熱門」試試吧！")

    # ==================== 📋 團隊掃描記錄 ====================
    elif st.session_state.page == "team_log":
        st.markdown("""
        <div class="main-header">
            <h1>📋 團隊掃描記錄</h1>
            <p>所有成員的掃描結果彙整</p>
        </div>
        """, unsafe_allow_html=True)

        shared = load_shared()
        scan_log = shared.get("scan_log", [])

        if scan_log:
            # 統計
            unique_scanners = list(set(s.get("scanned_by", "?") for s in scan_log))
            total_matches = sum(s.get("matches", 0) for s in scan_log)

            c1, c2, c3 = st.columns(3)
            c1.metric("📊 總掃描次數", len(scan_log))
            c2.metric("🎯 團隊總命中", total_matches)
            c3.metric("👥 參與人數", len(unique_scanners))

            st.divider()

            # 誰掃描了多少次
            st.subheader("👥 團隊成員貢獻")
            from collections import Counter
            scanner_counts = Counter(s.get("scanned_by", "?") for s in scan_log)
            for name, count in scanner_counts.most_common():
                st.write(f"• **{name}** — 掃描 {count} 次")

            st.divider()

            # 全部命中紀錄
            st.subheader("📝 掃描紀錄（最新在前）")
            for entry in reversed(scan_log[-50:]):
                emoji = "🎯" if entry.get("matches", 0) > 0 else "✅"
                label = f"{emoji} {entry.get('date', '')} | {entry.get('scanned_by', '?')} | {entry.get('forum', '')} — 命中 {entry.get('matches', 0)}"
                with st.expander(label):
                    if entry.get("matched_titles"):
                        for t in entry["matched_titles"]:
                            st.write(f"• {t}")
                    if entry.get("matched_keywords"):
                        st.write(f"**關鍵字：** {', '.join(entry['matched_keywords'])}")

            st.divider()
            if st.button("🗑️ 清除團隊記錄", use_container_width=True):
                shared["scan_log"] = []
                shared["last_scan"] = None
                save_shared(shared)
                st.rerun()
        else:
            st.info("團隊還沒有掃描紀錄")

    # ==================== ⚙️ 設定 ====================
    elif st.session_state.page == "settings":
        st.markdown("""
        <div class="main-header">
            <h1>⚙️ 設定</h1>
            <p>工具說明與資料管理</p>
        </div>
        """, unsafe_allow_html=True)

        shared = load_shared()

        st.subheader("📊 系統狀態")
        c1, c2, c3 = st.columns(3)
        c1.metric("🏷️ 共用關鍵字", len(shared.get("keywords", [])))
        c2.metric("📋 團隊掃描次數", len(shared.get("scan_log", [])))
        c3.metric("📌 追蹤看板數", len(shared.get("tracked_forums", [])))

        st.divider()

        st.subheader("📖 使用說明")
        st.markdown("""
        **每日操作流程（建議每天早上 10 點）：**

        1. 打開 [Dcard 即時熱門](https://www.dcard.tw/f)
        2. 選取頁面上的文章標題（可以用 Ctrl+A 全選）
        3. 複製（Ctrl+C）
        4. 回到 DcardRadar → 掃描熱門頁
        5. 貼上（Ctrl+V）→ 點「比對關鍵字」
        6. 命中的文章會用黃色卡片標示

        **看板操作同理：**
        - 打開 Dcard 特定看板（如 [美妝版](https://www.dcard.tw/f/makeup)）
        - 複製標題 → 貼上 → 選擇對應看板 → 比對

        **關鍵字語法：**
        - 一般關鍵字：`品牌名` → 標題含有「品牌名」就命中
        - OR 語法：`品牌A|品牌B` → 任一出現就命中
        - 不分大小寫
        """)

        st.divider()

        # 匯出
        st.subheader("📥 匯出團隊設定")
        if st.button("📥 匯出 JSON", use_container_width=True):
            export = {
                "keywords": shared.get("keywords", []),
                "tracked_forums": shared.get("tracked_forums", []),
            }
            st.json(export)

        st.divider()
        st.markdown("""
        **📡 DcardRadar v2.0 — 部門共用版**

        - ✅ 團隊共用關鍵字
        - ✅ 掃描結果共享
        - ✅ 個人掃描紀錄獨立
        - ✅ 團隊掃描記錄彙整
        - ✅ 成員貢獻統計
        - ✅ 完全免費，不需 API Key
        - ✅ 部署在 Streamlit Cloud，同事打開連結就能用
        """)
