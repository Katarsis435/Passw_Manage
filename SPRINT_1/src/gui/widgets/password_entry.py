from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout


class PasswordEntry(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)

    self.password_field = QLineEdit()
    self.password_field.setEchoMode(QLineEdit.Password)

    self.toggle_btn = QPushButton("Show")
    self.toggle_btn.setCheckable(True)
    self.toggle_btn.toggled.connect(self.toggle_visibility)

    layout.addWidget(self.password_field)
    layout.addWidget(self.toggle_btn)
    self.setLayout(layout)

  def toggle_visibility(self, checked):
    if checked:
      self.password_field.setEchoMode(QLineEdit.Normal)
      self.toggle_btn.setText("Hide")
    else:
      self.password_field.setEchoMode(QLineEdit.Password)
      self.toggle_btn.setText("Show")

  def text(self):
    return self.password_field.text()

  def setText(self, text):
    self.password_field.setText(text)
