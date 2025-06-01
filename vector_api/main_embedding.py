import json
from .slice_utils import slice_content
from .embed_utils import async_embed_text, embed_text
from .faiss_utils import initialize_faiss_db, add_to_faiss_db, search_faiss_db
from .storage_utils import save_to_zip, load_from_zip
from .async_utils import run_async
import numpy as np
import faiss
import os
from pathlib import Path
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
import httpx

# 主流程：分片、嵌入、存储

def embed_and_store_all_in_one(data_dir, db_zip_path, api_url, api_key, model='BAAI/bge-m3', max_length=5000, context_length=50, max_concurrency=32):
    files = list(sorted(Path(data_dir).glob('*.json')))
    vectors = []
    id2meta = {}
    id2content = {}
    id2title = {}
    id2raw = {}  # 新增：原始数据
    next_id = 0
    total_slices = 0
    slice_infos = []  # [(slice_text, meta_with_slice, title, raw_id)]
    # raw_id_map = {}  # 文件名或自定义唯一id -> raw_id
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        content = data.get('content', '')
        meta = data.get('meta', {})
        title = file.stem
        raw_id = title  # 以文件名为唯一id
        id2raw[raw_id] = {'content': content, 'meta': meta, 'title': title}
        slices = slice_content(content, max_length=max_length, context_length=context_length)
        for slice_idx, slice_text in enumerate(slices):
            meta_with_slice = dict(meta)
            meta_with_slice['slice_index'] = slice_idx + 1
            meta_with_slice['origin_title'] = title
            slice_infos.append((slice_text, meta_with_slice, title, raw_id))
        total_slices += len(slices)
    async def embed_slice(session, api_url, api_key, model, slice_text):
        for _ in range(3):
            try:
                return await async_embed_text(session, api_url, api_key, slice_text, model)
            except Exception:
                import asyncio; await asyncio.sleep(1)
        raise RuntimeError(f"嵌入失败: {slice_text[:30]}...")
    async def process_all():
        import asyncio
        sem = asyncio.Semaphore(max_concurrency)
        from typing import Any
        results: list[Any] = [None] * len(slice_infos)
        async with httpx.AsyncClient() as session:
            async def worker(idx, slice_text, meta_with_slice, title, raw_id):
                async with sem:
                    emb = await embed_slice(session, api_url, api_key, model, slice_text)
                    results[idx] = (emb, meta_with_slice, slice_text, title, raw_id)
                    progress.update(task, advance=1)
            tasks = [worker(idx, slice_text, meta_with_slice, title, raw_id)
                     for idx, (slice_text, meta_with_slice, title, raw_id) in enumerate(slice_infos)]
            await asyncio.gather(*tasks)
        return results
    if not slice_infos:
        print('[无可嵌入的数据]')
        return
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
        emb, meta_with_slice, slice_text, title, raw_id = tup
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
    faiss.write_index(id_index, 'faiss.index')
    save_to_zip(db_zip_path, 'faiss.index', id2meta, id2content, id2title, id2raw)
    print(f"已写入 {db_zip_path}，共{len(vectors_np)}条（分片）")

def search_all_in_one(query, db_zip_path, api_url, api_key, top_k=10, model='BAAI/bge-m3'):
    from .embed_utils import embed_text
    index, id2meta, id2content, id2title, id2raw = load_from_zip(db_zip_path)
    query_vec = embed_text(api_url, api_key, query, model).reshape(1, -1)
    D, I = index.search(query_vec, top_k)
    # 只返回唯一原始数据
    raw_ids = set()
    results = []
    for idx in I[0]:
        if idx == -1:
            continue
        meta = id2meta.get(idx, {})
        raw_id = meta.get('origin_title')
        if raw_id and raw_id not in raw_ids:
            raw_ids.add(raw_id)
            if id2raw and raw_id in id2raw:
                results.append(id2raw[raw_id])
            else:
                results.append({'title': raw_id})
    return results

def search_all_in_one_meta(query, db_zip_path, api_url, api_key, top_k=10, model='BAAI/bge-m3'):
    from .embed_utils import embed_text
    index, id2meta, id2content, id2title, id2raw = load_from_zip(db_zip_path)
    query_vec = embed_text(api_url, api_key, query, model).reshape(1, -1)
    D, I = index.search(query_vec, top_k)
    # 只返回唯一meta
    raw_ids = set()
    results = []
    for idx in I[0]:
        if idx == -1:
            continue
        meta = id2meta.get(idx, {})
        raw_id = meta.get('origin_title')
        if raw_id and raw_id not in raw_ids:
            raw_ids.add(raw_id)
            results.append(meta)
    return results
