"""
Import Verification Script
"""
def check_imports():
    try:
        from src.api.v1.main import app
        from src.data.chainstack_client import ChainStackClient
        print("✓ Core imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {str(e)}")
        return False

if __name__ == "__main__":
    check_imports()
