"""КОМАНДА 1: запуск изолированных тестов всех модулей (ТЗ №6).

Обходит проект от корня, находит все test_*.py внутри module_*/tests/ и
прогоняет их, исключая сквозные тесты из самой папки tests_project.

Запуск из корня проекта (src/):
    python -m tests_project.run_module_tests

Точечная проверка одного модуля (без этого скрипта):
    python -m unittest discover -s module_data_layer/tests -p "test_*.py"
"""
import os
import sys
import unittest


def run_isolated_tests() -> None:
    print("=" * 70)
    print(" ЗАПУСК ЛОКАЛЬНЫХ ТЕСТОВ РАЗРАБОТЧИКОВ (ОТДЕЛЬНЫЕ МОДУЛИ)")
    print("=" * 70)

    # Корень проекта — папка на уровень выше tests_project (т.е. src/)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=root_dir, pattern="test_*.py")

    # Убираем тесты самой папки tests_project (это интеграционный слой)
    filtered = unittest.TestSuite()
    for group in suite:
        for case in group:
            if "tests_project" not in str(case):
                filtered.addTest(case)

    result = unittest.TextTestRunner(verbosity=2).run(filtered)

    print("=" * 70)
    print(f" Всего локальных тестов пройдено: {result.testsRun}")
    print(f" Сбои / Ошибки:                  {len(result.errors) + len(result.failures)}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    run_isolated_tests()
