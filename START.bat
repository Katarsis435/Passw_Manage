@echo off
chcp 65001 >nul
title CryptoSafe Manager
echo ========================================
echo    CryptoSafe Manager
echo ========================================
echo.

:: Переходим в папку с проектом
cd /d "%~dp0"

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не установлен!
    echo Скачайте с https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Проверяем зависимости
python -c "import cryptography" >nul 2>&1
if errorlevel 1 (
    echo Установка зависимостей...
    pip install -r requirements.txt
    echo.
)

:: Запускаем main.py (теперь он в корне)
echo Запуск CryptoSafe Manager...
python main.py

pause
