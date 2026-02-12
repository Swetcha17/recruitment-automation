import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# --- Configuration ---
PARSED_DIR = Path("data/parsed")
VACANCY_DIR = Path("data/vacancies")
VACANCY_DIR.mkdir(parents=True, exist_ok=True)

class VacancyManager:
    def __init__(self):
        self.vacancy_dir = VACANCY_DIR
        self.vacancies = {}
        self.load_vacancies()
    
    def load_vacancies(self):
        """Loads all existing vacancy JSON files."""
        for json_file in self.vacancy_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    vacancy = json.load(f)
                    self.vacancies[vacancy['vacancy_id']] = vacancy
            except Exception as e:
                print(f"Error loading vacancy {json_file}: {e}")
    
    def save_vacancy(self, vacancy):
        """Saves a single vacancy to disk."""
        vacancy_file = self.vacancy_dir / f"{vacancy['vacancy_id']}.json"
        with open(vacancy_file, 'w') as f:
            json.dump(vacancy, f, indent=2)
        self.vacancies[vacancy['vacancy_id']] = vacancy
    
    def create_vacancy_from_role(self, role_name):
        """Creates a new vacancy based on a role category."""
        # Check if an open vacancy already exists for this role
        for vac in self.vacancies.values():
            if vac['role_name'] == role_name and vac['status'] == 'Open':
                return vac
        
        # Generate ID
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        # Sanitize filename
        safe_role = role_name.replace(' ', '_').replace('/', '-').upper()
        vacancy_id = f"VAC_{safe_role}_{timestamp}"
        
        vacancy = {
            'vacancy_id': vacancy_id,
            'role_name': role_name,
            'status': 'Open',  # Options: Open, On Hold, Closed, Filled
            'created_date': datetime.now().isoformat(),
            'assigned_candidates': [],
            'requirements': {
                'min_experience': 2, # Default baseline
                'required_skills': [],
                'work_authorization': None
            },
            'priority': 'Medium',
            'notes': []
        }
        
        self.save_vacancy(vacancy)
        return vacancy
    
    def auto_create_vacancies(self):
        """Scans parsed profiles and creates vacancies for discovered roles."""
        print("Auto-creating vacancies from candidate roles...")
        
        if not PARSED_DIR.exists():
            print("No parsed data found. Run parse_resumes.py first.")
            return

        found_roles = set()
        for json_file in PARSED_DIR.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    profile = json.load(f)
                    if profile.get('role_category'):
                        found_roles.add(profile['role_category'])
            except:
                continue
        
        count = 0
        for role in found_roles:
            self.create_vacancy_from_role(role)
            count += 1
            
        print(f"Processed {count} roles. Total active vacancies: {len(self.vacancies)}")

    def assign_candidate(self, vacancy_id, candidate_id):
        """Links a candidate to a specific vacancy."""
        if vacancy_id not in self.vacancies:
            return False
        
        vacancy = self.vacancies[vacancy_id]
        if candidate_id not in vacancy['assigned_candidates']:
            vacancy['assigned_candidates'].append(candidate_id)
            self.save_vacancy(vacancy)
            return True
        return False

    def get_all_vacancies(self):
        return list(self.vacancies.values())

    def match_candidates(self, vacancy_id, top_n=10):
        """Simple scoring system to find best matches for a vacancy."""
        vacancy = self.vacancies.get(vacancy_id)
        if not vacancy:
            return []

        candidates = []
        # Scan all parsed profiles
        for json_file in PARSED_DIR.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    profile = json.load(f)
                
                # Simple Scoring Logic
                score = 0
                
                # 1. Role Match (High Weight)
                if profile.get('role_category') == vacancy['role_name']:
                    score += 50
                
                # 2. Experience Match (Medium Weight)
                req_exp = vacancy['requirements'].get('min_experience', 0)
                cand_exp = profile.get('experience_years', 0)
                if cand_exp >= req_exp:
                    score += 20
                
                # 3. Text Match (Naive - Low Weight)
                # In a real app, we would use the vector search here
                
                if score > 0:
                    profile['match_score'] = score
                    candidates.append(profile)
            except:
                continue
        
        # Sort by highest score
        candidates.sort(key=lambda x: x['match_score'], reverse=True)
        return candidates[:top_n]

# Singleton Accessor for Streamlit
_manager = None
def get_vacancy_manager():
    global _manager
    if _manager is None:
        _manager = VacancyManager()
    return _manager

if __name__ == "__main__":
    print("--- Initializing Vacancy Manager ---")
    vm = VacancyManager()
    
    # 1. Auto-create vacancies based on parsed resumes
    vm.auto_create_vacancies()
    
    # 2. Print Summary
    all_vacs = vm.get_all_vacancies()
    print(f"\nTotal Vacancies Managed: {len(all_vacs)}")
    for v in all_vacs:
        print(f" - {v['role_name']} ({v['status']})")