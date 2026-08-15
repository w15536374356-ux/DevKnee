# 结构感知切块：按标题层级切分，保留语义边界；超长段落按字数切 + 前后重叠。
# 切块质量是 RAG 召回上限的源头，这里的花样面试常深挖。
MAX_CHUNK_LEN = 500
OVERLAP = 80


def chunk_segments(segments: list[dict]) -> list[dict]:
    """segments 来自 parser.parse_document。返回 [{"title", "content"}]。"""
    chunks: list[dict] = []
    heading_stack: list[str] = []  # 当前标题路径
    title_path: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            title = " / ".join(t for t in title_path if t) or ""
            chunks.append({"title": title, "content": "".join(current)})
        current = []
        current_len = 0

    for seg in segments:
        if seg["type"] == "heading":
            flush()
            level = seg["level"]
            # 同级或更上级标题出现 → 截断标题路径
            while heading_stack and len(heading_stack) >= level:
                heading_stack.pop()
                title_path.pop()
            heading_stack.append(seg["text"])
            title_path.append(seg["text"])
        else:
            text = seg["text"]
            if current_len + len(text) > MAX_CHUNK_LEN and current:
                # 保留尾部 OVERLAP 字符，避免切断语义
                tail = "".join(current)[-OVERLAP:]
                flush()
                if tail:
                    current.append(tail)
                    current_len = len(tail)
            current.append(text)
            current_len += len(text)

    flush()
    # 二次切分：单块超长（无标题分隔的大段正文）按字数硬切
    return _split_oversized(chunks)


def _split_oversized(chunks: list[dict]) -> list[dict]:
    result: list[dict] = []
    for chunk in chunks:
        content = chunk["content"]
        if len(content) <= MAX_CHUNK_LEN:
            result.append(chunk)
            continue
        parts = [
            content[i : i + MAX_CHUNK_LEN]
            for i in range(0, len(content), MAX_CHUNK_LEN - OVERLAP)
        ]
        for part in parts:
            result.append({"title": chunk["title"], "content": part})
    return result