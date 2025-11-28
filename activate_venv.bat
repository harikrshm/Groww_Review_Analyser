@echo off
echo Activating Python 3.12 virtual environment...
call venv312\Scripts\activate.bat
echo.
echo Virtual environment activated!
echo Python version:
python --version
echo.
echo To install dependencies, run:
echo   pip install -r requirements.txt
echo.
echo To run clustering:
echo   python cluster_reviews.py data/raw/reviews_2025-11-27.json 2025-W38
echo.

