import numpy as np

np.random.seed(1954)

# 1. Создаем трехмерную матрицу (куб 10x10x10 = 1000 узлов)
D, H, W = 10, 10, 10
N = D * H * W

# Формируем эталонный 3D-объект (объемный трехмерный крест в центре куба)
cube_clean = np.zeros((D, H, W))
cube_clean[4:6, 4:6, 1:9] = 1.0  # Ось X
cube_clean[4:6, 1:9, 4:6] = 1.0  # Ось Y
cube_clean[1:9, 4:6, 4:6] = 1.0  # Ось Z

# 2. Обучаем 3D-связи между всеми 1000 узлами
pattern = np.where(cube_clean.flatten() > 0.5, 1.0, -1.0)
weights = np.outer(pattern, pattern) / N
np.fill_diagonal(weights, 0)

# 3. Жестко портим объем: ломаем 45% всех ячеек куба
cube_damaged = cube_clean.copy()
noise = np.random.rand(D, H, W) < 0.45
cube_damaged[noise] = 1.0 - cube_damaged[noise]

# 4. Запускаем нелинейную 3D-динамику (возбуждение U и торможение V)
U = np.where(cube_damaged.flatten() > 0.5, 0.8, -0.8)
V = np.zeros(N)

dt = 0.2
for _ in range(30):
    input_current = weights @ U
    dU = -U + np.tanh(3.0 * input_current - 0.5 * V)
    dV = -0.5 * V + 0.5 * U
    U += dt * dU
    V += dt * dV

restored_cube = (U.reshape((D, H, W)) > 0).astype(int)

def render_slice(grid_2d):
    return "\n".join("".join("██" if c > 0.5 else "░░" for c in row) for row in grid_2d)

print("=== ЦЕНТРАЛЬНЫЙ СРЕЗ 3D-КУБА НА ВХОДЕ (45% шума) ===")
print(render_slice(cube_damaged[5]))

print("\n=== ЦЕНТРАЛЬНЫЙ СРЕЗ 3D-КУБА НА ВЫХОДЕ ===")
print(render_slice(restored_cube[5]))
