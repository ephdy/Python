import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.datasets import make_regression
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
import matplotlib.pyplot as plt
import warnings
import gc
import json
import time

warnings.filterwarnings('ignore')

print("=" * 80)
print("Optuna + XGBoost 回归优化完整方案")
print("=" * 80)

# ==================== 1. 准备数据 ====================
print("\n1. 准备数据...")

data = pd.read_csv("训练数据_可行解1.csv")

X = data.iloc[:, 1:-5].values
y = data.iloc[:, -5].values
print(len(X[0]))
y = (y - 7e7) /1.2e8
# y=(y-9e3)/2.3e4

y = np.log(y)

# 划分数据集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"训练集大小: {X_train.shape}")
print(f"测试集大小: {X_test.shape}")

# ==================== 2. 定义目标函数 ====================
print("\n2. 定义Optuna目标函数...")


def objective(trial):
    """
    Optuna目标函数
    每个trial尝试一组超参数，返回交叉验证分数
    """

    # 定义超参数搜索空间
    params = {
        # 核心参数
        'n_estimators': trial.suggest_int('n_estimators', 50, 8000, step=50),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),

        # 采样参数（防止过拟合）
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'colsample_bylevel': trial.suggest_float('colsample_bylevel', 0.6, 1.0),

        # 正则化参数
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),

        # 树结构参数
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),

        # 性能优化参数
        'tree_method': 'hist',  # 直方图算法
        'max_bin': trial.suggest_int('max_bin', 128, 512, step=64),
        'n_jobs': 1,  # 单线程避免冲突

        # 固定参数
        'random_state': 42,
        'objective': 'reg:squarederror',
        'verbosity': 0
    }

    # 创建模型
    model = xgb.XGBRegressor(**params)

    # 使用交叉验证评估
    try:
        cv_scores = cross_val_score(
            model, X_train, y_train,
            cv=5,  # 5折交叉验证
            scoring='neg_root_mean_squared_error',
            n_jobs=1  # 单线程
        )
        rmse = -np.mean(cv_scores)

        # 可选：添加早停提示（如果训练时间过长）
        if trial.should_prune():
            raise optuna.TrialPruned()

        return rmse

    except Exception as e:
        print(f"Trial失败: {e}")
        return float('inf')


# ==================== 3. 配置并运行优化 ====================
print("\n3. 配置并运行Optuna优化...")

# 创建Optuna研究
study = optuna.create_study(
    direction='minimize',  # 最小化RMSE
    sampler=TPESampler(seed=42),  # TPE采样器
    pruner=MedianPruner(  # 中位数剪枝器
        n_startup_trials=10,
        n_warmup_steps=20,
        interval_steps=1
    ),
    study_name='xgboost_optimization',
    storage=None  # 使用内存存储（不保存到文件）
)

# 记录开始时间
start_time = time.time()

# 执行优化
print("\n开始优化...")
print("=" * 60)

# 方法1：使用优化函数（推荐）
study.optimize(
    objective,
    n_trials=50,  # 50次试验
    n_jobs=1,  # 单线程
    show_progress_bar=True,  # 显示进度条
    catch=(Exception,)  # 捕获异常继续运行
)

# 计算优化时间
optimization_time = time.time() - start_time

print(f"\n优化完成！总耗时: {optimization_time:.2f} 秒")

# ==================== 4. 查看优化结果 ====================
print("\n4. 优化结果分析")
print("=" * 60)

print(f"\n最佳试验编号: {study.best_trial.number}")
print(f"最佳CV RMSE: {study.best_value:.4f}")
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
    n_jobs=-1,  # 最终模型可以使用多线程
    verbosity=0
)

# 训练最终模型
final_model.fit(X_train, y_train)

# 预测
y_pred_train = final_model.predict(X_train)
y_pred_test = final_model.predict(X_test)

# 计算指标
train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
test_mae = mean_absolute_error(y_test, y_pred_test)
test_r2 = r2_score(y_test, y_pred_test)

print(f"\n训练集RMSE: {train_rmse:.4f}")
print(f"测试集RMSE: {test_rmse:.4f}")
print(f"测试集MAE: {test_mae:.4f}")
print(f"测试集R²: {test_r2:.4f}")

# ==================== 6. 对比默认参数 ====================
print("\n6. 对比默认参数模型...")

default_model = xgb.XGBRegressor(random_state=42, objective='reg:squarederror')
default_model.fit(X_train, y_train)
y_pred_default = default_model.predict(X_test)
default_rmse = np.sqrt(mean_squared_error(y_test, y_pred_default))

print(f"默认参数模型RMSE: {default_rmse:.4f}")
print(f"优化后模型RMSE: {test_rmse:.4f}")
print(f"提升: {(default_rmse - test_rmse):.4f} ({(1 - test_rmse / default_rmse) * 100:.2f}%)")

# ==================== 7. 可视化优化过程 ====================
print("\n7. 生成可视化图表...")

# 创建图表
fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 1. 优化历史
ax1 = axes[0, 0]
optimization_history = study.trials_dataframe()
ax1.plot(optimization_history['value'], 'b-', alpha=0.5, label='每次试验')
ax1.plot(optimization_history['value'].cummin(), 'r-', linewidth=2, label='最佳值')
ax1.set_xlabel('试验次数')
ax1.set_ylabel('RMSE')
ax1.set_title('优化历史')
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
ax2.set_xlabel('重要性')
ax2.set_title('超参数重要性')

# 3. 学习曲线
ax3 = axes[0, 2]
# 获取最佳试验的完整历史
best_trial = study.best_trial
ax3.text(0.5, 0.5, f'最佳RMSE: {study.best_value:.4f}\n\n最佳参数:\n' +
         '\n'.join([f'{k}: {v}' for k, v in list(best_params.items())[:5]]),
         ha='center', va='center', transform=ax3.transAxes, fontsize=10)
ax3.set_title('最佳参数摘要')
ax3.axis('off')

# 4. 预测值与真实值对比
ax4 = axes[1, 0]
ax4.scatter(y_test, y_pred_test, alpha=0.5, s=10)
ax4.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
ax4.set_xlabel('真实值')
ax4.set_ylabel('预测值')
ax4.set_title(f'预测效果 (R² = {test_r2:.4f})')
ax4.grid(True, alpha=0.3)

# 5. 残差分布
ax5 = axes[1, 1]
residuals = y_test - y_pred_test
ax5.hist(residuals, bins=30, edgecolor='black', alpha=0.7)
ax5.axvline(x=0, color='r', linestyle='--', linewidth=2)
ax5.set_xlabel('残差')
ax5.set_ylabel('频次')
ax5.set_title('残差分布')
ax5.grid(True, alpha=0.3)

# 6. 训练时间分布
ax6 = axes[1, 2]
if 'duration' in optimization_history.columns:
    durations = optimization_history['duration'].dropna()
    ax6.hist(durations, bins=20, edgecolor='black', alpha=0.7)
    ax6.set_xlabel('训练时间 (秒)')
    ax6.set_ylabel('频次')
    ax6.set_title('每次试验的训练时间分布')
    ax6.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# ==================== 8. 特征重要性 ====================
print("\n8. 特征重要性分析...")

# 获取特征重要性
feature_importance = final_model.feature_importances_
feature_names = [f'Feature_{i}' for i in range(X.shape[1])]

# 排序
sorted_idx = np.argsort(feature_importance)[::-1][:20]  # Top 20

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

# ==================== 9. 保存模型和结果 ====================
print("\n9. 保存模型和优化结果...")

# 保存模型
import joblib

joblib.dump(final_model, 'xgboost_optuna_best_model.pkl')
print("最佳模型已保存: xgboost_optuna_best_model.pkl")

# 保存最佳参数
with open('best_params.json', 'w') as f:
    json.dump(best_params, f, indent=4)
print("最佳参数已保存: best_params.json")

# 保存优化结果摘要
results_summary = {
    'best_rmse': float(study.best_value),
    'test_rmse': float(test_rmse),
    'test_mae': float(test_mae),
    'test_r2': float(test_r2),
    'default_rmse': float(default_rmse),
    'improvement': float(default_rmse - test_rmse),
    'improvement_percent': float((1 - test_rmse / default_rmse) * 100),
    'optimization_time': optimization_time,
    'n_trials': len(study.trials),
    'best_params': {k: float(v) if isinstance(v, (np.float32, np.float64)) else v
                    for k, v in best_params.items()}
}

with open('optimization_results.json', 'w') as f:
    json.dump(results_summary, f, indent=4)
print("优化结果已保存: optimization_results.json")

# ==================== 10. 高级功能：并行优化 ====================
print("\n10. 高级功能示例...")


def advanced_optimization():
    """
    高级优化功能：
    1. 自定义剪枝
    2. 多目标优化
    3. 并行优化
    """

    print("\n高级优化选项:")

    # 1. 自定义剪枝器
    from optuna.pruners import HyperbandPruner

    study_advanced = optuna.create_study(
        direction='minimize',
        sampler=TPESampler(seed=42),
        pruner=HyperbandPruner(
            min_resource=1,
            max_resource=100,
            reduction_factor=3
        )
    )

    # 2. 带早停的目标函数
    def objective_with_early_stopping(trial):
        """支持早停的目标函数"""

        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'random_state': 42,
            'objective': 'reg:squarederror',
            'tree_method': 'hist',
            'verbosity': 0
        }

        # 使用早停
        X_train_sub, X_val, y_train_sub, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42
        )

        model = xgb.XGBRegressor(**params)

        # 使用早停训练
        model.fit(
            X_train_sub, y_train_sub,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )

        # 预测
        y_pred = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))

        return rmse

    print("  - 支持早停的优化")
    print("  - Hyperband剪枝策略")
    print("  - 可扩展到多目标优化")


advanced_optimization()

# ==================== 11. 使用建议 ====================
print("\n" + "=" * 80)
print("使用建议和最佳实践")
print("=" * 80)

recommendations = """
1. 优化策略:
   - 先用少量试验(20-30)快速探索
   - 根据重要性调整搜索空间
   - 增加试验次数(50-100)获得最佳结果

2. 内存优化:
   - 设置 n_jobs=1 避免内存冲突
   - 使用 tree_method='hist' 减少内存
   - 大数据集考虑采样

3. 时间优化:
   - 使用早停减少训练时间
   - 适当减少交叉验证折数
   - 使用剪枝器提前终止差的试验

4. 参数调优顺序:
   - 先调核心参数: n_estimators, max_depth, learning_rate
   - 再调采样参数: subsample, colsample_bytree
   - 最后调正则化: reg_alpha, reg_lambda

5. 保存和加载:
   - 使用 joblib 保存模型
   - 保存最佳参数到JSON
   - 记录优化过程供分析
"""

print(recommendations)

# ==================== 12. 加载和使用已保存的模型 ====================
print("\n示例: 加载和使用已保存的模型")
print("=" * 60)


def load_and_predict():
    """加载已保存的模型进行预测"""

    # 加载模型
    model = joblib.load('xgboost_optuna_best_model.pkl')

    # 加载参数
    with open('best_params.json', 'r') as f:
        params = json.load(f)

    print("加载的模型参数:")
    for k, v in list(params.items())[:5]:
        print(f"  {k}: {v}")

    # 对新数据进行预测
    # new_data = ... # 您的新数据
    # predictions = model.predict(new_data)

    print("\n模型已就绪，可以进行预测")


load_and_predict()

print("\n" + "=" * 80)
print("Optuna优化完成！")
print("=" * 80)