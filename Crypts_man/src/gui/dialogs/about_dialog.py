"""About dialog with features checklist"""

import tkinter as tk
from tkinter import ttk


class AboutDialog:
    """About dialog with features tab"""

    FEATURES = [
        ("Управление паролями", [
            "✓ Добавление/редактирование/удаление записей",
            "✓ Мягкое удаление (возможность восстановления)",
            "✓ Категории: Work, Personal, Finance, Social, Other",
            "✓ Теги для дополнительной организации",
        ]),
        ("Поиск и фильтрация", [
            "✓ Полнотекстовый поиск с нечётким сопоставлением",
            "✓ Фильтр по категории",
            "✓ Сортировка по любому столбцу",
        ]),
        ("Генератор паролей", [
            "✓ Длина от 8 до 64 символов",
            "✓ Настраиваемые наборы символов",
            "✓ Мнемонические фразы (correct-horse-battery-42)",
            "✓ Оценка сложности с цветным индикатором",
        ]),
        ("Защищённый буфер обмена", [
            "✓ Автоочистка через 5-30 секунд",
            "✓ Визуальный индикатор с таймером",
            "✓ Уровни безопасности: Standard → Secure → Paranoid",
            "✓ Ускорение очистки при подозрительной активности",
        ]),
        ("Безопасность", [
            "✓ AES-256-GCM шифрование каждой записи",
            "✓ Argon2id для мастер-пароля",
            "✓ Защита от подбора (экспоненциальная задержка)",
            "✓ Ключи только в памяти, никогда на диск",
            "✓ Паник-режим (Ctrl+Shift+X)",
            "✓ Автоблокировка при бездействии",
        ]),
        ("Аудит-лог", [
            "✓ Хэш-цепочка (защита от подделки)",
            "✓ Цифровая подпись Ed25519/HMAC",
            "✓ Просмотр с фильтрацией по дате/событию",
            "✓ Экспорт в JSON, CSV, PDF",
        ]),
        ("Импорт/Экспорт", [
            "✓ Форматы: JSON, CSV, Bitwarden, LastPass",
            "✓ Шифрование экспорта паролем или RSA-ключом",
            "✓ Режимы: merge (добавить) / replace (заменить)",
            "✓ Предпросмотр перед импортом",
        ]),
        ("Безопасный обмен", [
            "✓ Передача записей по паролю или публичному ключу",
            "✓ QR-код для обмена ключами",
            "✓ Контакты (хранилище публичных ключей)",
        ]),
        ("Горячие клавиши", [
            "• Ctrl+N — новая запись    • Ctrl+E — редактировать",
            "• Del — удалить            • Ctrl+F — поиск",
            "• Ctrl+L — заблокировать    • Ctrl+G — генератор",
            "• Ctrl+Shift+C — очистить   • Ctrl+Shift+A — аудит",
            "• Ctrl+Shift+X — паника     • F5 — обновить",
        ]),
    ]

    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("О программе — CryptoSafe Manager")
        self.dialog.geometry("700x550")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._center_dialog()

    def _center_dialog(self):
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (550 // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        # Основной фрейм
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(title_frame, text="🛡CryptoSafe Manager🛡", font=('Arial', 18, 'bold')).pack()
        ttk.Label(title_frame, text="Кроссплатформенный менеджер паролей", font=('Arial', 10)).pack()
        ttk.Label(title_frame, text="Версия 1.0 | Спринт 7/8", font=('Arial', 9), foreground="gray").pack()

        # Вкладки
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка "Возможности"
        features_frame = ttk.Frame(notebook, padding="10")
        notebook.add(features_frame, text="Возможности")

        # Canvas с прокруткой для длинного списка
        canvas = tk.Canvas(features_frame)
        scrollbar = ttk.Scrollbar(features_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Заполнение возможностей
        for cat_title, items in self.FEATURES:
            # Категория
            cat_frame = ttk.Frame(scrollable_frame)
            cat_frame.pack(fill=tk.X, pady=(10, 5))

            ttk.Label(cat_frame, text=cat_title, font=('Arial', 11, 'bold')).pack(anchor=tk.W)

            # Пункты
            for item in items:
                ttk.Label(scrollable_frame, text=f"  {item}", font=('Arial', 9)).pack(anchor=tk.W, padx=20)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Вкладка "О команде"
        team_frame = ttk.Frame(notebook, padding="10")
        notebook.add(team_frame, text="👥 О команде")

        ttk.Label(team_frame, text="CryptoSafe Manager", font=('Arial', 14)).pack(pady=10)
        ttk.Label(team_frame, text="Финальный проект по дисциплине методы и средства криптографической защиты информации", font=('Arial', 10)).pack()

        ttk.Label(team_frame, text="\nИспользуемые технологии:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(20, 5))
        techs = [
            "• Python 3.10+",
            "• Tkinter (GUI)",
            "• SQLite + шифрование на уровне приложения",
            "• cryptography (AES-256-GCM, Ed25519)",
            "• argon2-cffi (Argon2id)",
            "• pyperclip + платформенные адаптеры",
        ]
        for tech in techs:
            ttk.Label(team_frame, text=tech).pack(anchor=tk.W, padx=20)

        # Кнопка закрытия
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(btn_frame, text="Закрыть", command=self.dialog.destroy).pack()

    def _show_about(self):
        """Show about dialog"""
        about_text = """CryptoSafe Manager
        Версия 1.0 (Спринт 7)
        Безопасный менеджер паролей с AES-256-GCM и защищённым аудитом.

        © 2026 CryptoSafe"""
        messagebox.showinfo("О программе", about_text)
