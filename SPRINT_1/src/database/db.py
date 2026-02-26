import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from ..core.crypto.placeholder import AES256Placeholder


class Database:
  def __init__(self, db_path):
    self.db_path = db_path
    self.local = threading.local()
    self.crypto = AES256Placeholder()
    self._init_db()

  def _get_conn(self):
    if not hasattr(self.local, 'conn'):
      self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
      self.local.conn.row_factory = sqlite3.Row
    return self.local.conn

  @contextmanager
  def cursor(self):
    conn = self._get_conn()
    cursor = conn.cursor()
    try:
      yield cursor
      conn.commit()
    except:
      conn.rollback()
      raise
    finally:
      cursor.close()

  def _init_db(self):
    from .models import init_db
    with self.cursor() as c:
      init_db(c.connection)

  def backup(self, backup_path):
    conn = sqlite3.connect(backup_path)
    self._get_conn().backup(conn)
    conn.close()
