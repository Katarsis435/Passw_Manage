#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CryptoSafe Manager - Безопасное хранилище для криптовалютных ключей
Спринт 1: Полная реализация фундамента приложения

Версия: 0.1.0
Лицензия: MIT
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / ".cryptosafe" / "app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(name)


def setup_environment():
    """Настройка окружения"""
    # Создаем необходимые папки
    data_dir = Path.home() / ".cryptosafe"
    data_dir.mkdir(exist_ok=True)

    # Проверяем права доступа
    if not os.access(data_dir, os.W_OK):
        logger.error(f"Нет прав на запись в {data_dir}")
        sys.exit(1)

    logger.info(f"Директория данных: {data_dir}")


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description="CryptoSafe Manager")

    parser.add_argument(
        '--config',
        type=str,
        help='Путь к файлу конфигурации'
    )

    parser.add_argument(
        '--db',
        type=str,
        help='Путь к файлу базы данных'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Включить режим отладки'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='CryptoSafe Manager 0.1.0'
    )

    return parser.parse_args()


def main():
    """Главная функция"""
    print("=" * 60)
    print("🔐 CryptoSafe Manager v0.1.0")
    print("=" * 60)
    print("Безопасное хранилище для криптовалютных ключей")
    print("-" * 60)

    # Парсим аргументы
    args = parse_arguments()

    # Включаем отладку если нужно
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Режим отладки включен")

    try:
        # Настройка окружения
        setup_environment()

        # Переопределяем пути если нужно
        if args.config:
            os.environ['CRYPTOSAFE_CONFIG'] = args.config
            logger.info(f"Используется конфиг: {args.config}")

        if args.db:
            os.environ['CRYPTOSAFE_DB'] = args.db
            logger.info(f"Используется БД: {args.db}")

        # Импортируем модули после настройки
        from src.core.config import config
        from src.core.state_manager import state_manager
        from src.core.events import event_bus
        from src.gui.main_window import MainWindow

        # Создаем и запускаем приложение
        app = MainWindow()

        logger.info("Приложение запущено")
        app.run()

    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        return 1
    finally:
        # Очистка ресурсов
        from src.core.key_manager import KeyManager
        KeyManager().clear_master_key()

        # Останавливаем event bus
        event_bus.shutdown()

        logger.info("Приложение завершено")

    return 0


if name == "main":
    sys.exit(main())
