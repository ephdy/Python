import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import MDS
from scipy.spatial import procrustes

# 距离矩阵（原始数据）
dist_matrix_raw = np.array([
    [0.00, 1.61, 1.61, 3.22, 2.25, 3.22, 3.86, 3.86, 5.47, 4.51, 5.47, 6.11, 6.11],
    [1.61, 0.00, 2.25, 1.61, 1.61, 3.86, 2.25, 3.22, 3.86, 3.86, 4.83, 4.51, 5.47],
    [1.61, 2.25, 0.00, 3.86, 1.61, 1.61, 3.22, 2.25, 4.83, 3.86, 3.86, 5.47, 4.51],
    [3.22, 1.61, 3.86, 0.00, 2.25, 4.51, 1.61, 4.51, 2.25, 3.22, 5.47, 3.86, 4.83],
    [2.25, 1.61, 1.61, 2.25, 0.00, 2.25, 1.61, 1.61, 3.22, 2.25, 3.22, 3.86, 3.86],
    [3.22, 3.86, 1.61, 4.51, 2.25, 0.00, 3.86, 1.61, 5.47, 3.22, 2.25, 4.83, 3.86],
    [3.86, 2.25, 3.22, 1.61, 1.61, 3.86, 0.00, 2.25, 1.61, 1.61, 3.86, 2.25, 3.22],
    [3.86, 3.22, 2.25, 3.86, 1.61, 1.61, 2.25, 0.00, 3.86, 1.61, 1.61, 3.22, 2.25],
    [5.47, 3.86, 4.83, 2.25, 3.22, 5.47, 1.61, 3.86, 0.00, 2.25, 4.51, 1.61, 3.86],
    [4.51, 3.86, 3.86, 3.22, 2.25, 3.22, 1.61, 1.61, 2.25, 0.00, 2.25, 1.61, 1.61],
    [5.47, 4.83, 3.86, 5.47, 3.22, 2.25, 3.86, 1.61, 4.51, 2.25, 0.00, 3.86, 1.61],
    [6.11, 4.51, 5.47, 3.86, 3.86, 4.83, 2.25, 3.22, 1.61, 1.61, 3.86, 0.00, 2.25],
    [6.11, 5.47, 4.51, 4.83, 3.86, 3.86, 3.22, 2.25, 3.86, 1.61, 1.61, 2.25, 0.00]
])

# 确保矩阵对称（取上三角和下三角的平均值）
dist_matrix = (dist_matrix_raw + dist_matrix_raw.T) / 2

# 检查对称性（可选）
print("矩阵是否对称:", np.allclose(dist_matrix, dist_matrix.T))

# 使用MDS降维到2维，避免警告
mds = MDS(
    n_components=2,
    dissimilarity='precomputed',
    random_state=42,
    normalized_stress='auto',
    n_init=4,  # 明确指定n_init避免警告
    init='random'  # 明确指定init避免警告
)
coords = mds.fit_transform(dist_matrix)

# 平移使节点0到原点
translation = coords[0]
coords_aligned = coords - translation

# 可选：绕原点旋转使节点1在x正半轴上
angle = np.arctan2(coords_aligned[1, 1], coords_aligned[1, 0])
rotation_matrix = np.array([[np.cos(-angle), -np.sin(-angle)],
                            [np.sin(-angle), np.cos(-angle)]])
coords_rotated = coords_aligned @ rotation_matrix.T

# 绘图
plt.figure(figsize=(12, 10))
plt.scatter(coords_rotated[:, 0], coords_rotated[:, 1], c='red', s=100, zorder=5)

# 添加节点标签
for i, (x, y) in enumerate(coords_rotated):
    plt.annotate(str(i), (x, y), xytext=(5, 5), textcoords='offset points',
                 fontsize=12, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3",
                 facecolor="white", edgecolor="black", alpha=0.8))

# 添加连线（可选）
for i in range(len(dist_matrix)):
    for j in range(i+1, len(dist_matrix)):
        plt.plot([coords_rotated[i, 0], coords_rotated[j, 0]],
                 [coords_rotated[i, 1], coords_rotated[j, 1]],
                 'gray', alpha=0.3, linewidth=0.5)

plt.xlabel('X', fontsize=12)
plt.ylabel('Y', fontsize=12)
plt.title('13节点的MDS二维布局 (节点0固定在原点)', fontsize=14, fontweight='bold')
plt.axhline(0, color='black', linewidth=0.5, linestyle='--', alpha=0.5)
plt.axvline(0, color='black', linewidth=0.5, linestyle='--', alpha=0.5)
plt.grid(True, alpha=0.3)
plt.axis('equal')

# 添加坐标轴范围说明
x_min, x_max = coords_rotated[:, 0].min(), coords_rotated[:, 0].max()
y_min, y_max = coords_rotated[:, 1].min(), coords_rotated[:, 1].max()
margin = 0.5
plt.xlim(x_min - margin, x_max + margin)
plt.ylim(y_min - margin, y_max + margin)

plt.tight_layout()
plt.show()

# 打印坐标
print("\n节点坐标 (原点为节点0):")
print("-" * 40)
for i, (x, y) in enumerate(coords_rotated):
    print(f"节点 {i:2d}: ({x:8.4f}, {y:8.4f})")

# 计算并验证距离矩阵的误差
print("\n" + "-" * 40)
print("MDS重构误差分析:")
print("-" * 40)

# 从MDS坐标重新计算距离矩阵
reconstructed_dist = np.zeros_like(dist_matrix)
for i in range(len(coords_rotated)):
    for j in range(len(coords_rotated)):
        reconstructed_dist[i, j] = np.sqrt(np.sum((coords_rotated[i] - coords_rotated[j])**2))

# 计算平均绝对误差
mae = np.mean(np.abs(dist_matrix - reconstructed_dist))
print(f"平均绝对误差 (MAE): {mae:.6f}")
print(f"最大绝对误差: {np.max(np.abs(dist_matrix - reconstructed_dist)):.6f}")