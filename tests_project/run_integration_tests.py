"""КОМАНДА 2: запуск сквозного интеграционного теста проекта (ТЗ №6).

Прогоняет только test_e2e_*.py из папки tests_project — разворачивает
единую in-memory БД и гонит данные по всей цепочке модулей.

Запуск из корня проекта (src/):
    python -m tests_project.run_integration_tests
"""
import os
import sys
import unittest


def run_project_integration() -> None:
    print("=" * 70)
    print(" ЗАПУСК СКВОЗНОГО ИНТЕГРАЦИОННОГО ТЕСТА (СОВМЕСТИМОСТЬ ПРОЕКТА)")
    print("=" * 70)

    current_dir = os.path.dirname(os.path.abspath(__file__))

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=current_dir, pattern="test_e2e_*.py")

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print("=" * 70)
    print(f" Интеграционных сценариев проверено: {result.testsRun}")
    print(f" Конфликты совместимости:            {len(result.errors) + len(result.failures)}")
    print("=" * 70)

    if result.wasSuccessful():
        print("🔥 ОТЛИЧНО! Модули проекта работают как единое целое.")
        sys.exit(0)
    else:
        print("🚨 ВНИМАНИЕ! Обнаружен конфликт контрактов данных между модулями.")
        sys.exit(1)


if __name__ == "__main__":
    run_project_integration()
