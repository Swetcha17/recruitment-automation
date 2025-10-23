import json
import sqlite3
from pathlib import Path

PARSED_DIR = Path("data/parsed")
INDEX_DIR = Path("data/index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = INDEX_DIR / "meta.sqlite"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS profiles_fts")

cursor.execute("""
    CREATE VIRTUAL TABLE profiles_fts USING fts5(
        candidate_id,
        name,
        role_category,
        titles,
        skills,
        location,
        work_authorization,
        resume_snippet,
        email,
        phone,
        experience_years UNINDEXED,
        source_file UNINDEXED
    )
""")

for json_file in sorted(PARSED_DIR.glob("*.json")):
    with open(json_file, 'r') as f:
        profile = json.load(f)
    skills_text = " ".join([s['name'] for s in profile.get('skills', [])])
    titles_text = " ".join(profile.get('titles', []))
    location_text = profile.get('location', '') or ''
    work_auth_text = profile.get('work_authorization', '') or ''
    cursor.execute("""
        INSERT INTO profiles_fts (
            candidate_id, name, role_category, titles, skills, 
            location, work_authorization, resume_snippet, 
            email, phone, experience_years, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        profile['candidate_id'],
        profile.get('name', ''),
        profile.get('role_category', ''),
        titles_text,
        skills_text,
        location_text,
        work_auth_text,
        profile.get('resume_snippet', ''),
        profile.get('email', ''),
        profile.get('phone', ''),
        profile.get('experience_years', 0),
        profile.get('source_file', '')
    ))

conn.commit()
conn.close()