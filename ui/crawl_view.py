from rich.console import Console
import asyncio
from crawler.crawl_main import run_crawl

def crawl_menu():
    console = Console()
    console.clear()
    console.rule("[bold cyan]爬虫启动")
    try:
        asyncio.run(run_crawl(None))
    except KeyboardInterrupt:
        console.print("[red]用户中断。")
    except Exception as e:
        console.print(f"[red]程序异常终止: {e}")
    console.input("\n按回车返回主菜单...")
