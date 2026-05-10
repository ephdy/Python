import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from torch.utils.data import TensorDataset, DataLoader
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

df = pd.read_csv("100万fop.csv")
data= df[df.iloc[:, -1] < 9000]
print()
# Split features and labels
X = data.iloc[:, :13 + 33 + 2].values
y = data.iloc[:, -1].values
print(y.max())
y=np.log1p(y)
y_scaler = StandardScaler()

y = y.reshape(-1, 1)
y_scaled = y_scaler.fit_transform(y)



X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_scaled,
    test_size=0.2,
    random_state=42
)

X_train = torch.FloatTensor(X_train)
X_test = torch.FloatTensor(X_test)

y_train = torch.FloatTensor(y_train)
y_test = torch.FloatTensor(y_test)



train_dataset = TensorDataset(X_train, y_train)
test_dataset = TensorDataset(X_test, y_test)

train_loader = DataLoader(
    train_dataset,
    batch_size=256,
    shuffle=True
)

test_loader = DataLoader(
    test_dataset,
    batch_size=256
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = BinaryRegressionNet().to(device)

criterion = nn.MSELoss(
    reduction='none'
)

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=1e-3,
    weight_decay=1e-4
)

epochs = 500

for epoch in range(epochs):

    model.train()

    total_loss = 0

    for xb, yb in train_loader:

        xb = xb.to(device)
        yb = yb.to(device)

        pred = model(xb)

        loss_raw = criterion(
            pred,
            yb
        )

        weights = torch.ones_like(yb)

        weights[yb > 10000] = 3

        weights[yb < 9400] = 3

        loss = (
                loss_raw * weights
        ).mean()

        optimizer.zero_grad()

        loss.backward()

        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss = {total_loss:.6f}")

model.eval()



with torch.no_grad():

    pred_scaled = model(X_test.to(device)).cpu().numpy()

pred = y_scaler.inverse_transform(pred_scaled)

true = y_scaler.inverse_transform(y_test.numpy())

from sklearn.metrics import mean_absolute_percentage_error
from sklearn.metrics import r2_score

mape = mean_absolute_percentage_error(true, pred)

r2 = r2_score(true, pred)

print("MAPE =", mape)
print("R2 =", r2)

# 方法1：保存完整模型（推荐）
torch.save({
    'model_state_dict': model.state_dict(),
    'y_scaler': y_scaler,
    'model_architecture': model.__class__.__name__,
    'model_config': {
        'input_dim': 48
    },
    'performance': {
        'mape': mape,
        'r2': r2
    }
}, '加权_model_full.pth')

print("模型已保存为: 加权logNN.pth")





import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 支持中文
matplotlib.rcParams['axes.unicode_minus'] = False

# 计算误差
errors = true - pred  # 残差
percentage_errors = np.abs(errors / true) * 100  # 百分比误差
max_percentage_error = np.max(percentage_errors)
max_error_idx = np.argmax(percentage_errors)

print(f"最大百分比误差: {max_percentage_error:.2f}%")
print(f"最大百分比误差对应的样本 - 真实值: {true[max_error_idx][0]:.4f}, 预测值: {pred[max_error_idx][0]:.4f}")

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
axes[1, 0].set_xlabel('百分比误差 (%)')
axes[1, 0].set_ylabel('频数')
axes[1, 0].set_title(f'百分比误差分布\n最大={max_percentage_error:.2f}%')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# 5. 百分比误差 > 5% 的样本比例
error_above_5 = np.sum(percentage_errors > 5)
total_samples = len(percentage_errors)
ratio_above_5 = (error_above_5 / total_samples) * 100

axes[1, 1].bar(['≤5%', '>5%'], [total_samples - error_above_5, error_above_5],
               color=['lightgreen', 'salmon'], edgecolor='black')
axes[1, 1].set_ylabel('样本数')
axes[1, 1].set_title(f'百分比误差分组\n>5%: {error_above_5}个样本 ({ratio_above_5:.2f}%)')
for i, (value, count) in enumerate(zip(['≤5%', '>5%'],
                                       [total_samples - error_above_5, error_above_5])):
    axes[1, 1].text(i, count, f'{count}\n({count / total_samples * 100:.1f}%)',
                    ha='center', va='bottom')

# 6. 按预测值分10个区间的误差分析
n_intervals = 10
sorted_idx = np.argsort(pred.flatten())
pred_sorted = pred[sorted_idx].flatten()
percentage_errors_sorted = percentage_errors[sorted_idx]

interval_indices = np.array_split(np.arange(len(pred_sorted)), n_intervals)
interval_stats = []

for i, idx in enumerate(interval_indices):
    interval_pred = pred_sorted[idx]
    interval_pe = percentage_errors_sorted[idx]
    above_5_count = np.sum(interval_pe > 5)
    above_5_ratio = (above_5_count / len(interval_pe)) * 100

    interval_stats.append({
        'interval': f'{interval_pred.min():.2f}-{interval_pred.max():.2f}',
        'count': len(interval_pe),
        'mean_pe': interval_pe.mean(),
        'above_5_count': above_5_count,
        'above_5_ratio': above_5_ratio
    })

# 绘制区间分析
ax = axes[1, 2]
interval_labels = [stat['interval'] for stat in interval_stats]
above_5_ratios = [stat['above_5_ratio'] for stat in interval_stats]
above_5_counts = [stat['above_5_count'] for stat in interval_stats]

bars = ax.bar(range(n_intervals), above_5_ratios, color='salmon', edgecolor='black', alpha=0.7)
ax.set_xlabel('预测值区间')
ax.set_ylabel('百分比误差>5%的比例 (%)')
ax.set_title('各预测值区间中百分比误差>5%的样本比例')
ax.set_xticks(range(n_intervals))
ax.set_xticklabels([f'区间{i + 1}' for i in range(n_intervals)], rotation=45)
ax.grid(True, alpha=0.3, axis='y')

# 添加数值标签
for bar, ratio, count in zip(bars, above_5_ratios, above_5_counts):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2., height,
            f'{ratio:.1f}%\n({count})', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.show()

# ========== 打印详细统计信息 ==========
print("\n" + "=" * 60)
print("详细误差分析报告")
print("=" * 60)
print(f"总样本数: {total_samples}")
print(f"百分比误差 > 5% 的样本数: {error_above_5} ({ratio_above_5:.2f}%)")
print(
    f"百分比误差 > 10% 的样本数: {np.sum(percentage_errors > 10)} ({np.sum(percentage_errors > 10) / total_samples * 100:.2f}%)")
print(
    f"百分比误差 > 20% 的样本数: {np.sum(percentage_errors > 20)} ({np.sum(percentage_errors > 20) / total_samples * 100:.2f}%)")
print(f"最大百分比误差: {max_percentage_error:.2f}%")
print(f"平均百分比误差: {percentage_errors.mean():.2f}%")
print(f"中位数百分比误差: {np.median(percentage_errors):.2f}%")

print("\n" + "-" * 60)
print("各预测值区间的误差分析（按预测值排序分10个区间）:")
print("-" * 60)
print(f"{'区间':<20} {'样本数':<8} {'平均%误差':<12} {'>5%样本数':<12} {'>5%比例'}")
print("-" * 60)
for stat in interval_stats:
    print(f"{stat['interval']:<20} {stat['count']:<8} {stat['mean_pe']:<12.2f} "
          f"{stat['above_5_count']:<12} {stat['above_5_ratio']:.2f}%")
print("=" * 60 + "\n")
