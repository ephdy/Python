import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
import matplotlib.pyplot as plt
import warnings
import json
import time
import joblib

warnings.filterwarnings('ignore')

print("=" * 80)
print("Optuna + XGBoost 回归优化（小值样本高权重）")
print("=" * 80)

# ==================== 1. 准备数据 ====================
print("\n1. 准备数据...")

data = pd.read_csv("100万fop.CSV")

X = data.iloc[:, :13 + 33 + 2].values
y = data.iloc[:, 55].values


# y=(y-y.min())/(y.max()-y.min())
print(f"X shape: {X.shape}")
print(f"y 范围: [{y.min():.2f}, {y.max():.2f}]")

# 对 y 取对数
y_log = y
# y_log = np.log(y)
print(f"log(y) 范围: [{y_log.min():.4f}, {y_log.max():.4f}]")



sample_weights = np.ones(y.shape[0])
# ====== 构造样本权重：小值样本权重更高 ======
# 方法1：权重与 y 值成反比（小值权重大）
# sample_weights = 1.0 / y/y  # y 越小，权重越大

# 方法2（备选）：用分位数分段给权重
# quantiles = pd.qcut(y, q=10, labels=False)
# sample_weights = 10 - quantiles  # 最小的一组权重=5，最大的一组权重=1

# 方法3（备选）：对数反比，压缩权重范围
# sample_weights = 1.0 / np.log1p(y)

# 归一化权重，使权重均值为 1（不影响学习率）
sample_weights = sample_weights / sample_weights.mean()

print(f"样本权重范围: [{sample_weights.min():.4f}, {sample_weights.max():.4f}]")
print(f"样本权重均值: {sample_weights.mean():.4f}")
print(f"小值样本 (y < {np.percentile(y, 20):.0f}) 平均权重: {sample_weights[y < np.percentile(y, 20)].mean():.4f}")
print(f"大值样本 (y > {np.percentile(y, 80):.0f}) 平均权重: {sample_weights[y > np.percentile(y, 80)].mean():.4f}")

# 划分数据集（权重也跟着划分）
# X_train, X_test, y_train_log, y_test_log, y_train_orig, y_test_orig, w_train, w_test = train_test_split(
#     X, y_log, y, sample_weights, test_size=0.2, random_state=42
# )
# Split training and test sets (no log transformation)
X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
    X, y, sample_weights, test_size=0.2, random_state=42
)

print(f"\n训练集大小: {X_train.shape}")
print(f"测试集大小: {X_test.shape}")

# ==================== 2. 定义目标函数 ====================
print("\n2. 定义Optuna目标函数...")


def objective(trial, X_train, y_train, sample_weight_train):
    """
    Optuna目标函数（带样本权重，交叉验证）
    """
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 4000, step=50),
        'max_depth': trial.suggest_int('max_depth', 6, 7),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'colsample_bylevel': trial.suggest_float('colsample_bylevel', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
        'random_state': 42,
        'objective': 'reg:squarederror',
        'verbosity': 0
    }

    # ====== 手动 KFold 交叉验证，传入权重 ======
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rmse_scores = []

    for train_idx, val_idx in kf.split(X_train):
        X_tr, X_val = X_train[train_idx], X_train[val_idx]
        y_tr, y_val = y_train[train_idx], y_train[val_idx]
        w_tr = sample_weight_train[train_idx]
        w_val = sample_weight_train[val_idx]

        model = xgb.XGBRegressor(**params)
        model.fit(
            X_tr, y_tr,
            sample_weight=w_tr,    # 👈 传入训练权重
            verbose=False
        )

        y_pred = model.predict(X_val)

        # 加权 RMSE（验证集也加权，与训练目标一致）
        weighted_rmse = np.sqrt(np.average((y_val - y_pred) ** 2, weights=w_val))
        rmse_scores.append(weighted_rmse)

        # 剪枝判断
        trial.report(np.mean(rmse_scores), step=len(rmse_scores))
        if trial.should_prune():
            raise optuna.TrialPruned()

    return np.mean(rmse_scores)


# ==================== 3. 配置并运行优化 ====================
print("\n3. 配置并运行Optuna优化...")

study = optuna.create_study(
    direction='minimize',
    sampler=TPESampler(seed=42),
    pruner=MedianPruner(
        n_startup_trials=10,
        n_warmup_steps=20,
        interval_steps=1
    ),
    study_name='xgboost_weighted_optimization',
)

start_time = time.time()

print("\n开始优化...")
print("=" * 60)

study.optimize(
    lambda trial: objective(trial, X_train, y_train, w_train),
    n_trials=50,
    n_jobs=1,
    show_progress_bar=True,
    catch=(Exception,)
)

optimization_time = time.time() - start_time
print(f"\n优化完成！总耗时: {optimization_time:.2f} 秒")

# ==================== 4. 查看优化结果 ====================
print("\n4. 优化结果分析")
print("=" * 60)

print(f"\n最佳试验编号: {study.best_trial.number}")
print(f"最佳CV RMSE（对数空间）: {study.best_value:.4f}")
print(f"\n最佳超参数:")
best_params = study.best_params
for param_name, param_value in best_params.items():
    print(f"  {param_name}: {param_value}")

# ==================== 5. 训练最佳模型 ====================
print("\n5. 使用最佳参数训练最终模型...")

final_model = xgb.XGBRegressor(
    **best_params,
    random_state=42,
    objective='reg:squarederror',
    n_jobs=-1,
    verbosity=0
)

# 用权重训练
final_model.fit(
    X_train, y_train,
    sample_weight=w_train,    # 👈 传入权重
    verbose=False
)
path='m_fop.csv'
final_model.save_model(path)
print(f"✅ 最佳模型已保存为 JSON 文件: {path}")
# 预测（对数空间）
y_pred_train = final_model.predict(X_train)
y_pred_test = final_model.predict(X_test)


# # 限制对数空间的范围，防止 exp 溢出
# max_log = 13  # ln(1.79e308)，float64 最大值
# min_log = -13  # 最小值
#
# y_pred_log_train = np.clip(y_pred_log_train, min_log, max_log)
# y_pred_log_test = np.clip(y_pred_log_test, min_log, max_log)
#
# # 还原到原始尺度
# y_pred_train = np.exp(y_pred_log_train)
# y_pred_test = np.exp(y_pred_log_test)

# ==================== 6. 评估（原始尺度） ====================
print("\n6. 模型评估（原始尺度）...")

# 计算加权指标（小值样本权重更高）
def weighted_mse(y_true, y_pred, weights):
    return np.average((y_true - y_pred) ** 2, weights=weights)

def weighted_mae(y_true, y_pred, weights):
    return np.average(np.abs(y_true - y_pred), weights=weights)

def weighted_r2(y_true, y_pred, weights):
    ss_res = np.average((y_true - y_pred) ** 2, weights=weights)
    ss_tot = np.average((y_true - np.average(y_true, weights=weights)) ** 2, weights=weights)
    return 1 - ss_res / ss_tot

# 标准指标
train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
test_mae = mean_absolute_error(y_test, y_pred_test)
test_r2 = r2_score(y_test, y_pred_test)

# 加权指标
test_weighted_rmse = np.sqrt(weighted_mse(y_test, y_pred_test, w_test))
test_weighted_mae = weighted_mae(y_test, y_pred_test, w_test)
test_weighted_r2 = weighted_r2(y_test, y_pred_test, w_test)

# MAPE
def mape(y_true, y_pred):
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

test_mape = mape(y_train, y_pred_test)

# 分区间评估
def evaluate_by_quantile(y_true, y_pred, weights, n_quantiles=5):
    """按 y 值大小分区间评估"""
    quantiles = pd.qcut(y_true, q=n_quantiles, labels=False, duplicates='drop')
    results = []
    for q in range(n_quantiles):
        mask = quantiles == q
        if mask.sum() > 0:
            y_t = y_true[mask]
            y_p = y_pred[mask]
            w_t = weights[mask]
            rmse = np.sqrt(weighted_mse(y_t, y_p, w_t))
            mape_val = mape(y_t, y_p)
            results.append({
                '区间': f'Q{q+1}',
                'y范围': f'[{y_t.min():.0f}, {y_t.max():.0f}]',
                '样本数': mask.sum(),
                'RMSE': rmse,
                'MAPE(%)': mape_val
            })
    return pd.DataFrame(results)

quantile_results = evaluate_by_quantile(y_train, y_pred_test, w_test)

print(f"\n========== 整体指标 ==========")
print(f"训练集 RMSE: {train_rmse:.4f}")
print(f"测试集 RMSE: {test_rmse:.4f}")
print(f"测试集 MAE: {test_mae:.4f}")
print(f"测试集 MAPE: {test_mape:.2f}%")
print(f"测试集 R²: {test_r2:.4f}")
print(f"\n加权 RMSE（小值权重高）: {test_weighted_rmse:.4f}")
print(f"加权 MAE（小值权重高）: {test_weighted_mae:.4f}")
print(f"加权 R²（小值权重高）: {test_weighted_r2:.4f}")

print(f"\n========== 分区间评估 ==========")
print(quantile_results.to_string(index=False))

# ==================== 7. 对比默认参数 ====================
print("\n7. 对比默认参数模型...")

default_model = xgb.XGBRegressor(random_state=42, objective='reg:squarederror')
default_model.fit(X_train, y_train, verbose=False)
y_pred_default_log = default_model.predict(X_test)
y_pred_default = np.exp(y_pred_default_log)

default_rmse = np.sqrt(mean_squared_error(y_train, y_pred_default))
default_mape = mape(y_train, y_pred_default)
default_weighted_rmse = np.sqrt(weighted_mse(y_train, y_pred_default, w_test))

print(f"\n默认参数 RMSE: {default_rmse:.4f}")
print(f"优化后 RMSE: {test_rmse:.4f}")
print(f"提升: {(default_rmse - test_rmse):.4f} ({(1 - test_rmse / default_rmse) * 100:.2f}%)")
print(f"\n默认参数 MAPE: {default_mape:.2f}%")
print(f"优化后 MAPE: {test_mape:.2f}%")
print(f"\n默认参数 加权RMSE: {default_weighted_rmse:.4f}")
print(f"优化后 加权RMSE: {test_weighted_rmse:.4f}")

# ==================== 8. 可视化 ====================
print("\n8. 生成可视化图表...")

fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 1. 优化历史
ax1 = axes[0, 0]
optimization_history = study.trials_dataframe()
ax1.plot(optimization_history['value'], 'b-', alpha=0.5, label='每次试验')
ax1.plot(optimization_history['value'].cummin(), 'r-', linewidth=2, label='最佳值')
ax1.set_xlabel('Trials')
ax1.set_ylabel('Weighted RMSE')
ax1.set_title('Optimization History')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. 参数重要性
ax2 = axes[0, 1]
importance = optuna.importance.get_param_importances(study)
params_names = list(importance.keys())
params_importance = list(importance.values())
y_pos = np.arange(len(params_names))
ax2.barh(y_pos, params_importance)
ax2.set_yticks(y_pos)
ax2.set_yticklabels(params_names)
ax2.set_xlabel('Importance')
ax2.set_title('Hyperparameter Importance')

# 3. 最佳参数摘要
ax3 = axes[0, 2]
summary_text = f'最佳加权RMSE: {study.best_value:.4f}\n\n最佳参数:\n'
for k, v in list(best_params.items())[:8]:
    summary_text += f'{k}: {v}\n'
ax3.text(0.1, 0.5, summary_text, transform=ax3.transAxes, fontsize=9, verticalalignment='center')
ax3.set_title('Best Parameters')
ax3.axis('off')

# 4. 预测值 vs 真实值
ax4 = axes[1, 0]
# 用散点大小表示权重
sizes = 10 + 50 * (w_test / w_test.max())
scatter = ax4.scatter(y_train, y_pred_test, alpha=0.5, s=sizes, c=w_test, cmap='Reds')
ax4.plot([y_train.min(), y_train.max()], [y_train.min(), y_train.max()], 'r--', lw=2)
ax4.set_xlabel('True Value')
ax4.set_ylabel('Predicted Value')
ax4.set_title(f'Prediction Results (R² = {test_r2:.4f})\nLarger dot = higher weight')
ax4.grid(True, alpha=0.3)
plt.colorbar(scatter, ax=ax4, label='Weights')

# 5. 残差 vs 真实值
ax5 = axes[1, 1]
residuals = y_train - y_pred_test
relative_residuals = residuals / y_train * 100
ax5.scatter(y_train, relative_residuals, alpha=0.5, s=10)
ax5.axhline(y=0, color='r', linestyle='--')
ax5.set_xlabel('True Value')
ax5.set_ylabel('Relative Residual (%)')
ax5.set_title('Relative Residual Distribution')
ax5.grid(True, alpha=0.3)

# 6. 分区间 MAPE
ax6 = axes[1, 2]
ax6.bar(range(len(quantile_results)), quantile_results['MAPE(%)'])
ax6.set_xlabel('y Value Range (small to large)')
ax6.set_ylabel('MAPE (%)')
ax6.set_title('MAPE by Interval')
ax6.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(quantile_results['MAPE(%)']):
    ax6.text(i, v + 0.5, f'{v:.1f}%', ha='center', fontsize=9)

plt.tight_layout()
plt.show()

# ==================== 9. 特征重要性 ====================
print("\n9. 特征重要性分析...")

feature_importance = final_model.feature_importances_
feature_names = [f'Feature_{i}' for i in range(X.shape[1])]
sorted_idx = np.argsort(feature_importance)[::-1][:20]

plt.figure(figsize=(10, 8))
plt.barh(range(20), feature_importance[sorted_idx][::-1])
plt.yticks(range(20), [feature_names[i] for i in sorted_idx][::-1])
plt.xlabel('特征重要性')
plt.title('Top 20 重要特征')
plt.tight_layout()
plt.show()

print("\nTop 10 重要特征:")
for i in range(10):
    idx = sorted_idx[i]
    print(f"  {i + 1}. {feature_names[idx]}: {feature_importance[idx]:.4f}")

# ==================== 10. 保存模型和结果 ====================
print("\n10. 保存模型和优化结果...")

joblib.dump(final_model, 'xgboost_weighted_best_model.pkl')
print("最佳模型已保存: xgboost_weighted_best_model.pkl")

with open('best_params_weighted.json', 'w') as f:
    json.dump(best_params, f, indent=4)
print("最佳参数已保存: best_params_weighted.json")

results_summary = {
    'best_cv_weighted_rmse': float(study.best_value),
    'test_rmse': float(test_rmse),
    'test_weighted_rmse': float(test_weighted_rmse),
    'test_mape': float(test_mape),
    'test_r2': float(test_r2),
    'default_rmse': float(default_rmse),
    'default_weighted_rmse': float(default_weighted_rmse),
    'improvement_rmse': float(default_rmse - test_rmse),
    'improvement_weighted_rmse': float(default_weighted_rmse - test_weighted_rmse),
    'optimization_time': optimization_time,
    'n_trials': len(study.trials),
    'weight_method': 'inverse_y',
    'weight_range': [float(sample_weights.min()), float(sample_weights.max())],
    'best_params': {k: float(v) if isinstance(v, (np.floating,)) else int(v) if isinstance(v, (np.integer,)) else v
                    for k, v in best_params.items()}
}

with open('optimization_results_weighted.json', 'w') as f:
    json.dump(results_summary, f, indent=4)
print("优化结果已保存: optimization_results_weighted.json")

print("\n" + "=" * 80)
print("优化完成！")
print(f"标准 RMSE: {test_rmse:.4f}")
print(f"加权 RMSE（小值权重高）: {test_weighted_rmse:.4f}")
print(f"MAPE: {test_mape:.2f}%")
print("=" * 80)