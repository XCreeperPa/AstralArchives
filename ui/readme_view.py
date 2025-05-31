from rich.console import Console
from rich.markdown import Markdown
from pathlib import Path

def show_readme():
    console = Console()
    readme_path = Path(__file__).parent.parent / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            md = Markdown(f.read())
        console.clear()
        console.rule("[bold cyan]README")
        console.print(md)
        console.input("\n按回车返回主菜单...")
    else:
        console.print("[red]README.md 未找到！")
        console.input("\n按回车返回主菜单...")
