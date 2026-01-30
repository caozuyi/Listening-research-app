from pathlib import Path
from tqdm import tqdm

from ingest import load_document
from cleaner import clean_text
from splitter import split_for_audio
from tts import text_to_mp3

# =========================
# 路径配置
# =========================
BASE_DIR = Path(__file__).parent
UPLOADS = BASE_DIR / "uploads"
BOOKS = BASE_DIR / "books"

UPLOADS.mkdir(exist_ok=True)
BOOKS.mkdir(exist_ok=True)


def build_audiobook(file_path: Path):
    """
    从单个文档生成听书：
    - 支持断点续跑
    - 已存在 mp3 自动跳过
    - 单段失败不影响整体
    """
    print(f"\n📖 Processing: {file_path.name}")

    # 1. 读取文档
    raw_text = load_document(file_path)

    # 2. 清洗文本
    cleaned_text = clean_text(raw_text)

    # 3. 切分为适合听的 chunk
    chunks = split_for_audio(cleaned_text)

    # 4. 创建输出目录
    book_dir = BOOKS / file_path.stem
    book_dir.mkdir(exist_ok=True)

    print(f"🔹 总段落数: {len(chunks)}")
    print(f"🔹 输出目录: {book_dir}")

    # 5. 逐段生成音频（断点续跑）
    for idx, chunk in enumerate(tqdm(chunks)):
        output_mp3 = book_dir / f"{idx:03d}.mp3"

        # 已存在则跳过（核心：支持断点续跑）
        if output_mp3.exists():
            continue

        try:
            text_to_mp3(chunk, output_mp3)
        except Exception as e:
            # 理论上 tts.py 已经兜底，这里再保险一次
            print(f"❌ 段落 {idx} 生成失败，已跳过。错误：{e}")
            continue

    print(f"✅ Audiobook ready: {book_dir}")


def main():
    """
    主入口：
    - 顺序处理 uploads 目录下所有文件
    - 一个文件失败不影响其他文件
    """
    files = [f for f in UPLOADS.iterdir() if f.is_file()]

    if not files:
        print("⚠️ uploads 目录中没有可处理的文件。")
        return

    print(f"📚 共发现 {len(files)} 个文件待处理。\n")

    for f in files:
        try:
            build_audiobook(f)
        except Exception as e:
            print(f"❌ 文件 {f.name} 处理失败，已跳过。错误：{e}")


if __name__ == "__main__":
    main()
