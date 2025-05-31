import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import httpx
import aiohttp
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
import aiofiles
import sys
import datetime
import traceback
import time
import logging

# 配置
CONFIG_DIR = Path("./config")
WIKI_DIR = Path("./wiki")
CATEGORY_CONFIG_PATH = CONFIG_DIR / "categories.json"
API_URL = "https://wiki.biligame.com/sr/api.php"
LOG_DIR = Path("./log")

# 静默所有日志
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("aiohttp.client").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp.connector").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("root").setLevel(logging.CRITICAL)

# 屏蔽aiohttp关闭连接的报错输出
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

console = Console()
LOG_DIR.mkdir(exist_ok=True)
log_filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.log")
LOG_PATH = LOG_DIR / log_filename

# 初始化时创建空日志文件
with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write(f"[{datetime.datetime.now()}] 日志开始记录\n")

# 纯异步日志写入
async def write_log(msg: str):
    try:
        async with aiofiles.open(LOG_PATH, "a", encoding="utf-8") as f:
            await f.write(f"[{datetime.datetime.now()}] {msg}\n")
    except Exception as e:
        console.print(f"[red]日志写入异常: {e}")

# 同步写日志（用于主进程异常）
def write_log_sync(msg: str):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
            f.flush()
    except Exception as e:
        print(f"[red]日志写入异常: {e}")

# 获取所有分类
async def fetch_categories() -> List[str]:
    params = {
        "action": "query",
        "list": "allcategories",
        "aclimit": "max",
        "format": "json"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(API_URL, params=params)
        data = resp.json()
        return [c["*"] for c in data["query"]["allcategories"]]

# 保存分类配置
async def save_category_config(categories: List[str]):
    CONFIG_DIR.mkdir(exist_ok=True)
    config = {c: {"enabled": True} for c in categories}
    async with aiofiles.open(CATEGORY_CONFIG_PATH, "w", encoding="utf-8") as f:
        await f.write(json.dumps(config, ensure_ascii=False, indent=2))

# 加载分类配置
async def load_category_config() -> Dict[str, Dict]:
    if not CATEGORY_CONFIG_PATH.exists():
        categories = await fetch_categories()
        await save_category_config(categories)
        console.print(f"[green]已生成分类配置文件：{CATEGORY_CONFIG_PATH}")
    async with aiofiles.open(CATEGORY_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.loads(await f.read())

# aiohttp版本的fetch_category_members，支持重试
async def fetch_category_members_with_retry(category: str, max_retries: int = 5, delay: float = 2.0) -> List[str]:
    members = []
    cmcontinue = None
    for attempt in range(1, max_retries + 1):
        try:
            while True:
                params = {
                    "action": "query",
                    "list": "categorymembers",
                    "cmtitle": f"Category:{category}",
                    "cmlimit": "max",
                    "format": "json"
                }
                if cmcontinue:
                    params["cmcontinue"] = cmcontinue
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(API_URL, params=params) as resp:
                        data = await resp.json()
                        members.extend([m["title"] for m in data["query"]["categorymembers"]])
                        cmcontinue = data.get("continue", {}).get("cmcontinue")
                        if not cmcontinue:
                            break
            return members
        except Exception as e:
            if attempt == max_retries:
                raise
            await asyncio.sleep(delay)
    return members

# aiohttp版本的页面源码获取，带重试
async def fetch_page_wikitext_with_retry(title: str, max_retries: int = 5, delay: float = 2.0) -> str:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "titles": title
    }
    for attempt in range(1, max_retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(API_URL, params=params) as resp:
                    data = await resp.json()
                    pages = data["query"]["pages"]
                    for page in pages.values():
                        revs = page.get("revisions")
                        if revs:
                            return revs[0]["*"] if "*" in revs[0] else revs[0]["slots"]["main"]["*"]
            return ""
        except Exception as e:
            if attempt == max_retries:
                raise
            await asyncio.sleep(delay)
    return ""

# 保存页面源码
async def save_page(category: str, title: str, wikitext: str):
    safe_cat = category.replace("/", "_")
    safe_title = title.replace("/", "_")
    dir_path = WIKI_DIR / safe_cat
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{safe_title}.txt"
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(wikitext)

# 主爬取逻辑，增加全局进度条和未成功页面统计
async def crawl(categories: Optional[List[str]] = None):
    start_time = time.time()
    config = await load_category_config()
    if categories:
        enabled_categories = [c for c in categories if c in config and config[c].get("enabled")]
        if not enabled_categories:
            console.print("[yellow]命令行参数无有效分类，或未启用。请检查 config/categories.json。")
            return
    else:
        enabled_categories = [c for c, v in config.items() if v.get("enabled")]
    if not enabled_categories:
        console.print("[yellow]没有启用的分类，请编辑 config/categories.json 后重试。")
        return
    # 分类并发获取，带进度条
    cat2members = {}
    all_members = []
    failed_cats = []
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
        console=console
    ) as progress:
        cat_task = progress.add_task("分类页面列表获取", total=len(enabled_categories))
        sem = asyncio.Semaphore(32)
        async def fetch_cat(category):
            async with sem:
                try:
                    members = await fetch_category_members_with_retry(category)
                    cat2members[category] = members
                    all_members.extend([(category, title) for title in members])
                except Exception as e:
                    console.print(f"[red]分类获取失败: {category} | {type(e).__name__}: {e}")
                    tb = traceback.format_exc()
                    await write_log(f"[{datetime.datetime.now()}] 分类: {category} 页面列表获取失败\n{tb}\n")
                    failed_cats.append(category)
                progress.update(cat_task, advance=1, description=category)
        await asyncio.gather(*(fetch_cat(category) for category in enabled_categories))
        progress.remove_task(cat_task)
    if failed_cats:
        console.print("[red]以下分类页面列表获取失败：")
        for category in failed_cats:
            console.print(f"[red]- 分类: {category}")
    total_pages = len(all_members)
    failed_pages = []
    # 全局进度条
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
        console=console
    ) as progress:
        global_task = progress.add_task("全部页面进度", total=total_pages)
        for category in enabled_categories:
            members = cat2members[category]
            if not members:
                console.print(f"[yellow]分类 {category} 下无页面。")
                continue
            cat_task = progress.add_task(f"分类 {category} 进度", total=len(members))
            sem = asyncio.Semaphore(256)  # 极高并发
            async def fetch_and_save(title):
                async with sem:
                    try:
                        wikitext = await fetch_page_wikitext_with_retry(title)
                        await save_page(category, title, wikitext)
                        progress.update(cat_task, advance=1, description=title)
                        progress.update(global_task, advance=1)
                    except Exception as e:
                        console.print(f"[red]页面爬取失败: {title} | {type(e).__name__}: {e}")
                        tb = traceback.format_exc()
                        await write_log(f"[{datetime.datetime.now()}] 分类: {category} 页面: {title}\n{tb}\n")
                        failed_pages.append((category, title))
                        progress.update(cat_task, advance=1, description=f"失败: {title}")
                        progress.update(global_task, advance=1)
            # 用create_task最大化并发
            tasks = [asyncio.create_task(fetch_and_save(title)) for title in members]
            await asyncio.gather(*tasks)
            progress.remove_task(cat_task)
        progress.remove_task(global_task)
    if failed_pages:
        console.print("[red]以下页面多次重试后仍然失败：")
        for category, title in failed_pages:
            console.print(f"[red]- 分类: {category} 页面: {title}")
    else:
        console.print("[green]全部页面均已成功爬取。")
    elapsed = time.time() - start_time
    console.print(f"[bold green]总用时：{elapsed:.2f} 秒")

if __name__ == "__main__":
    # 屏蔽aiohttp和asyncio相关的低级别日志和SSL shutdown警告，防止干扰控制台输出。
    logging.getLogger("aiohttp.client").setLevel(logging.CRITICAL)
    logging.getLogger("aiohttp.connector").setLevel(logging.CRITICAL)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)

    # 屏蔽aiohttp关闭连接的报错输出
    import warnings
    from aiohttp import ClientConnectionError
    warnings.filterwarnings("ignore", category=UserWarning, message=".*SSL shutdown timed out.*")

    try:
        if len(sys.argv) > 1:
            # 命令行参数模式
            asyncio.run(crawl(sys.argv[1:]))
        else:
            # 交互式全部启用分类
            asyncio.run(crawl())
    except KeyboardInterrupt:
        console.print("[red]用户中断。")
    except Exception as e:
        tb = traceback.format_exc()
        msg = f"[FATAL] {datetime.datetime.now()}\n{tb}\n"
        print(f"[red]程序异常终止: {e}")
        # 用同步写法保证日志一定写入
        write_log_sync(msg)
