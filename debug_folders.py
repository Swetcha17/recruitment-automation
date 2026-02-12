"""
Debug script to inspect the folder structure and verify resume files.
"""
import os
from pathlib import Path

# CHANGED: Use a relative path so it works on any machine
BASE_PATH = Path("data/resumes")

print(f"\nInspecting Directory: {BASE_PATH}\n")

if not BASE_PATH.exists():
    print(f"Error: Directory '{BASE_PATH}' does not exist.")
    print("Action Required: Please create a folder named 'data/resumes' and add your candidate folders inside.")
    exit()

print("=" * 60)
print("DIRECTORY STRUCTURE")
print("=" * 60)

# List all top-level folders (Roles)
for item in sorted(BASE_PATH.iterdir()):
    if item.is_dir() and not item.name.startswith('.'):
        print(f"\nDirectory: {item.name}")
        
        # Count subfolders (Candidates)
        subfolders = [x for x in item.iterdir() if x.is_dir()]
        print(f"   Subdirectories: {len(subfolders)}")
        
        # List first 5 subfolders to keep output clean
        for subfolder in subfolders[:5]:
            print(f"   -- {subfolder.name}")
            
            # Check for resume files
            docx_files = list(subfolder.glob("*.docx"))
            pdf_files = list(subfolder.glob("*.pdf"))
            doc_files = list(subfolder.glob("*.doc"))
            
            if docx_files:
                print(f"      Found {len(docx_files)} .docx file(s)")
            if pdf_files:
                print(f"      Found {len(pdf_files)} .pdf file(s)")
            if doc_files:
                print(f"      Found {len(doc_files)} .doc file(s)")
                
            if not (docx_files or pdf_files or doc_files):
                # Check if folder is empty or contains other files
                files = list(subfolder.glob("*"))
                if files:
                    print(f"      [!] No resumes, but found: {[f.name for f in files[:3]]}")
                else:
                    print(f"      [!] Empty folder")
        
        if len(subfolders) > 5:
            print(f"   ... and {len(subfolders) - 5} more")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

total_candidates = 0
total_resumes = 0

for role_folder in BASE_PATH.iterdir():
    if not role_folder.is_dir() or role_folder.name.startswith('.'):
        continue
    
    # Skip specific internal folders if necessary
    if role_folder.name in ['Active Associates', 'Archive']:
        continue
    
    subfolders = [x for x in role_folder.iterdir() if x.is_dir()]
    total_candidates += len(subfolders)
    
    for candidate_folder in subfolders:
        docx = len(list(candidate_folder.glob("*.docx")))
        pdf = len(list(candidate_folder.glob("*.pdf")))
        doc = len(list(candidate_folder.glob("*.doc")))
        total_resumes += (docx + pdf + doc)

print(f"Total Candidate Profiles: {total_candidates}")
print(f"Total Resume Files Found: {total_resumes}")