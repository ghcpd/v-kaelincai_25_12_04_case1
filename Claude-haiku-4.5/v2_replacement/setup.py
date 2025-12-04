#!/usr/bin/env python
"""
Setup script for v2 routing system.

Usage:
  python setup.py
  
  OR on Windows:
  python.exe setup.py
"""

import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run shell command."""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}\n")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"ERROR: {description} failed with exit code {result.returncode}")
        sys.exit(1)

def main():
    repo_root = Path(__file__).parent
    
    print(f"\nSetup v2 Routing System")
    print(f"Repository root: {repo_root}\n")
    
    # Step 1: Create virtual environment (if not exists)
    venv_path = repo_root / ".venv"
    if not venv_path.exists():
        run_command(
            f"{sys.executable} -m venv .venv",
            "Creating virtual environment"
        )
    
    # Step 2: Activate and upgrade pip
    if sys.platform == "win32":
        activate_cmd = ".venv\\Scripts\\activate.bat && "
    else:
        activate_cmd = "source .venv/bin/activate && "
    
    run_command(
        f"{activate_cmd}{sys.executable} -m pip install --upgrade pip setuptools wheel",
        "Upgrading pip, setuptools, wheel"
    )
    
    # Step 3: Install dependencies
    run_command(
        f"{activate_cmd}{sys.executable} -m pip install -r requirements.txt",
        "Installing dependencies"
    )
    
    # Step 4: Create directories
    for dir_name in ["logs", "results", "mocks"]:
        (repo_root / dir_name).mkdir(exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"  Setup Complete!")
    print(f"{'='*70}\n")
    print(f"Next steps:")
    print(f"  1. Activate environment:")
    if sys.platform == "win32":
        print(f"     .venv\\Scripts\\activate")
    else:
        print(f"     source .venv/bin/activate")
    print(f"  2. Run tests:")
    print(f"     pytest tests/ -v")
    print(f"  3. View logs:")
    print(f"     logs/test_run.log")

if __name__ == "__main__":
    main()
