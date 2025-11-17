@echo off
REM Run GUI using the repo .venv python
SET REPO_ROOT=%~dp0
IF EXIST "%REPO_ROOT%.venv\Scripts\python.exe" (
  "%REPO_ROOT%.venv\Scripts\python.exe" "%REPO_ROOT%scripts\gui_extract.py"
) ELSE (
  echo .venv not found. Create one with:
  echo   py -3.11-64 -m venv .venv
  echo Then install dependencies:
  echo   .venv\Scripts\python.exe -m pip install PyMuPDF
  exit /b 1
)
