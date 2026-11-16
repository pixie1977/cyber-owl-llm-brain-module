"""
Простой тестовый раннер для проверки тестов behaviour.
"""
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.test_behaviour_register import *


def run_tests():
    """Запуск всех тестов."""
    passed = 0
    failed = 0
    errors = []

    # Тесты STOP_COMMANDS
    print("\n=== Тесты STOP_COMMANDS ===")
    test_class = TestStopCommands()
    test_class.setup_method()
    
    for method_name in dir(test_class):
        if method_name.startswith('test_'):
            try:
                getattr(test_class, method_name)()
                print(f"  ✓ {method_name}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {e}")
                failed += 1
                errors.append(f"TestStopCommands.{method_name}: {e}")

    # Тесты REGISTER_COMMANDS
    print("\n=== Тесты REGISTER_COMMANDS ===")
    test_class = TestRegisterCommands()
    test_class.setup_method()
    
    for method_name in dir(test_class):
        if method_name.startswith('test_'):
            try:
                getattr(test_class, method_name)()
                print(f"  ✓ {method_name}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {e}")
                failed += 1
                errors.append(f"TestRegisterCommands.{method_name}: {e}")

    # Тесты извлечения имени
    print("\n=== Тесты извлечения имени ===")
    test_class = TestExtractName()
    test_class.setup_method()
    
    for method_name in dir(test_class):
        if method_name.startswith('test_'):
            try:
                getattr(test_class, method_name)()
                print(f"  ✓ {method_name}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {e}")
                failed += 1
                errors.append(f"TestExtractName.{method_name}: {e}")

    print(f"\n{'='*60}")
    print(f"Результаты: {passed} passed, {failed} failed")
    
    if errors:
        print(f"\nОшибки:")
        for error in errors:
            print(f"  - {error}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
