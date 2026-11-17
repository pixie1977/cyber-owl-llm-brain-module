import numpy as np

np.random.seed(42)

# 1. Создаем эталонную цифру "5" на сетке 16x12
H, W = 16, 12
clean_five = np.zeros((H, W))
clean_five[2:4, 2:10] = 1.0    # Верхняя перекладина
clean_five[2:8, 2:4] = 1.0     # Левая вертикаль
clean_five[7:9, 2:10] = 1.0    # Средняя перекладина
clean_five[7:14, 8:10] = 1.0   # Правая нижняя вертикаль
clean_five[12:14, 2:10] = 1.0  # Нижняя перекладина

# 2. Обучаем связи между узлами (аналог подстройки резисторов в 1954 году)
pattern = np.where(clean_five.flatten() > 0.5, 1.0, -1.0)
N = len(pattern)
weights = np.outer(pattern, pattern) / N
np.fill_diagonal(weights, 0)

# 3. Портим картинку: вырываем куски и добавляем 25% случайного шума
damaged = clean_five.copy()
damaged[2:4, 6:10] = 0.0   # Оторвали часть верха
damaged[7:9, 5:8] = 0.0    # Дыра в середине
noise = np.random.rand(H, W) < 0.25
damaged[noise] = 1.0 - damaged[noise]

# 4. Запускаем нелинейную сеть (возбуждение U и торможение V)
U = np.where(damaged.flatten() > 0.5, 0.8, -0.8)
V = np.zeros(N)

dt = 0.2
for _ in range(40):
    input_current = weights @ U
    # np.tanh — это та самая плавная нелинейная характеристика транзистора
    dU = -U + np.tanh(2.5 * input_current - 0.5 * V)
    dV = -0.5 * V + 0.5 * U
    U += dt * dU
    V += dt * dV

restored = (U.reshape((H, W)) > 0).astype(int)

def render(grid):
    return "\n".join("".join("██" if c > 0.5 else "░░" for c in row) for row in grid)

print("ВХОД:\n" + render(damaged))
print("\nВЫХОД:\n" + render(restored))
