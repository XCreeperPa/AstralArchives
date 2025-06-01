# rag/utils.py
"""
RAG相关工具函数，可根据后续需求扩展。
"""
import json
from pathlib import Path

def load_llm_config():
    config_path = Path(__file__).parent.parent / "config" / "api_keys.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    llm_conf = config.get("llm", {})
    return llm_conf.get("base_url"), llm_conf.get("api_key")

def load_embed_config():
    config_path = Path(__file__).parent.parent / "config" / "api_keys.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    embed_conf = config.get("embedding", {})
    return embed_conf.get("api_key")
