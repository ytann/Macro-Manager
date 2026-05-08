import sys
import os
sys.path.append(os.getcwd())

def test_wiki_entities_dir_empty():
    dir_path = "wiki/entities/"
    if not os.path.exists(dir_path):
        print(f"✅ PASS: {dir_path} does not exist (effectively empty).")
        return
    
    if not os.listdir(dir_path):
        print(f"❌ FAIL: {dir_path} exists but is empty. Should be removed.")
    else:
        print(f"✅ PASS: {dir_path} is not empty.")

if __name__ == "__main__":
    test_wiki_entities_dir_empty()
