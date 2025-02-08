"""
Package Version Checker Script
"""
import importlib.metadata

def check_package_versions():
    packages = ['python-dotenv', 'pytest-qt']
    for package in packages:
        try:
            version = importlib.metadata.version(package)
            print(f"{package}: {version}")
        except importlib.metadata.PackageNotFoundError:
            print(f"{package}: Not found")

if __name__ == "__main__":
    check_package_versions()
