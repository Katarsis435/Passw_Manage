import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gui.main_window import MainWindow

def main():
    window = MainWindow()
    window.run()  # Было window.show(), а нужно window.run()

if __name__ == '__main__':
    main()
