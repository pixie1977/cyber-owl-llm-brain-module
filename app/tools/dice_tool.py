import random
import re

from app.tools.dice_data.merovinjan_replics_for_dnd import MerovinJanReplicsForDnD

merov = MerovinJanReplicsForDnD()

@tool
def roll_dice_tool(dice_expression: str = "1d20") -> str:
    """Симулятор бросков игровых костей (кубиков) в стиле настольных игр D&D.

    Используй этот инструмент обязательно, когда пользователь просит бросить кубик,
    кинуть дайсы, выполнить ролл, а ТАКЖЕ когда просит сделать спасбросок (saving throw)
    или проверку любого навыка/характеристики.

    Args:
        dice_expression (str): Математическая формула броска костей в стандартной
                               нотации D&D (например: '1d20', '2d6+5', '3d10-2').
                               Если пользователь просит сделать СПАСБРОСОК,
                               проверку навыка или количество кубиков не указано
                               (например, 'кинь спасбросок на реакцию', 'сделай ролл'),
                               обязательно подставляй и передавай строку '1d20'.

    Returns:
        str: Полный детализированный текст с результатами бросков кубиков.
    """
    # Очищаем входящую строку от пробелов
    expression = dice_expression.replace(" ", "").lower()

    # Регулярное выражение для парсинга формата: [количество]d[граней](+[модификатор] или -[модификатор])
    match = re.match(r'(\d*)d(\d+)(?:([+-]\d+))?', expression)

    if not match:
        return "Ошибка синтаксиса броска. Передай строку в формате, например, '2d6+5'."

    # 1. Извлекаем количество кубиков (если не указано, то 1, например "d20" -> "1d20")
    count_str, sides_str, modifier_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = int(modifier_str) if modifier_str else 0

    # Защита от сумасшедших запросов юзера (ограничиваем пулы)
    if count > 50 or sides > 1000:
        return "Мои кубики не помещаются в ладонь для такого броска. Поубавь аппетиты."

    # 2. Симулируем броски случайных чисел
    rolls = [random.randint(1, sides) for _ in range(count)]
    subtotal = sum(rolls)
    total = subtotal + modifier

    # 3. Формируем красивый ироничный лог для Совы
    rolls_str = " + ".join(map(str, rolls))
    mod_str = f" {modifier_str}" if modifier != 0 else ""

    response = (
        f"Выполняю бросок {expression}: "
        f"на кубах выпало [{rolls_str}]{mod_str}. "
        f"Итоговая сумма: {total}."
    )

    # Добавляем щепотку айтишно-настольного юмора для критических исходов (d20)
    if sides == 20 and count == 1:
        if rolls[0] == 20:
            response += merov.get_critical_success_comment()
        elif rolls[0] == 1:
            response += merov.get_critical_fail_comment()

    return response
