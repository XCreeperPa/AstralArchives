import asyncio
import sys
import os
import subprocess
import importlib

async def automated_workflow():
    print("[2/4] 启动爬虫 ...")
    print("自动抓取《崩坏：星穹铁道》的Wiki数据，配置见 config/categories.json。\n")
    # 动态导入依赖模块
    crawl_menu = importlib.import_module('ui.crawl_view').crawl_menu
    await crawl_menu()
    print("爬虫任务完成，数据已保存到 wiki/ 目录。\n")

    print("[3/4] 清洗数据 ...")
    print("对抓取到的原始数据进行清洗和结构化，结果保存到 wiki_cleaned/ 目录。\n")
    clean_data_menu = importlib.import_module('ui.clean_data_view').clean_data_menu
    clean_data_menu()
    print("数据清洗完成，结构化数据已保存。\n")

    print("[4/4] 数据嵌入 ...")
    print("对清洗后的数据进行向量化嵌入，结果保存到 db/ 目录。\n")
    embed_data_menu = importlib.import_module('ui.embed_data_view').embed_data_menu
    embed_data_menu()
    print("数据嵌入完成，向量数据库已生成。\n")

    print("[bold green]自动化工作流全部完成！[/bold green]" if 'rprint' in locals() else "自动化工作流全部完成！")
    print("您现在可以继续使用星穹智库的其他功能，例如启动RAG问答界面或OpenAI兼容API服务端。\n感谢您的使用！")

if __name__ == "__main__":
    # 步骤1：使用ANSI控制字符高亮欢迎信息（无需依赖rich）
    print("\033[1;36m\n==============================\n星穹智库自动化工作流\n==============================\033[0m")
    print("\033[1;32m欢迎使用星穹智库自动化脚本！\033[0m")
    print("\033[1;33m本脚本将引导您完成环境设置、依赖安装以及核心数据处理流程。\033[0m\n")

    # 步骤2：环境检测与依赖安装
    in_venv = sys.prefix != sys.base_prefix
    if not os.path.exists(".venv"):
        print("[1/4] 正在创建虚拟环境 (.venv)...")
        subprocess.check_call([sys.executable, "-m", "venv", ".venv"])
        print("虚拟环境创建成功！")
    else:
        print("[1/4] 虚拟环境 (.venv) 已存在。")

    if not in_venv:
        venv_python = os.path.join(".venv", "bin", "python")
        print("[1/4] 正在使用虚拟环境的Python重新运行 auto_build.py ...")
        subprocess.check_call([venv_python, __file__])
        sys.exit(0)

    print("[1/4] 正在安装依赖（uv sync）...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uv"])
        subprocess.check_call([sys.executable, "-m", "uv", "sync"])
    except Exception as e:
        print(f"uv 安装或依赖同步失败: {e}")
        print("请手动检查依赖安装问题。")
        sys.exit(1)

    # 步骤3：依赖安装后再导入和运行主流程
    asyncio.run(automated_workflow())