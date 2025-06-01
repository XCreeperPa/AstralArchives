import sys
import asyncio
from rich.console import Console
from rich.prompt import Prompt

from ui.category_manage_view import category_manage_menu
from .readme_view import show_readme
from .crawl_view import crawl_menu
from .category_manage_view import category_manage_menu

console = Console()

async def main_menu():
    while True:
        console.clear()
        console.rule("[bold cyan]星穹智库 - 主菜单")
        console.print("[bold]请选择操作：")
        console.print("[yellow]0.[/] 退出")
        console.print("[yellow]1.[/] 查看README")
        console.print("[yellow]2.[/] 启动爬虫")
        console.print("[yellow]3.[/] 管理分类 (config/categories.json)")
        console.print("[yellow]4.[/] 清洗数据")
        choice = Prompt.ask("输入序号", choices=["0","1","2","3","4"], default="0")
        if choice == "0":
            console.print("[green]再见！")
            sys.exit(0)
        elif choice == "1":
            show_readme()
        elif choice == "2":
            await crawl_menu()
        elif choice == "3":
            category_manage_menu()
        elif choice == "4":
            from .clean_data_view import clean_data_menu
            clean_data_menu()

if __name__ == "__main__":
    asyncio.run(main_menu())
