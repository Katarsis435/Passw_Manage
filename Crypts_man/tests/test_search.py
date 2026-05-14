import sqlite3
from pathlib import Path

db_path = Path.home() / ".cryptosafe" / "vault.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ТЕСТ 1: Поиск слова "Test"
search = "Test"
cursor.execute("""
    SELECT id, title, username, url, tags
    FROM vault_entries
    WHERE title LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ?
""", (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))

results = cursor.fetchall()
print(f"Поиск '{search}': найдено {len(results)} записей")
for row in results:
    print(f"  - {row[1]}")

# ТЕСТ 2: Поиск слова "test" (маленькими буквами)
search = "test"
cursor.execute("""
    SELECT id, title, username, url, tags
    FROM vault_entries
    WHERE title LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ?
""", (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))

results = cursor.fetchall()
print(f"\nПоиск '{search}': найдено {len(results)} записей")
for row in results:
    print(f"  - {row[1]}")

# ТЕСТ 3: Поиск слова "gmail"
search = "gmail"
cursor.execute("""
    SELECT id, title, username, url, tags
    FROM vault_entries
    WHERE title LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ?
""", (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))

results = cursor.fetchall()
print(f"\nПоиск '{search}': найдено {len(results)} записей")

conn.close()
