import json
import sqlite3
from pathlib import Path
import numpy as np
import faiss
import pickle

PARSED_DIR = Path("data/parsed")
INDEX_DIR = Path("data/index")

class CandidateRetriever:
    def __init__(self):
        self.index_dir = INDEX_DIR
        self.parsed_dir = PARSED_DIR
        self.faiss_index = None
        self.candidate_ids = []
        self.vectorizer = None
        self.load_indexes()
    
    def load_indexes(self):
        faiss_path = self.index_dir / "faiss.index"
        meta_path = self.index_dir / "meta.json"
        vectorizer_path = self.parsed_dir / "vectorizer.pkl"
        if faiss_path.exists() and meta_path.exists():
            self.faiss_index = faiss.read_index(str(faiss_path))
            with open(meta_path, 'r') as f:
                meta = json.load(f)
                self.candidate_ids = meta['candidate_ids']
        if vectorizer_path.exists():
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
    
    def load_profile(self, candidate_id):
        profile_path = self.parsed_dir / f"{candidate_id}.json"
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                return json.load(f)
        return None
    
    def semantic_search(self, query, k=10):
        if not self.faiss_index or not self.vectorizer:
            return []
        query_vec = self.vectorizer.transform([query]).toarray()[0].astype('float32')
        query_vec = query_vec.reshape(1, -1)
        faiss.normalize_L2(query_vec)
        distances, indices = self.faiss_index.search(query_vec, min(k, len(self.candidate_ids)))
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.candidate_ids):
                candidate_id = self.candidate_ids[idx]
                profile = self.load_profile(candidate_id)
                if profile:
                    profile['search_score'] = float(dist)
                    results.append(profile)
        return results
    
    def keyword_search(self, query, k=10):
        db_path = self.index_dir / "meta.sqlite"
        if not db_path.exists():
            return []
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT candidate_id, name, role_category, skills, location, 
                   work_authorization, experience_years
            FROM profiles_fts
            WHERE profiles_fts MATCH ?
            LIMIT ?
        """, (query, k))
        results = []
        for row in cursor.fetchall():
            candidate_id = row[0]
            profile = self.load_profile(candidate_id)
            if profile:
                profile['search_score'] = 0.5
                results.append(profile)
        conn.close()
        return results
    
    def search(self, query, k=10, filters=None):
        if not query:
            return []
        semantic_results = self.semantic_search(query, k=k*2)
        keyword_results = self.keyword_search(query, k=k)
        combined = {}
        for profile in semantic_results:
            combined[profile['candidate_id']] = profile
        for profile in keyword_results:
            cid = profile['candidate_id']
            if cid in combined:
                combined[cid]['search_score'] = max(combined[cid]['search_score'], profile['search_score'] + 0.2)
            else:
                combined[cid] = profile
        results = list(combined.values())
        results.sort(key=lambda x: x.get('search_score', 0), reverse=True)
        if filters:
            filtered_results = []
            for profile in results:
                if self.matches_filters(profile, filters):
                    filtered_results.append(profile)
            results = filtered_results
        return results[:k]
    
    def matches_filters(self, profile, filters):
        if 'role_category' in filters:
            if profile.get('role_category') != filters['role_category']:
                return False
        if 'min_experience' in filters:
            if profile.get('experience_years', 0) < filters['min_experience']:
                return False
        if 'max_experience' in filters:
            if profile.get('experience_years', 0) > filters['max_experience']:
                return False
        if 'location' in filters:
            prof_loc = (profile.get('location') or '').lower()
            if filters['location'].lower() not in prof_loc:
                return False
        if 'work_authorization' in filters:
            if profile.get('work_authorization') != filters['work_authorization']:
                return False
        return True

def get_retriever():
    return CandidateRetriever()