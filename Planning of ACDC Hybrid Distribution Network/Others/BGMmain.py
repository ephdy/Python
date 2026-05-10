import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import warnings
from sklearn.metrics import mean_absolute_percentage_error, r2_score, mean_absolute_error
warnings.filterwarnings('ignore')

# ==================== 1. 准备数据 ====================
print("=" * 50)
print("准备数据...")
print("=" * 50)

# 模拟0-1拓扑数据（替换为你的真实数据）
np.random.seed(42)
df = pd.read_csv("小规模样本end.CSV")
data = df.sample(frac=0.5, random_state=42)
# Split features and labels
X = data.iloc[:, :15].values
y = data.iloc[:, -1].values
print(X.shape, y.shape)
# y=np.log(y)
print(y.min(), y.max())
# y=(y-y.min())/(y.max()-y.min())
print(f"X shape: {X.shape}")
print(f"y range: [{y.min():.2f}, {y.max():.2f}]")
# quantiles = pd.qcut(y, q=10, labels=False)
# sample_weights = 10 - quantiles  # 最小的一组权重=5，最大的一组权重=1
# Split training and test sets (no log transformation)
X_train, X_test, y_train, y_test = train_test_split(
    X, y,test_size=0.2, random_state=42
)

print(f"训练集大小: {X_train.shape}")
print(f"测试集大小: {X_test.shape}")
print(f"目标值范围: [{y.min():.2f}, {y.max():.2f}]")


# ==================== 2. 定义多目标优化函数 ====================
def multi_objective(trial):
    """
    多目标优化函数
    目标1: RMSE (最小化)
    目标2: R² (最大化)
    """

    params = {
        # 树结构参数
        'max_depth': trial.suggest_int('max_depth', 4, 20),
        'num_leaves': trial.suggest_int('num_leaves', 31, 255, log=True),
        'min_data_in_leaf': trial.suggest_int('min_data_in_leaf', 5, 10),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 10),

        # 采样参数
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'subsample_freq': trial.suggest_int('subsample_freq', 0, 10),

        # 正则化参数
        'lambda_l1': trial.suggest_float('lambda_l1', 1e-10, 1.0, log=True),
        'lambda_l2': trial.suggest_float('lambda_l2', 1e-10, 5.0, log=True),
        'min_split_gain': trial.suggest_float('min_split_gain', 0.0, 0.5),

        # 学习率
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 500, 15000, log=True),



        # 固定参数
        'objective': 'RMSE',      # ⭐ Huber损失：MAPE的稳定性+MSE的平滑
        'metric': 'mape',
        'verbose': -1,
        'random_state': 42,
        'n_jobs': -1,
        'max_bin': 2,  # 0-1数据专用
        'boosting_type': 'gbdt',
        'force_col_wise': True,
    }

    # 创建模型
    model = lgb.LGBMRegressor(**params)

    # 训练（带早停）
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric='mape',
        callbacks=[lgb.early_stopping(50, verbose=False)]
    )

    # 预测
    y_pred = model.predict(X_test)

    # 计算两个目标
    # rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mape = mean_absolute_percentage_error(y_test, y_pred) * 100  # sklearn返回小数，乘100变百分比
    # mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    # 返回两个目标值
    return mape, r2


# ==================== 3. 创建多目标研究 ====================
print("\n" + "=" * 50)
print("开始多目标优化 (RMSE最小化 + R²最大化)...")
print("=" * 50)

# 创建多目标研究
study = optuna.create_study(
    directions=['minimize', 'maximize'],  # 目标1最小化, 目标2最大化
    study_name='lightgbm_multi_objective',
    sampler=optuna.samplers.TPESampler(
        seed=42,
        n_startup_trials=10,  # 前10次随机探索
        multivariate=True  # 考虑参数间的相关性
    )
)

# 运行优化
study.optimize(
    multi_objective,
    n_trials=100,  # 尝试100组参数
    show_progress_bar=True,
    n_jobs=1  # 多目标优化建议单线程，避免冲突
)

# ==================== 4. 分析优化结果 ====================
print("\n" + "=" * 50)
print("优化完成！分析结果...")
print("=" * 50)

# 获取Pareto前沿解（互不支配的最优解集）
pareto_trials = study.best_trials

print(f"\n找到 {len(pareto_trials)} 个Pareto最优解:")
print("-" * 60)
print(f"{'解':<5} {'RMSE':<10} {'R²':<10} {'试验号':<8}")
print("-" * 60)

for i, trial in enumerate(pareto_trials[:10]):  # 显示前10个
    print(f"{i + 1:<5} {trial.values[0]:<10.4f} {trial.values[1]:<10.4f} {trial.number:<8}")

# ==================== 5. 选择最终模型 ====================
print("\n" + "=" * 50)
print("选择最终模型...")
print("=" * 50)

# 策略1: 选择RMSE最小的
best_rmse_trial = min(pareto_trials, key=lambda t: t.values[0])
print(f"\n策略1 - 最佳RMSE模型:")
print(f"  RMSE: {best_rmse_trial.values[0]:.4f}")
print(f"  R²: {best_rmse_trial.values[1]:.4f}")
print(f"  参数: {best_rmse_trial.params}")

# 策略2: 选择R²最大的
best_r2_trial = max(pareto_trials, key=lambda t: t.values[1])
print(f"\n策略2 - 最佳R²模型:")
print(f"  RMSE: {best_r2_trial.values[0]:.4f}")
print(f"  R²: {best_r2_trial.values[1]:.4f}")
print(f"  参数: {best_r2_trial.params}")


# 策略3: 平衡选择（RMSE和R²综合最优）
def composite_score(trial):
    """综合评分：RMSE归一化 + (1-R²)归一化，越小越好"""
    rmse = trial.values[0]
    r2 = trial.values[1]
    # 简单加权平均
    return rmse - 0.5 * r2  # RMSE权重更大


best_balanced_trial = min(pareto_trials, key=composite_score)
print(f"\n策略3 - 平衡模型:")
print(f"  RMSE: {best_balanced_trial.values[0]:.4f}")
print(f"  R²: {best_balanced_trial.values[1]:.4f}")
print(f"  参数: {best_balanced_trial.params}")

# ==================== 6. 训练最终模型 ====================
print("\n" + "=" * 50)
print("训练最终模型（选择平衡策略）...")
print("=" * 50)

# 使用平衡策略的参数
final_params = best_balanced_trial.params.copy()

# 提取学习率，降低它以获得更好的收敛
learning_rate = final_params.pop('learning_rate')

final_params.update({
    'n_estimators': 2000,
    'learning_rate': learning_rate,
    'verbose': 1,
    'random_state': 42,
    'n_jobs': -1,
    'max_bin': 2,
    'force_col_wise': True,
})

# 训练最终模型
final_model = lgb.LGBMRegressor(**final_params)
final_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    eval_metric='rmse',
    callbacks=[lgb.early_stopping(100, verbose=True)]
)
final_model.booster_.save_model('pareto_optimal_model.txt')
print("✓ 模型已保存: pareto_optimal_model.txt")
# ==================== 7. 最终评估 ====================
print("\n" + "=" * 50)
print("最终模型评估...")
print("=" * 50)

# 测试集预测
y_pred = final_model.predict(X_test)
y_train_pred = final_model.predict(X_train)

# 计算指标
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
test_r2 = r2_score(y_test, y_pred)
test_mae = np.mean(np.abs(y_test - y_pred))

train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
train_r2 = r2_score(y_train, y_train_pred)

print(f"\n训练集性能:")
print(f"  RMSE: {train_rmse:.4f}")
print(f"  R²:   {train_r2:.4f}")

print(f"\n测试集性能:")
print(f"  RMSE: {test_rmse:.4f}")
print(f"  R²:   {test_r2:.4f}")
print(f"  MAE:  {test_mae:.4f}")
print(f"  最佳迭代数: {final_model.best_iteration_}")

# 过拟合检查
if train_rmse / test_rmse < 0.8:
    print(f"\n⚠️ 警告: 可能存在过拟合 (训练/测试RMSE比值={train_rmse / test_rmse:.2f})")
else:
    print(f"\n✓ 过拟合检查通过 (训练/测试RMSE比值={train_rmse / test_rmse:.2f})")

# ==================== 8. 特征重要性 ====================
print("\n" + "=" * 50)
print("特征重要性分析...")
print("=" * 50)

importance_df = pd.DataFrame({
    'feature': X.columns,
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\n前15重要特征:")
print(importance_df.head(15).to_string(index=False))

# ==================== 9. 保存结果 ====================
print("\n" + "=" * 50)
print("保存结果...")
print("=" * 50)

# 保存模型
final_model.booster_.save_model('pareto_optimal_model.txt')
print("✓ 模型已保存: pareto_optimal_model.txt")

# 保存特征重要性
importance_df.to_csv('feature_importance.csv', index=False)
print("✓ 特征重要性已保存: feature_importance.csv")

# 保存所有Pareto解
pareto_results = []
for i, trial in enumerate(pareto_trials):
    pareto_results.append({
        'rank': i + 1,
        'rmse': trial.values[0],
        'r2': trial.values[1],
        'trial_number': trial.number,
        **trial.params
    })

pareto_df = pd.DataFrame(pareto_results)
pareto_df.to_csv('pareto_solutions.csv', index=False)
print("✓ Pareto解集已保存: pareto_solutions.csv")

# ==================== 10. 可视化 ====================
print("\n" + "=" * 50)
print("生成可视化图表...")
print("=" * 50)

fig, axes = plt.subplots(2, 3, figsize=(18, 12))

# 1. Pareto前沿
ax = axes[0, 0]
all_trials = study.trials
rmse_values = [t.values[0] for t in all_trials if t.values is not None]
r2_values = [t.values[1] for t in all_trials if t.values is not None]
pareto_rmse = [t.values[0] for t in pareto_trials]
pareto_r2 = [t.values[1] for t in pareto_trials]

ax.scatter(rmse_values, r2_values, alpha=0.3, label='所有试验', s=20)
ax.scatter(pareto_rmse, pareto_r2, color='red', s=100,
           edgecolors='black', linewidth=2, label='Pareto最优解', zorder=5)
ax.set_xlabel('RMSE (越小越好)')
ax.set_ylabel('R² (越大越好)')
ax.set_title('Pareto前沿')
ax.legend()
ax.grid(True, alpha=0.3)

# 2. 优化历史 - RMSE
ax = axes[0, 1]
best_rmse_history = []
current_best = float('inf')
for t in all_trials:
    if t.values is not None:
        current_best = min(current_best, t.values[0])
        best_rmse_history.append(current_best)
ax.plot(best_rmse_history)
ax.set_xlabel('试验次数')
ax.set_ylabel('最佳RMSE')
ax.set_title('RMSE优化历史')
ax.grid(True, alpha=0.3)

# 3. 优化历史 - R²
ax = axes[0, 2]
best_r2_history = []
current_best = float('-inf')
for t in all_trials:
    if t.values is not None:
        current_best = max(current_best, t.values[1])
        best_r2_history.append(current_best)
ax.plot(best_r2_history, color='green')
ax.set_xlabel('试验次数')
ax.set_ylabel('最佳R²')
ax.set_title('R²优化历史')
ax.grid(True, alpha=0.3)

# 4. 预测 vs 真实值
ax = axes[1, 0]
ax.scatter(y_test, y_pred, alpha=0.5, s=10)
ax.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
ax.set_xlabel('真实值')
ax.set_ylabel('预测值')
ax.set_title(f'预测 vs 真实 (R²={test_r2:.3f})')
ax.grid(True, alpha=0.3)

# 5. 残差分布
ax = axes[1, 1]
residuals = y_test - y_pred
ax.hist(residuals, bins=50, edgecolor='black', alpha=0.7)
ax.axvline(0, color='red', linestyle='--', linewidth=2)
ax.set_xlabel('残差')
ax.set_ylabel('频数')
ax.set_title(f'残差分布 (均值={residuals.mean():.4f})')
ax.grid(True, alpha=0.3)

# 6. 特征重要性
ax = axes[1, 2]
top_features = importance_df.head(10)
ax.barh(range(len(top_features)), top_features['importance'].values)
ax.set_yticks(range(len(top_features)))
ax.set_yticklabels(top_features['feature'].values)
ax.set_xlabel('重要性')
ax.set_title('前10重要特征')
ax.invert_yaxis()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('multi_objective_optimization_results.png', dpi=150, bbox_inches='tight')
plt.show()

print("✓ 图表已保存: multi_objective_optimization_results.png")

# ==================== 11. 最终总结 ====================
print("\n" + "=" * 50)
print("优化总结")
print("=" * 50)
print(f"""
多目标优化完成！

最终模型类型: LightGBM
优化目标: [RMSE最小化, R²最大化]
试验总数: {len(study.trials)}
Pareto最优解数: {len(pareto_trials)}

选择策略: 平衡RMSE和R²
最终测试集RMSE: {test_rmse:.4f}
最终测试集R²: {test_r2:.4f}
最终测试集MAE: {test_mae:.4f}

模型文件: pareto_optimal_model.txt
结果文件: pareto_solutions.csv
图表文件: multi_objective_optimization_results.png

提示: 如需更高精度，可增加n_trials参数（如200-500）
""")