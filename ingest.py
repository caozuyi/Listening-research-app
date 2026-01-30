import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import pdfplumber
import docx
import mobi  # 新增
import os
import shutil
from pathlib import Path

def load_document(file_path):
    path = Path(file_path)
    ext = path.suffix.lower()

    # --- 1. 处理 TXT ---
    if ext == '.txt':
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # --- 2. 处理 PDF ---
    elif ext == '.pdf':
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        return text

    # --- 3. 处理 DOCX ---
    elif ext == '.docx':
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    # --- 4. 处理 EPUB ---
    elif ext == '.epub':
        book = epub.read_epub(str(path))
        chapters = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                chapters.append(soup.get_text())
        return "\n".join(chapters)

    # --- 5. 处理 MOBI (新增) ---
    elif ext == '.mobi':
        # mobi 库会将内容解压到一个临时目录
        temp_dir, html_file = mobi.extract(str(path))
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        # 提取纯文本并清理临时文件
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # 清理临时解压出的文件夹，保持环境干净
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return text

    else:
        raise ValueError(f"暂不支持的文件格式: {ext}")