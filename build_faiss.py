import json
import numpy as np
from pathlib import Path
import faiss

PARSED_DIR = Path("data/parsed")
INDEX_DIR = Path("data/index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)

embeddings = []
candidate_ids = []

for npy_file in sorted(PARSED_DIR.glob("*.npy")):
    candidate_id = npy_file.stem
    emb = np.load(npy_file).astype('float32')
    if emb.ndim > 1:
        emb = emb.flatten()
    embeddings.append(emb)
    candidate_ids.append(candidate_id)

if embeddings:
    xb = np.vstack(embeddings)
    faiss.normalize_L2(xb)
    dimension = xb.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(xb)
    index_path = INDEX_DIR / "faiss.index"
    faiss.write_index(index, str(index_path))
    meta_path = INDEX_DIR / "meta.json"
    with open(meta_path, 'w') as f:
        json.dump({"candidate_ids": candidate_ids}, f, indent=2)