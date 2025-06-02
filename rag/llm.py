# rag/llm.py
"""
LLM相关接口，便于后续切换模型或多模型支持。
"""
from langchain_community.chat_models import ChatOpenAI

def get_llm(base_url, api_key, model="deepseek-chat", temperature=0.5, max_tokens=8192):
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url
    )

def extract_user_need(llm, question):
    prompt = f"""
你是一个知识库检索助手。请从用户问题中提取最核心的检索需求，输出简明的检索关键词或主题，中文逗号分隔。
用户问题：{question}
只输出关键词。
"""
    result = llm.invoke(prompt)
    return result.content.strip()

def answer_with_rag(llm, question, context):
    prompt = f"""
你是《崩坏：星穹铁道》知识库智能问答助手。请结合下方资料片段，回答用户问题。

用户问题：{question}

{context}

请用简洁、准确的语言作答。
"""
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
