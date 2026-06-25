@echo off
cd /d "%~dp0"
echo Adicionando arquivos...
git add backend/app/services/dataset_service.py backend/app/services/analytics_service.py backend/app/services/suggestion_service.py backend/tests/test_analytics_service.py backend/tests/test_dataset_service.py
echo Commitando...
git commit -m "feat: contagem distinta no chat + cache LRU de datasets"
echo Enviando para o GitHub (dispara Vercel + Render)...
git push origin main
echo.
echo ===== CONCLUIDO (codigo de saida: %errorlevel%) =====
pause
