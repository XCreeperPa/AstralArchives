import os
import json
import faiss
import numpy as np
import httpx
import pickle
import zipfile
from pathlib import Path
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

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

def embed_and_store(data_dir, db_path, api_url, api_key):
    """
    嵌入数据并存储到FAISS数据库。
    """
    files = list(Path(data_dir).glob("*.json"))
    if not files:
        print("[无可嵌入的数据]")
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        index = faiss.read_index(db_path)
    else:
        index = None

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False
    ) as progress:
        task = progress.add_task("嵌入数据中", total=len(files))

        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            content = data.get("content", "")
            meta = json.dumps(data.get("meta", {}), ensure_ascii=False)

            if len(meta) > 2000:
                print(f"[跳过] {file.name} 的meta字段过长")
                progress.update(task, advance=1)
                continue

            if len(content) > 5000:
                slices = slice_content(content)
            else:
                slices = [content]

            embeddings = []
            for i in range(0, len(slices), 30):
                batch = slices[i:i+30]
                payload = {
                    'model': 'BAAI/bge-m3',
                    'input': batch,
                    'encoding_format': 'float'
                }
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                response = httpx.post(api_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                embeddings.extend(response.json()['data'])

            vectors = np.array([e['embedding'] for e in embeddings], dtype='float32')

            if index is None:
                index = faiss.IndexFlatL2(vectors.shape[1])

            index.add(vectors) # type: ignore
            faiss.write_index(index, db_path)

            progress.update(task, advance=1)

    print("[嵌入完成]")

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

def embed_and_store_all_in_one(data_dir, db_zip_path, api_url, api_key, model='BAAI/bge-m3', max_length=5000, context_length=50):
    files = list(sorted(Path(data_dir).glob('*.json')))
    vectors = []
    id2meta = {}
    id2content = {}
    id2title = {}
    next_id = 0
    total_slices = 0
    # 预统计总分片数
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        content = data.get('content', '')
        slices = slice_content(content, max_length=max_length, context_length=context_length)
        total_slices += len(slices)
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False
    ) as progress:
        task = progress.add_task("嵌入分片中", total=total_slices)
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
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                payload = {
                    'model': model,
                    'input': [slice_text],
                    'encoding_format': 'float'
                }
                response = httpx.post(api_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                embedding = response.json()['data'][0]['embedding']
                vectors.append(np.array(embedding, dtype='float32'))
                id2meta[next_id] = meta_with_slice
                id2content[next_id] = slice_text
                id2title[next_id] = title
                next_id += 1
                progress.update(task, advance=1)
    if not vectors:
        print('[无可嵌入的数据]')
        return
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
