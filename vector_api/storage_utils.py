import pickle
import zipfile
import os

def save_to_zip(db_zip_path, faiss_index_path, id2meta, id2content, id2title, id2raw=None):
    with zipfile.ZipFile(db_zip_path, 'w') as zf:
        zf.write(faiss_index_path)
        os.remove(faiss_index_path)
        zf.writestr('id2meta.pkl', pickle.dumps(id2meta))
        zf.writestr('id2content.pkl', pickle.dumps(id2content))
        zf.writestr('id2title.pkl', pickle.dumps(id2title))
        if id2raw is not None:
            zf.writestr('id2raw.pkl', pickle.dumps(id2raw))

def load_from_zip(db_zip_path):
    with zipfile.ZipFile(db_zip_path, 'r') as zf:
        with zf.open('faiss.index') as fidx:
            with open('tmp_faiss.index', 'wb') as fout:
                fout.write(fidx.read())
            import faiss
            index = faiss.read_index('tmp_faiss.index')
            os.remove('tmp_faiss.index')
        id2meta = pickle.loads(zf.read('id2meta.pkl'))
        id2content = pickle.loads(zf.read('id2content.pkl'))
        id2title = pickle.loads(zf.read('id2title.pkl'))
        id2raw = None
        if 'id2raw.pkl' in zf.namelist():
            id2raw = pickle.loads(zf.read('id2raw.pkl'))
    return index, id2meta, id2content, id2title, id2raw
