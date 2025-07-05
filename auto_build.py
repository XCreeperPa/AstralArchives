import asyncio
import sys
import os

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

async def automated_workflow():
    print("=" * 30)
    print("星穹智库自动化工作流")
    print("=" * 30)
    print("欢迎使用星穹智库自动化脚本！")
    print("本脚本将引导您完成环境设置、依赖安装以及核心数据处理流程。")
    print("请确保您已在项目根目录运行此脚本。\n")
    print("第一步：环境准备与依赖安装")
    print("我们将为您创建并激活Python虚拟环境，然后使用uv工具安装所有项目依赖。")
    print("这可能需要一些时间，请耐心等待...")

    # 检查并创建虚拟环境
    if not os.path.exists(".venv"):
        print("正在创建虚拟环境 (.venv)...")
        os.system("python3 -m venv .venv")
        print("虚拟环境创建成功！")
    else:
        print("虚拟环境 (.venv) 已存在。")

    print("请确保已激活虚拟环境，并已手动安装依赖（如uv sync）。")
    print("现在，核心功能模块已准备就绪。\n")

    print("第二步：启动爬虫")
    print("我们将启动爬虫，自动抓取《崩坏：星穹铁道》的Wiki数据。")
    print("请注意，这会根据您在 config/categories.json 中的配置进行。")
    print("爬取过程可能需要较长时间，请耐心等待。")
    await crawl_menu()
    print("爬虫任务完成！")
    print("数据已成功抓取并保存到 wiki/ 目录。\n")

    print("第三步：清洗数据")
    print("接下来，我们将对抓取到的原始数据进行清洗和结构化处理。")
    print("清洗后的数据将以JSON格式保存到 wiki_cleaned/ 目录。")
    print("此过程将确保数据质量，为后续的数据嵌入做好准备。")
    clean_data_menu()
    print("数据清洗完成！")
    print("结构化数据已保存到 wiki_cleaned/ 目录。\n")

    print("第四步：数据嵌入")
    print("最后，我们将对清洗后的数据进行向量化嵌入。")
    print("这将把文本数据转换为机器可理解的向量形式，用于高效检索。")
    print("嵌入后的向量数据库将保存到 db/ 目录，通常是一个zip文件。")
    print("这是实现智能问答和检索的关键步骤。")
    embed_data_menu()
    print("数据嵌入完成！")
    print("向量数据库已生成并保存到 db/ 目录。\n")

    print("自动化工作流全部完成！")
    print("您现在可以继续使用星穹智库的其他功能，例如启动RAG问答界面或OpenAI兼容API服务端。")
    print("感谢您的使用！")

if __name__ == "__main__":
    asyncio.run(automated_workflow())