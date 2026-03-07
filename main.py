# main.py
import sys
import os
import logging
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  handlers=[
    logging.FileHandler(Path.home() / ".cryptosafe" / "app.log"),
    logging.StreamHandler()
  ]
)

logger = logging.getLogger(__name__)  # Используем __name__


def main():
  """Основная функция запуска приложения"""
  try:
    logger.info("=" * 50)
    logger.info("Запуск CryptoSafe Manager")
    logger.info("=" * 50)

    # Создаем необходимые директории
    config_dir = Path.home() / ".cryptosafe"
    config_dir.mkdir(exist_ok=True)
    logger.info(f"Директория конфигурации: {config_dir}")

    # Импортируем и запускаем приложение
    from src.core.config import Config
    from src.gui.main_window import MainWindow

    logger.info("Инициализация конфигурации...")
    config = Config()

    logger.info("Запуск графического интерфейса...")
    app = MainWindow(config)

    logger.info("Приложение успешно запущено")
    app.run()

  except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    logger.error(f"Python path: {sys.path}")
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что структура проекта правильная:")
    print("- Есть директория src/")
    print("- В src/ есть файл __init__.py")
    print("- Все зависимости установлены")

  except Exception as e:
    logger.error(f"Критическая ошибка: {e}", exc_info=True)
    print(f"Ошибка: {e}")

  finally:
    logger.info("Завершение работы приложения")


def check_structure():
  """Проверка структуры проекта"""
  required_paths = [
    "src/__init__.py",
    "src/core/__init__.py",
    "src/core/config.py",
    "src/gui/__init__.py",
    "src/gui/main_window.py",
    "src/database/__init__.py",
    "src/database/db.py",
  ]

  missing = []
  for path in required_paths:
    if not Path(path).exists():
      missing.append(path)

  if missing:
    print("Отсутствуют необходимые файлы:")
    for path in missing:
      print(f"  - {path}")
    return False

  print("Структура проекта корректна")
  return True


if __name__ == "__main__":
  print("Проверка структуры проекта...")
  if check_structure():
    main()
  else:
    print("\nСоздайте недостающие файлы и директории")
