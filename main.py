import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import httpx
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
import aiofiles
import sys

# 配置
CONFIG_DIR = Path("./config")
WIKI_DIR = Path("./wiki")
CATEGORY_CONFIG_PATH = CONFIG_DIR / "categories.json"
API_URL = "https://wiki.biligame.com/sr/api.php"

console = Console()

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

# 获取分类下所有页面
async def fetch_category_members(category: str) -> List[str]:
    members = []
    cmcontinue = None
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
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL, params=params)
            data = resp.json()
            members.extend([m["title"] for m in data["query"]["categorymembers"]])
            cmcontinue = data.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                break
    return members

# 获取页面源码
async def fetch_page_wikitext(title: str) -> str:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "titles": title
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(API_URL, params=params)
        data = resp.json()
        pages = data["query"]["pages"]
        for page in pages.values():
            revs = page.get("revisions")
            if revs:
                return revs[0]["*"] if "*" in revs[0] else revs[0]["slots"]["main"]["*"]
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

# 主爬取逻辑
async def crawl(categories: Optional[List[str]] = None):
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
    for category in enabled_categories:
        console.print(f"[cyan]正在爬取分类：{category}")
        members = await fetch_category_members(category)
        if not members:
            console.print(f"[yellow]分类 {category} 下无页面。")
            continue
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), transient=True) as progress:
            task = progress.add_task(f"保存 {category} 页面", total=len(members))
            sem = asyncio.Semaphore(10)
            async def fetch_and_save(title):
                async with sem:
                    wikitext = await fetch_page_wikitext(title)
                    await save_page(category, title, wikitext)
                    progress.update(task, advance=1, description=title)
            await asyncio.gather(*(fetch_and_save(title) for title in members))
        console.print(f"[green]分类 {category} 完成，共 {len(members)} 页。")

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # 命令行参数模式
            asyncio.run(crawl(sys.argv[1:]))
        else:
            # 交互式全部启用分类
            asyncio.run(crawl())
    except KeyboardInterrupt:
        console.print("[red]用户中断。")
