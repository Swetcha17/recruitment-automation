# AI-Powered Talent Acquisition System

A privacy-focused, local recruitment platform that automates resume parsing, candidate matching, and KPI tracking. This system uses AI (Vector Search & TF-IDF) to match candidates to vacancies without sending data to the cloud.

---

## Key Features

* Intelligent Resume Parsing: Automatically extracts skills, experience, contact info, and role categories from PDF and DOCX resumes.
* Hybrid Search Engine: Combines **Semantic Search** (conceptual matching via FAISS) with **Keyword Search** (SQLite FTS5) for high-precision candidate discovery.
* Executive Dashboard: Visualizes hiring funnels, time-to-hire, source effectiveness, and other critical recruitment KPIs.
* Vacancy Management: Auto-creates vacancies based on resume folders and scores candidates against job requirements.
* Privacy First: 100% local processing. No data is sent to external APIs (unless you explicitly enable Ollama integration).

---

##  Installation & Setup

### 1. Prerequisites
* Python 3.8 or higher
* pip (Python Package Manager)

### 2. Install Dependencies
Create a virtual environment (recommended) and install the required packages:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On Mac/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
