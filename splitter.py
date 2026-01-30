import re

def split_for_audio(text: str, max_chars=700):
    """
    继承您验证成功的 700 字逻辑
    """
    sentences = re.split(r"(?<=[。！？；.!?])", text)
    chunks = []
    current = ""
    for s in sentences:
        s = s.strip()
        if not s: continue
        if len(current) + len(s) <= max_chars:
            current += s
        else:
            if current.strip(): chunks.append(current.strip())
            current = s
    if current.strip(): chunks.append(current.strip())
    return chunks