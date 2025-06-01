import os
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rag.llm import get_llm, extract_user_need, answer_with_rag
from rag.db import search_db, build_context_from_db
from rag.utils import load_llm_config
import sys

import sys
import io

# 替换标准流
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', 
                            line_buffering=True)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                             line_buffering=True)
import tempfile
import subprocess

def better_file_input(prompt):
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
        f.write(f"# {prompt}\n# 请输入内容后保存退出\n\n")
        path = f.name
    editor = os.getenv('EDITOR', 'nano')
    print(f"\n即将打开编辑器输入，提示: {prompt}")
    subprocess.call(f'{editor} "{path}"', shell=True)
    with open(path, 'r') as f:
        lines = [line.rstrip() for line in f.readlines() if not line.startswith('#')]
        content = '\n'.join([line for line in lines if line.strip()])
    os.unlink(path)
    print(f"\n您输入的内容是: {content}")
    return content
def load_system_prompt():
    prompt_path = Path(__file__).parent / "config" / "prompts.json"
    with open(prompt_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("system_prompt", "")
def stream_llm_answer(llm, question, context, console):
    system_prompt = load_system_prompt()
    prompt = f"{system_prompt}\n\n用户问题：{question}\n\n资料片段：{context}\n"
    stream = llm.stream(prompt)
    console.print("[bold blue]LLM 正在流式输出回答...\n", style="blue")
    md_buffer = ""
    for chunk in stream:
        if hasattr(chunk, 'content'):
            md_buffer += chunk.content
            console.print(chunk.content, end="", style="white", soft_wrap=True)
        else:
            md_buffer += str(chunk)
            console.print(str(chunk), end="", style="white", soft_wrap=True)
    # 保存到 output.md
    with open("output.md", "w", encoding="utf-8") as f:
        f.write(md_buffer)
    console.print("\n[bold green]Markdown 渲染：[/bold green]")
    console.print(Markdown(md_buffer), soft_wrap=True)
    console.print("[bold green]内容已保存到 output.md[/bold green]")
# 主界面
def main():
    console = Console()
    base_url, api_key = load_llm_config()
    if not base_url or not api_key or api_key == "your_api_key_here":
        console.print("[red]请先在 config/api_keys.json 配置正确的 base_url 和 api_key！")
        return
    llm = get_llm(base_url, api_key)
    console.rule("[bold cyan]星穹智库 RAG 智能问答")
    question = better_file_input("请输入你的问题 (支持多行，输入后保存退出)")
    if question.strip().lower() in ("exit", "quit", "q", ""):
        return
    # 1. LLM 提取需求
    user_need = extract_user_need(llm, question)
    # 2. 检索数据库
    meta_list = search_db(user_need, top_k=5)
    # 3. 展示元数据
    if meta_list:
        table = Table(title="数据库检索元数据", show_lines=True, expand=True)
        for k in meta_list[0].keys():
            table.add_column(str(k), overflow="fold", max_width=40)
        for meta in meta_list:
            table.add_row(*[str(meta.get(k, "")) for k in meta_list[0].keys()])
        console.print(table)
    else:
        console.print("[red]未检索到相关资料")
    # 4. 拼接资料
    context = build_context_from_db(meta_list, max_chars=64000)
    # 5. LLM 流式回答
    console.print(Panel(f"[bold green]LLM 提取需求：[/bold green]{user_need}", title="LLM 提取的检索需求"))
    stream_llm_answer(llm, question, context, console)

if __name__ == "__main__":
    main()
