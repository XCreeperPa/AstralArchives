import os
import sys
import logging
import time
import json
from functools import wraps
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator, Union, AsyncGenerator
from fastapi import FastAPI, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from rag.llm import get_llm, extract_user_need
from rag.db import search_db
from rag.utils import load_llm_config, load_multi_llm_config
from rag.rag_service import count_tokens
from config.apikey_db import init_db, check_api_key, add_token_usage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AstralArchives")

# 数据结构定义
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False

class Choice(BaseModel):
    index: int
    message: Dict[str, Any] = Field(default_factory=lambda: {"role": "assistant", "content": ""})
    finish_reason: Optional[str] = "stop"

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: "chatcmpl-astralarchives")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "AstralArchives"
    choices: List[Choice]
    usage: Usage

# 提示词模板
RAG_PROMPT_TEMPLATE = """\
{system_prompt}

当前参考资料：
{metadata_table}

相关资料片段：
{context}

请基于上述资料回答：{question}
"""

BASIC_PROMPT_TEMPLATE = """\
{system_prompt}

用户问题：{question}
"""

# 性能监控装饰器
def log_execution_time(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Start {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Finish {func.__name__} in {duration:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return async_wrapper

# 核心功能函数
def format_messages(messages: List[Message]) -> List[Union[HumanMessage, AIMessage]]:
    return [
        HumanMessage(content=msg.content) if msg.role == "user" 
        else AIMessage(content=msg.content)
        for msg in messages
    ]

def meta_to_md_table(meta_list: List[dict]) -> str:
    if not meta_list:
        return ""
    header = "| 序号 | 标题 | 分类 |\n| --- | --- | --- |\n"
    rows = "\n".join(
        f"| {idx} | {meta.get('title','无标题')[:25]} | {meta.get('category','未分类')} |"
        for idx, meta in enumerate(meta_list, 1)
    )
    return header + rows

async def generate_response(
    llm,
    prompt_template: str,
    system_prompt: str,
    history_messages: List[Union[HumanMessage, AIMessage]],
    question: str,
    keyword: str = "",
    metadata_table: str = "",
    context: Optional[str] = None
) -> AsyncGenerator[str, None]:
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    
    formatted_context = f"相关文档：\n{metadata_table}\n\n资料片段：\n{context}" if context else ""
    
    async for chunk in chain.astream({
        "system_prompt": system_prompt,
        "history": "\n".join(f"{msg.type}: {msg.content}" for msg in history_messages),
        "keyword": keyword,
        "metadata_table": metadata_table,
        "context": formatted_context,
        "question": question
    }):
        yield chunk

@log_execution_time
async def determine_retrieval_need(llm, question: str, history: list) -> bool:
    prompt = """根据对话历史和当前问题，判断是否需要检索知识库：
历史对话：
{history}

当前问题：{question}

请用Y/N回答是否需要检索："""
    
    response = await llm.ainvoke(prompt.format(
        history="\n".join([f"{msg.type}: {msg.content}" for msg in history]),
        question=question
    ))
    return response.content.strip().upper() == "Y"

@app.post("/v1/chat/completions")
@log_execution_time
async def chat_completions(req: ChatCompletionRequest, authorization: Optional[str] = Header(None)):
    logger.info(f"New request received. Messages count: {len(req.messages)}")
    
    try:
        # API密钥校验
        api_key_header = authorization.split("Bearer ")[-1] if authorization else None
        if api_key_header:
            logger.debug(f"API key header: {api_key_header[:6]}...")
        
        if not api_key_header or not check_api_key(api_key_header):
            return JSONResponse(status_code=401, content={"error": "无效API密钥"})

        # 初始化处理流程
        history_messages = format_messages(req.messages[:-1])
        current_question = req.messages[-1].content
        
        # 加载配置
        base_url, api_key = load_llm_config()
        llm_cfgs = load_multi_llm_config()
        main_llm = get_llm(base_url, api_key, temperature=0.3)
        
        # 动态检索判断
        need_retrieval = await determine_retrieval_need(main_llm, current_question, history_messages)
        
        # 知识库检索流程
        merged_context = ""
        user_need = ""
        meta_list = []
        meta_md = ""
        if need_retrieval:
            user_need = extract_user_need(main_llm, current_question)
            logger.info(f"Starting retrieval with user_need: {user_need}")
            
            logger.debug(f"Searching DB with query: {user_need}")
            meta_list = search_db(user_need, top_k=5)
            logger.info(f"Found {len(meta_list)} metadata entries")
            
            # 构建上下文
            db_zip_path = Path(__file__).parent / "db" / "wiki_allinone.zip"
            from vector_api.main_embedding import load_from_zip
            _, id2meta, id2content, _, _ = load_from_zip(str(db_zip_path))
            
            context_list = []
            used = set()
            for meta in meta_list:
                for idx, m in id2meta.items():
                    if m == meta and idx not in used:
                        context_list.append(id2content[idx])
                        used.add(idx)
            merged_context = "\n".join(context_list)[:60000]
            meta_md = meta_to_md_table(meta_list)

        # 加载提示词配置
        with open(Path(__file__).parent / "config" / "prompts.json") as f:
            prompts = json.load(f)

        # 流式响应处理
        if req.stream:
            async def stream_generator():
                full_content = ""
                
                # 预发送元数据
                if need_retrieval:
                    metadata_chunk = json.dumps({
                        "id": "chatcmpl-astralarchives",
                        "object": "chat.completion.chunk",
                        "choices": [{
                            "delta": {
                                "content": f"# 检索关键词\n{user_need}\n\n# 相关文档\n{meta_md}\n\n",
                                "metadata": {
                                    "search_used": True,
                                    "keywords": user_need.split(','),
                                    "doc_count": len(meta_list)
                                }
                            },
                            "index": 0,
                            "finish_reason": None
                        }]
                    }, ensure_ascii=False)
                    yield f"data: {metadata_chunk}\n\n"
                
                # 流式生成内容
                async for chunk in generate_response(
                    llm=main_llm,
                    prompt_template=RAG_PROMPT_TEMPLATE if need_retrieval else BASIC_PROMPT_TEMPLATE,
                    system_prompt=prompts.get("system_prompt", ""),
                    history_messages=history_messages,
                    question=current_question,
                    keyword=user_need,
                    metadata_table=meta_md,
                    context=merged_context
                ):
                    full_content += chunk
                    yield f"""data: {json.dumps({
                        'id': 'chatcmpl-astralarchives',
                        'object': 'chat.completion.chunk',
                        'choices': [{
                            'delta': {'content': chunk},
                            'index': 0,
                            'finish_reason': None
                        }]
                    }, ensure_ascii=False)}\n\n"""
                
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        
        # 非流式响应
        else:
            full_response = ""
            if need_retrieval:
                full_response += f"检索关键词：{user_need}\n\n相关文档：\n{meta_md}\n\n"
            
            async for chunk in generate_response(
                llm=main_llm,
                prompt_template=RAG_PROMPT_TEMPLATE if need_retrieval else BASIC_PROMPT_TEMPLATE,
                system_prompt=prompts.get("system_prompt", ""),
                history_messages=history_messages,
                question=current_question,
                keyword=user_need,
                metadata_table=meta_md,
                context=merged_context
            ):
                full_response += chunk
            
            prompt_tokens = count_tokens(full_response)
            completion_tokens = count_tokens(full_response)
            
            return ChatCompletionResponse(
                choices=[Choice(index=0, message={"role": "assistant", "content": full_response})],
                usage=Usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )
            )

    except Exception as e:
        logger.error(f"Critical error processing request: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "内部服务器错误"})

# 初始化API密钥数据库
init_db()