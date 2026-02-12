import faiss
import pickle
import json
import numpy as np
import sqlite3
from pathlib import Path

INDEX_DIR = Path("data/index")
PARSED_DIR = Path("data/parsed")

class Retriever:
    def __init__(self):
        self.index = None
        self.candidate_ids = []
        self.vectorizer = None
        self.db_path = INDEX_DIR / "meta.sqlite"
        self.load_resources()

    def load_resources(self):
        """Loads FAISS index, Vectorizer, and Metadata."""
        # Load FAISS
        try:
            self.index = faiss.read_index(str(INDEX_DIR / "faiss.index"))
            with open(INDEX_DIR / "meta.json", 'r') as f:
                self.candidate_ids = json.load(f)['candidate_ids']
        except Exception:
            print("Warning: Vector index not found.")

        # Load Vectorizer (created by parse_resumes.py)
        try:
            with open(PARSED_DIR / "vectorizer.pkl", 'rb') as f:
                self.vectorizer = pickle.load(f)
        except Exception:
            print("Warning: Vectorizer not found.")

    def semantic_search(self, query, k=10, filters=None):
        results = {}

        # 1. Vector Search (Meaning)
        if self.index and self.vectorizer and query:
            # Convert query text to vector
            q_vec = self.vectorizer.transform([query]).toarray().astype('float32')
            faiss.normalize_L2(q_vec)
            
            # Search FAISS
            scores, indices = self.index.search(q_vec, k * 2)
            
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.candidate_ids):
                    cid = self.candidate_ids[idx]
                    results[cid] = {'score': float(score), 'source': 'vector'}

        # 2. Keyword Search (Exact Match)
        if query:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Sanitize query for FTS
            clean_query = query.replace('"', '')
            fts_query = f'"{clean_query}"' 
            try:
                cursor.execute("SELECT candidate_id FROM profiles_fts WHERE profiles_fts MATCH ? LIMIT ?", (fts_query, k))
                for row in cursor.fetchall():
                    cid = row[0]
                    if cid in results:
                        results[cid]['score'] += 0.2 # Boost score if keyword also matches
                    else:
                        results[cid] = {'score': 0.4, 'source': 'keyword'} # Base score for keyword only
            except:
                pass 
            conn.close()

        # 3. Load Profiles & Filter
        final_list = []
        for cid, data in results.items():
            profile = self.get_profile(cid)
            if not profile: continue
            
            # Apply Role Filter
            if filters and 'role_category' in filters:
                if profile.get('role_category') != filters['role_category']:
                    continue
            
            # Apply Experience Filter
            if filters and 'min_experience' in filters:
                # Mock experience check (since we don't have real extracted exp in this demo)
                pass 
            
            profile['search_score'] = data['score']
            final_list.append(profile)

        # Sort by relevance
        final_list.sort(key=lambda x: x['search_score'], reverse=True)
        return final_list[:k]

    def get_profile(self, cid):
        path = PARSED_DIR / f"{cid}.json"
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return None

def get_retriever():
    return Retriever()