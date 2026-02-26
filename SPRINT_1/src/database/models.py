def init_db(conn):
  conn.execute('''
      CREATE TABLE IF NOT EXISTS vault_entries (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          username TEXT,
          encrypted_password BLOB,
          url TEXT,
          notes TEXT,
          created_at TIMESTAMP,
          updated_at TIMESTAMP,
          tags TEXT
      )
  ''')

  conn.execute('''
      CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          action TEXT,
          timestamp TIMESTAMP,
          entry_id INTEGER,
          details TEXT,
          signature TEXT
      )
  ''')

  conn.execute('''
      CREATE TABLE IF NOT EXISTS settings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          setting_key TEXT UNIQUE,
          setting_value TEXT,
          encrypted BOOLEAN
      )
  ''')

  conn.execute('''
      CREATE TABLE IF NOT EXISTS key_store (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          key_type TEXT,
          salt BLOB,
          hash BLOB,
          params TEXT
      )
  ''')

  conn.execute('PRAGMA user_version = 1')
