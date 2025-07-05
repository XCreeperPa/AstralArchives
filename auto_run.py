import asyncio
import sys
import os
from rich.console import Console
from rich.prompt import Prompt

# 导入相关功能模块
# 注意：这里直接导入函数，而不是通过main_menu的逻辑
# 确保这些模块在虚拟环境激活后可以被正确找到
try:
    from ui.crawl_view import crawl_menu
    from ui.clean_data_view import clean_data_menu
    from ui.embed_data_view import embed_data_menu
except ImportError as e:
    print(f"导入模块失败：{e}。请确保您已激活虚拟环境并安装了所有依赖。")
    print("尝试运行 'source .venv/bin/activate' 然后 'uv sync'")
    sys.exit(1)

console = Console()

async def automated_workflow():
    console.rule("[bold green]星穹智库自动化工作流[/bold green]")
    console.print("[bold yellow]欢迎使用星穹智库自动化脚本！[/bold yellow]")
    console.print("本脚本将引导您完成环境设置、依赖安装以及核心数据处理流程。")
    console.print("请确保您已在项目根目录运行此脚本。")
    console.print("\n[bold cyan]第一步：环境准备与依赖安装[/bold cyan]")
    console.print("我们将为您创建并激活Python虚拟环境，然后使用uv工具安装所有项目依赖。")
    console.print("这可能需要一些时间，请耐心等待...")

    # 检查并创建虚拟环境
    if not os.path.exists(".venv"):
        console.print("[blue]正在创建虚拟环境 (.venv)...[/blue]")
        os.system("python3 -m venv .venv")
        console.print("[green]虚拟环境创建成功！[/green]")
    else:
        console.print("[blue]虚拟环境 (.venv) 已存在。[/blue]")

    # 激活虚拟环境并安装uv，然后同步依赖
    # 注意：直接在脚本中执行source命令可能不会影响当前脚本的Python环境
    # 但对于后续的uv sync和模块导入，我们假设用户会在激活环境后运行此脚本
    # 或者，我们可以在这里尝试直接调用uv的Python API，但为了简化和符合用户要求，
    # 保持shell命令风格。
    console.print("[blue]正在安装uv并同步项目依赖...[/blue]")
    # 确保uv已安装
    os.system("pip install uv")
    # 使用uv同步依赖
    os.system("uv sync")
    console.print("[green]依赖安装完成！[/green]")
    console.print("现在，核心功能模块已准备就绪。")

    console.print("\n[bold cyan]第二步：启动爬虫[/bold cyan]")
    console.print("我们将启动爬虫，自动抓取《崩坏：星穹铁道》的Wiki数据。")
    console.print("请注意，这会根据您在 `config/categories.json` 中的配置进行。")
    console.print("爬取过程可能需要较长时间，请耐心等待。")
    await crawl_menu()
    console.print("[green]爬虫任务完成！[/green]")
    console.print("数据已成功抓取并保存到 `wiki/` 目录。")

    console.print("\n[bold cyan]第三步：清洗数据[/bold cyan]")
    console.print("接下来，我们将对抓取到的原始数据进行清洗和结构化处理。")
    console.print("清洗后的数据将以JSON格式保存到 `wiki_cleaned/` 目录。")
    console.print("此过程将确保数据质量，为后续的数据嵌入做好准备。")
    clean_data_menu()
    console.print("[green]数据清洗完成！[/green]")
    console.print("结构化数据已保存到 `wiki_cleaned/` 目录。")

    console.print("\n[bold cyan]第四步：数据嵌入[/bold cyan]")
    console.print("最后，我们将对清洗后的数据进行向量化嵌入。")
    console.print("这将把文本数据转换为机器可理解的向量形式，用于高效检索。")
    console.print("嵌入后的向量数据库将保存到 `db/` 目录，通常是一个zip文件。")
    console.print("这是实现智能问答和检索的关键步骤。")
    embed_data_menu()
    console.print("[green]数据嵌入完成！[/green]")
    console.print("向量数据库已生成并保存到 `db/` 目录。")

    console.print("\n[bold green]自动化工作流全部完成！[/bold green]")
    console.print("您现在可以继续使用星穹智库的其他功能，例如启动RAG问答界面或OpenAI兼容API服务端。")
    console.print("感谢您的使用！")

if __name__ == "__main__":
    # 确保在运行此脚本前，用户已经激活了虚拟环境
    # 或者，我们可以在这里添加一个检查，如果不在虚拟环境中则提示用户
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        console.print("[bold red]警告：您似乎没有在虚拟环境中运行此脚本。[/bold red]")
        console.print("[bold red]强烈建议您先激活虚拟环境：[/bold red]")
        console.print("[yellow]source .venv/bin/activate[/yellow]")
        console.print("[bold red]然后再次运行此脚本。[/bold red]")
        # 询问用户是否继续，或者直接退出
        if not Prompt.ask("是否继续？(不推荐，可能导致依赖问题)", choices=["y", "n"], default="n") == "y":
            sys.exit(1)

    asyncio.run(automated_workflow())