import re


def clean_text(raw: str) -> str:
    lines = raw.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # 页码
        if re.fullmatch(r"\d+", line):
            continue

        # 图表
        if line.lower().startswith(("figure", "fig.", "table")):
            continue

        # 参考文献
        if re.match(r"(references|bibliography)", line.lower()):
            break

        # 公式（简单过滤）
        if any(sym in line for sym in ["=", "∑", "∫", "λ"]):
            continue

        cleaned.append(line)

    text = " ".join(cleaned)
    text = re.sub(r"\s{2,}", " ", text)
    return text
