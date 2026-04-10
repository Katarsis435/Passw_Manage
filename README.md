# README.md
Безопасный менеджер паролей с открытым исходным кодом и шифрованием AES-256-GCM.

## О проекте
CryptoSafe Manager — это десктопное приложение для хранения паролей с шифрованием, аудитом действий и удобным интерфейсом. Проект разрабатывается модульно, чтобы каждый компонент можно было улучшать независимо.

### Возможности (Sprint 1, Sprint 2)
- Хранение паролей в зашифрованной SQLite базе
- Мастер первого запуска (создание мастер-пароля)
- Базовый интерфейс с таблицей записей
- Добавление/удаление записей
- Система событий для слабосвязанной архитектуры
- Резервное копирование базы данных
## Возможности (Спринт 3)
- Популярное шифрование AES-256-GCM для каждой записи с аутентификацией
- Полные CRUD операции с поддержкой транзакций
- Безопасный генератор паролей (8-64 символа, наборы символов)
- Индикатор надёжности пароля (интеграция с zxcvbn)
- Таблица с сортировкой, множественным выбором, контекстным меню
- Мгновенный поиск по всем полям
- Мягкое удаление с возможностью восстановления
- Система событий для слабосвязанной архитектуры

### В разработке (Sprint 4)
- Интеграция с буфером обмена с автоочисткой
- Двухфакторная аутентификация (TOTP)
- Автоматическая блокировка при бездействии

## Быстрый старт
Установка

* Клонируем репозиторий
git clone https://github.com/Katarsis435/cryptosafe-manager.git
cd PW

* Создаём виртуальное окружение
python -m venv venv

* Активируем
- Windows:
venv\Scripts\activate
- Linux/Mac:
source venv/bin/activate

* Ставим зависимости
pip install -r requirements.txt

* Запуск
python main.py
При первом запуске откроется мастер настройки:
- Придумайте мастер-пароль
- Выберите где хранить базу данных

* Тестирование
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
│   │   │   ├── __init__.py
│   │   │   ├── abstract.py       # EncryptionService abstract class
│   │   │   └── placeholder.py    # AES256Placeholder (XOR)
│   │   ├── __init__.py
│   │   ├── events.py             # Event system
│   │   ├── config.py             # Configuration manager
│   │   ├── key_manager.py        # Key management stub
│   │   └── state_manager.py      # State tracking
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py                 # Database helper with migrations
│   │   └── models.py             # (Future: SQLAlchemy models)
│   └── gui/
│       ├── main_window.py        # Main application window
│       ├── __init__.py
│       └── widgets/
│           ├── __init__.py
│           ├── password_entry.py # Password input with show/hide
│           ├── secure_table.py   # Vault entries table
│           └── audit_log_viewer.py # Audit log viewer stub
├── tests/
│   ├── __init__.py
│   ├── test_crypto.py            # Crypto unit tests
│   ├── test_database.py          # Database unit tests
│   ├── test_config.py            # SPR_2
│   ├── test_db.py                # SPR_2
│   ├── test_events.py            # Event system tests
│   ├── test_integration.py       # Integration tests
│   ├── test_key_derivation.py    # SPR_2
│   ├── test_widgers.py           # SPR_2
│   └── test_tkinter.py           # SPR_2
├── .github/
│   └── workflows/
│       └── tests.yml             # GitHub Actions CI
├── __init__.py
├── main.py                       # Entry point
├── requirements.txt              # Dependencies
├── Dockerfile                    # Container stub (Sprint 8)
└── README.md                     # This file
```
# Технологии
Python 3.8+ (я использую 3.13)
SQLite (встроенная БД)
tkinter (интерфейс)
unittest (тесты)

# Лицензия
MIT
Это README без лишних таблиц и сложных диаграмм. Просто и понятно: что это, как запустить, как устроено.


