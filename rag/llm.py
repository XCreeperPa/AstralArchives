# rag/llm.py
"""
LLM相关接口，便于后续切换模型或多模型支持。
"""
from langchain_community.chat_models import ChatOpenAI

def get_llm(base_url, api_key, model="deepseek-chat", temperature=0.3, max_tokens=2048):
    return ChatOpenAI(
        model=model, # type: ignore
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
