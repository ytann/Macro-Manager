import sys
import os
import ast
sys.path.append(os.getcwd())

def test_frontend_async_pattern():
    frontend_path = "app/frontend.py"
    if not os.path.exists(frontend_path):
        print(f"❌ FAIL: {frontend_path} not found.")
        return

    with open(frontend_path, 'r') as f:
        tree = ast.parse(f.read())
    
    # Check if the frontend uses async functions or httpx.AsyncClient
    has_async = any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(tree))
    has_httpx = any(
        isinstance(node, ast.ImportFrom) and node.module == 'httpx' 
        or (isinstance(node, ast.Import) and any(alias.name == 'httpx' for alias in node.names))
        for node in ast.walk(tree)
    )
    
    if has_async or has_httpx:
        print("✅ PASS: Frontend uses async patterns or httpx.")
    else:
        print("❌ FAIL: Frontend appears to be entirely synchronous.")

if __name__ == "__main__":
    test_frontend_async_pattern()
