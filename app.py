import streamlit as st
from datetime import datetime
from pathlib import Path
from retrieval import get_retriever
import re
import json
import requests

def check_password():
    def password_entered():
        if st.session_state["password"] == "your-secret-password":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password")
        return False
    else:
        return True

if not check_password():
    st.stop()

st.set_page_config(
    page_title="AVS Talent Search | AI-Powered",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    .bot-message {
        background: rgba(255, 255, 255, 0.1);
        border-left: 4px solid #2a5298;
        margin-right: 20%;
    }
    .skill-tag {
        background-color: #e5e7eb;
        padding: 0.25rem 0.5rem;
        border-radius: 5px;
        margin: 0.25rem;
        display: inline-block;
        font-size: 0.875rem;
    }
    .match-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .excellent-match { background-color: #10b981; color: white; }
    .good-match { background-color: #f59e0b; color: white; }
    .possible-match { background-color: #6b7280; color: white; }
    .stTextInput > div > div > input {
        background-color: rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

def check_ollama_available():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def chat_with_ollama(prompt, context=""):
    try:
        full_prompt = f"""You are an AI recruitment assistant for AVS company. You help recruiters find and analyze candidates.

Context: {context}

User question: {prompt}

Provide a helpful, concise response. If you're showing candidates, format them clearly with bullet points."""

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 500
            }
        }
        
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return "Sorry, I couldn't process that request. Please try again."
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

@st.cache_resource
def load_retriever():
    return get_retriever()

def get_cv_path(profile):
    source_file = profile.get('source_file')
    if source_file:
        base_path = Path("data/resumes")
        return base_path / source_file
    return None

def extract_key_requirements(jd_text):
    skills = []
    years_exp = 0
    
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'node', 'aws', 'azure', 'gcp',
        'docker', 'kubernetes', 'sql', 'nosql', 'mongodb', 'postgresql',
        'machine learning', 'ml', 'ai', 'tensorflow', 'pytorch',
        'automation', 'testing', 'qa', 'selenium', 'jenkins',
        'validation', 'regulatory', 'medical device', 'gmp', 'fda', 'iso',
        'project management', 'agile', 'scrum', 'lean', 'six sigma'
    ]
    
    jd_lower = jd_text.lower()
    for skill in skill_keywords:
        if skill in jd_lower:
            skills.append(skill)
    
    exp_patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
        r'(\d+)\+?\s*years?\s+in',
        r'minimum\s+(?:of\s+)?(\d+)\s+years?'
    ]
    for pattern in exp_patterns:
        match = re.search(pattern, jd_lower)
        if match:
            years_exp = max(years_exp, int(match.group(1)))
    
    search_query = ' '.join(skills[:5]) if skills else jd_text[:100]
    
    return {
        'skills': skills[:10],
        'min_experience': years_exp,
        'search_query': search_query
    }

def mask_pii(value, reveal=False):
    if not value or reveal:
        return value
    
    if '@' in value:
        parts = value.split('@')
        return f"{'*' * min(len(parts[0]), 3)}@{parts[1]}"
    else:
        return f"+1-***-***-{value[-4:]}" if len(value) >= 4 else "***"

def log_action(action_type, details):
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    with open(log_dir / "audit.log", 'a') as f:
        timestamp = datetime.now().isoformat()
        user = st.session_state.get('user_email', 'unknown')
        f.write(f"{timestamp} | user:{user} | {action_type} | {details}\n")

def format_candidate_for_ai(profile):
    skills = [s['name'] for s in profile.get('skills', [])]
    return f"""
Candidate: {profile.get('name', 'Unknown')}
Role: {profile.get('role_category', 'N/A')}
Experience: {profile.get('experience_years', 0)} years
Skills: {', '.join(skills[:10])}
Location: {profile.get('location', 'Not specified')}
Work Auth: {profile.get('work_authorization', 'Not specified')}
"""

def process_ai_query(query, retriever):
    results = retriever.search(query, k=10)
    
    if not results:
        return "I couldn't find any candidates matching your query. Try different keywords.", []
    
    context_parts = []
    for i, profile in enumerate(results[:5], 1):
        context_parts.append(f"{i}. {format_candidate_for_ai(profile)}")
    
    context = "\n".join(context_parts)
    
    response = chat_with_ollama(query, context)
    
    return response, results

def main():
    if 'retriever' not in st.session_state:
        with st.spinner("Loading candidate database..."):
            st.session_state.retriever = load_retriever()
    
    if 'ollama_available' not in st.session_state:
        st.session_state.ollama_available = check_ollama_available()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'results' not in st.session_state:
        st.session_state.results = []
    
    if 'revealed_pii' not in st.session_state:
        st.session_state.revealed_pii = set()
    
    st.markdown("""
    <div class="main-header">
        <h1> AVS Talent Search Platform</h1>
        <p style="margin:0;">AI-Powered Recruitment • Find the Perfect Candidate Instantly</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.ollama_available:
        ai_status = " AI Assistant Active"
    else:
        ai_status = " AI Assistant Offline"
    
    st.sidebar.markdown(f"### {ai_status}")
    
    mode = st.sidebar.radio(
        "Search Mode",
        [" AI Chat Assistant", " JD Match", " Traditional Search"],
        label_visibility="collapsed"
    )
    
    st.sidebar.divider()
    st.sidebar.markdown("###  Filters")
    
    role_filter = st.sidebar.selectbox(
        "Role Category",
        ["All", "Engineering", "Quality Assurance", "Project Management", "Data Science", "Other"]
    )
    
    exp_range = st.sidebar.slider(
        "Years of Experience",
        0, 30, (0, 30)
    )
    
    k = st.sidebar.slider("Max Results", 5, 50, 10)
    
    required_skills = st.sidebar.text_input(
        "Required Skills (comma-separated)",
        placeholder="python, aws, docker"
    )
    
    if mode == "AI Chat Assistant":
        st.subheader(" AI Chat Assistant")
        
        if not st.session_state.ollama_available:
            st.warning(" AI Assistant is offline. Install Ollama and run 'ollama pull llama3' to enable.")
        
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg['role'] == 'user':
                    st.markdown(f'<div class="chat-message user-message"> {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message bot-message"> {msg["content"]}</div>', unsafe_allow_html=True)
                    
                    if 'results' in msg and msg['results']:
                        with st.expander(f"{len(msg['results'])} Candidates Found"):
                            for i, profile in enumerate(msg['results'], 1):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"**{i}. {profile.get('name', 'Unknown')}**")
                                    skills = [s['name'] for s in profile.get('skills', [])][:5]
                                    st.caption(f"Skills: {', '.join(skills)}")
                                with col2:
                                    if st.button("View Profile", key=f"view_{profile['candidate_id']}_{i}"):
                                        st.session_state.results = [profile]
                                        st.rerun()
        
        col1, col2 = st.columns([5, 1])
        with col1:
            user_message = st.text_input(
                "Ask AI Assistant",
                placeholder="e.g., 'Find senior Python engineers with AWS experience' or 'Tell me about John Smith'",
                key="chat_input",
                label_visibility="collapsed"
            )
        with col2:
            send_button = st.button("Send", use_container_width=True)
        
        st.caption("**Try:** *'Who has medical device experience?'* • *'Compare the top 3 QA engineers'* • *'Find remote workers with Python skills'*")
        
        if send_button and user_message:
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_message
            })
            
            with st.spinner("AI is thinking..."):
                ai_response, results = process_ai_query(user_message, st.session_state.retriever)
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': ai_response,
                    'results': results[:5] if results else []
                })
                
                log_action("ai_chat", f"query='{user_message}' | results={len(results)}")
            
            st.rerun()
    
    elif mode == "JD Match":
        st.subheader("Job Description Matcher")
        
        jd_text = st.text_area(
            "Paste job description",
            height=200,
            placeholder="Paste the full job description here..."
        )
        
        if st.button("Analyze JD", type="primary"):
            if jd_text:
                with st.spinner("Analyzing..."):
                    extracted = extract_key_requirements(jd_text)
                    st.session_state.jd_extracted = extracted
                    
                    if st.session_state.ollama_available:
                        ai_summary = chat_with_ollama(
                            f"Summarize this job description in 2-3 sentences:\n{jd_text[:500]}"
                        )
                        st.success("JD Analyzed!")
                        st.info(f"**AI Summary:** {ai_summary}")
                    else:
                        st.success("JD Analyzed!")
                    
                    st.markdown(f"**Skills Found:** {', '.join(extracted['skills'])}")
                    if extracted['min_experience'] > 0:
                        st.markdown(f"**Min Experience:** {extracted['min_experience']} years")
        
        if 'jd_extracted' in st.session_state:
            if st.button("Find Matching Candidates", type="primary"):
                query = st.session_state.jd_extracted['search_query']
                results = st.session_state.retriever.search(query, k=15)
                st.session_state.results = results
                log_action("jd_match", f"query='{query}' | results={len(results)}")
    
    else:
        st.subheader("Traditional Search")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            query = st.text_input(
                "Search by skills, role, or keywords",
                placeholder="e.g., python aws, QA automation, project manager",
                label_visibility="collapsed"
            )
        with col2:
            search_button = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_button and query:
            with st.spinner("Searching..."):
                filters = {}
                if role_filter != "All":
                    filters['role_category'] = role_filter
                if exp_range != (0, 30):
                    filters['min_experience'] = exp_range[0]
                    filters['max_experience'] = exp_range[1]
                
                results = st.session_state.retriever.search(query, k=k, filters=filters if filters else None)
                
                if required_skills:
                    required_list = [s.strip().lower() for s in required_skills.split(',')]
                    filtered = []
                    for profile in results:
                        profile_skills = [s['name'].lower() for s in profile.get('skills', [])]
                        if all(req in ' '.join(profile_skills) for req in required_list):
                            filtered.append(profile)
                    results = filtered
                
                st.session_state.results = results
                log_action("search", f"query='{query}' | results={len(results)}")
    
    if st.session_state.results and mode != " AI Chat Assistant":
        st.divider()
        st.subheader(f" Found {len(st.session_state.results)} Candidates")
        
        for i, profile in enumerate(st.session_state.results, 1):
            cid = profile['candidate_id']
            reveal_pii = cid in st.session_state.revealed_pii
            score = profile.get('search_score', 0)
            
            if score >= 0.7:
                badge_html = '<span class="match-badge excellent-match"> Excellent Match</span>'
            elif score >= 0.4:
                badge_html = '<span class="match-badge good-match"> Good Match</span>'
            else:
                badge_html = '<span class="match-badge possible-match"> Possible Match</span>'
            
            with st.expander(
                f"**#{i} - {profile.get('name', 'Unknown')}** | {profile.get('role_category', 'N/A')} | Match: {score:.0%}",
                expanded=(i <= 3)
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {profile.get('name', 'Unknown')}")
                    st.markdown(badge_html, unsafe_allow_html=True)
                    st.caption(f" {profile.get('role_category', 'N/A')} • {profile.get('experience_years', 0)} years")
                    
                    skills = profile.get('skills', [])
                    if skills:
                        st.markdown("**Skills:**")
                        skill_names = [s['name'] for s in skills[:12]]
                        skill_html = "".join([f'<span class="skill-tag">{s}</span>' for s in skill_names])
                        st.markdown(skill_html, unsafe_allow_html=True)
                    
                    loc = profile.get('location', 'Not specified')
                    auth = profile.get('work_authorization', 'Not specified')
                    st.caption(f"{loc} | {auth}")
                    
                    email = profile.get('email')
                    if email:
                        st.caption(f"📧 {mask_pii(email, reveal_pii)}")
                
                with col2:
                    st.metric("Match", f"{score:.0%}")
                    
                    if st.session_state.ollama_available:
                        if st.button("AI Analysis", key=f"ai_{cid}"):
                            with st.spinner("Analyzing..."):
                                candidate_context = format_candidate_for_ai(profile)
                                insight = chat_with_ollama(
                                    "Provide a brief analysis of this candidate's strengths and potential fit",
                                    candidate_context
                                )
                                st.info(f"**AI Insight:**\n\n{insight}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    cv_path = get_cv_path(profile)
                    if cv_path and cv_path.exists():
                        with open(cv_path, "rb") as file:
                            st.download_button(
                                "Download CV",
                                file,
                                file_name=cv_path.name,
                                key=f"download_{cid}"
                            )
                with col2:
                    if not reveal_pii and email:
                        if st.button("Reveal Contact", key=f"reveal_{cid}"):
                            st.session_state.revealed_pii.add(cid)
                            log_action("reveal_pii", f"candidate={cid}")
                            st.rerun()
                with col3:
                    if st.button("Shortlist", key=f"short_{cid}"):
                        st.success("Added to shortlist!")

main()