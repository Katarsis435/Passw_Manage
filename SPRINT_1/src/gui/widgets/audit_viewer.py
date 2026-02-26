from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit


class AuditViewer(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    layout = QVBoxLayout()
    self.log_area = QTextEdit()
    self.log_area.setReadOnly(True)
    layout.addWidget(self.log_area)
    self.setLayout(layout)

  def add_log(self, message):
    self.log_area.append(message)
