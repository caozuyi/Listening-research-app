import streamlit as st
import os, shutil, re, subprocess, base64, time
from pathlib import Path

# =====================================================
# 页面配置 & 样式（彻底修复 sidebar 白色按钮）
# =====================================================
st.set_page_config(page_title="科研听书工坊-专业版", layout="wide")

st.markdown("""
<style>
/* ================================
   Sidebar 整体背景
================================ */
[data-testid="stSidebar"] {
    background-color: #111827 !important;
}
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* ================================
   Sidebar Button
================================ */
[data-testid="stSidebar"] button {
    background-color: #1f2937 !important;
    border: 1px solid #374151 !important;
    color: #ffffff !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] button:hover,
[data-testid="stSidebar"] button:focus,
[data-testid="stSidebar"] button:active {
    background-color: #374151 !important;
    color: #ffffff !important;
}

/* ================================
   ⭐ 关键修复：选择播音员（selectbox）
================================ */
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #1f2937 !important;
    border: 1px solid #374151 !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] span {
    color: #ffffff !important;
}

/* 下拉展开的选项 */
ul[role="listbox"] {
    background-color: #1f2937 !important;
}
ul[role="listbox"] li {
    color: #ffffff !important;
}
ul[role="listbox"] li:hover {
    background-color: #374151 !important;
}

/* ================================
   语速调节（slider）
================================ */
[data-testid="stSidebar"] div[data-baseweb="slider"] {
    color: #ffffff !important;
}
[data-testid="stSidebar"] div[data-baseweb="slider"] > div {
    background-color: #374151 !important;
}

/* ================================
   书卡
================================ */
.book-card {
    border-left: 5px solid #2563EB;
    padding: 12px;
    margin-bottom: 12px;
    background: #f8fafc;
    border-radius: 6px;
}
.format-tag {
    background: #374151;
    color: #f9fafb;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    margin-right: 8px;
}

/* ================================
   自动切章隐藏按钮
================================ */
button[title="auto-next"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# Sidebar 控制中心
# =====================================================
with st.sidebar:
    st.markdown("## ⚙️ 听书设置")

    # ⭐ 4 个播音员：男/女 × 专业/休闲
    voice_map = {
        "云希（男｜专业）": "zh-CN-YunxiNeural",
        "云扬（男｜休闲）": "zh-CN-YunyangNeural",
        "晓晓（女｜专业）": "zh-CN-XiaoxiaoNeural",
        "晓曼（女｜休闲）": "zh-CN-XiaomanNeural"
    }

    st.selectbox("选择播音员", list(voice_map.keys()), key="voice_label")
    st.select_slider("语速调节", ["-20%", "正常", "+20%"], value="正常", key="rate_label")

    if st.button("🗑 清空整个书架"):
        shutil.rmtree("books", ignore_errors=True)
        Path("books").mkdir(exist_ok=True)
        st.rerun()

# =====================================================
# TTS 参数获取（让 Sidebar 设置真正生效）
# =====================================================
def get_tts_config():
    # 播音员
    voice = voice_map[st.session_state.voice_label]

    # 语速
    rate_map = {
        "-20%": "-20%",
        "正常": "0%",
        "+20%": "+20%"
    }
    rate = rate_map[st.session_state.rate_label]

    return voice, rate


# =====================================================
# 核心模块
# =====================================================
from ingest import load_document
from cleaner import clean_text
from splitter import split_for_audio
from tts import text_to_mp3

BASE_DIR = Path(__file__).parent.resolve()
BOOKS_DIR = BASE_DIR / "books"
BOOKS_DIR.mkdir(exist_ok=True)

# =====================================================
# Session State
# =====================================================
for k, v in {
    "shelf_playing_book": None,
    "shelf_chapter_idx": {},
    "active_book": None,
    "play_idx": 0
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# 工具函数
# =====================================================
def get_book_format(book_dir):
    fmt = book_dir / "format.txt"
    if fmt.exists():
        return fmt.read_text().replace(".", "").upper()
    src = list(book_dir.glob("source.*"))
    return src[0].suffix.replace(".", "").upper() if src else "UNK"

def render_chapter_player(mp3_path, book_id):
    with open(mp3_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.components.v1.html(f"""
    <audio id="player-{book_id}" controls autoplay style="width:100%">
      <source src="data:audio/mp3;base64,{b64}">
    </audio>
    <script>
      document.getElementById("player-{book_id}").onended = function() {{
        var btns = window.parent.document.querySelectorAll("button");
        for (var b of btns) {{
          if (b.innerText.includes("NEXT_CH_{book_id}")) {{
            b.click(); break;
          }}
        }}
      }};
    </script>
    """, height=70)

# =====================================================
# Tabs
# =====================================================
t1, t2, t3 = st.tabs(["📥 批量导入", "📚 智能书架", "📖 同步阅读"])

# =====================================================
# 📥 批量导入（详细进度）
# =====================================================
with t1:
    st.markdown("### 支持格式：PDF / DOCX / TXT / EPUB / MOBI")

    files = st.file_uploader(
        "可多选上传文献",
        type=["pdf", "docx", "txt", "epub", "mobi"],
        accept_multiple_files=True
    )

    if files and st.button("🚀 开始转化"):
        for f in files:
            book_name = re.sub(r"[^\w\u4e00-\u9fa5]", "_", Path(f.name).stem)
            book_dir = BOOKS_DIR / book_name
            book_dir.mkdir(exist_ok=True)
            (book_dir / "segments").mkdir(exist_ok=True)
            (book_dir / "chapters").mkdir(exist_ok=True)

            ext = Path(f.name).suffix
            (book_dir / "format.txt").write_text(ext)

            with open(book_dir / f"source{ext}", "wb") as wf:
                wf.write(f.getbuffer())

            with st.status(f"📘 正在处理：{f.name}") as status:
                status.write("📄 读取文献")
                raw = load_document(book_dir / f"source{ext}")

                status.write("🧹 清洗文本")
                cleaned = clean_text(raw)

                status.write("✂️ 切分文本")
                chunks = split_for_audio(cleaned)

                prog = st.progress(0)
                mp3s = []

                # ⭐ TTS 参数（作用域正确）
                voice, rate = get_tts_config()

                for i, c in enumerate(chunks):
                    seg_txt = book_dir / "segments" / f"{i:03d}.txt"
                    seg_txt.write_text(c, encoding="utf-8")

                    mp3 = book_dir / f"{i:03d}.mp3"
                    text_to_mp3(c, mp3, voice=voice, rate=rate)
                    mp3s.append(mp3)

                    prog.progress((i + 1) / len(chunks))
                    status.write(f"🔊 转化音频 {i+1}/{len(chunks)}")

                status.write("📦 合并章节")
                for i in range(0, len(mp3s), 10):
                    batch = mp3s[i:i+10]
                    list_file = book_dir / "list.txt"
                    with open(list_file, "w", encoding="utf-8") as lf:
                        for m in batch:
                            lf.write(f"file '{m.name}'\n")

                    out = book_dir / "chapters" / f"chapter_{i//10+1:02d}.mp3"
                    subprocess.run(
                        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                         "-i", list_file, "-c", "copy", out],
                        capture_output=True
                    )

                status.update(label=f"✅ 完成：{f.name}", state="complete")

        st.rerun()

# =====================================================
# 📚 智能书架（含删除）
# =====================================================
with t2:
    books = sorted([d for d in BOOKS_DIR.iterdir() if d.is_dir()])

    for book in books:
        fmt = get_book_format(book)
        colA, colB = st.columns([8, 1])

        with colA:
            st.markdown(
                f"<div class='book-card'><span class='format-tag'>{fmt}</span><b>{book.name}</b></div>",
                unsafe_allow_html=True
            )

        with colB:
            if st.button("🗑", key=f"del_{book.name}"):
                shutil.rmtree(book, ignore_errors=True)
                if st.session_state.active_book == book.name:
                    st.session_state.active_book = None
                if st.session_state.shelf_playing_book == book.name:
                    st.session_state.shelf_playing_book = None
                st.rerun()

        chapters = sorted((book / "chapters").glob("*.mp3"))
        if not chapters:
            continue

        if book.name not in st.session_state.shelf_chapter_idx:
            st.session_state.shelf_chapter_idx[book.name] = 0

        cur = st.session_state.shelf_chapter_idx[book.name]

        if st.button(
            f"NEXT_CH_{book.name}",
            key=f"hidden_next_{book.name}",
            help="auto-next"
        ):
            if cur < len(chapters) - 1:
                st.session_state.shelf_chapter_idx[book.name] += 1
                st.rerun()

        c1, c2, c3 = st.columns([1.2, 1.5, 4])

        with c1:
            if st.button("🎧 试听", key=f"play_{book.name}"):
                st.session_state.shelf_playing_book = book.name
                st.rerun()

        with c2:
            sel = st.selectbox(
                "章节",
                list(range(1, len(chapters) + 1)),
                index=cur,
                key=f"sel_{book.name}"
            )
            st.session_state.shelf_chapter_idx[book.name] = sel - 1

        with c3:
            if st.session_state.shelf_playing_book == book.name:
                render_chapter_player(
                    chapters[st.session_state.shelf_chapter_idx[book.name]],
                    book.name
                )

        if st.button("📖 阅读", key=f"read_{book.name}"):
            st.session_state.active_book = book.name
            st.session_state.play_idx = 0
            st.rerun()

# =====================================================
# 📖 同步阅读（保持原逻辑）
# =====================================================
with t3:
    if not st.session_state.active_book:
        st.info("请从智能书架选择一本书")
    else:
        bp = BOOKS_DIR / st.session_state.active_book
        segs = sorted((bp / "segments").glob("*.txt"))

        st.subheader(f"📖 同步阅读：{bp.name}")

        if not segs:
            st.info("该书暂无逐段文本，仅支持章节音频播放")
            chapters = sorted((bp / "chapters").glob("*.mp3"))
            if chapters:
                render_chapter_player(chapters[0], bp.name)
        else:
            idx = min(st.session_state.play_idx, len(segs) - 1)
            st.session_state.play_idx = idx

            st.markdown(
                f"<div style='padding:20px;border:2px solid #f59e0b;border-radius:8px'>{segs[idx].read_text(encoding='utf-8')}</div>",
                unsafe_allow_html=True
            )

            audio = bp / f"{idx:03d}.mp3"
            if audio.exists():
                with open(audio, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                st.components.v1.html(f"""
                <audio id="rd" controls autoplay style="width:100%">
                  <source src="data:audio/mp3;base64,{b64}">
                </audio>
                <script>
                  document.getElementById("rd").onended = function() {{
                    var btns = window.parent.document.querySelectorAll("button");
                    for (var b of btns) {{
                      if (b.innerText.includes("下一段")) {{
                        b.click(); break;
                      }}
                    }}
                  }};
                </script>
                """, height=80)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("⬅ 上一段") and idx > 0:
                    st.session_state.play_idx -= 1
                    st.rerun()
            with c2:
                st.write(f"{idx+1}/{len(segs)}")
            with c3:
                if st.button("下一段 ➡") and idx < len(segs) - 1:
                    st.session_state.play_idx += 1
                    st.rerun()
