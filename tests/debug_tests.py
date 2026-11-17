import sys
sys.path.insert(0, 'C:/Users/Pixie/PycharmProjects/cyber-owl-llm-brain-module')

print("Starting debug...")
print("Python version:", sys.version)
print("Path:", sys.path)

try:
    from app.core.behaviour import Behaviour
    print('Import OK')
except Exception as e:
    print(f'Import failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    b = Behaviour()
    print('Behaviour created OK')
except Exception as e:
    print(f'Behaviour creation failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    result = b._is_stop_command('стоп')
    print(f'_is_stop_command("стоп") = {result}')
except Exception as e:
    print(f'_is_stop_command failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    result = b._is_register_command('запомни')
    print(f'_is_register_command("запомни") = {result}')
except Exception as e:
    print(f'_is_register_command failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    result = b._extract_name_from_text('я - иван')
    print(f'_extract_name_from_text("я - иван") = {result}')
except Exception as e:
    print(f'_extract_name_from_text failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('All tests passed!')
