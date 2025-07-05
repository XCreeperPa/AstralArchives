from rich.console import Console
from rich.prompt import Prompt
from vector_api.main_embedding import embed_and_store_all_in_one
from pathlib import Path
import json

def embed_data_menu():
    console = Console()
    console.clear()
    console.rule("[bold cyan]数据嵌入")

    # 从配置文件读取API密钥
    config_path = Path("config/api_keys.json")
    if not config_path.exists():
        console.print("[bold red]未找到配置文件 config/api_keys.json")
   
        return

    with open(config_path, "r", encoding="utf-8") as f:
        api_config = json.load(f)
    api_key = api_config.get("embedding", {}).get("api_key")

    if not api_key:
        console.print("[bold red]未在配置文件中找到有效的API密钥")
   
        return

    # 嵌入数据
    try:
        embed_and_store_all_in_one(
            data_dir="wiki_cleaned",
            db_zip_path="./db/wiki_allinone.zip",
            api_url="https://api.siliconflow.cn/v1/embeddings",
            api_key=api_key
        )
        console.print("[bold green]数据嵌入完成！")
    except Exception as e:
        console.print(f"[bold red]嵌入失败: {e}")
