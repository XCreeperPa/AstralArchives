# rag/db.py
"""
数据库检索相关接口，便于后续扩展多种检索方式。
"""
from pathlib import Path
import json
from vector_api.main_embedding import search_all_in_one_meta, load_from_zip

def search_db(keywords, top_k=5):
    db_zip_path = str(Path(__file__).parent.parent / "db" / "wiki_allinone.zip")
    config_path = Path(__file__).parent.parent / "config" / "api_keys.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    api_url = config.get("embedding", {}).get("api_url", "https://api.siliconflow.cn/v1/embeddings")
    api_key = config.get("embedding", {}).get("api_key")
    results = search_all_in_one_meta(keywords, db_zip_path, api_url, api_key, top_k=top_k)
    return results

def build_context_from_db(meta_list, max_chars=64000):
    db_zip_path = str(Path(__file__).parent.parent / "db" / "wiki_allinone.zip")
    _, id2meta, id2content, _, _ = load_from_zip(db_zip_path)
    context = ""
    used = set()
    for meta in meta_list:
        for idx, m in id2meta.items():
            if m == meta and idx not in used:
                fragment = id2content[idx]
                if len(context) + len(fragment) > max_chars:
                    return context
                context += f"\n【资料片段】{fragment}\n"
                used.add(idx)
    return context
