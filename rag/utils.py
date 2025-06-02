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

def load_multi_llm_config():
    """
    支持多 LLM 配置，返回 [(base_url, api_key, model, name)]
    """
    config_path = Path(__file__).parent.parent / "config" / "api_keys.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    llm_list = []
    # deepseek-chat
    llm_conf = config.get("llm", {})
    if llm_conf.get("base_url") and llm_conf.get("api_key"):
        llm_list.append((llm_conf["base_url"], llm_conf["api_key"], llm_conf.get("model", "deepseek-chat"), "deepseek-chat"))
    # 支持 gpt-3.5-turbo 等
    if "llm_extra" in config:
        for item in config["llm_extra"]:
            if item.get("base_url") and item.get("api_key"):
                llm_list.append((item["base_url"], item["api_key"], item.get("model", "gpt-3.5-turbo"), item.get("name", item.get("model", "gpt-3.5-turbo"))))
    return llm_list
