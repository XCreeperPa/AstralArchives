def slice_content(content, max_length=5000, context_length=50):
    """
    切片算法：将content字段切片为不超过max_length字符的片段，
    每个片段包含context_length字符的上下文。
    """
    slices = []
    start = 0
    while start < len(content):
        end = min(start + max_length, len(content))
        if end < len(content):
            while end > start and content[end] not in ['。', '！', '？', '\n']:
                end -= 1
            if end == start:
                end = start + max_length
        slice_start = max(0, start - context_length)
        slice_end = min(len(content), end + context_length)
        sliced_content = content[slice_start:slice_end]
        slices.append(sliced_content)
        start = end
    return slices
