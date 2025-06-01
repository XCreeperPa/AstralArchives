# 数据清洗主流程
# 1. 所有清洗后的json文件统一输出到wiki_cleaned/下，不再分子文件夹，索引为全局自增
# 2. rich进度条展示整体清洗进度
import os
import json
from pathlib import Path
from datacleaner.lightcone import LightconeCleaner
from datacleaner.character import CharacterCleaner
from datacleaner.mission import MissionCleaner
import mwparserfromhell
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

def get_cleaner(category: str):
    if category == "光锥":
        return LightconeCleaner()
    elif category == "角色":
        return CharacterCleaner()
    elif category in ("开拓任务", "开拓续闻"):
        return MissionCleaner()
    else:
        return None

def clean_all():
    src_dir = Path("wiki")
    dst_dir = Path("wiki_cleaned")
    dst_dir.mkdir(exist_ok=True)
    # 收集所有txt文件（所有分类）
    all_files = []
    for category in os.listdir(src_dir):
        cat_path = src_dir / category
        if cat_path.is_dir():
            for file in cat_path.glob("*.txt"):
                all_files.append((category, file))
    total = len(all_files)
    if total == 0:
        print("[无可清洗的页面]")
        return
    idx = 1
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False
    ) as progress:
        task = progress.add_task("数据清洗中", total=total)
        for category, file in all_files:
            cleaner = get_cleaner(category)
            if not cleaner:
                progress.update(task, advance=1)
                continue
            with open(file, "r", encoding="utf-8") as f:
                raw = f.read()
            title = file.stem
            result = cleaner.clean(idx, title, raw)
            out_path = dst_dir / f"{title}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            idx += 1
            progress.update(task, advance=1)
    print("[数据清洗完成]")

if __name__ == "__main__":
    clean_all()
