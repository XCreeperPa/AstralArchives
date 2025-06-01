from rich.console import Console
from rich.prompt import Prompt
from vector_api.main_embedding import search_all_in_one_meta
import numpy as np
import json
import os

def search_data_menu():
    console = Console()
    console.clear()
    console.rule("[bold cyan]检索数据")

    # 提示用户输入查询关键词
    query = Prompt.ask("请输入查询关键词")

    # 读取配置文件以获取 API URL 和密钥
    with open("config/api_keys.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    api_url = "https://api.siliconflow.cn/v1/embeddings"
    api_key = config["embedding"]["api_key"]

    # 检索向量数据库
    try:
        db_zip_path = "./db/wiki_allinone.zip"
        top_k = 10
        results = search_all_in_one_meta(query, db_zip_path, api_url, api_key, top_k)
        console.print("[bold green]检索结果（前十）：")
        for result in results:
            console.print_json(data=result)
    except Exception as e:
        console.print(f"[bold red]检索失败: {e}")

    console.input("\n按回车返回主菜单...")
