"""
Verify required packages are installed correctly
"""
import importlib
from termcolor import cprint

def verify_packages():
    """Verify all required packages are installed"""
    required_packages = [
        'numpy',
        'pandas',
        'pymongo',
        'motor',
        'dnspython',
        'websockets',
        'solders',
        'apscheduler',
        'PyQt6',
        'qt_material',
        'darkdetect'
    ]
    
    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        cprint("❌ Missing required packages:", "red")
        for pkg in missing:
            cprint(f"  - {pkg}", "red")
        return False
    
    cprint("✅ All required packages installed successfully", "green")
    return True

if __name__ == '__main__':
    verify_packages()
