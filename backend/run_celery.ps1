# Воркер Celery для Windows: пул solo (prefork на Win даёт PermissionError).
# Нужен запущенный Redis (см. README: docker compose up redis -d).
Set-Location $PSScriptRoot
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
