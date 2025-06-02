import os
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rag.llm import get_llm, extract_user_need
from rag.db import search_db
from rag.utils import load_llm_config, load_multi_llm_config
from rag.rag_service import get_user_need, retrieve_context, build_history_str, count_tokens
import tempfile
import subprocess
import sys

def better_file_input(prompt):
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
        f.write(f"# {prompt}\n# 请输入内容后保存退出\n\n")
        path = f.name
    editor = os.getenv('EDITOR', 'nano')
    print(f"\n即将打开编辑器输入，提示: {prompt}")
    input("请按回车进入编辑器...")
    subprocess.call(f'{editor} "{path}"', shell=True)
    with open(path, 'r') as f:
        lines = [line.rstrip() for line in f.readlines() if not line.startswith('#')]
        content = '\n'.join([line for line in lines if line.strip()])
    os.unlink(path)
    print(f"\n您输入的内容是: {content}")
    return content
def load_prompts():
    prompt_path = Path(__file__).parent / "config" / "prompts.json"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return json.load(f)
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
    prompts = load_prompts()
    base_url, api_key = load_llm_config()
    if not base_url or not api_key or api_key == "your_api_key_here":
        console.print("[red]请先在 config/api_keys.json 配置正确的 base_url 和 api_key！")
        return
    llm_cfgs = load_multi_llm_config()
    llm_list = [(get_llm(base_url, api_key, model, temperature=0.3), name) for base_url, api_key, model, name in llm_cfgs]
    main_llm = llm_list[0][0]
    # 检查是否为测试模式（提前，避免进入人工输入）
    if '--test' in sys.argv:
        test_questions = [
            "如何理解翁法罗斯的黄金裔与泰坦的循环关系？",
            "赏析任务“夜色名为温柔”中带着开拓者去秘密据点的流萤形象。",
            "评价星期日的反派形象塑造。"
        ]
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        label_list = ['A1', 'B1', 'C1']
        for idx, question in enumerate(test_questions):
            console.rule(f"[bold cyan]自动测试问题 {idx+1}: {question}")
            user_need = extract_user_need(main_llm, question)
            meta_list = search_db(user_need, top_k=5)
            if meta_list:
                table = Table(title="数据库检索元数据", show_lines=True, expand=True)
                for k in meta_list[0].keys():
                    table.add_column(str(k), overflow="fold", max_width=40)
                for meta in meta_list:
                    table.add_row(*[str(meta.get(k, "")) for k in meta_list[0].keys()])
                console.print(table)
            else:
                console.print("[red]未检索到相关资料")
            db_zip_path = str(Path(__file__).parent / "db" / "wiki_allinone.zip")
            from vector_api.main_embedding import load_from_zip
            _, id2meta, id2content, _, _ = load_from_zip(db_zip_path)
            context_list = []
            used = set()
            for meta in meta_list:
                for idx2, m in id2meta.items():
                    if m == meta and idx2 not in used:
                        fragment = id2content[idx2]
                        context_list.append(fragment)
                        used.add(idx2)
            merged_context = "\n".join(context_list)
            if len(merged_context) > 60000:
                merged_context = merged_context[:60000]
            console.print(Panel(f"[bold green]LLM 提取需求：[/bold green]{user_need}", title="LLM 提取的检索需求"))
            # 捕获流式输出
            system_prompt = load_system_prompt()
            prompt = f"{system_prompt}\n\n用户问题：{question}\n\n资料片段：{merged_context}\n"
            stream = main_llm.stream(prompt)
            md_buffer = ""
            for chunk in stream:
                # 类型安全拼接chunk内容
                content = chunk.content if hasattr(chunk, 'content') else chunk
                if isinstance(content, str):
                    md_buffer = md_buffer + content
                    console.print(content, end="", style="white", soft_wrap=True)
                elif isinstance(content, list):
                    md_buffer = md_buffer + ''.join(str(item) for item in content)
                    console.print(''.join(str(item) for item in content), end="", style="white", soft_wrap=True)
                else:
                    md_buffer = md_buffer + str(content)
                    console.print(str(content), end="", style="white", soft_wrap=True)
            out_path = output_dir / f"{label_list[idx]}.md"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md_buffer)
            console.print(f"[green]已保存: {out_path}")
        return
    history = []
    db_zip_path = str(Path(__file__).parent / "db" / "wiki_allinone.zip")
    while True:
        question = better_file_input(prompts.get("user_input_prompt", "请输入你的问题（支持多轮，输入exit/quit/q退出）："))
        if question.strip().lower() in ("exit", "quit", "q", ""):
            break
        # 构造历史对话字符串
        history_turn_format = prompts.get("history_turn_format", "用户：{user}\n分析师：{assistant}")
        dialogue_history_format = prompts.get("dialogue_history_format", "# 历史对话\n{history}")
        history_str = "\n".join([
            history_turn_format.format(user=h["user"], assistant=h["assistant"]) for h in history
        ]) if history else ""
        # 允许用户选择是否检索资料
        console.print("[yellow]本轮是否需要检索资料？输入 y 检索，n 跳过，仅用历史对话作答。[/yellow]")
        need_search = input("检索资料？(y/n, 默认y): ").strip().lower()
        if need_search == "n":
            merged_context = ""
            meta_list = []
            user_need = question  # 直接用原问题
        else:
            # 1. LLM 提取需求（带上下文）
            user_need = get_user_need(main_llm, question, history_str)
            # 2. 检索数据库并拼接资料
            meta_list, merged_context = retrieve_context(user_need, db_zip_path, top_k=5)
        # 3. 展示元数据
        if meta_list:
            table = Table(title="数据库检索元数据", show_lines=True, expand=True)
            for k in meta_list[0].keys():
                table.add_column(str(k), overflow="fold", max_width=40)
            for meta in meta_list:
                table.add_row(*[str(meta.get(k, "")) for k in meta_list[0].keys()])
            console.print(table)
        elif need_search != "n":
            console.print("[red]未检索到相关资料")
        if need_search != "n":
            console.print(Panel(f"[bold green]LLM 提取需求：[/bold green]{user_need}", title="LLM 提取的检索需求"))
        # 4. 构造历史对话
        history_turn_format = prompts.get("history_turn_format", "用户：{user}\n分析师：{assistant}")
        dialogue_history_format = prompts.get("dialogue_history_format", "# 历史对话\n{history}")
        dialogue_history = build_history_str(history, history_turn_format, dialogue_history_format)
        # 5. 构造 context 插入
        context_insert_format = prompts.get("context_insert_format", "# 资料片段\n{context}")
        context_insert = context_insert_format.format(context=merged_context)
        # 6. 构造最终prompt
        answer_with_rag_prompt = prompts.get("answer_with_rag_prompt",
            "{system_prompt}\n\n{dialogue_history}\n\n用户问题：{question}\n\n{context_insert}\n\n请基于上述资料片段和历史对话，输出专业、结构化的分析。"
        )
        system_prompt = prompts.get("system_prompt", "")
        final_prompt = answer_with_rag_prompt.format(
            system_prompt=system_prompt,
            dialogue_history=dialogue_history,
            question=question,
            context_insert=context_insert
        )
        # 7. token统计
        prompt_tokens = count_tokens(final_prompt)
        console.print(f"[yellow]本轮Prompt Token数：{prompt_tokens}[/yellow]")
        # 8. LLM 回答
        stream = main_llm.stream(final_prompt)
        console.print("[bold blue]LLM 正在流式输出回答...\n", style="blue")
        md_buffer = ""
        for chunk in stream:
            content = chunk.content if hasattr(chunk, 'content') else chunk
            if isinstance(content, str):
                md_buffer = md_buffer + content
                console.print(content, end="", style="white", soft_wrap=True)
            elif isinstance(content, list):
                joined = ''.join(str(item) for item in content)
                md_buffer = md_buffer + joined
                console.print(joined, end="", style="white", soft_wrap=True)
            else:
                s = str(content)
                md_buffer = md_buffer + s
                console.print(s, end="", style="white", soft_wrap=True)
        answer_tokens = count_tokens(md_buffer)
        console.print(f"\n[yellow]本轮LLM输出 Token数：{answer_tokens}[/yellow]")
        with open("output.md", "w", encoding="utf-8") as f:
            f.write(md_buffer)
        console.print("\n[bold green]Markdown 渲染：[/bold green]")
        console.print(Markdown(md_buffer), soft_wrap=True)
        console.print("[bold green]内容已保存到 output.md[/bold green]")
        # 9. 更新历史对话
        history.append({"user": question, "assistant": md_buffer})

if __name__ == "__main__":
    main()
