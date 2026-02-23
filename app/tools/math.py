"""
Модуль для математических вычислений с поддержкой тригонометрии, корней, дробей и выбора режима (градусы/радианы).
"""

import re
from math import pi

from sympy import pi as sym_pi, sin, cos, tan
from app.core.logger import get_logger


# --- Настройка логирования ---
log = get_logger(__name__)


def trig_replace(match, use_degrees: bool = True) -> str:
    """Обрабатывает тригонометрические функции, преобразуя аргументы в нужную систему.

    Args:
        match: Регулярное выражение с группами (функция, аргумент).
        use_degrees: Если True — аргументы в градусах, иначе — в радианах.

    Returns:
        Строка с подставленным выражением.
    """
    func = match.group(1).lower()
    arg = match.group(2)

    if use_degrees:
        # Переводим градусы в радианы: x → x * pi / 180
        rad_arg = f"({arg}) * {sym_pi} / 180"
    else:
        # Оставляем как есть (радианы)
        rad_arg = f"({arg})"

    if func == "sin":
        return str(sin(rad_arg))
    elif func == "cos":
        return str(cos(rad_arg))
    elif func == "tan":
        return str(tan(rad_arg))
    elif func == "ctg":
        return str(1/tan(rad_arg))
    return "0"


def calculator(expression: str) -> str:
    """Выполняет математические вычисления с поддержкой дробей, корней, тригонометрии и выбора режима.

    Поддерживает:
      - sin, cos, tan, ctg
      - sqrt(x), √x
      - Дроби: 1/3, (2+1)/(4-2)
      - Упрощение выражений
      - pi, π, пи → число π (или 180° в градусном режиме)
      - Режимы: автоматическое определение по суффиксам '°' или 'rad'

    Примеры:
      - sin(30) градусов
      - sin(90) → 1         # по умолчанию градусы
      - sin(pi/2 rad) → 1   # явное указание радиан
      - cos(180°) → -1      # явное указание градусов

    Args:
        expression: Математическое выражение.

    Returns:
        Упрощённый результат в символьной форме.
    """
    log.info(f"calculator tool: Получено выражение '{expression}'")

    try:
        from sympy import sympify, sqrt, simplify, nan
        import sympy as sp

        expr = expression.strip()

        # Определяем режим: если есть 'rad', 'radian', 'рад' или 'π' без ° — считаем радианами
        # Если есть '°', 'deg', 'град' — градусы
        use_degrees = True

        if re.search(r"\b(rad|радиан|рад|pi|пи)\b", expr, re.IGNORECASE):
            use_degrees = False
            expr = re.sub(r"\s*(rad|радиан|рад)\b", "", expr, flags=re.IGNORECASE)

        if "°" in expr or re.search(r"\b(deg|град)\b", expr, re.IGNORECASE):
            use_degrees = True
            expr = re.sub(r"°|\s*(deg|град)\b", "", expr, flags=re.IGNORECASE)

        # Заменяем π, pi, пи на символ π
        expr = re.sub(r"pi\(\)|pi|π|пи", f"{pi}", expr, flags=re.IGNORECASE)

        # Заменяем √x → sqrt(x), учитываем отсутствие скобок
        expr = re.sub(r"√\s*", "sqrt(", expr)
        expr = re.sub(r"sqrt(?=\s*[^()])", r"sqrt(", expr)

        # Преобразуем степени: x^y → x**y
        expr = re.sub(r"(?<!\*)\^(?!\*)", "**", expr)

        # Обработка тригонометрических функций с учётом режима
        trig_pattern = r"\b(sin|cos|tan|ctg)\s*\(\s*([^)]+)\s*\)"
        expr = re.sub(
            trig_pattern,
            lambda m: trig_replace(m, use_degrees=use_degrees),
            expr,
            flags=re.IGNORECASE
        )

        # Закрытие открытых скобок (простая эвристика)
        open_parens = expr.count("(") - expr.count(")")
        expr += ")" * open_parens

        # Парсим и упрощаем выражение
        result_expr = sympify(expr, evaluate=True)
        simplified = simplify(result_expr)

        # Численное приближение
        try:
            float_result = float(simplified.evalf())
            if abs(float_result) == float('inf'):
                numeric_str = "infinity"
            elif simplified is sp.nan:
                numeric_str = "nan"
            else:
                # Округление до 4 знаков после запятой
                numeric_str = f"{round(float_result, 4):.4f}"
        except Exception:
            numeric_str = "error"

        # Форматирование результата
        str_result = str(simplified).replace("sqrt", "sqrt")

        # Коррекция: значения близкие к нулю → 0.0000
        if numeric_str != "error" and abs(float(simplified.evalf())) < 1e-10:
            numeric_str = "0.0000"

        # Используем только ASCII в логах
        log.info(
            f"Mode: {'degrees' if use_degrees else 'radians'} | "
            f"Input: {expression} -> "
            f"Result: {str_result} ~= {numeric_str}"
        )
        return f"Result: {str_result} ~ {numeric_str}"
    except Exception as e:
        log.error(f"Error in calculator for expression '{expression}': {e}")
        return "error"