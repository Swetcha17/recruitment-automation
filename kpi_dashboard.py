import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

PARSED_DIR = Path("data/parsed")
METRICS_DIR = Path("data/metrics")
METRICS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_FILE = METRICS_DIR / "kpi_metrics.json"

class KPIDashboard:
    def __init__(self):
        self.metrics_file = METRICS_FILE
        self.load_metrics()
    
    def load_metrics(self):
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                self.metrics = json.load(f)
        else:
            self.metrics = {
                'candidates_by_stage': defaultdict(int),
                'stage_transitions': [],
                'time_to_present': [],
                'time_to_hire': [],
                'conversions': {'uploaded': 0, 'reviewed': 0, 'interviewed': 0, 'offered': 0, 'hired': 0},
                'rejections_by_reason': defaultdict(int),
                'candidates_by_source': defaultdict(int),
                'last_updated': datetime.now().isoformat()
            }
    
    def save_metrics(self):
        self.metrics['last_updated'] = datetime.now().isoformat()
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def calculate_metrics_from_profiles(self):
        self.metrics['candidates_by_stage'] = defaultdict(int)
        self.metrics['conversions'] = {'uploaded': 0, 'reviewed': 0, 'interviewed': 0, 'offered': 0, 'hired': 0}
        time_to_present_list = []
        time_to_hire_list = []
        for json_file in PARSED_DIR.glob("*.json"):
            with open(json_file, 'r') as f:
                profile = json.load(f)
            stage = profile.get('stage', 'Uploaded')
            self.metrics['candidates_by_stage'][stage] += 1
            if stage == 'Uploaded':
                self.metrics['conversions']['uploaded'] += 1
            elif stage in ['Screening', 'Reviewed']:
                self.metrics['conversions']['reviewed'] += 1
                self.metrics['conversions']['uploaded'] += 1
            elif stage == 'Interview':
                self.metrics['conversions']['interviewed'] += 1
                self.metrics['conversions']['reviewed'] += 1
                self.metrics['conversions']['uploaded'] += 1
            elif stage == 'Offer':
                self.metrics['conversions']['offered'] += 1
                self.metrics['conversions']['interviewed'] += 1
                self.metrics['conversions']['reviewed'] += 1
                self.metrics['conversions']['uploaded'] += 1
            elif stage == 'Hired':
                self.metrics['conversions']['hired'] += 1
                self.metrics['conversions']['offered'] += 1
                self.metrics['conversions']['interviewed'] += 1
                self.metrics['conversions']['reviewed'] += 1
                self.metrics['conversions']['uploaded'] += 1
            parsed_date = profile.get('parsed_date')
            if parsed_date:
                parsed_dt = datetime.fromisoformat(parsed_date)
                if stage not in ['Uploaded', 'New']:
                    time_to_present_list.append({
                        'candidate_id': profile['candidate_id'],
                        'hours': (datetime.now() - parsed_dt).total_seconds() / 3600
                    })
                if stage == 'Hired':
                    time_to_hire_list.append({
                        'candidate_id': profile['candidate_id'],
                        'days': (datetime.now() - parsed_dt).days
                    })
            role_category = profile.get('role_category', 'Unknown')
            self.metrics['candidates_by_source'][role_category] += 1
        self.metrics['time_to_present'] = time_to_present_list
        self.metrics['time_to_hire'] = time_to_hire_list
        self.save_metrics()
    
    def get_time_to_present(self):
        times = self.metrics.get('time_to_present', [])
        if times:
            return round(sum(t['hours'] for t in times) / len(times), 1)
        return 0
    
    def get_time_to_hire(self):
        times = self.metrics.get('time_to_hire', [])
        if times:
            return round(sum(t['days'] for t in times) / len(times), 1)
        return 0
    
    def get_conversion_rate(self):
        conversions = self.metrics.get('conversions', {})
        uploaded = conversions.get('uploaded', 0)
        hired = conversions.get('hired', 0)
        if uploaded > 0:
            return round((hired / uploaded) * 100, 1)
        return 0
    
    def get_pipeline_velocity(self):
        baseline_days = 7
        actual_days = self.get_time_to_hire()
        if actual_days > 0:
            return round(baseline_days / actual_days, 1)
        return 1.0
    
    def get_candidate_pool_size(self):
        return len(list(PARSED_DIR.glob("*.json")))
    
    def get_active_vacancies(self):
        role_categories = set()
        for json_file in PARSED_DIR.glob("*.json"):
            with open(json_file, 'r') as f:
                profile = json.load(f)
                role_cat = profile.get('role_category')
                if role_cat:
                    role_categories.add(role_cat)
        return len(role_categories)
    
    def get_stage_distribution(self):
        return dict(self.metrics.get('candidates_by_stage', {}))
    
    def get_conversion_funnel_data(self):
        conversions = self.metrics.get('conversions', {})
        return {
            'stages': ['Uploaded', 'Reviewed', 'Interviewed', 'Offered', 'Hired'],
            'values': [
                conversions.get('uploaded', 0),
                conversions.get('reviewed', 0),
                conversions.get('interviewed', 0),
                conversions.get('offered', 0),
                conversions.get('hired', 0)
            ]
        }
    
    def get_source_effectiveness(self):
        return dict(self.metrics.get('candidates_by_source', {}))
    
    def get_hiring_trends(self, days=30):
        date_counts = defaultdict(int)
        cutoff_date = datetime.now() - timedelta(days=days)
        for json_file in PARSED_DIR.glob("*.json"):
            with open(json_file, 'r') as f:
                profile = json.load(f)
                parsed_date = profile.get('parsed_date')
                if parsed_date:
                    parsed_dt = datetime.fromisoformat(parsed_date)
                    if parsed_dt >= cutoff_date:
                        date_key = parsed_dt.strftime('%Y-%m-%d')
                        date_counts[date_key] += 1
        sorted_dates = sorted(date_counts.items())
        return {'dates': [d[0] for d in sorted_dates], 'counts': [d[1] for d in sorted_dates]}
    
    def get_stage_duration_analysis(self):
        return {'Uploaded': 0.5, 'Screening': 1.0, 'Interview': 2.0, 'Offer': 1.5, 'Hired': 0}
    
    def get_rejection_breakdown(self):
        return dict(self.metrics.get('rejections_by_reason', {}))
    
    def track_stage_transition(self, candidate_id, from_stage, to_stage):
        transition = {
            'candidate_id': candidate_id,
            'from_stage': from_stage,
            'to_stage': to_stage,
            'timestamp': datetime.now().isoformat()
        }
        if 'stage_transitions' not in self.metrics:
            self.metrics['stage_transitions'] = []
        self.metrics['stage_transitions'].append(transition)
        self.save_metrics()
    
    def record_rejection(self, candidate_id, reason):
        if 'rejections_by_reason' not in self.metrics:
            self.metrics['rejections_by_reason'] = defaultdict(int)
        self.metrics['rejections_by_reason'][reason] += 1
        self.save_metrics()
    
    def get_dashboard_summary(self):
        self.calculate_metrics_from_profiles()
        return {
            'time_to_present': self.get_time_to_present(),
            'time_to_hire': self.get_time_to_hire(),
            'conversion_rate': self.get_conversion_rate(),
            'pipeline_velocity': self.get_pipeline_velocity(),
            'candidate_pool': self.get_candidate_pool_size(),
            'active_vacancies': self.get_active_vacancies(),
            'stage_distribution': self.get_stage_distribution(),
            'conversion_funnel': self.get_conversion_funnel_data(),
            'source_effectiveness': self.get_source_effectiveness(),
            'hiring_trends': self.get_hiring_trends(),
            'stage_durations': self.get_stage_duration_analysis(),
            'rejection_breakdown': self.get_rejection_breakdown()
        }

_dashboard = None

def get_dashboard():
    global _dashboard
    if _dashboard is None:
        _dashboard = KPIDashboard()
    return _dashboard