# rag/rag_service.py
"""
RAG 业务逻辑分离：检索、拼接资料、历史对话构造、token统计等
"""
from pathlib import Path
from rag.llm import extract_user_need
from rag.db import search_db

def get_user_need(llm, question, history_str=None):
    from rag.llm import extract_user_need_with_history, extract_user_need
    if history_str:
        return extract_user_need_with_history(llm, question, history_str)
    else:
        return extract_user_need(llm, question)

def retrieve_context(user_need, db_zip_path, top_k=5):
    meta_list = search_db(user_need, top_k=top_k)
    from vector_api.main_embedding import load_from_zip
    _, id2meta, id2content, _, _ = load_from_zip(db_zip_path)
    context_list = []
    used = set()
    for meta in meta_list:
        for idx, m in id2meta.items():
            if m == meta and idx not in used:
                fragment = id2content[idx]
                context_list.append(fragment)
                used.add(idx)
    merged_context = "\n".join(context_list)
    if len(merged_context) > 60000:
        merged_context = merged_context[:60000]
    return meta_list, merged_context

def build_history_str(history, turn_format, history_format):
    history_str = "\n".join([
        turn_format.format(user=h["user"], assistant=h["assistant"]) for h in history
    ]) if history else ""
    return history_format.format(history=history_str)

def count_tokens(text, encoding_name="cl100k_base"):
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return len(text)  # fallback: char count
