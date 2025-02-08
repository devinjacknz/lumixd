"""
Comprehensive Package Version Verification Script
"""
import sys
import importlib.metadata as metadata
from packaging.version import parse

def verify_versions():
    """Verify all required package versions"""
    packages = {
        'websockets': '12.0',
        'PyQt6': '6.6.1',
        'qt-material': '2.14',
        'darkdetect': '0.8.0',
        'fastapi': '>=0.110.0',
        'uvicorn': '>=0.29.0',
        'python-dotenv': '>=1.0.0',
        'pytest-asyncio': None,
        'pytest-mock': None,
        'pytest-cov': None,
        'pytest-qt': None
    }
    
    print("Package Version Verification:")
    print("-" * 50)
    
    all_ok = True
    for pkg, required_ver in packages.items():
        try:
            installed = metadata.version(pkg)
            if required_ver:
                if required_ver.startswith('>='):
                    min_ver = parse(required_ver[2:])
                    ok = parse(installed) >= min_ver
                    status = f"✓ {installed} (>={min_ver})" if ok else f"✗ {installed} (requires >={min_ver})"
                else:
                    ok = parse(installed) == parse(required_ver)
                    status = f"✓ {installed}" if ok else f"✗ {installed} (requires {required_ver})"
                all_ok = all_ok and ok
            else:
                status = f"✓ {installed}"
            print(f"{pkg:20} {status}")
        except metadata.PackageNotFoundError:
            print(f"{pkg:20} ✗ Not installed")
            all_ok = False
    
    print("\nSystem Dependencies:")
    print("-" * 50)
    try:
        from PyQt6.QtCore import QT_VERSION_STR
        print(f"Qt version:          ✓ {QT_VERSION_STR}")
    except ImportError as e:
        print(f"Qt version:          ✗ {str(e)}")
        all_ok = False
    
    return all_ok

if __name__ == "__main__":
    success = verify_versions()
    sys.exit(0 if success else 1)
