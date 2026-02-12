import sys
import os
import json
import re
import pickle
from pathlib import Path
from datetime import datetime
import numpy as np
import PyPDF2
from docx import Document

# --- Configuration ---
BASE_PATH = Path("data/resumes")
PARSED_DIR = Path("data/parsed")
PARSED_DIR.mkdir(parents=True, exist_ok=True)

# Set to False if you want to use the heavier, smarter AI model (requires internet to download model first time)
USE_SIMPLE_EMBEDDINGS = True 

class EnhancedLocalResumeParser:
    def __init__(self):
        self.parsed_dir = PARSED_DIR
        self.stats = {
            'folders_scanned': 0,
            'resumes_parsed': 0,
            'failed': 0
        }
        
        if USE_SIMPLE_EMBEDDINGS:
            print("Loading TF-IDF Vectorizer...")
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
            self.model = None
        else:
            print("Loading SentenceTransformer (Deep Learning)...")
            os.environ['TOKENIZERS_PARALLELISM'] = 'false'
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.vectorizer = None
    
    def extract_text(self, filepath):
        """Dispatches to specific extractors based on file extension."""
        suffix = filepath.suffix.lower()
        try:
            if suffix == '.pdf':
                text = ""
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text
            elif suffix == '.docx':
                doc = Document(filepath)
                return "\n".join([para.text for para in doc.paragraphs])
            elif suffix == '.txt':
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            else:
                return ""
        except Exception as e:
            print(f"Error reading {filepath.name}: {e}")
            return ""
    
    def extract_contact_info(self, text):
        contact = {'email': None, 'phone': None, 'linkedin': None, 'location': None}
        
        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            contact['email'] = email_match.group(0)
            
        # Phone
        phone_patterns = [
            r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'
        ]
        for p in phone_patterns:
            match = re.search(p, text)
            if match:
                contact['phone'] = match.group(0)
                break
                
        # LinkedIn
        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
        if linkedin_match:
            contact['linkedin'] = linkedin_match.group(0)
            
        return contact
    
    def extract_skills(self, text):
        """Simple keyword matching for demo purposes."""
        found_skills = []
        text_lower = text.lower()
        # Add more keywords as needed
        keywords = [
            'python', 'java', 'javascript', 'c++', 'sql', 'aws', 'azure', 'docker', 
            'kubernetes', 'react', 'node', 'pytorch', 'tensorflow', 'scikit-learn',
            'agile', 'scrum', 'project management', 'communication', 'leadership'
        ]
        
        for k in keywords:
            if k in text_lower:
                found_skills.append({'name': k.title()})
        return found_skills

    def extract_experience_years(self, text):
        # Look for patterns like "5+ years", "10 years experience"
        patterns = [
            r'(\d+)\+?\s*years?',
            r'experience\s*:\s*(\d+)'
        ]
        max_exp = 0
        for p in patterns:
            matches = re.findall(p, text.lower())
            for m in matches:
                try:
                    val = int(m)
                    if 0 < val < 50: # Sanity check
                        max_exp = max(max_exp, val)
                except:
                    continue
        return max_exp

    def parse_directory(self):
        print(f"Scanning {BASE_PATH}...")
        profiles = []
        texts = []

        # Recursively find all resumes
        for root, dirs, files in os.walk(BASE_PATH):
            for file in files:
                if file.lower().endswith(('.pdf', '.docx', '.txt')):
                    file_path = Path(root) / file
                    self.stats['folders_scanned'] += 1
                    
                    # Extraction
                    raw_text = self.extract_text(file_path)
                    if len(raw_text) < 50:
                        continue

                    candidate_id = file_path.stem.replace(" ", "_")
                    role_category = Path(root).name
                    
                    # Metadata Extraction
                    contact = self.extract_contact_info(raw_text)
                    skills = self.extract_skills(raw_text)
                    exp_years = self.extract_experience_years(raw_text)
                    
                    profile = {
                        "candidate_id": candidate_id,
                        "name": candidate_id.replace("_", " "),
                        "role_category": role_category,
                        "email": contact['email'],
                        "phone": contact['phone'],
                        "skills": skills,
                        "experience_years": exp_years,
                        "resume_snippet": raw_text[:600], # First 600 chars for preview
                        "source_file": str(file_path.name)
                    }
                    
                    profiles.append(profile)
                    texts.append(raw_text)
                    self.stats['resumes_parsed'] += 1

        if not profiles:
            print("No resumes found! Make sure they are in data/resumes/")
            return

        print(f"Generating embeddings for {len(profiles)} profiles...")
        
        # Vectorization
        if USE_SIMPLE_EMBEDDINGS:
            embeddings = self.vectorizer.fit_transform(texts).toarray()
            # Save Vectorizer for query transformation later
            with open(self.parsed_dir / "vectorizer.pkl", "wb") as f:
                pickle.dump(self.vectorizer, f)
        else:
            embeddings = self.model.encode(texts)

        # Save Results
        for i, profile in enumerate(profiles):
            # Save JSON
            with open(self.parsed_dir / f"{profile['candidate_id']}.json", "w") as f:
                json.dump(profile, f, indent=2)
            
            # Save NPY
            np.save(self.parsed_dir / f"{profile['candidate_id']}.npy", embeddings[i].astype('float32'))

        print(f"Done! Parsed {len(profiles)} resumes.")

if __name__ == "__main__":
    parser = EnhancedLocalResumeParser()
    parser.parse_directory()