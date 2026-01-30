from pathlib import Path
import subprocess

# ===== 可调参数 =====
SEGMENTS_PER_CHAPTER = 12   # 每章包含多少段 mp3
# ===================

BOOKS_DIR = Path("books")


def merge_book(book_dir: Path):
    mp3_files = sorted(book_dir.glob("*.mp3"))
    if not mp3_files:
        return

    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)

    for i in range(0, len(mp3_files), SEGMENTS_PER_CHAPTER):
        chunk = mp3_files[i:i + SEGMENTS_PER_CHAPTER]
        chapter_idx = i // SEGMENTS_PER_CHAPTER

        list_file = chapters_dir / f"list_{chapter_idx:02d}.txt"
        output_mp3 = chapters_dir / f"chapter_{chapter_idx:02d}.mp3"

        # 生成 ffmpeg concat 列表
        with open(list_file, "w", encoding="utf-8") as f:
            for mp3 in chunk:
                # 注意路径中的反斜杠和空格
                f.write(f"file '{mp3.resolve()}'\n")

        # 调用 ffmpeg 合并
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_mp3)
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f"✅ 生成章节：{output_mp3.name}")


def main():
    for book in BOOKS_DIR.iterdir():
        if book.is_dir():
            print(f"\n📘 合并章节：{book.name}")
            merge_book(book)


if __name__ == "__main__":
    main()
