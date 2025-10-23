"""
Vacancy Management Module
Auto-create vacancies from folder structure, track status, assign candidates
"""
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PARSED_DIR = Path("data/parsed")
VACANCY_DIR = Path("data/vacancies")
VACANCY_DIR.mkdir(parents=True, exist_ok=True)

class VacancyManager:
    def __init__(self):
        self.vacancy_dir = VACANCY_DIR
        self.vacancies = {}
        self.load_vacancies()
    
    def load_vacancies(self):
        """Load existing vacancies"""
        for json_file in self.vacancy_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                vacancy = json.load(f)
                self.vacancies[vacancy['vacancy_id']] = vacancy
    
    def save_vacancy(self, vacancy):
        """Save a vacancy to file"""
        vacancy_file = self.vacancy_dir / f"{vacancy['vacancy_id']}.json"
        with open(vacancy_file, 'w') as f:
            json.dump(vacancy, f, indent=2)
        self.vacancies[vacancy['vacancy_id']] = vacancy
    
    def create_vacancy_from_role(self, role_name):
        """Create a vacancy from a role category"""
        # Check if vacancy already exists
        for vac in self.vacancies.values():
            if vac['role_name'] == role_name and vac['status'] == 'Open':
                return vac
        
        # Generate vacancy ID
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        vacancy_id = f"VAC_{role_name.replace(' ', '_')}_{timestamp}"
        
        vacancy = {
            'vacancy_id': vacancy_id,
            'role_name': role_name,
            'status': 'Open',  # Open, On Hold, Closed, Filled
            'created_date': datetime.now().isoformat(),
            'assigned_candidates': [],
            'requirements': {
                'required_skills': [],
                'preferred_skills': [],
                'min_experience': 0,
                'education': [],
                'work_authorization': None,
                'location': None
            },
            'hiring_manager': None,
            'department': None,
            'priority': 'Medium',  # Low, Medium, High, Urgent
            'target_hire_date': None,
            'notes': []
        }
        
        self.save_vacancy(vacancy)
        return vacancy
    
    def auto_create_vacancies_from_profiles(self):
        """Auto-create vacancies from parsed profiles"""
        print("\n🔄 Auto-creating vacancies from role categories...")
        
        role_categories = set()
        
        # Get all unique role categories
        for json_file in PARSED_DIR.glob("*.json"):
            with open(json_file, 'r') as f:
                profile = json.load(f)
                role_cat = profile.get('role_category')
                if role_cat:
                    role_categories.add(role_cat)
        
        created_count = 0
        for role in role_categories:
            vacancy = self.create_vacancy_from_role(role)
            if vacancy:
                created_count += 1
                print(f"   ✅ Created/Updated vacancy: {role}")
        
        print(f"\n✅ Total vacancies: {len(self.vacancies)}")
        return created_count
    
    def assign_candidate_to_vacancy(self, vacancy_id, candidate_id):
        """Assign a candidate to a vacancy"""
        if vacancy_id not in self.vacancies:
            print(f"❌ Vacancy {vacancy_id} not found")
            return False
        
        vacancy = self.vacancies[vacancy_id]
        
        if candidate_id not in vacancy['assigned_candidates']:
            vacancy['assigned_candidates'].append(candidate_id)
            vacancy['last_updated'] = datetime.now().isoformat()
            self.save_vacancy(vacancy)
            print(f"✅ Assigned candidate {candidate_id} to vacancy {vacancy_id}")
            return True
        
        return False
    
    def update_vacancy_status(self, vacancy_id, status):
        """Update vacancy status"""
        valid_statuses = ['Open', 'On Hold', 'Closed', 'Filled']
        
        if status not in valid_statuses:
            print(f"❌ Invalid status: {status}. Must be one of {valid_statuses}")
            return False
        
        if vacancy_id not in self.vacancies:
            print(f"❌ Vacancy {vacancy_id} not found")
            return False
        
        vacancy = self.vacancies[vacancy_id]
        vacancy['status'] = status
        vacancy['last_updated'] = datetime.now().isoformat()
        
        if status == 'Filled':
            vacancy['filled_date'] = datetime.now().isoformat()
        
        self.save_vacancy(vacancy)
        print(f"✅ Updated vacancy {vacancy_id} status to {status}")
        return True
    
    def update_vacancy_requirements(self, vacancy_id, requirements):
        """Update vacancy requirements"""
        if vacancy_id not in self.vacancies:
            print(f"❌ Vacancy {vacancy_id} not found")
            return False
        
        vacancy = self.vacancies[vacancy_id]
        vacancy['requirements'].update(requirements)
        vacancy['last_updated'] = datetime.now().isoformat()
        
        self.save_vacancy(vacancy)
        print(f"✅ Updated requirements for vacancy {vacancy_id}")
        return True
    
    def add_note_to_vacancy(self, vacancy_id, note):
        """Add a note to a vacancy"""
        if vacancy_id not in self.vacancies:
            return False
        
        vacancy = self.vacancies[vacancy_id]
        vacancy['notes'].append({
            'text': note,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_vacancy(vacancy)
        return True
    
    def get_vacancy(self, vacancy_id):
        """Get a specific vacancy"""
        return self.vacancies.get(vacancy_id)
    
    def get_vacancy_by_role(self, role_name):
        """Get vacancy by role name"""
        for vacancy in self.vacancies.values():
            if vacancy['role_name'] == role_name:
                return vacancy
        return None
    
    def get_all_vacancies(self, status_filter=None):
        """Get all vacancies, optionally filtered by status"""
        if status_filter:
            return [v for v in self.vacancies.values() if v['status'] == status_filter]
        return list(self.vacancies.values())
    
    def get_vacancy_stats(self):
        """Get statistics about vacancies"""
        stats = {
            'total': len(self.vacancies),
            'by_status': defaultdict(int),
            'by_priority': defaultdict(int),
            'total_candidates': 0,
            'avg_candidates_per_vacancy': 0
        }
        
        for vacancy in self.vacancies.values():
            stats['by_status'][vacancy['status']] += 1
            stats['by_priority'][vacancy.get('priority', 'Medium')] += 1
            stats['total_candidates'] += len(vacancy.get('assigned_candidates', []))
        
        if stats['total'] > 0:
            stats['avg_candidates_per_vacancy'] = round(
                stats['total_candidates'] / stats['total'], 1
            )
        
        return stats
    
    def get_candidates_for_vacancy(self, vacancy_id):
        """Get all candidates assigned to a vacancy"""
        vacancy = self.get_vacancy(vacancy_id)
        if not vacancy:
            return []
        
        candidates = []
        for candidate_id in vacancy.get('assigned_candidates', []):
            # Load candidate profile
            candidate_file = PARSED_DIR / f"{candidate_id}.json"
            if candidate_file.exists():
                with open(candidate_file, 'r') as f:
                    candidates.append(json.load(f))
        
        return candidates
    
    def match_candidates_to_vacancy(self, vacancy_id, top_n=10):
        """Find top matching candidates for a vacancy using requirements"""
        vacancy = self.get_vacancy(vacancy_id)
        if not vacancy:
            return []
        
        requirements = vacancy['requirements']
        required_skills = set(s.lower() for s in requirements.get('required_skills', []))
        min_experience = requirements.get('min_experience', 0)
        
        # Score all candidates
        scored_candidates = []
        
        for json_file in PARSED_DIR.glob("*.json"):
            with open(json_file, 'r') as f:
                profile = json.load(f)
            
            # Skip if already assigned
            if profile['candidate_id'] in vacancy.get('assigned_candidates', []):
                continue
            
            score = 0
            
            # Match role category
            if profile.get('role_category') == vacancy['role_name']:
                score += 20
            
            # Match skills
            candidate_skills = set(s['name'].lower() for s in profile.get('skills', []))
            if required_skills:
                skill_match = len(required_skills & candidate_skills) / len(required_skills)
                score += skill_match * 40
            
            # Match experience
            candidate_exp = profile.get('experience_years', 0)
            if candidate_exp >= min_experience:
                score += 20
                # Bonus for more experience
                score += min((candidate_exp - min_experience) * 2, 10)
            
            # Work authorization
            if requirements.get('work_authorization'):
                if profile.get('work_authorization') == requirements['work_authorization']:
                    score += 10
            
            if score > 0:
                profile['match_score'] = score
                scored_candidates.append(profile)
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)
        
        return scored_candidates[:top_n]

# Singleton
_manager = None

def get_vacancy_manager():
    global _manager
    if _manager is None:
        _manager = VacancyManager()
    return _manager

if __name__ == "__main__":
    # Test vacancy management
    manager = VacancyManager()
    manager.auto_create_vacancies_from_profiles()
    
    stats = manager.get_vacancy_stats()
    print("\n" + "="*60)
    print("VACANCY STATISTICS")
    print("="*60)
    print(f"Total Vacancies: {stats['total']}")
    print(f"\nBy Status:")
    for status, count in stats['by_status'].items():
        print(f"  {status}: {count}")
    print(f"\nBy Priority:")
    for priority, count in stats['by_priority'].items():
        print(f"  {priority}: {count}")
    print(f"\nTotal Candidates: {stats['total_candidates']}")
    print(f"Avg Candidates/Vacancy: {stats['avg_candidates_per_vacancy']}")
    print("="*60 + "\n")