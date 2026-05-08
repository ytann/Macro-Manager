import sys
import os
sys.path.append(os.getcwd())

def test_wiki_index_links():
    index_path = "wiki/index.md"
    if not os.path.exists(index_path):
        print(f"❌ FAIL: {index_path} not found.")
        return

    with open(index_path, 'r') as f:
        content = f.read()

    # Find all [[path/to/file.md]]
    import re
    links = re.findall(r'\[\[(.*?)\]\]', content)
    
    broken = []
    for link in links:
        # Index links might be relative to wiki/ or root
        # Try various paths
        paths_to_check = [link, f"wiki/{link}"]
        exists = any(os.path.exists(p) for p in paths_to_check)
        if not exists:
            broken.append(link)
    
    if not broken:
        print("✅ PASS: All wiki index links are valid.")
    else:
        print(f"❌ FAIL: Broken wiki links found: {broken}")

if __name__ == "__main__":
    test_wiki_index_links()
