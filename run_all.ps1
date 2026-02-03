# Activate venv
$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Error "Virtual environment not found"
    exit
}

# Start Ollama
Start-Process powershell -ArgumentList "ollama serve"

# Start FastAPI
Start-Process powershell -ArgumentList "uvicorn app.api.main:app --reload"

# Start Streamlit
Start-Process powershell -ArgumentList "streamlit run app/streamlit_app.py"
