import httpx
import numpy as np

async def async_embed_text(session, api_url, api_key, text, model='BAAI/bge-m3'):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'input': [text],
        'encoding_format': 'float'
    }
    resp = await session.post(api_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return np.array(resp.json()['data'][0]['embedding'], dtype='float32')

# 同步版本
def embed_text(api_url, api_key, text, model='BAAI/bge-m3'):
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
