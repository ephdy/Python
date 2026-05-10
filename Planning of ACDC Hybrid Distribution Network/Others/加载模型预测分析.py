import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error, r2_score, mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


# ==================== 1. 定义模型结构 ====================
class BinaryRegressionNet(nn.Module):
    def __init__(self, input_dim=48):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.2),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.2),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),

            nn.Linear(64, 1)
        )

    def forward(self, x):
        return self.net(x)


# ==================== 2. 加载模型 ====================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {device}")

# 加载检查点（注意添加 weights_only=False）
checkpoint = torch.load('小值模型.pth', map_location=device, weights_only=False)

# 初始化模型并加载权重
model = BinaryRegressionNet(input_dim=checkpoint['model_config']['input_dim'])
model.load_state_dict(checkpoint['model_state_dict'])
model = model.to(device)
model.eval()

# 获取 y_scaler
y_scaler = checkpoint['y_scaler']

print(f"模型加载成功！")
print(f"训练时性能: MAPE={checkpoint['performance']['mape']:.4f}, R²={checkpoint['performance']['r2']:.4f}")

# ==================== 3. 加载并准备测试数据 ====================
print("\n加载数据...")
df = pd.read_csv("100万fop.csv")
data= df[df.iloc[:, -1] < 9000]
# 分割特征和标签（与训练时完全一致）
X = data.iloc[:, :13 + 33 + 2].values
y = data.iloc[:, -1].values

# 对 y 进行 log1p 变换并用 y_scaler 标准化（与训练时一致）
y = np.log1p(y)
y = y.reshape(-1, 1)
y_scaled = y_scaler.transform(y)  # 注意：用之前拟合好的 scaler 做 transform

# 划分训练/测试集（用相同的 random_state）
X_train, X_test, y_train_scaled, y_test_scaled = train_test_split(
    X, y_scaled, test_size=0.2, random_state=42
)

# 转换为 tensor
X_test_tensor = torch.FloatTensor(X_test).to(device)
y_test_tensor = torch.FloatTensor(y_test_scaled).to(device)

print(f"测试集样本数: {len(X_test)}")

# ==================== 4. 预测 ====================
print("\n开始预测...")
with torch.no_grad():
    pred_scaled = model(X_test_tensor).cpu().numpy()

# 逆变换：先逆 scaler，再 expm1
pred_normalized = y_scaler.inverse_transform(pred_scaled)
true_normalized = y_scaler.inverse_transform(y_test_scaled)

# 逆 log1p 变换，得到原始尺度的值
pred_original = np.expm1(pred_normalized)
true_original = np.expm1(true_normalized)

print("预测完成！")

# ==================== 5. 计算评估指标 ====================
mape = mean_absolute_percentage_error(true_original, pred_original)
r2 = r2_score(true_original, pred_original)
mse = mean_squared_error(true_original, pred_original)
rmse = np.sqrt(mse)
mae = mean_absolute_error(true_original, pred_original)

print(f"\n===== 模型评估结果 =====")
print(f"MAPE: {mape:.6f}")
print(f"R²: {r2:.6f}")
print(f"MSE: {mse:.6f}")
print(f"RMSE: {rmse:.6f}")
print(f"MAE: {mae:.6f}")

# ==================== 6. 可视化 ====================
print("\n生成可视化图表...")

# 展平数组用于绘图
true = true_original.flatten()
pred = pred_original.flatten()

# 计算误差
errors = true - pred
percentage_errors = np.abs(errors / true) * 100
max_percentage_error = np.max(percentage_errors)
max_error_idx = np.argmax(percentage_errors)

print(f"最大百分比误差: {max_percentage_error:.2f}%")
print(f"最大百分比误差对应的样本 - 真实值: {true[max_error_idx]:.4f}, 预测值: {pred[max_error_idx]:.4f}")

# 创建画布
fig, axes = plt.subplots(2, 3, figsize=(18, 12))

# 1. 预测值 vs 真实值散点图
axes[0, 0].scatter(true, pred, alpha=0.5, edgecolors='k', linewidth=0.5)
min_val = min(true.min(), pred.min())
max_val = max(true.max(), pred.max())
axes[0, 0].plot([min_val, max_val], [min_val, max_val], 'r--', lw=2, label='理想线 y=x')
axes[0, 0].set_xlabel('真实值')
axes[0, 0].set_ylabel('预测值')
axes[0, 0].set_title(f'预测值 vs 真实值\nR²={r2:.4f}, MAPE={mape:.4f}')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# 2. 残差分布直方图
axes[0, 1].hist(errors, bins=50, edgecolor='black', alpha=0.7, color='skyblue')
axes[0, 1].axvline(x=0, color='red', linestyle='--', linewidth=2)
axes[0, 1].set_xlabel('残差 (真实值 - 预测值)')
axes[0, 1].set_ylabel('频数')
axes[0, 1].set_title(f'残差分布\n均值={errors.mean():.6f}, 标准差={errors.std():.6f}')
axes[0, 1].grid(True, alpha=0.3)

# 3. 残差 vs 预测值
axes[0, 2].scatter(pred, errors, alpha=0.5, edgecolors='k', linewidth=0.5)
axes[0, 2].axhline(y=0, color='red', linestyle='--', linewidth=2)
axes[0, 2].set_xlabel('预测值')
axes[0, 2].set_ylabel('残差')
axes[0, 2].set_title('残差 vs 预测值')
axes[0, 2].grid(True, alpha=0.3)

# 4. 百分比误差分布直方图
axes[1, 0].hist(percentage_errors, bins=50, edgecolor='black', alpha=0.7, color='lightcoral')
axes[1, 0].axvline(x=5, color='red', linestyle='--', linewidth=2, label='5%阈值')
axes[1, 0].axvline(x=10, color='orange', linestyle='--', linewidth=2, label='10%阈值')
axes[1, 0].set_xlabel('百分比误差 (%)')
axes[1, 0].set_ylabel('频数')
axes[1, 0].set_title(f'百分比误差分布\n最大={max_percentage_error:.2f}%')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# 5. 百分比误差 > 5% 和 >10% 的样本比例对比
error_above_5 = np.sum(percentage_errors > 5)
error_above_10 = np.sum(percentage_errors > 10)
error_above_20 = np.sum(percentage_errors > 20)
total_samples = len(percentage_errors)

ratio_above_5 = (error_above_5 / total_samples) * 100
ratio_above_10 = (error_above_10 / total_samples) * 100
ratio_above_20 = (error_above_20 / total_samples) * 100

# 创建分组柱状图
categories = ['≤5%', '5%-10%', '10%-20%', '>20%']
counts = [
    total_samples - error_above_5,  # ≤5%
    error_above_5 - error_above_10,  # 5%-10%
    error_above_10 - error_above_20,  # 10%-20%
    error_above_20  # >20%
]
ratios_segment = [count / total_samples * 100 for count in counts]
colors = ['lightgreen', 'gold', 'orange', 'salmon']

bars = axes[1, 1].bar(categories, ratios_segment, color=colors, edgecolor='black')
axes[1, 1].set_ylabel('样本比例 (%)')
axes[1, 1].set_title(
    f'百分比误差分组分布\n>5%: {error_above_5}个 ({ratio_above_5:.2f}%) | >10%: {error_above_10}个 ({ratio_above_10:.2f}%)')

# 添加数值标签
for bar, ratio, count in zip(bars, ratios_segment, counts):
    height = bar.get_height()
    axes[1, 1].text(bar.get_x() + bar.get_width() / 2., height,
                    f'{ratio:.1f}%\n({count})', ha='center', va='bottom', fontsize=9)

# 6. 按预测值分10个区间的详细误差分析
n_intervals = 10
sorted_idx = np.argsort(pred)
pred_sorted = pred[sorted_idx]
true_sorted = true[sorted_idx]
errors_sorted = errors[sorted_idx]
percentage_errors_sorted = percentage_errors[sorted_idx]

interval_indices = np.array_split(np.arange(len(pred_sorted)), n_intervals)
interval_stats = []

for i, idx in enumerate(interval_indices):
    interval_pred = pred_sorted[idx]
    interval_true = true_sorted[idx]
    interval_pe = percentage_errors_sorted[idx]
    interval_errors = errors_sorted[idx]

    # 计算区间内的MAPE
    interval_mape = np.mean(np.abs((interval_true - interval_pred) / interval_true)) * 100

    # 计算超过5%和10%的样本比例
    above_5_count = np.sum(interval_pe > 5)
    above_5_ratio = (above_5_count / len(interval_pe)) * 100

    above_10_count = np.sum(interval_pe > 10)
    above_10_ratio = (above_10_count / len(interval_pe)) * 100

    above_20_count = np.sum(interval_pe > 20)
    above_20_ratio = (above_20_count / len(interval_pe)) * 100

    interval_stats.append({
        'interval': f'{interval_pred.min():.2f}-{interval_pred.max():.2f}',
        'count': len(interval_pe),
        'mean_pred': interval_pred.mean(),
        'mean_true': interval_true.mean(),
        'mape': interval_mape,
        'mean_pe': interval_pe.mean(),
        'median_pe': np.median(interval_pe),
        'above_5_count': above_5_count,
        'above_5_ratio': above_5_ratio,
        'above_10_count': above_10_count,
        'above_10_ratio': above_10_ratio,
        'above_20_count': above_20_count,
        'above_20_ratio': above_20_ratio
    })

# 绘制区间分析图（多指标）
ax = axes[1, 2]

# 提取数据
interval_labels = [stat['interval'] for stat in interval_stats]
above_5_ratios = [stat['above_5_ratio'] for stat in interval_stats]
above_10_ratios = [stat['above_10_ratio'] for stat in interval_stats]
mapes = [stat['mape'] for stat in interval_stats]

x = np.arange(n_intervals)
width = 0.35

# 绘制双轴图
bars1 = ax.bar(x - width / 2, above_5_ratios, width, label='>5%比例',
               color='salmon', edgecolor='black', alpha=0.7)
bars2 = ax.bar(x + width / 2, above_10_ratios, width, label='>10%比例',
               color='darkred', edgecolor='black', alpha=0.7)

ax.set_xlabel('预测值区间')
ax.set_ylabel('超出阈值的样本比例 (%)')
ax.set_title('各预测值区间的误差分布')
ax.set_xticks(x)
ax.set_xticklabels([f'区间{i + 1}' for i in range(n_intervals)], rotation=45)
ax.legend(loc='upper left')
ax.grid(True, alpha=0.3, axis='y')

# 添加MAPE的折线图在次坐标轴
ax2 = ax.twinx()
line = ax2.plot(x, mapes, 'b-o', linewidth=2, markersize=8, label='MAPE(%)')
ax2.set_ylabel('MAPE (%)', color='blue')
ax2.tick_params(axis='y', labelcolor='blue')
ax2.legend(loc='upper right')

# 添加数值标签到柱状图
for bar, ratio in zip(bars1, above_5_ratios):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2., height,
            f'{ratio:.1f}%', ha='center', va='bottom', fontsize=7)

for bar, ratio in zip(bars2, above_10_ratios):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2., height,
            f'{ratio:.1f}%', ha='center', va='bottom', fontsize=7)

# 添加MAPE数值标签
for i, (xi, mape_val) in enumerate(zip(x, mapes)):
    ax2.annotate(f'{mape_val:.1f}%', (xi, mape_val),
                 textcoords="offset points", xytext=(0, 10),
                 ha='center', fontsize=8, color='blue')

plt.tight_layout()
plt.savefig('model_evaluation.png', dpi=150, bbox_inches='tight')
plt.show()

# ========== 打印详细统计信息 ==========
print("\n" + "=" * 100)
print("详细误差分析报告")
print("=" * 100)
print(f"总样本数: {total_samples}")
print(f"整体MAPE: {mape:.4f}%")
print(f"整体R²: {r2:.6f}")
print(f"整体RMSE: {rmse:.6f}")
print(f"整体MAE: {mae:.6f}")

print("\n" + "-" * 100)
print("全局百分比误差分布:")
print("-" * 100)
print(f"百分比误差 > 5% 的样本数: {error_above_5} ({ratio_above_5:.2f}%)")
print(f"百分比误差 > 10% 的样本数: {error_above_10} ({ratio_above_10:.2f}%)")
print(f"百分比误差 > 20% 的样本数: {error_above_20} ({ratio_above_20:.2f}%)")
print(
    f"百分比误差 > 50% 的样本数: {np.sum(percentage_errors > 50)} ({np.sum(percentage_errors > 50) / total_samples * 100:.2f}%)")
print(
    f"百分比误差 > 100% 的样本数: {np.sum(percentage_errors > 100)} ({np.sum(percentage_errors > 100) / total_samples * 100:.2f}%)")
print(f"最大百分比误差: {max_percentage_error:.2f}%")
print(f"平均百分比误差: {percentage_errors.mean():.2f}%")
print(f"中位数百分比误差: {np.median(percentage_errors):.2f}%")
print(f"百分比误差标准差: {percentage_errors.std():.2f}%")

print("\n" + "-" * 100)
print("各预测值区间的详细误差分析（按预测值排序分10个区间）:")
print("-" * 100)
print(
    f"{'区间':<25} {'样本数':<8} {'MAPE(%)':<10} {'平均PE(%)':<10} {'中位PE(%)':<10} {'>5%样本数':<10} {'>5%比例':<10} {'>10%样本数':<10} {'>10%比例'}")
print("-" * 100)

for stat in interval_stats:
    print(f"{stat['interval']:<25} "
          f"{stat['count']:<8} "
          f"{stat['mape']:<10.2f} "
          f"{stat['mean_pe']:<10.2f} "
          f"{stat['median_pe']:<10.2f} "
          f"{stat['above_5_count']:<10} "
          f"{stat['above_5_ratio']:<10.2f} "
          f"{stat['above_10_count']:<10} "
          f"{stat['above_10_ratio']:.2f}%")

print("=" * 100)

# 额外：打印各区间的统计摘要
print("\n" + "-" * 100)
print("区间统计摘要（按预测值范围）:")
print("-" * 100)
for i, stat in enumerate(interval_stats):
    print(f"区间 {i + 1} [{stat['interval']}]:")
    print(f"  样本数: {stat['count']}, "
          f"平均预测值: {stat['mean_pred']:.4f}, "
          f"平均真实值: {stat['mean_true']:.4f}")
    print(f"  MAPE: {stat['mape']:.2f}%, "
          f"误差>5%: {stat['above_5_count']}/{stat['count']} ({stat['above_5_ratio']:.1f}%), "
          f"误差>10%: {stat['above_10_count']}/{stat['count']} ({stat['above_10_ratio']:.1f}%), "
          f"误差>20%: {stat['above_20_count']}/{stat['count']} ({stat['above_20_ratio']:.1f}%)")
print("=" * 100 + "\n")

# ==================== 7. 保存结果 ====================
# 保存预测结果到CSV
results_df = pd.DataFrame({
    'true_value': true,
    'predicted_value': pred,
    'error': errors,
    'percentage_error': percentage_errors
})
results_df.to_csv('test_predictions.csv', index=False)
print("预测结果已保存到 test_predictions.csv")

# 保存区间分析结果到CSV
interval_df = pd.DataFrame([{
    '区间': stat['interval'],
    '样本数': stat['count'],
    '平均预测值': stat['mean_pred'],
    '平均真实值': stat['mean_true'],
    'MAPE(%)': stat['mape'],
    '平均百分比误差(%)': stat['mean_pe'],
    '中位数百分比误差(%)': stat['median_pe'],
    '超出5%样本数': stat['above_5_count'],
    '超出5%比例(%)': stat['above_5_ratio'],
    '超出10%样本数': stat['above_10_count'],
    '超出10%比例(%)': stat['above_10_ratio'],
    '超出20%样本数': stat['above_20_count'],
    '超出20%比例(%)': stat['above_20_ratio']
} for stat in interval_stats])

interval_df.to_csv('interval_analysis.csv', index=False, encoding='utf-8-sig')
print("区间分析结果已保存到 interval_analysis.csv")