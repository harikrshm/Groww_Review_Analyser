# Quick Start Guide - Python 3.12 Virtual Environment

## Virtual Environment Created ✅

Your virtual environment `venv312` has been created with Python 3.12.0.

## How to Activate (Choose One Method)

### Method 1: Batch File (Easiest - Double-click or run in CMD)
```cmd
activate_venv.bat
```

### Method 2: PowerShell Script
```powershell
.\venv312\Scripts\Activate.ps1
```

If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv312\Scripts\Activate.ps1
```

### Method 3: Command Prompt (CMD)
```cmd
venv312\Scripts\activate.bat
```

### Method 4: Direct Python (No activation needed)
```powershell
.\venv312\Scripts\python.exe -m pip install -r requirements.txt
.\venv312\Scripts\python.exe cluster_reviews.py data/raw/reviews_2025-11-27.json 2025-W38
```

## After Activation

You should see `(venv312)` in your prompt. Then:

```powershell
# Install dependencies
pip install -r requirements.txt

# Run clustering
python cluster_reviews.py data/raw/reviews_2025-11-27.json 2025-W38
```

## Verify Installation

```powershell
python --version  # Should show Python 3.12.0
python -c "import umap; print('UMAP OK')"
python -c "import hdbscan; print('HDBSCAN OK')"
python -c "import sentence_transformers; print('Sentence-Transformers OK')"
```

## Troubleshooting

**If PowerShell activation fails:**
- Use `activate_venv.bat` instead (works in CMD)
- Or use direct Python path: `.\venv312\Scripts\python.exe`

**If pip install fails:**
- Make sure you're in the venv (see `(venv312)` in prompt)
- Or use: `.\venv312\Scripts\python.exe -m pip install -r requirements.txt`

