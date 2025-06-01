import os
import json
import faiss
import numpy as np
import httpx
import pickle
import zipfile
from pathlib import Path
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
import asyncio
import sys

# 兼容旧接口，推荐直接用 main_embedding.py
from .main_embedding import embed_and_store_all_in_one, search_all_in_one

def slice_content(content, max_length=5000, context_length=50):
    """
    切片算法：将content字段切片为不超过max_length字符的片段，
    每个片段包含context_length字符的上下文。
    """
    slices = []
    start = 0
    while start < len(content):
        end = min(start + max_length, len(content))

        # 确保不会在关键处断裂
        if end < len(content):
            while end > start and content[end] not in ['。', '！', '？', '\n']:
                end -= 1
            if end == start:
                end = start + max_length

        # 添加上下文
        slice_start = max(0, start - context_length)
        slice_end = min(len(content), end + context_length)
        sliced_content = content[slice_start:slice_end]

        slices.append(sliced_content)
        start = end

    return slices

def initialize_faiss_db(db_path: str, vector_dim: int):
    """
    初始化或加载 FAISS 数据库。
    """
    if os.path.exists(db_path):
        return faiss.read_index(db_path)
    else:
        return faiss.IndexFlatL2(vector_dim)

def embed_text(api_url: str, api_key: str, text: str, model: str = 'BAAI/bge-m3') -> np.ndarray:
    """
    调用嵌入 API，将文本转换为向量。
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'input': [text],
        'encoding_format': 'float'
    }
    response = httpx.post(api_url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    embedding = response.json()['data'][0]['embedding']
    return np.array(embedding, dtype='float32')

def add_to_faiss_db(index, embedding: np.ndarray, db_path: str):
    """
    将嵌入向量添加到 FAISS 数据库并保存。
    """
    index.add(embedding.reshape(1, -1))  # type: ignore
    faiss.write_index(index, db_path)

def search_faiss_db(index, query_embedding: np.ndarray, k: int = 1):
    """
    在 FAISS 数据库中进行向量检索。
    """
    D, I = index.search(query_embedding.reshape(1, -1), k)  # type: ignore
    return D, I

def search_vectors(query_text: str, db_path: str, api_url: str, api_key: str, k: int = 1):
    """
    使用查询文本在向量数据库中检索。
    """
    # 加载数据库
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"FAISS 数据库文件 {db_path} 不存在。")

    index = faiss.read_index(db_path)

    # 获取查询文本的嵌入
    query_embedding = embed_text(api_url, api_key, query_text)

    # 检索
    D, I = search_faiss_db(index, query_embedding, k=k)
    return D, I

def embed_and_store_all_in_one(data_dir, db_zip_path, api_url, api_key, model='BAAI/bge-m3', max_length=5000, context_length=50, max_concurrency=32):
    files = list(sorted(Path(data_dir).glob('*.json')))
    vectors = []
    id2meta = {}
    id2content = {}
    id2title = {}
    next_id = 0
    total_slices = 0
    slice_infos = []  # [(slice_text, meta_with_slice, title)]
    # 预统计总分片数并收集分片信息
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        content = data.get('content', '')
        meta = data.get('meta', {})
        title = file.stem
        slices = slice_content(content, max_length=max_length, context_length=context_length)
        for slice_idx, slice_text in enumerate(slices):
            meta_with_slice = dict(meta)
            meta_with_slice['slice_index'] = slice_idx + 1
            meta_with_slice['origin_title'] = title
            slice_infos.append((slice_text, meta_with_slice, title))
        total_slices += len(slices)

    async def embed_slice(session, api_url, api_key, model, slice_text):
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': model,
            'input': [slice_text],
            'encoding_format': 'float'
        }
        for _ in range(3):  # 最多重试3次
            try:
                resp = await session.post(api_url, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                return np.array(resp.json()['data'][0]['embedding'], dtype='float32')
            except Exception as e:
                await asyncio.sleep(1)
        raise RuntimeError(f"嵌入失败: {slice_text[:30]}...")

    async def process_all():
        sem = asyncio.Semaphore(max_concurrency)
        from typing import Any
        results: list[Any] = [None] * len(slice_infos)
        async with httpx.AsyncClient() as session:
            async def worker(idx, slice_text, meta_with_slice, title):
                async with sem:
                    emb = await embed_slice(session, api_url, api_key, model, slice_text)
                    results[idx] = (emb, meta_with_slice, slice_text, title)
                    progress.update(task, advance=1)
            tasks = [worker(idx, slice_text, meta_with_slice, title)
                     for idx, (slice_text, meta_with_slice, title) in enumerate(slice_infos)]
            await asyncio.gather(*tasks)
        return results

    def run_async(coro):
        try:
            import asyncio
            if sys.version_info >= (3, 7):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop and loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    return loop.run_until_complete(coro)
                else:
                    return asyncio.run(coro)
            else:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(coro)
        except Exception as e:
            raise e

    if not slice_infos:
        print('[无可嵌入的数据]')
        return
    # 自动创建目标目录
    os.makedirs(os.path.dirname(db_zip_path), exist_ok=True)
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False
    ) as progress:
        task = progress.add_task("嵌入分片中", total=total_slices)
        results = run_async(process_all())
    for tup in results:
        if tup is None:
            continue
        emb, meta_with_slice, slice_text, title = tup
        vectors.append(emb)
        id2meta[next_id] = meta_with_slice
        id2content[next_id] = slice_text
        id2title[next_id] = title
        next_id += 1
    vectors_np = np.stack(vectors)
    dim = vectors_np.shape[1]
    index = faiss.IndexFlatL2(dim)
    id_index = faiss.IndexIDMap(index)
    ids = np.arange(len(vectors_np), dtype='int64')
    id_index.add_with_ids(vectors_np.astype('float32'), ids) # type: ignore
    with zipfile.ZipFile(db_zip_path, 'w') as zf:
        faiss.write_index(id_index, 'faiss.index')
        zf.write('faiss.index')
        os.remove('faiss.index')
        zf.writestr('id2meta.pkl', pickle.dumps(id2meta))
        zf.writestr('id2content.pkl', pickle.dumps(id2content))
        zf.writestr('id2title.pkl', pickle.dumps(id2title))
    print(f"已写入 {db_zip_path}，共{len(vectors_np)}条（分片）")

def search_all_in_one(query, db_zip_path, api_url, api_key, top_k=10, model='BAAI/bge-m3'):
    import zipfile
    import pickle
    with zipfile.ZipFile(db_zip_path, 'r') as zf:
        with zf.open('faiss.index') as fidx:
            with open('tmp_faiss.index', 'wb') as fout:
                fout.write(fidx.read())
            index = faiss.read_index('tmp_faiss.index')
            os.remove('tmp_faiss.index')
        id2meta = pickle.loads(zf.read('id2meta.pkl'))
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'input': [query],
        'encoding_format': 'float'
    }
    response = httpx.post(api_url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    query_vec = np.array(response.json()['data'][0]['embedding'], dtype='float32').reshape(1, -1)
    D, I = index.search(query_vec, top_k)
    results = []
    for rank, (dist, idx) in enumerate(zip(D[0], I[0]), 1):
        if idx == -1:
            continue
        results.append(id2meta.get(idx, {}))
    return results
