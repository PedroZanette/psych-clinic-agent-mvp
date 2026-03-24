@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Ambiente virtual nao encontrado.
    echo Crie com: py -3.10 -m venv .venv
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

if exist ".env" (
    echo Arquivo .env encontrado.
) else (
    echo Aviso: arquivo .env nao encontrado.
)

echo Iniciando Streamlit...
streamlit run app.py

pause