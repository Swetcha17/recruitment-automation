import streamlit as st
import subprocess
import sys
import re
import json
import requests
from datetime import datetime
from pathlib import Path
from retrieval import get_retriever

# --- Configuration & Setup ---
st.set_page_config(
    page_title="AVS Talent Search Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        color: white;
    }
    .skill-tag {
        background-color: #f0f2f6;
        padding: 4px 8px;
        border-radius: 4px;
        margin: 2px;
        display: inline-block;
        font-size: 0.85rem;
        border: 1px solid #d1d5db;
    }
    .match-badge {
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    .badge-high { background-color: #d1fae5; color: #065f46; }
    .badge-med { background-color: #fef3c7; color: #92400e; }
    .badge-low { background-color: #f3f4f6; color: #374151; }
</style>
""", unsafe_allow_html=True)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# --- Helper Functions ---

def ensure_data_exists():
    """Checks for data and builds indexes if missing."""
    parsed_dir = Path("data/parsed")
    index_dir = Path("data/index")
    
    if not parsed_dir.exists() or not list(parsed_dir.glob("*.json")):
        st.warning("No candidate data found.")
        st.info("Please add resumes to 'data/resumes/' and run the parsing script.")
        st.stop()
    
    if not (index_dir / "faiss.index").exists():
        with st.spinner("Building search indexes..."):
            try:
                subprocess.run([sys.executable, "build_faiss.py"], check=True)
                subprocess.run([sys.executable, "build_fts.py"], check=True)
                st.success("Indexes built successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to build indexes: {e}")
                st.stop()

def check_ollama_available():
    """Checks if local LLM is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=1)
        return response.status_code == 200
    except:
        return False

def chat_with_ollama(prompt, context=""):
    """Interacts with local LLM."""
    try:
        full_prompt = f"""You are a recruitment assistant.
        Context: {context}
        User Query: {prompt}
        Provide a concise, professional response."""

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 300}
        }
        
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["response"]
        return "AI processing failed."
    except Exception as e:
        return f"AI Connection Error: {e}"

def mask_pii(value, reveal=False):
    """Masks email and phone numbers for privacy."""
    if not value or reveal:
        return value
    if '@' in value:
        parts = value.split('@')
        return f"{'*' * 3}@{parts[1]}"
    return "***-***-****"

def extract_requirements_from_jd(text):
    """Simple keyword extraction from Job Description."""
    keywords = [
        'python', 'java', 'sql', 'aws', 'docker', 'kubernetes', 'react', 
        'node', 'machine learning', 'nlp', 'pytorch', 'agile', 'scrum'
    ]
    found_skills = [k for k in keywords if k in text.lower()]
    return {
        'skills': found_skills,
        'search_query': ' '.join(found_skills) if found_skills else text[:100]
    }

@st.cache_resource
def load_retriever():
    return get_retriever()

# --- Main Application ---

def main():
    ensure_data_exists()
    
    # Session State Init
    if 'revealed_pii' not in st.session_state:
        st.session_state.revealed_pii = set()
    if 'ollama_online' not in st.session_state:
        st.session_state.ollama_online = check_ollama_available()

    try:
        retriever = load_retriever()
    except Exception as e:
        st.error(f"System Error: {e}")
        st.stop()

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>AVS Talent Search Platform</h1>
        <p style="margin:0;">AI-Powered Recruitment & Candidate Analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("Navigation")
    mode = st.sidebar.radio("Search Mode", ["Traditional Search", "JD Match", "AI Assistant"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    role_filter = st.sidebar.selectbox("Role", ["All", "Engineering", "Sales", "Product", "Marketing"])
    min_exp = st.sidebar.slider("Min Experience", 0, 20, 0)
    
    # Logic Controller
    results = []
    
    # MODE 1: Traditional Search
    if mode == "Traditional Search":
        query = st.text_input("Search Candidates", placeholder="e.g. Senior Python Developer with Cloud experience")
        if st.button("Search Database", type="primary") or query:
            filters = {}
            if role_filter != "All":
                filters['role_category'] = role_filter
            if min_exp > 0:
                filters['min_experience'] = min_exp
                
            results = retriever.semantic_search(query, k=10, filters=filters)

    # MODE 2: JD Match
    elif mode == "JD Match":
        st.subheader("Job Description Analysis")
        jd_text = st.text_area("Paste Job Description", height=200)
        
        if st.button("Analyze & Match"):
            if jd_text:
                reqs = extract_requirements_from_jd(jd_text)
                st.success(f"Extracted Key Skills: {', '.join(reqs['skills'])}")
                
                # AI Summary if available
                if st.session_state.ollama_online:
                    with st.spinner("Generating AI Summary..."):
                        summary = chat_with_ollama(f"Summarize this role in 1 sentence: {jd_text[:500]}")
                        st.info(f"AI Summary: {summary}")

                results = retriever.semantic_search(reqs['search_query'], k=15)

    # MODE 3: AI Assistant
    elif mode == "AI Assistant":
        st.subheader("AI Recruitment Chat")
        if not st.session_state.ollama_online:
            st.warning("AI Service Offline. Ensure Ollama is running locally.")
        else:
            user_query = st.text_input("Ask the AI", placeholder="Find me candidates who know PyTorch...")
            if st.button("Send Query") and user_query:
                # 1. Search first to get context
                search_res = retriever.semantic_search(user_query, k=5)
                
                # 2. Format context for LLM
                context_str = "\n".join([f"- {r.get('name')}: {r.get('resume_snippet')[:200]}" for r in search_res])
                
                # 3. Get LLM Response
                with st.spinner("AI is analyzing candidates..."):
                    ai_response = chat_with_ollama(user_query, context=context_str)
                    st.markdown(f"**AI Response:**\n\n{ai_response}")
                    results = search_res

    # --- Results Rendering ---
    if results:
        st.markdown(f"### Found {len(results)} Candidates")
        for profile in results:
            cid = profile['candidate_id']
            score = profile.get('search_score', 0)
            
            # Badge Logic
            if score > 0.6:
                badge_class = "badge-high"
                match_text = "Excellent Match"
            elif score > 0.4:
                badge_class = "badge-med"
                match_text = "Good Match"
            else:
                badge_class = "badge-low"
                match_text = "Potential Match"

            with st.expander(f"{profile.get('name', 'Candidate')} - {match_text} ({score:.0%})"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"<span class='match-badge {badge_class}'>{match_text}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Role:** {profile.get('role_category', 'N/A')}")
                    st.markdown(f"**Experience:** {profile.get('experience_years', 0)} years")
                    
                    # Skills
                    skills = [s['name'] for s in profile.get('skills', [])][:8]
                    skill_html = "".join([f"<span class='skill-tag'>{s}</span>" for s in skills])
                    st.markdown(f"<div style='margin-top:8px'>{skill_html}</div>", unsafe_allow_html=True)
                    
                    st.caption(f"Snippet: ...{profile.get('resume_snippet', '')[:300]}...")

                with col2:
                    # PII Handling
                    is_revealed = cid in st.session_state.revealed_pii
                    email = profile.get('email', 'N/A')
                    phone = profile.get('phone', 'N/A')
                    
                    st.markdown("#### Contact")
                    st.text(f"Email: {mask_pii(email, is_revealed)}")
                    st.text(f"Phone: {mask_pii(phone, is_revealed)}")
                    
                    if not is_revealed:
                        if st.button("Reveal Contact", key=f"rev_{cid}"):
                            st.session_state.revealed_pii.add(cid)
                            st.rerun()
                    
                    if st.button("Download CV", key=f"dl_{cid}"):
                        st.toast("Download disabled in demo mode.")

if __name__ == "__main__":
    main()