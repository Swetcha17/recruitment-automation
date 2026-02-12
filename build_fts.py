import sqlite3
import json
from pathlib import Path

PARSED_DIR = Path("data/parsed")
INDEX_DIR = Path("data/index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = INDEX_DIR / "meta.sqlite"

def build_text_index():
    print("--- Building SQLite Full-Text Search ---")
    
    # Connect to local database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Virtual Table for fast text searching
    cursor.execute("DROP TABLE IF EXISTS profiles_fts")
    cursor.execute("""
        CREATE VIRTUAL TABLE profiles_fts USING fts5(
            candidate_id,
            name,
            role_category,
            skills,
            resume_snippet,
            email,
            phone
        )
    """)
    
    files = list(sorted(PARSED_DIR.glob("*.json")))
    if not files:
        print(" No JSON profiles found.")
        return

    count = 0
    for json_file in files:
        try:
            with open(json_file, 'r') as f:
                p = json.load(f)
            
            # Flatten skills list into a string "Python SQL Docker"
            skills = " ".join([s['name'] for s in p.get('skills', [])])
            
            cursor.execute("""
                INSERT INTO profiles_fts VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                p.get('candidate_id'),
                p.get('name', ''),
                p.get('role_category', ''),
                skills,
                p.get('resume_snippet', ''),
                p.get('email', ''),
                p.get('phone', '')
            ))
            count += 1
        except Exception as e:
            print(f"Skipping {json_file}: {e}")
            
    conn.commit()
    conn.close()
    print(f" Indexed {count} profiles for keyword search.")

if __name__ == "__main__":
    build_text_index()