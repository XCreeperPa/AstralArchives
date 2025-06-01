from rich.console import Console
import subprocess
import sys
from pathlib import Path

def clean_data_menu():
    console = Console()
    console.clear()
    console.rule("[bold cyan]数据清洗")
    # 检查 mwparserfromhell
    try:
        import mwparserfromhell
    except ImportError:
        console.print("[red]未检测到 mwparserfromhell，正在尝试安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mwparserfromhell"])
        console.print("[green]已安装 mwparserfromhell。")
    # 检查 wiki 目录
    if not Path("wiki").exists():
        console.print("[red]未找到 wiki/ 目录，请先运行爬虫。")
        console.input("\n按回车返回主菜单...")
        return
    # 执行清洗
    from datacleaner.clean_main import clean_all
    clean_all()
    console.print("[bold green]数据清洗完成，结果已保存于 wiki_cleaned/ 目录。")
    console.input("\n按回车返回主菜单...")
