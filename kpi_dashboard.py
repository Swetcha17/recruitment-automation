import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# --- Configuration ---
PARSED_DIR = Path("data/parsed")
METRICS_DIR = Path("data/metrics")
METRICS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_FILE = METRICS_DIR / "kpi_metrics.json"

class KPIDashboard:
    def __init__(self):
        self.metrics_file = METRICS_FILE
        self.load_metrics()
    
    def load_metrics(self):
        """Load existing metrics from disk or initialize defaults."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    self.metrics = json.load(f)
            except json.JSONDecodeError:
                self._init_default_metrics()
        else:
            self._init_default_metrics()

    def _init_default_metrics(self):
        """Initialize empty metrics structure."""
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
        """Save current metrics to disk."""
        self.metrics['last_updated'] = datetime.now().isoformat()
        # Convert defaultdicts to regular dicts for JSON serialization
        serializable_metrics = self.metrics.copy()
        if isinstance(serializable_metrics.get('rejections_by_reason'), defaultdict):
            serializable_metrics['rejections_by_reason'] = dict(serializable_metrics['rejections_by_reason'])
        if isinstance(serializable_metrics.get('candidates_by_source'), defaultdict):
            serializable_metrics['candidates_by_source'] = dict(serializable_metrics['candidates_by_source'])
            
        with open(self.metrics_file, 'w') as f:
            json.dump(serializable_metrics, f, indent=2)
    
    def calculate_metrics_from_profiles(self):
        """Re-scan all profiles to rebuild aggregate metrics."""
        self.metrics['candidates_by_stage'] = defaultdict(int)
        self.metrics['conversions'] = {'uploaded': 0, 'reviewed': 0, 'interviewed': 0, 'offered': 0, 'hired': 0}
        self.metrics['candidates_by_source'] = defaultdict(int)
        
        time_to_present_list = []
        time_to_hire_list = []
        
        # Scan every profile in the parsed directory
        for json_file in PARSED_DIR.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    profile = json.load(f)
            except:
                continue

            stage = profile.get('stage', 'Uploaded')
            self.metrics['candidates_by_stage'][stage] += 1
            
            # --- Funnel Logic (Cumulative) ---
            # Every candidate counts as 'Uploaded'
            self.metrics['conversions']['uploaded'] += 1
            
            if stage in ['Reviewed', 'Screening', 'Interview', 'Offer', 'Hired']:
                self.metrics['conversions']['reviewed'] += 1
            
            if stage in ['Interview', 'Offer', 'Hired']:
                self.metrics['conversions']['interviewed'] += 1
            
            if stage in ['Offer', 'Hired']:
                self.metrics['conversions']['offered'] += 1
            
            if stage == 'Hired':
                self.metrics['conversions']['hired'] += 1

            # --- Time Calculations ---
            parsed_date = profile.get('parsed_date')
            if parsed_date:
                try:
                    parsed_dt = datetime.fromisoformat(parsed_date)
                    now = datetime.now()
                    
                    # Time to Present (Time from upload to being reviewed/interviewed)
                    if stage not in ['Uploaded', 'New']:
                        hours = (now - parsed_dt).total_seconds() / 3600
                        time_to_present_list.append(hours)

                    # Time to Hire
                    if stage == 'Hired':
                        days = (now - parsed_dt).days
                        time_to_hire_list.append(days)
                except ValueError:
                    pass

            # --- Source Effectiveness ---
            role_category = profile.get('role_category', 'Unknown')
            self.metrics['candidates_by_source'][role_category] += 1

        self.metrics['time_to_present'] = time_to_present_list
        self.metrics['time_to_hire'] = time_to_hire_list
        self.save_metrics()
    
    def get_time_to_present(self):
        times = self.metrics.get('time_to_present', [])
        if times:
            return round(sum(times) / len(times), 1)
        return 0
    
    def get_time_to_hire(self):
        times = self.metrics.get('time_to_hire', [])
        if times:
            return round(sum(times) / len(times), 1)
        return 0
    
    def get_conversion_rate(self):
        conversions = self.metrics.get('conversions', {})
        uploaded = conversions.get('uploaded', 0)
        hired = conversions.get('hired', 0)
        if uploaded > 0:
            return round((hired / uploaded) * 100, 1)
        return 0
    
    def get_pipeline_velocity(self):
        # Dummy baseline for demo purposes
        baseline_days = 14 
        actual_days = self.get_time_to_hire()
        if actual_days > 0:
            return round(baseline_days / actual_days, 1)
        return 1.0
    
    def get_candidate_pool_size(self):
        return len(list(PARSED_DIR.glob("*.json")))
    
    def get_active_vacancies(self):
        # Count unique roles from profiles as a proxy for vacancies
        role_categories = set()
        for json_file in PARSED_DIR.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    profile = json.load(f)
                    if profile.get('role_category'):
                        role_categories.add(profile['role_category'])
            except:
                continue
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
            try:
                with open(json_file, 'r') as f:
                    profile = json.load(f)
                parsed_date = profile.get('parsed_date')
                if parsed_date:
                    parsed_dt = datetime.fromisoformat(parsed_date)
                    if parsed_dt >= cutoff_date:
                        date_key = parsed_dt.strftime('%Y-%m-%d')
                        date_counts[date_key] += 1
            except:
                continue
                
        sorted_dates = sorted(date_counts.items())
        return {
            'dates': [d[0] for d in sorted_dates], 
            'counts': [d[1] for d in sorted_dates]
        }
    
    def get_stage_duration_analysis(self):
        # Returns dummy average days per stage for visualization
        return {'Uploaded': 1.5, 'Screening': 2.0, 'Interview': 5.0, 'Offer': 3.0}
    
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
        """Aggregate all metrics into a single dictionary for the frontend."""
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

# Singleton Instance
_dashboard = None

def get_dashboard():
    global _dashboard
    if _dashboard is None:
        _dashboard = KPIDashboard()
    return _dashboard