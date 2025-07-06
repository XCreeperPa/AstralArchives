# rag/llm.py
"""
LLM相关接口，便于后续切换模型或多模型支持。
"""
# 从 langchain_openai 导入 ChatOpenAI
from langchain_openai import ChatOpenAI
import json
from pathlib import Path

def get_llm(base_url, api_key, model="deepseek-chat", temperature=0.5, max_tokens=8192):
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens, # type: ignore
        api_key=api_key,
        base_url=base_url
    )

def _load_prompts():
    prompt_path = Path(__file__).parent.parent / "config" / "prompts.json"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return json.load(f)

prompts = _load_prompts()

def extract_user_need(llm, question):
    prompt = prompts["extract_need_prompt"].replace("{question}", question)
    result = llm.invoke(prompt)
    return result.content.strip()

def answer_with_rag(llm, question, context, dialogue_history=None, system_prompt=None, context_insert=None):
    # 支持可选参数，便于主流程灵活拼接
    p = prompts["answer_with_rag_prompt"]
    if system_prompt is None:
        system_prompt = prompts.get("system_prompt", "")
    if dialogue_history is None:
        dialogue_history = ""
    if context_insert is None:
        context_insert = prompts.get("context_insert_format", "# 资料片段\n{context}").replace("{context}", context)
    prompt = p.format(
        system_prompt=system_prompt,
        dialogue_history=dialogue_history,
        question=question,
        context_insert=context_insert
    )
    result = llm.invoke(prompt)
    return result.content.strip()

def extract_key_info_multi_llm(llm_list, context_list):
    """
    llm_list: [(llm对象, 名称)]
    context_list: [str]
    return: List[Dict[llm_name, 提取结果]]
    """
    results = []
    for context in context_list:
        item = {}
        for llm, name in llm_list:
            prompt = f"请提取下述资料的关键信息，要求结构化、凝练、突出核心要点：\n{context}"
            try:
                resp = llm.invoke(prompt)
                item[name] = resp.content.strip() if hasattr(resp, 'content') else str(resp)
            except Exception as e:
                item[name] = f"[提取失败: {e}]"
        results.append(item)
    return results

def extract_user_need_with_history(llm, question, history_str):
    prompt = prompts["extract_need_with_history_prompt"].replace("{question}", question).replace("{history}", history_str)
    result = llm.invoke(prompt)
    return result.content.strip()
