import sqlite3
from pathlib import Path

db_path = Path.home() / ".cryptosafe" / "vault.db"
print(f"БД путь: {db_path}")
print(f"БД существует: {db_path.exists()}")

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Поиск
    search = "Test"
    cursor.execute("""
          SELECT id, title, username, url, tags
          FROM vault_entries
          WHERE title LIKE ? OR username LIKE ? OR url LIKE ? OR tags LIKE ?
      """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))

    results = cursor.fetchall()
    print(f"\nПоиск '{search}': найдено {len(results)} записей")
    for row in results:
        print(f"  - {row[1]}")

    conn.close()
else:
    print("БД не найдена!")
