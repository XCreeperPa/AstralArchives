from rich.console import Console
import json
from pathlib import Path
from crawler.crawl_main import run_crawl

async def crawl_menu():
    console = Console()
    console.clear()
    console.rule("[bold cyan]爬虫启动")
    # 直接读取所有 enabled 分类
    config_path = Path(__file__).parent.parent / "config/categories.json"
    if not config_path.exists():
        console.print("[red]未找到 config/categories.json！")
        return
    with open(config_path, "r", encoding="utf-8") as f:
        categories = json.load(f)
    enabled = [k for k, v in categories.items() if v.get("enabled")]
    if not enabled:
        console.print("[yellow]没有启用的分类，请先在 config/categories.json 启用分类。")
        return
    console.print(f"[green]将自动爬取以下分类：\n{', '.join(enabled)}")
    await run_crawl(enabled)
