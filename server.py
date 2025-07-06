import os
import sys
from fastapi import FastAPI, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Generator
from rag.llm import get_llm, extract_user_need
from rag.db import search_db
from rag.utils import load_llm_config, load_multi_llm_config
from rag.rag_service import build_history_str, count_tokens
from pathlib import Path
import json
from fastapi.middleware.cors import CORSMiddleware
from config.apikey_db import init_db, check_api_key, add_token_usage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 可根据需要指定前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI Chat API request/response格式
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    # 其他参数全部忽略

class Choice(BaseModel):
    index: int
    message: Dict[str, Any]
    finish_reason: Optional[str] = "stop"

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: "chatcmpl-astralarchives")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(__import__('time').time()))
    model: str = "AstralArchives"
    choices: List[Choice]
    usage: Usage

# Markdown表格生成，单元格30字内
def meta_to_md_table(meta_list: List[dict]) -> str:
    if not meta_list:
        return "无检索结果"
    keys = list(meta_list[0].keys())
    header = "|" + "|".join(keys) + "|\n"
    sep = "|" + "|".join(["---"] * len(keys)) + "|\n"
    rows = []
    for meta in meta_list:
        def short(val):
            s = str(val)
            return s[:30] + '...' if len(s) > 30 else s
        row = "|" + "|".join(short(meta.get(k, "")) for k in keys) + "|"
        rows.append(row)
    return header + sep + "\n".join(rows)

# 拼接历史
def get_history_from_messages(messages: List[Message]) -> str:
    history = []
    for m in messages[:-1]:
        if m.role == "user":
            history.append({"user": m.content, "assistant": ""})
        elif m.role == "assistant":
            if history:
                history[-1]["assistant"] = m.content
    # 只拼接到倒数第二条，最后一条为当前问题
    return "\n".join([f"用户：{h['user']}\n分析师：{h['assistant']}" for h in history if h['user']])

# 启动时初始化API-KEY数据库
init_db()

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, authorization: Optional[str] = Header(None)):
    # API密钥校验
    api_key_header = None
    if authorization and authorization.startswith("Bearer "):
        api_key_header = authorization[7:]
    if not api_key_header or not check_api_key(api_key_header):
        from config.apikey_db import get_key_status
        status = get_key_status(api_key_header) if api_key_header else None
        if status and status['total_tokens'] >= status['max_tokens']:
            return JSONResponse(status_code=402, content={"error": {"message": f"API-KEY已超最大用量({status['max_tokens']})，请联系管理员续费或更换KEY。", "type": "usage_limit_exceeded"}})
        return JSONResponse(status_code=401, content={"error": {"message": "无效API密钥", "type": "invalid_request_error"}})
    if req.model != "AstralArchives":
        return JSONResponse(status_code=400, content={"error": {"message": "仅支持 AstralArchives", "type": "invalid_request_error"}})
    # 历史对话
    history_str = get_history_from_messages(req.messages)
    question = req.messages[-1].content
    # LLM加载
    base_url, api_key = load_llm_config()
    llm_cfgs = load_multi_llm_config()
    llm_list = [(get_llm(base_url, api_key, model, temperature=0.3), name) for base_url, api_key, model, name in llm_cfgs]
    main_llm = llm_list[0][0]
    # 1. LLM提取检索需求
    user_need = extract_user_need(main_llm, question)
    # 2. 检索数据库
    meta_list = search_db(user_need, top_k=5)
    # 3. 组装元数据表
    meta_md = meta_to_md_table(meta_list)
    # 4. 组装 context
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
    # 5. 构造最终prompt
    with open(Path(__file__).parent / "config" / "prompts.json", "r", encoding="utf-8") as f:
        prompts = json.load(f)
    answer_with_rag_prompt = prompts.get("answer_with_rag_prompt",
        "{system_prompt}\n\n{dialogue_history}\n\n用户问题：{question}\n\n{context_insert}\n\n请基于上述资料片段和历史对话，输出专业、结构化的分析。"
    )
    system_prompt = prompts.get("system_prompt", "")
    dialogue_history_format = prompts.get("dialogue_history_format", "# 历史对话\n{history}")
    context_insert_format = prompts.get("context_insert_format", "# 资料片段\n{context}")
    dialogue_history = dialogue_history_format.format(history=history_str)
    context_insert = context_insert_format.format(context=merged_context)
    final_prompt = answer_with_rag_prompt.format(
        system_prompt=system_prompt,
        dialogue_history=dialogue_history,
        question=question,
        context_insert=context_insert
    )
    prompt_tokens = count_tokens(final_prompt)
    # 6. LLM分析结果
    def make_content():
        # 三段式输出
        yield f"[检索关键词]\n{user_need}\n\n"
        yield f"[检索元数据]\n{meta_md}\n\n"
    # 非流式
    if not req.stream:
        content = "".join(list(make_content()))
        md_buffer = ""
        completion_tokens = 0
        stream = main_llm.stream(final_prompt)
        for chunk in stream:
            content_chunk = chunk.content if hasattr(chunk, 'content') else chunk
            md_buffer += str(content_chunk)
            completion_tokens += count_tokens(str(content_chunk))
        content += f"[分析结果]\n{md_buffer}"
        total_tokens = prompt_tokens + completion_tokens
        # 记录token消耗
        add_token_usage(api_key_header, total_tokens)
        resp = ChatCompletionResponse(
            choices=[Choice(index=0, message={"role": "assistant", "content": content})],
            usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens)
        )
        return resp
    # 流式
    def stream_gen() -> Generator[bytes, None, None]:
        sent_tokens = 0
        for part in make_content():
            sent_tokens += count_tokens(part)
            chunk = {
                'id': 'chatcmpl-astralarchives',
                'object': 'chat.completion.chunk',
                'choices': [{
                    'delta': {'role': 'assistant', 'content': part},
                    'index': 0,
                    'finish_reason': None
                }],
                'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': 0, 'total_tokens': prompt_tokens}
            }
            yield f"data: {json.dumps(chunk)}\n\n".encode()
        # LLM流式
        completion_tokens = 0
        for chunk in main_llm.stream(final_prompt):
            content_chunk = chunk.content if hasattr(chunk, 'content') else chunk
            chunk_str = str(content_chunk)
            completion_tokens += count_tokens(chunk_str)
            chunk_data = {
                'id': 'chatcmpl-astralarchives',
                'object': 'chat.completion.chunk',
                'choices': [{
                    'delta': {'content': chunk_str},
                    'index': 0,
                    'finish_reason': None
                }],
                'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'total_tokens': prompt_tokens + completion_tokens}
            }
            yield f"data: {json.dumps(chunk_data)}\n\n".encode()
        # 结束信号前记录token消耗
        add_token_usage(api_key_header, prompt_tokens + completion_tokens)
        yield b"data: [DONE]\n\n"
    return StreamingResponse(stream_gen(), media_type="text/event-stream")
