# Run pytest for greenfield_routing tests (Windows PowerShell)
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; pytest -q
