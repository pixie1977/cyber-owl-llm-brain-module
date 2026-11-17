import numpy as np

np.random.seed(1954)

H, W = 16, 12
N = H * W

# 1. Формируем три эталона: "5", "0" и "2"
five = np.zeros((H, W))
five[2:4, 2:10] = 1.0
five[2:8, 2:4] = 1.0
five[7:9, 2:10] = 1.0
five[7:14, 8:10] = 1.0
five[12:14, 2:10] = 1.0

zero = np.zeros((H, W))
zero[2:4, 2:10] = 1.0
zero[12:14, 2:10] = 1.0
zero[2:14, 2:4] = 1.0
zero[2:14, 8:10] = 1.0

two = np.zeros((H, W))
two[2:4, 2:10] = 1.0
two[2:8, 8:10] = 1.0
two[7:9, 2:10] = 1.0
two[7:14, 2:4] = 1.0
two[12:14, 2:10] = 1.0

# 2. Записываем все три образа в единую матрицу связей
patterns = [np.where(p.flatten() > 0.5, 1.0, -1.0) for p in (five, zero, two)]
weights = sum(np.outer(p, p) for p in patterns) / N
np.fill_diagonal(weights, 0)

# 3. Портим цифру "2": отрываем куски и добавляем шум
damaged = two.copy()
damaged[2:4, 6:10] = 0.0   # Вырван правый верх
damaged[7:12, 2:4] = 0.0   # Вырвана левая нижняя ножка
noise = np.random.rand(H, W) < 0.30
damaged[noise] = 1.0 - damaged[noise]

# 4. Запускаем динамику возбуждения U и торможения V
U = np.where(damaged.flatten() > 0.5, 0.8, -0.8)
V = np.zeros(N)

def render(grid):
    return "\n".join("".join("██" if c > 0.5 else "░░" for c in row) for row in grid)

print("=== ВХОД (порванная '2' + шум) ===")
print(render(damaged))

dt = 0.2
for step in range(45):
    input_current = weights @ U
    dU = -U + np.tanh(2.8 * input_current - 0.6 * V)
    dV = -0.5 * V + 0.5 * U
    U += dt * dU
    V += dt * dV
    if step in (0, 5, 15, 44):
        print(f"\n=== ЦИКЛ {step + 1} ===")
        print(render((U.reshape((H, W)) > 0).astype(int)))
