import os
import sys
import json
import requests
import tempfile
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

def better_file_input(prompt):
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
        f.write(f"# {prompt}\n# 请输入内容后保存退出\n\n\n")
        path = f.name
    editor = os.getenv('EDITOR', 'nano')
    editor_cmd = f'{editor} +5 "{path}"' if 'nano' in editor or 'vim' in editor or 'nvim' in editor else f'{editor} "{path}"'
    print(f"\n即将打开编辑器输入，提示: {prompt}")
    input("请按回车进入编辑器...")
    subprocess.call(editor_cmd, shell=True)
    with open(path, 'r') as f:
        lines = [line.rstrip() for line in f.readlines() if not line.startswith('#')]
        content = '\n'.join([line for line in lines if line.strip()])
    os.unlink(path)
    print(f"\n您输入的内容是: {content}")
    return content

def get_temp_api_key():
    # 动态生成临时key，设置5分钟过期时间
    from config.apikey_db import add_api_key
    expire_at = int(time.time()) + 300  # 5分钟后过期
    key = add_api_key("client临时测试", expire_at)
    return key


def disable_temp_api_key(key):
    try:
        from config.apikey_db import disable_api_key
        disable_api_key(key)
    except Exception:
        pass

# 新增：Token计数函数（与服务端保持一致）
def count_tokens(text: str) -> int:
    """简单的Token计数（示例实现，可替换为服务端同款）"""
    return len(text.encode('utf-8')) // 4  # 近似：1token≈4字节（中文场景可调整）

def main():
    console = Console()
    api_url = os.environ.get("AA_API_URL", "http://127.0.0.1:8080/v1/chat/completions")
    api_key = os.environ.get("AA_API_KEY")
    temp_key = None
    if not api_key:
        temp_key = get_temp_api_key()
        if temp_key:
            api_key = temp_key
            console.print("[yellow]未检测到环境变量AA_API_KEY，已自动生成临时测试KEY。[/yellow]")
        else:
            console.print("[red]未检测到API-KEY，且无法生成临时KEY。请先生成API-KEY并设置AA_API_KEY环境变量。[/red]")
            sys.exit(1)
    model = "AstralArchives"
    history = []
    console.print(Panel("[bold cyan]AstralArchives API 测试客户端 (Ctrl+C 退出)[/bold cyan]", title="欢迎"))
    while True:
        try:
            question = better_file_input("请输入你的问题 (exit/quit/q 退出)")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[green]再见！")
            break
        if question.strip().lower() in ("exit", "quit", "q", ""):
            break
        messages = []
        for h in history:
            messages.append({"role": "user", "content": h["user"]})
            messages.append({"role": "assistant", "content": h["assistant"]})
        messages.append({"role": "user", "content": question})
        payload = {
            "model": model,
            "messages": messages,
            "stream": True  # 启用流式
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("[green]已生成Token数: {task.completed}"),
                transient=True,
                console=console
            ) as progress:
                task = progress.add_task("LLM 正在流式生成回答...", total=None)
                resp = requests.post(api_url, headers=headers, json=payload, stream=True, timeout=300)
                if resp.status_code != 200:
                    console.print(f"[red]请求失败: {resp.status_code} {resp.text}")
                    continue
                md_buffer = ""
                # 关键修改：初始化Token统计变量
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0
                manual_completion_tokens = 0  # 手动累加的Token数
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith('data: '):
                        continue
                    chunk = line[6:]
                    if chunk.strip() == '[DONE]':
                        # 尝试从最终chunk获取完整usage信息（如果服务端返回）
                        try:
                            final_data = json.loads(chunk)
                            prompt_tokens = final_data.get('usage', {}).get('prompt_tokens', prompt_tokens)
                            completion_tokens = final_data.get('usage', {}).get('completion_tokens', completion_tokens)
                            total_tokens = prompt_tokens + completion_tokens
                        except Exception:
                            pass
                        break
                    try:
                        data = json.loads(chunk)
                    except Exception:
                        continue
                    delta = data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        md_buffer += content
                        manual_completion_tokens += count_tokens(content)
                        progress.update(task, completed=manual_completion_tokens)
                    # 更新Token统计（如果服务端返回部分信息）
                    usage = data.get('usage', {})
                    prompt_tokens = usage.get('prompt_tokens', prompt_tokens)
                    completion_tokens = usage.get('completion_tokens', completion_tokens)
                    total_tokens = usage.get('total_tokens', total_tokens)
                # 若服务端未返回，使用手动累加值
                if completion_tokens == 0:
                    completion_tokens = manual_completion_tokens
                    total_tokens = prompt_tokens + completion_tokens

            # 输出token统计信息（已定义变量）
            console.print("\n[cyan]本轮Token统计：Prompt {}，Completion {}，Total {}[/cyan]".format(prompt_tokens, completion_tokens, total_tokens))
            console.print(Panel(f"[bold green]模型回复：[/bold green]\n", title="回复", subtitle="Markdown 渲染"))
            console.print(Markdown(md_buffer), soft_wrap=True)
            history.append({"user": question, "assistant": md_buffer})
        except Exception as e:
            console.print(f"[red]请求异常: {e}")
        finally:
            if temp_key:
                disable_temp_api_key(temp_key)
                temp_key = get_temp_api_key()
                api_key = temp_key

if __name__ == "__main__":
    main()
