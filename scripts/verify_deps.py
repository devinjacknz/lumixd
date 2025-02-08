"""
Dependency and Environment Verification Script
"""
import os
import sys
import importlib
import importlib.metadata
from packaging import version
from dotenv import load_dotenv

def verify_env_vars():
    """Verify required environment variables"""
    load_dotenv()
    required_vars = ['CHAINSTACK_WS_ENDPOINT', 'RPC_ENDPOINT']
    all_set = True
    print("\nEnvironment Variables:")
    for var in required_vars:
        value = os.getenv(var)
        status = '✓ Set' if value else '✗ Missing'
        print(f"{var}: {status}")
        if not value:
            all_set = False
    return all_set

def verify_package(package_name, required_version=None):
    """Verify package installation and version"""
    try:
        # Handle special cases for package names
        import_name = package_name.replace('-', '_').replace('python_dotenv', 'dotenv')
        pkg = importlib.import_module(import_name)
        
        if not required_version:
            return f"✓ {package_name} installed"
            
        # Special handling for PyQt6
        if package_name == 'PyQt6':
            from PyQt6.QtCore import PYQT_VERSION_STR
            pkg_version = PYQT_VERSION_STR
        # Special handling for qt-material
        elif package_name == 'qt_material':
            pkg_version = importlib.metadata.version('qt-material')
        # Special handling for python-dotenv
        elif package_name == 'python-dotenv':
            pkg_version = importlib.metadata.version('python-dotenv')
        else:
            pkg_version = getattr(pkg, '__version__', None)
            if not pkg_version:
                try:
                    pkg_version = importlib.metadata.version(package_name)
                except importlib.metadata.PackageNotFoundError:
                    pass
                    
        if pkg_version:
            if required_version.startswith('>='):
                req_ver = version.parse(required_version[2:])
                current_ver = version.parse(pkg_version)
                if current_ver >= req_ver:
                    return f"✓ {package_name}=={pkg_version} (>={req_ver})"
                return f"✗ {package_name}=={pkg_version} (requires >={req_ver})"
            elif version.parse(pkg_version) == version.parse(required_version):
                return f"✓ {package_name}=={pkg_version}"
            return f"✗ {package_name}=={pkg_version} (requires {required_version})"
        return f"? {package_name} version unknown"
    except ImportError:
        return f"✗ {package_name} not installed"

def verify_dependencies():
    """Verify all required dependencies"""
    required_packages = {
        'websockets': '12.0',
        'PyQt6': '6.6.1',
        'qt_material': '2.14',
        'darkdetect': '0.8.0',
        'fastapi': '>=0.110.0',
        'uvicorn': '>=0.29.0',
        'python-dotenv': '>=1.0.0',
        'pytest_asyncio': None,
        'pytest_mock': None,
        'pytest_cov': None,
        'pytest_qt': None
    }
    
    all_installed = True
    print("\nPython Packages:")
    for package, version_req in required_packages.items():
        status = verify_package(package.replace('-', '_'), version_req)
        print(status)
        if status.startswith('✗'):
            all_installed = False
    return all_installed

def verify_system_deps():
    """Verify system dependencies"""
    print("\nSystem Dependencies:")
    try:
        from PyQt6.QtWidgets import QApplication
        print("✓ PyQt6 system integration")
        return True
    except Exception as e:
        print(f"✗ PyQt6 system integration: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Dependency Verification ===")
    env_ok = verify_env_vars()
    deps_ok = verify_dependencies()
    sys_ok = verify_system_deps()
    
    if not all([env_ok, deps_ok, sys_ok]):
        print("\n❌ Some verifications failed")
        sys.exit(1)
    print("\n✓ All verifications passed")
