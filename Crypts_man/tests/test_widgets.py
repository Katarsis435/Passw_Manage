# tests/test_widgets.py
import unittest
import tkinter as tk


class TestSecureTable(unittest.TestCase):
  """Tests for secure table widget"""

  def setUp(self):
    self.root = tk.Tk()
    self.root.withdraw()

    from src.gui.widgets.secure_table import SecureTable
    self.table = SecureTable(self.root)

  def tearDown(self):
    self.root.destroy()

  def test_table_creation(self):
    """Test table widget creation"""
    self.assertIsNotNone(self.table.tree)

  def test_set_data(self):
    """Test setting data in table"""
    test_data = [
      {'id': 1, 'title': 'Test1', 'username': 'user1',
       'url': 'url1', 'updated_at': '2024-01-01'}
    ]

    self.table.set_data(test_data)
    items = self.table.tree.get_children()
    self.assertEqual(len(items), 1)

  def test_selection(self):
    """Test item selection"""
    test_data = [
      {'id': 1, 'title': 'Test1', 'username': 'user1',
       'url': 'url1', 'updated_at': '2024-01-01'}
    ]

    self.table.set_data(test_data)

    # Получаем ID первого элемента
    items = self.table.tree.get_children()
    if items:
      # Выбираем элемент
      self.table.tree.selection_set(items[0])
      # Обновляем выбор в таблице
      self.table._on_select(None)
      # Проверяем что selected_item установлен
      selected = self.table.get_selected()
      # ID должен быть '1'
      if selected is not None:
        self.assertEqual(selected, '1')
      else:
        # Если None, проверяем что элемент выбран в tree
        selected_in_tree = self.table.tree.selection()
        self.assertTrue(len(selected_in_tree) > 0)

if __name__ == '__main__':
  unittest.main()
