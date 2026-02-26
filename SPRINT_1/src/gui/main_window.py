import sys
from PyQt5.QtWidgets import (QMainWindow, QAction, QStatusBar,
                             QLabel, QVBoxLayout, QWidget,
                             QMessageBox)
from PyQt5.QtCore import Qt
from ..core.events import EventBus, EventType
from ..core.state_manager import StateManager
from ..core.config import Config
from ..database.db import Database
from .widgets.secure_table import SecureTable
from .widgets.audit_viewer import AuditViewer


class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()

    # Инициализация компонентов
    self.config = Config()
    self.event_bus = EventBus()
    self.state = StateManager()
    self.db = Database(self.config.get('db_path'))

    self.setWindowTitle("CryptoSafe Manager")
    self.setGeometry(100, 100, 900, 600)

    self._create_menu()
    self._create_status_bar()
    self._create_central_widget()

    self.state.update_activity()

  def _create_menu(self):
    menubar = self.menuBar()

    file_menu = menubar.addMenu("File")
    file_menu.addAction("New Vault", self.new_vault)
    file_menu.addAction("Open Vault", self.open_vault)
    file_menu.addAction("Backup", self.backup_vault)
    file_menu.addSeparator()
    file_menu.addAction("Exit", self.close)

    edit_menu = menubar.addMenu("Edit")
    edit_menu.addAction("Add Entry", self.add_entry)
    edit_menu.addAction("Edit Entry", self.edit_entry)
    edit_menu.addAction("Delete Entry", self.delete_entry)

    view_menu = menubar.addMenu("View")
    view_menu.addAction("Audit Log", self.show_audit_log)
    view_menu.addAction("Settings", self.show_settings)

    help_menu = menubar.addMenu("Help")
    help_menu.addAction("About", self.show_about)

  def _create_status_bar(self):
    self.status_label = QLabel("Locked")
    self.statusBar().addWidget(self.status_label)

    self.timer_label = QLabel("Clipboard: --")
    self.statusBar().addPermanentWidget(self.timer_label)

  def _create_central_widget(self):
    central = QWidget()
    layout = QVBoxLayout()

    self.table = SecureTable()
    self._add_placeholder_data()

    layout.addWidget(self.table)
    central.setLayout(layout)
    self.setCentralWidget(central)

  def _add_placeholder_data(self):
    self.table.add_entry("Gmail", "user@gmail.com", "https://gmail.com", "2024-01-01")
    self.table.add_entry("GitHub", "dev_user", "https://github.com", "2024-01-01")

  def new_vault(self):
    QMessageBox.information(self, "New Vault", "Create new vault wizard")

  def open_vault(self):
    QMessageBox.information(self, "Open Vault", "Open existing vault")

  def backup_vault(self):
    QMessageBox.information(self, "Backup", "Backup vault")

  def add_entry(self):
    QMessageBox.information(self, "Add", "Add new entry")

  def edit_entry(self):
    QMessageBox.information(self, "Edit", "Edit selected entry")

  def delete_entry(self):
    QMessageBox.information(self, "Delete", "Delete selected entry")

  def show_audit_log(self):
    viewer = AuditViewer()
    viewer.show()

  def show_settings(self):
    QMessageBox.information(self, "Settings", "Settings dialog")

  def show_about(self):
    QMessageBox.about(self, "About", "CryptoSafe Manager v1.0")


def main():
  app = QApplication(sys.argv)
  window = MainWindow()
  window.show()
  sys.exit(app.exec_())


if __name__ == "__main__":
  from PyQt5.QtWidgets import QApplication

  main()
