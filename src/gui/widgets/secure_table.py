from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView


class SecureTable(QTableWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.setColumnCount(4)
    self.setHorizontalHeaderLabels(["Title", "Username", "URL", "Last Updated"])
    self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    self.setAlternatingRowColors(True)
    self.setSelectionBehavior(QTableWidget.SelectRows)

  def add_entry(self, title, username, url, updated):
    row = self.rowCount()
    self.insertRow(row)
    self.setItem(row, 0, QTableWidgetItem(title))
    self.setItem(row, 1, QTableWidgetItem(username))
    self.setItem(row, 2, QTableWidgetItem(url))
    self.setItem(row, 3, QTableWidgetItem(updated))
