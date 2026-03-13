# README.md
Безопасный менеджер паролей с открытым исходным кодом.

## О проекте
CryptoSafe Manager — это десктопное приложение для хранения паролей с шифрованием, аудитом действий и удобным интерфейсом. Проект разрабатывается модульно, чтобы каждый компонент можно было улучшать независимо.

### Возможности (Sprint 1)
- Хранение паролей в зашифрованной SQLite базе
- Мастер первого запуска (создание мастер-пароля)
- Базовый интерфейс с таблицей записей
- Добавление/удаление записей
- Система событий для слабосвязанной архитектуры
- Резервное копирование базы данных

### Что дальше
Проект рассчитан на 8 спринтов. Сейчас готов первый:

1. **Фундамент** (готов) — база данных, шифрование-заглушка, базовый GUI
2. Мастер-пароль и Key Derivation
3. Настоящее AES-GCM шифрование
4. Буфер обмена и двухфакторка (TOTP)
5. Просмотр аудита с подписями
6. Импорт/экспорт (CSV, JSON)
7. Автоблокировка, генератор паролей
8. Безопасный шаринг и финальная сборка

## Быстрый старт

### Установка

# Клонируем репозиторий
git clone https://github.com/Katarsis435/cryptosafe-manager.git
cd PW

# Создаём виртуальное окружение
python -m venv venv

# Активируем
- Windows:
venv\Scripts\activate
- Linux/Mac:
source venv/bin/activate

# Ставим зависимости
pip install -r requirements.txt

# Запуск
python main.py
При первом запуске откроется мастер настройки:
- Придумайте мастер-пароль
- Выберите где хранить базу данных

# Тестирование
Запустить все тесты
python -m unittest discover tests
С проверкой покрытия
pip install coverage
coverage run -m unittest discover tests
coverage report

# Структура проекта
```
cryptosafe-manager/
├── src/
│   ├── core/
│   │   ├── crypto/
│   │   │   ├── abstract.py       # EncryptionService abstract class
│   │   │   └── placeholder.py    # AES256Placeholder (XOR)
│   │   ├── events.py             # Event system
│   │   ├── config.py             # Configuration manager
│   │   ├── key_manager.py        # Key management stub
│   │   └── state_manager.py      # State tracking
│   ├── database/
│   │   ├── db.py                 # Database helper with migrations
│   │   └── models.py             # (Future: SQLAlchemy models)
│   └── gui/
│       ├── main_window.py        # Main application window
│       └── widgets/
│           ├── password_entry.py # Password input with show/hide
│           ├── secure_table.py   # Vault entries table
│           └── audit_log_viewer.py # Audit log viewer stub
├── tests/
│   ├── test_crypto.py            # Crypto unit tests
│   ├── test_database.py          # Database unit tests
│   ├── test_events.py            # Event system tests
│   └── test_integration.py       # Integration tests
├── .github/
│   └── workflows/
│       └── tests.yml             # GitHub Actions CI
├── main.py                       # Entry point
├── requirements.txt              # Dependencies
├── Dockerfile                    # Container stub (Sprint 8)
└── README.md                     # This file
```

# Технологии
Python 3.8+
SQLite (встроенная БД)
tkinter (интерфейс)
unittest (тесты)

# Лицензия
MIT
Это README без лишних таблиц и сложных диаграмм. Просто и понятно: что это, как запустить, как устроено.


