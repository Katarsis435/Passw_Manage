import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime  # Добавить эту строку
from pathlib import Path

from ..core.events import event_bus, EventType
from ..core.config import Config
from ..core.state_manager import StateManager
from ..core.crypto.placeholder import AES256Placeholder, KeyManager
from ..database.db import Database
from ..database.models import VaultEntry

from .widgets.password_entry import PasswordEntry
from .widgets.secure_table import SecureTable
from .widgets.audit_log_viewer import AuditLogViewer


class MainWindow:
  def __init__(self):
    self.root = tk.Tk()
    self.root.title('CryptoSafe Manager')
    self.root.geometry('900x600')

    # Инициализация компонентов
    self.config = Config()
    self.state = StateManager()
    self.crypto = AES256Placeholder()
    self.key_manager = KeyManager()
    self.db = Database(self.config.db_path)

    self.setup_menu()
    self.setup_ui()
    self.setup_events()

    # Показываем мастер настройки при первом запуске
    self.check_first_run()

  def setup_menu(self):
    menubar = tk.Menu(self.root)
    self.root.config(menu=menubar)

    # Файл
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Файл', menu=file_menu)
    file_menu.add_command(label='Разблокировать', command=self.unlock_vault)  # ДОБАВИТЬ
    file_menu.add_command(label='Заблокировать', command=self.lock_vault)  # ДОБАВИТЬ
    file_menu.add_separator()  # ДОБАВИТЬ
    file_menu.add_command(label='Создать БД', command=self.create_db)
    file_menu.add_command(label='Открыть БД', command=self.open_db)
    file_menu.add_separator()
    file_menu.add_command(label='Резервная копия', command=self.backup)
    file_menu.add_separator()
    file_menu.add_command(label='Выход', command=self.root.quit)

    # Правка
    edit_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Правка', menu=edit_menu)
    edit_menu.add_command(label='Добавить', command=self.add_entry)
    edit_menu.add_command(label='Изменить', command=self.edit_entry)
    edit_menu.add_command(label='Удалить', command=self.delete_entry)

    # Вид
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Вид', menu=view_menu)
    view_menu.add_command(label='Журнал', command=self.show_log)
    view_menu.add_command(label='Настройки', command=self.show_settings)

    # Справка
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Справка', menu=help_menu)
    help_menu.add_command(label='О программе', command=self.show_about)

  def setup_ui(self):
    # Основной контейнер
    main_frame = ttk.Frame(self.root, padding='5')
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Панель инструментов
    toolbar = ttk.Frame(main_frame)
    toolbar.pack(fill=tk.X, pady=5)

    ttk.Button(toolbar, text='➕ Добавить', command=self.add_entry).pack(side=tk.LEFT, padx=2)
    ttk.Button(toolbar, text='✏️ Изменить', command=self.edit_entry).pack(side=tk.LEFT, padx=2)
    ttk.Button(toolbar, text='🗑️ Удалить', command=self.delete_entry).pack(side=tk.LEFT, padx=2)

    # Таблица записей
    self.table = SecureTable(main_frame)
    self.table.pack(fill=tk.BOTH, expand=True, pady=5)

    self.load_entries()

    # Строка состояния
    self.status_bar = ttk.Frame(self.root)
    self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    self.status_label = ttk.Label(self.status_bar, text='🔒 Заблокировано')
    self.status_label.pack(side=tk.LEFT, padx=5)

    # Кнопка разблокировки в статус-баре
    self.unlock_btn = ttk.Button(self.status_bar, text='🔓 Разблокировать',
                                 command=self.unlock_vault)
    self.unlock_btn.pack(side=tk.LEFT, padx=5)

    self.timer_label = ttk.Label(self.status_bar, text='⏱️ Таймер: -')
    self.timer_label.pack(side=tk.RIGHT, padx=5)

    # Лог (скрыт по умолчанию)
    self.log_viewer = AuditLogViewer(self.root)

  def setup_events(self):
    event_bus.subscribe(EventType.ENTRY_ADDED, self.on_entry_added)
    event_bus.subscribe(EventType.ENTRY_UPDATED, self.on_entry_updated)
    event_bus.subscribe(EventType.ENTRY_DELETED, self.on_entry_deleted)
    event_bus.subscribe(EventType.USER_LOGIN, self.on_user_login)
    event_bus.subscribe(EventType.USER_LOGOUT, self.on_user_logout)

  def check_first_run(self):
    if not self.config.db_path.exists():
      self.first_run_wizard()

  def first_run_wizard(self):
    dialog = tk.Toplevel(self.root)
    dialog.title('Первоначальная настройка')
    dialog.geometry('400x300')

    ttk.Label(dialog, text='Создание мастер-пароля').pack(pady=10)

    ttk.Label(dialog, text='Пароль:').pack()
    pwd_entry = PasswordEntry(dialog)
    pwd_entry.pack(pady=5, padx=20, fill=tk.X)

    ttk.Label(dialog, text='Подтверждение:').pack()
    confirm_entry = PasswordEntry(dialog)
    confirm_entry.pack(pady=5, padx=20, fill=tk.X)

    ttk.Label(dialog, text='Расположение БД:').pack()
    db_path = ttk.Entry(dialog)
    db_path.insert(0, str(self.config.db_path))
    db_path.pack(pady=5, padx=20, fill=tk.X)

  def unlock_vault(self):
    """Диалог разблокировки хранилища"""
    if not self.state.locked:
      return  # Уже разблокировано

    password = simpledialog.askstring("Разблокировка",
                                       "Введите мастер-пароль:",
                                       show='*')
    if password:  # В реальном проекте тут проверка хеша
      self.state.login()
      event_bus.publish(EventType.USER_LOGIN)
      return True
    return False

  def lock_vault(self):
    """Блокировка хранилища"""
    if not self.state.locked:
      self.state.logout()
      event_bus.publish(EventType.USER_LOGOUT)
      self.table.set_data([])  # Очищаем таблицу

    def finish():
      if pwd_entry.get() != confirm_entry.get():
        messagebox.showerror('Ошибка', 'Пароли не совпадают')
        return

      # Тут будет создание ключа
      self.state.login()
      event_bus.publish(EventType.USER_LOGIN)
      dialog.destroy()

    ttk.Button(dialog, text='Готово', command=finish).pack(pady=20)

  def load_entries(self):
    entries = self.db.get_entries()
    self.table.set_data(entries)

  def add_entry(self):
    if self.state.locked:
      messagebox.showwarning('Внимание', 'Сначала разблокируйте хранилище')
      return

    dialog = tk.Toplevel(self.root)
    dialog.title('Новая запись')
    dialog.geometry('400x300')

    fields = {}
    for i, field in enumerate(['Название', 'Логин', 'Пароль', 'URL', 'Заметки']):
      ttk.Label(dialog, text=field).grid(row=i, column=0, sticky='w', padx=5, pady=2)
      if field == 'Пароль':
        entry = PasswordEntry(dialog)
        entry.grid(row=i, column=1, padx=5, pady=2, sticky='ew')
      else:
        entry = ttk.Entry(dialog)
        entry.grid(row=i, column=1, padx=5, pady=2, sticky='ew')
      fields[field] = entry

    dialog.grid_columnconfigure(1, weight=1)

    def save():
      # Создаем запись
      entry = VaultEntry(
        title=fields['Название'].get(),
        username=fields['Логин'].get(),
        encrypted_password=self.crypto.encrypt(
          fields['Пароль'].get().encode(),
          b'fixedkey32bytesforplaceholder!!'
        ),
        url=fields['URL'].get(),
        notes=fields['Заметки'].get()
      )

      entry_id = self.db.add_entry(entry)
      event_bus.publish(EventType.ENTRY_ADDED, {'id': entry_id})
      dialog.destroy()
      self.load_entries()

    ttk.Button(dialog, text='Сохранить', command=save).grid(row=5, column=0, columnspan=2, pady=10)

  def edit_entry(self):
    selected = self.table.selection()
    if not selected:
      return
    # TODO: реализовать редактирование
    messagebox.showinfo('Инфо', 'Редактирование (заглушка)')

  def delete_entry(self):
    selected = self.table.selection()
    if not selected:
      return

    if messagebox.askyesno('Подтверждение', 'Удалить запись?'):
      # TODO: получить ID и удалить
      event_bus.publish(EventType.ENTRY_DELETED)
      self.load_entries()

  def show_log(self):
    if self.log_viewer.winfo_ismapped():
      self.log_viewer.pack_forget()
    else:
      self.log_viewer.pack(fill=tk.BOTH, expand=True)

  def show_settings(self):
    messagebox.showinfo('Настройки', 'Диалог настроек (заглушка)')

  def show_about(self):
    messagebox.showinfo('О программе', 'CryptoSafe Manager\nВерсия 0.1 (Спринт 1)')

  def create_db(self):
    # TODO: создание новой БД
    pass

  def open_db(self):
    # TODO: открыть существующую БД
    pass

  def backup(self):
    backup_path = self.config.data_dir / f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    self.db.backup(backup_path)
    messagebox.showinfo('Резервная копия', f'Создана копия: {backup_path}')

  def on_entry_added(self, data):
    self.log_viewer.add_log(f'Добавлена запись {data}')

  def on_entry_updated(self, data):
    self.log_viewer.add_log(f'Обновлена запись {data}')

  def on_entry_deleted(self, data):
    self.log_viewer.add_log('Удалена запись')

  def on_user_login(self, data):
    self.status_label.config(text='🔓 Разблокировано')
    if hasattr(self, 'unlock_btn'):
      self.unlock_btn.config(state=tk.DISABLED, text='✅ Разблокировано')
    self.log_viewer.add_log('Вход в систему')
    self.load_entries()  # Загружаем записи при входе

  def on_user_logout(self, data):
    self.status_label.config(text='🔒 Заблокировано')
    if hasattr(self, 'unlock_btn'):
      self.unlock_btn.config(state=tk.NORMAL, text='🔓 Разблокировать')
    self.log_viewer.add_log('Выход из системы')
    self.table.set_data([])  # Очищаем таблицу

  def run(self):
    self.root.mainloop()


