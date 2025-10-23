"""
Debug script to see what's in your folders
"""
from pathlib import Path

BASE_PATH = Path("/Users/swetchareddy/Desktop/Recruiting/OneDrive_1_9-22-2025")

print(f"\n🔍 Inspecting: {BASE_PATH}\n")
print(f"Path exists: {BASE_PATH.exists()}")
print(f"Is directory: {BASE_PATH.is_dir()}\n")

if not BASE_PATH.exists():
    print("❌ BASE_PATH doesn't exist! Check the path.")
    exit()

print("="*60)
print("FOLDER STRUCTURE:")
print("="*60)

# List all top-level folders
for item in sorted(BASE_PATH.iterdir()):
    if item.is_dir():
        print(f"\n📁 {item.name}")
        
        # Count subfolders
        subfolders = [x for x in item.iterdir() if x.is_dir()]
        print(f"   Subfolders: {len(subfolders)}")
        
        # List first 5 subfolders
        for subfolder in subfolders[:5]:
            print(f"   └── {subfolder.name}")
            
            # Check for resume files
            docx_files = list(subfolder.glob("*.docx"))
            pdf_files = list(subfolder.glob("*.pdf"))
            doc_files = list(subfolder.glob("*.doc"))
            
            if docx_files:
                print(f"       ✓ Found {len(docx_files)} .docx file(s)")
            if pdf_files:
                print(f"       ✓ Found {len(pdf_files)} .pdf file(s)")
            if doc_files:
                print(f"       ✓ Found {len(doc_files)} .doc file(s)")
            if not (docx_files or pdf_files or doc_files):
                # List what IS in there
                files = list(subfolder.glob("*"))
                if files:
                    print(f"       ⚠️  No resume files, but found: {[f.name for f in files[:3]]}")
                else:
                    print(f"       ⚠️  Empty folder")
        
        if len(subfolders) > 5:
            print(f"   ... and {len(subfolders) - 5} more")

print("\n" + "="*60)
print("SUMMARY:")
print("="*60)

total_candidates = 0
total_resumes = 0

for role_folder in BASE_PATH.iterdir():
    if not role_folder.is_dir():
        continue
    
    if role_folder.name.startswith('.') or role_folder.name in ['Active Associates', 'AVS CV\'s']:
        continue
    
    subfolders = [x for x in role_folder.iterdir() if x.is_dir()]
    total_candidates += len(subfolders)
    
    for candidate_folder in subfolders:
        docx = len(list(candidate_folder.glob("*.docx")))
        pdf = len(list(candidate_folder.glob("*.pdf")))
        doc = len(list(candidate_folder.glob("*.doc")))
        total_resumes += (docx + pdf + doc)

print(f"Total candidate folders: {total_candidates}")
print(f"Total resume files found: {total_resumes}")
print()