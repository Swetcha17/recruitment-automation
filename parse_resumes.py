import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
import numpy as np
import PyPDF2
from docx import Document

BASE_PATH = Path("data/resumes")
PARSED_DIR = Path("data/parsed")
PARSED_DIR.mkdir(parents=True, exist_ok=True)
USE_SIMPLE_EMBEDDINGS = True

class EnhancedLocalResumeParser:
    def __init__(self):
        self.parsed_dir = PARSED_DIR
        self.stats = {
            'total_folders_scanned': 0,
            'resumes_found': 0,
            'successfully_parsed': 0,
            'failed': 0,
            'errors': []
        }
        
        if USE_SIMPLE_EMBEDDINGS:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
            self.model = None
        else:
            os.environ['TOKENIZERS_PARALLELISM'] = 'false'
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            self.vectorizer = None
    
    def extract_text_from_pdf(self, filepath):
        try:
            text = ""
            with open(filepath, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except:
            return ""
    
    def extract_text_from_docx(self, filepath):
        try:
            doc = Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        except:
            return ""
    
    def extract_text_from_doc(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
                text = content.decode('latin-1', errors='ignore')
                text = ''.join(char for char in text if char.isprintable() or char in '\n\r\t')
                return text
        except:
            return ""
    
    def extract_contact_info(self, text):
        contact = {}
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        contact['email'] = emails[0] if emails else None
        phone_patterns = [
            r'\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+\d{1,3}\s?\d{10,14}',
            r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                contact['phone'] = phones[0]
                break
        else:
            contact['phone'] = None
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin = re.search(linkedin_pattern, text, re.IGNORECASE)
        contact['linkedin'] = linkedin.group(0) if linkedin else None
        location_patterns = [
            r'([A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})',
            r'([A-Za-z\s]+,\s*[A-Z]{2})',
        ]
        for pattern in location_patterns:
            location = re.search(pattern, text)
            if location:
                contact['location'] = location.group(1)
                break
        else:
            contact['location'] = None
        return contact
    
    def extract_work_authorization(self, text):
        text_lower = text.lower()
        auth_patterns = {
            'US Citizen': [r'u\.?s\.?\s+citizen', r'united\s+states\s+citizen', r'citizenship\s*:\s*u\.?s', r'american\s+citizen'],
            'Green Card': [r'green\s+card', r'permanent\s+resident', r'lawful\s+permanent\s+resident', r'lpr\b'],
            'H1B': [r'h-?1b', r'h1-?b\s+visa', r'work\s+visa\s+h1b'],
            'EAD': [r'\bead\b', r'employment\s+authorization', r'work\s+authorization\s+document'],
            'OPT': [r'\bopt\b', r'optional\s+practical\s+training', r'f-?1\s+opt'],
            'CPT': [r'\bcpt\b', r'curricular\s+practical\s+training'],
            'TN Visa': [r'\btn\b.*visa', r'tn-?1', r'nafta\s+visa']
        }
        for auth_type, patterns in auth_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return auth_type
        if re.search(r'authorized\s+to\s+work', text_lower):
            return 'Authorized to Work'
        if re.search(r'(?:requires?|needs?)\s+(?:visa\s+)?sponsor', text_lower):
            return 'Requires Sponsorship'
        return None
    
    def extract_skills(self, text):
        skills = []
        text_lower = text.lower()
        skill_keywords = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'go', 'rust', 'swift', 'kotlin',
            'react', 'angular', 'vue', 'django', 'flask', 'spring', 'node.js', 'express', '.net', 'laravel',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'dynamodb', 'cassandra', 'elasticsearch',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'terraform', 'ci/cd', 'devops',
            'machine learning', 'deep learning', 'data science', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'spark',
            'git', 'jira', 'agile', 'scrum', 'rest api', 'graphql', 'microservices',
            'leadership', 'team management', 'communication', 'problem solving', 'analytical', 'project management'
        ]
        for skill in skill_keywords:
            if skill in text_lower:
                skills.append({'name': skill, 'confidence': 0.9 if f' {skill} ' in text_lower else 0.7})
        return skills
    
    def extract_work_experience(self, text):
        patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'experience\s*:\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s+in'
        ]
        max_years = 0
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                years = int(match)
                if 0 <= years <= 50:
                    max_years = max(max_years, years)
        return max_years
    
    def extract_education(self, text):
        education = []
        degree_patterns = [
            r"(bachelor(?:'s)?|b\.?s\.?|b\.?a\.?)\s+(?:of\s+)?(?:science|arts)?\s+(?:in\s+)?([a-z\s]+)",
            r"(master(?:'s)?|m\.?s\.?|m\.?a\.?)\s+(?:of\s+)?(?:science|arts)?\s+(?:in\s+)?([a-z\s]+)",
            r"(ph\.?d\.?|doctorate)\s+(?:in\s+)?([a-z\s]+)",
            r"(associate)\s+(?:degree)?\s+(?:in\s+)?([a-z\s]+)"
        ]
        text_lower = text.lower()
        for pattern in degree_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                degree = match[0].strip()
                field = match[1].strip() if len(match) > 1 else ""
                if field:
                    education.append({'degree': degree, 'field': field})
        return education
    
    def extract_availability(self, text):
        text_lower = text.lower()
        if re.search(r'immediate(?:ly)?\s+available', text_lower):
            return 'Immediate'
        if re.search(r'(?:2|two)\s+weeks?\s+notice', text_lower):
            return '2 Weeks Notice'
        if re.search(r'(?:1|one)\s+month\s+notice', text_lower):
            return '1 Month Notice'
        if re.search(r'contract', text_lower) and re.search(r'prefer', text_lower):
            return 'Contract Preferred'
        return None
    
    def create_resume_snippet(self, text):
        sentences = text.split('.')
        snippet = '. '.join(sentences[:3])
        return snippet[:300] + '...' if len(snippet) > 300 else snippet
    
    def create_searchable_text(self, profile, full_text):
        parts = [
            profile.get('name', ''),
            profile.get('role_category', ''),
            ' '.join(profile.get('titles', [])),
            ' '.join([s['name'] for s in profile.get('skills', [])]),
            profile.get('location', ''),
            profile.get('work_authorization', ''),
            ' '.join([e.get('degree', '') + ' ' + e.get('field', '') for e in profile.get('education', [])])
        ]
        searchable = ' '.join(filter(None, parts))
        searchable += ' ' + full_text[:1000]
        return searchable
    
    def parse_resume(self, file_path, role_category, candidate_name):
        suffix = file_path.suffix.lower()
        if suffix == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif suffix == '.docx':
            text = self.extract_text_from_docx(file_path)
        elif suffix == '.doc':
            text = self.extract_text_from_doc(file_path)
        else:
            return None
        if not text or len(text) < 50:
            return None
        contact = self.extract_contact_info(text)
        skills = self.extract_skills(text)
        experience_years = self.extract_work_experience(text)
        education = self.extract_education(text)
        resume_snippet = self.create_resume_snippet(text)
        work_authorization = self.extract_work_authorization(text)
        availability = self.extract_availability(text)
        titles = [role_category] if role_category else []
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        candidate_id = f"CAND_{timestamp}"
        profile = {
            'candidate_id': candidate_id,
            'name': candidate_name,
            'role_category': role_category,
            'titles': titles,
            'skills': skills,
            'experience_years': experience_years,
            'education': education,
            'contact': contact,
            'email': contact.get('email'),
            'phone': contact.get('phone'),
            'location': contact.get('location'),
            'work_authorization': work_authorization,
            'availability': availability,
            'resume_snippet': resume_snippet,
            'source_file': str(file_path.name),
            'parsed_date': datetime.now().isoformat(),
            'status': 'New',
            'stage': 'Uploaded'
        }
        searchable_text = self.create_searchable_text(profile, text)
        return profile, searchable_text
    
    def scan_and_parse(self):
        if not BASE_PATH.exists():
            return
        profiles_with_text = []
        for role_folder in sorted(BASE_PATH.iterdir()):
            if not role_folder.is_dir() or role_folder.name.startswith('.'):
                continue
            role_name = role_folder.name
            candidate_folders = [f for f in role_folder.iterdir() if f.is_dir()]
            for candidate_folder in candidate_folders:
                self.stats['total_folders_scanned'] += 1
                candidate_name = candidate_folder.name
                resume_files = []
                resume_files.extend(candidate_folder.glob("*.pdf"))
                resume_files.extend(candidate_folder.glob("*.docx"))
                resume_files.extend(candidate_folder.glob("*.doc"))
                if not resume_files:
                    continue
                for resume_file in resume_files:
                    self.stats['resumes_found'] += 1
                    try:
                        result = self.parse_resume(resume_file, role_name, candidate_name)
                        if result:
                            profile, searchable_text = result
                            profiles_with_text.append((profile, searchable_text))
                            self.stats['successfully_parsed'] += 1
                        else:
                            self.stats['failed'] += 1
                    except Exception as e:
                        self.stats['failed'] += 1
                        self.stats['errors'].append(f"{resume_file.name}: {str(e)}")
        if profiles_with_text:
            if USE_SIMPLE_EMBEDDINGS:
                import pickle
                texts = [text for _, text in profiles_with_text]
                self.vectorizer.fit(texts)
                vectorizer_path = self.parsed_dir / "vectorizer.pkl"
                with open(vectorizer_path, 'wb') as f:
                    pickle.dump(self.vectorizer, f)
                for i, (profile, text) in enumerate(profiles_with_text):
                    embedding = self.vectorizer.transform([text]).toarray()[0].astype('float32')
                    profile_path = self.parsed_dir / f"{profile['candidate_id']}.json"
                    with open(profile_path, 'w') as f:
                        json.dump(profile, f, indent=2)
                    embedding_path = self.parsed_dir / f"{profile['candidate_id']}.npy"
                    np.save(embedding_path, embedding)
            else:
                texts = [text for _, text in profiles_with_text]
                embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
                for i, (profile, text) in enumerate(profiles_with_text):
                    embedding = embeddings[i].astype('float32')
                    profile_path = self.parsed_dir / f"{profile['candidate_id']}.json"
                    with open(profile_path, 'w') as f:
                        json.dump(profile, f, indent=2)
                    embedding_path = self.parsed_dir / f"{profile['candidate_id']}.npy"
                    np.save(embedding_path, embedding)

parser = EnhancedLocalResumeParser()
parser.scan_and_parse()