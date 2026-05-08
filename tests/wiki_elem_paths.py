import sys
import os
sys.path.append(os.getcwd())

def test_wiki_architecture_paths():
    arch_path = "wiki/logic/Architecture.md"
    if not os.path.exists(arch_path):
        print(f"❌ FAIL: {arch_path} not found.")
        return

    with open(arch_path, 'r') as f:
        content = f.read()

    # Look for patterns like `app/services/database.py`
    import re
    paths = re.findall(r'`([^`]+?\.py)`', content)
    
    broken = []
    for p in paths:
        if not os.path.exists(p):
            broken.append(p)
            
    if not broken:
        print("✅ PASS: All code paths in Architecture.md exist.")
    else:
        print(f"❌ FAIL: Broken code paths in Architecture.md: {broken}")

if __name__ == "__main__":
    test_wiki_architecture_paths()
