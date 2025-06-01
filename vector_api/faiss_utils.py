import faiss
import numpy as np
import os

def initialize_faiss_db(db_path: str, vector_dim: int):
    if os.path.exists(db_path):
        return faiss.read_index(db_path)
    else:
        return faiss.IndexFlatL2(vector_dim)

def add_to_faiss_db(index, embedding: np.ndarray, db_path: str):
    index.add(embedding.reshape(1, -1))  # type: ignore
    faiss.write_index(index, db_path)

def search_faiss_db(index, query_embedding: np.ndarray, k: int = 1):
    D, I = index.search(query_embedding.reshape(1, -1), k)  # type: ignore
    return D, I
