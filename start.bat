@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env >nul

rem v2 uses explicit LM Studio model IDs so chat never selects the embedding model by mistake.
findstr /B /C:"EMBEDDING_MODEL=" .env >nul || echo EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5>>.env
powershell -NoProfile -Command "$p='.env'; $s=Get-Content $p -Raw; $s=$s -replace '(?m)^LM_STUDIO_MODEL=.*$','LM_STUDIO_MODEL=google/gemma-4-e4b'; $s=$s -replace '(?m)^MAX_CONTEXT_CHUNKS=.*$','MAX_CONTEXT_CHUNKS=3'; Set-Content -Path $p -Value $s -Encoding UTF8"

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
