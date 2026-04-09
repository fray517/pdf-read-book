# Запуск API только из каталога backend (где пакет app).
Set-Location $PSScriptRoot
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
