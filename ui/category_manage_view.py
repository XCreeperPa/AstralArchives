from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import json
from pathlib import Path
import re

CATEGORY_PATH = Path("config/categories.json")

def load_categories():
    with open(CATEGORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.keys()), data

def save_categories(data):
    with open(CATEGORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def split_list(lst, n):
    # 平均分成n组
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]

def show_category_table(categories, data, page=1, page_size=15):
    console = Console()
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("序号", justify="right", width=4)
    table.add_column("分类", width=18)
    table.add_column("状态", width=6)
    table.add_column("序号", justify="right", width=4)
    table.add_column("分类", width=18)
    table.add_column("状态", width=6)
    table.add_column("序号", justify="right", width=4)
    table.add_column("分类", width=18)
    table.add_column("状态", width=6)
    start = (page-1)*page_size
    end = start+page_size
    page_cats = categories[start:end]
    groups = split_list(list(enumerate(page_cats, start+1)), 3)
    maxlen = max(len(g) for g in groups)
    for i in range(maxlen):
        row = []
        for group in groups:
            if i < len(group):
                idx, cat = group[i]
                enabled = data[cat]["enabled"]
                status = f"[bold green]✔[/]" if enabled else f"[bold red]✘[/]"
                row += [str(idx), cat, status]
            else:
                row += ["", "", ""]
        table.add_row(*row)
    console.print(table)
    total_pages = (len(categories) + page_size - 1) // page_size
    console.print(f"[cyan]第 {page}/{total_pages} 页，共 {len(categories)} 项")
    return total_pages

def parse_selection(selection, total):
    # 支持全半角逗号，去除空格
    selection = re.sub(r'[，,]', ',', selection)
    selection = selection.replace(' ', '')
    if not selection:
        return []
    result = []
    for part in selection.split(','):
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= total:
                result.append(idx-1)
    return sorted(set(result))

def category_manage_menu():
    console = Console()
    console.clear()
    console.rule("[bold cyan]分类管理")
    categories, data = load_categories()
    page_size = 15
    total_pages = (len(categories) + page_size - 1) // page_size
    page = 1
    changed_indices = set()
    while True:
        console.clear()
        console.rule(f"[bold cyan]分类管理 第{page}/{total_pages}页")
        show_category_table(categories, data, page, page_size)
        console.print("[yellow]请输入要[bold]反转状态[/bold]的分类序号，支持单选/多选/不选，逗号分隔（全半角均可）。")
        console.print("[cyan]输入 e 下一页，w 上一页，s 保存")
        selection = Prompt.ask("操作/序号输入 (e/w/s/序号)", default="e")
        if selection.lower() == 'e':
            if page < total_pages:
                page += 1
            continue
        elif selection.lower() == 'w':
            if page > 1:
                page -= 1
            continue
        elif selection.lower() == 's':
            break
        selected = parse_selection(selection, len(categories))
        for i in selected:
            changed_indices.add(i)
            cat = categories[i]
            data[cat]["enabled"] = not data[cat]["enabled"]
        if selected:
            console.print(f"[green]已反转 {len(selected)} 个分类状态。可继续翻页或输入s保存。")
            console.input("按回车继续...")
    # 统计变更项
    changed = [categories[i] for i in sorted(changed_indices)]
    if not changed:
        console.print("[green]未修改任何分类，所有分类状态保持不变。")
        console.input("\n按回车返回主菜单...")
        return
    # 显示变更表
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("分类", width=18)
    table.add_column("新状态", width=8)
    for cat in changed:
        enabled = data[cat]["enabled"]
        status = f"[bold green]✔ 启用[/]" if enabled else f"[bold red]✘ 禁用[/]"
        table.add_row(cat, status)
    console.print("[bold yellow]本次修改的分类如下：")
    console.print(table)
    # 保存前三选项，数字选择
    options = ["返回编辑", "取消", "保存"]
    option_map = {"1": "返回编辑", "2": "取消", "3": "保存"}
    console.print("[cyan]请选择操作：")
    for i, opt in enumerate(options, 1):
        console.print(f"  [bold]{i}[/]. {opt}")
    while True:
        action = Prompt.ask("请选择操作", choices=["1", "2", "3"], default="1")
        if action in option_map:
            action = option_map[action]
            break
        else:
            console.print("[red]无效输入，请输入 1、2 或 3。")
    if action == "返回编辑":
        return category_manage_menu()
    elif action == "取消":
        console.print("[yellow]操作已取消，无更改。")
        console.input("\n按回车返回主菜单...")
        return
    save_categories(data)
    console.print("[bold green]配置已更新！")
    console.input("\n按回车返回主菜单...")
