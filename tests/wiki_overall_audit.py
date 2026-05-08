import sys
import os
sys.path.append(os.getcwd())

def test_wiki_overall_audit():
    wiki_dir = "wiki/logic"
    if not os.path.exists(wiki_dir):
        print(f"❌ FAIL: {wiki_dir} not found.")
        return

    files = os.listdir(wiki_dir)
    # Current files in wiki/logic as per README: Architecture.md, FoodLearning.md, FoodLogSchema.md, OfflineSync.md, audit_logic.md
    expected = {"Architecture.md", "FoodLearning.md", "FoodLogSchema.md", "OfflineSync.md", "audit_logic.md"}
    
    missing = expected - set(files)
    if not missing:
        print("✅ PASS: All required logic pages exist.")
    else:
        print(f"❌ FAIL: Missing logic pages: {missing}")

if __name__ == "__main__":
    test_wiki_overall_audit()
