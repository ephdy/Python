import numpy as np
import pandas as pd
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
from skopt import BayesSearchCV
from skopt.space import Real, Integer, Categorical
from skopt.utils import use_named_args
import warnings

warnings.filterwarnings('ignore')

# 设置随机种子保证可重复性
RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# ==================== 1. 准备数据 ====================
print("=" * 60)
print("1. 准备数据")
print("=" * 60)


data = pd.read_csv("受限邻接矩阵可行解.CSV")

X = data.iloc[:,:33].values
y = data.iloc[:, -4].values
print(len(X[0]))
# y = (y - 7e7) /1.2e8
# y=(y-9e3)/2.3e4

y = np.log(y)

# 分割训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE
)

print(f"训练集大小: {X_train.shape}")
print(f"测试集大小: {X_test.shape}")
print(f"特征数量: {X_train.shape[1]}")

# ==================== 2. 定义搜索空间 ====================
print("\n" + "=" * 60)
print("2. 定义贝叶斯优化搜索空间")
print("=" * 60)

# 定义超参数搜索空间
search_spaces = {
    # 核心参数
    'n_estimators': Integer(3000, 30000),  # 树的数量
    'max_depth': Integer(3, 15),  # 树的最大深度
    'learning_rate': Real(0.01, 0.3, 'log-uniform'),  # 学习率

    # 正则化参数
    'subsample': Real(0.1, 1.0),  # 行采样比例
    'colsample_bytree': Real(0.1, 1.0),  # 列采样比例
    'colsample_bylevel': Real(0.1, 1.0),  # 层级列采样

    # L1和L2正则化
    'reg_alpha': Real(1e-5, 10, 'log-uniform'),  # L1正则化
    'reg_lambda': Real(1e-5, 10, 'log-uniform'),  # L2正则化

    # 其他参数
    'min_child_weight': Integer(1, 10),  # 叶子节点最小权重
    'gamma': Real(1e-5, 5, 'log-uniform'),  # 分裂所需的最小损失减少
}

print("搜索空间定义完成，包含以下参数:")
for param, space in search_spaces.items():
    print(f"  - {param}: {space}")

# ==================== 3. 创建基础模型 ====================
print("\n" + "=" * 60)
print("3. 创建XGBoost回归模型")
print("=" * 60)

# 基础模型配置
xgb_model = xgb.XGBRegressor(
    objective='reg:squarederror',
    random_state=RANDOM_STATE,
    n_jobs=-1,  # 使用所有CPU核心
    verbosity=0  # 减少输出
)

print("基础模型创建完成")

# ==================== 4. 贝叶斯优化 ====================
print("\n" + "=" * 60)
print("4. 执行贝叶斯优化")
print("=" * 60)

# 创建BayesSearchCV对象
bayes_search = BayesSearchCV(
    estimator=xgb_model,
    search_spaces=search_spaces,
    n_iter=200,  # 迭代次数
    cv=5,  # 5折交叉验证
    scoring='neg_mean_squared_error',  # 优化目标（负MSE）
    n_jobs=-1,  # 并行计算
    verbose=1,  # 输出详细信息
    random_state=RANDOM_STATE,
    refit=True  # 找到最佳参数后重新训练
)

# 执行贝叶斯优化
print("开始贝叶斯优化搜索...")
bayes_search.fit(X_train, y_train)

# ==================== 5. 查看优化结果 ====================
print("\n" + "=" * 60)
print("5. 贝叶斯优化结果")
print("=" * 60)

# 最佳参数
print("\n最佳超参数组合:")
best_params = bayes_search.best_params_
for param, value in best_params.items():
    print(f"  {param}: {value:.4f}" if isinstance(value, float) else f"  {param}: {value}")

# 最佳分数
print(f"\n最佳交叉验证分数 (负MSE): {bayes_search.best_score_:.4f}")
print(f"对应的RMSE: {np.sqrt(-bayes_search.best_score_):.4f}")

# ==================== 6. 评估最佳模型 ====================
print("\n" + "=" * 60)
print("6. 评估最佳模型")
print("=" * 60)

# 获取最佳模型
best_model = bayes_search.best_estimator_

# 在测试集上预测
y_pred = best_model.predict(X_test)

# 计算评估指标
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\n测试集评估结果:")
print(f"  MSE: {mse:.4f}")
print(f"  RMSE: {rmse:.4f}")
print(f"  MAE: {mae:.4f}")
print(f"  R²: {r2:.4f}")

# ==================== 7. 对比默认参数模型 ====================
print("\n" + "=" * 60)
print("7. 对比默认参数模型")
print("=" * 60)

# 创建默认参数的模型
default_model = xgb.XGBRegressor(
    objective='reg:squarederror',
    random_state=RANDOM_STATE,
    n_jobs=-1
)

# 训练默认模型
default_model.fit(X_train, y_train)
y_pred_default = default_model.predict(X_test)

# 计算默认模型指标
mse_default = mean_squared_error(y_test, y_pred_default)
rmse_default = np.sqrt(mse_default)
r2_default = r2_score(y_test, y_pred_default)

print("\n默认参数模型:")
print(f"  RMSE: {rmse_default:.4f}")
print(f"  R²: {r2_default:.4f}")

print("\n优化后模型:")
print(f"  RMSE: {rmse:.4f}")
print(f"  R²: {r2:.4f}")

print(f"\n性能提升:")
print(f"  RMSE降低: {(rmse_default - rmse):.4f} ({(1 - rmse / rmse_default) * 100:.2f}%)")
print(f"  R²提升: {(r2 - r2_default):.4f} ({((r2 - r2_default) / abs(r2_default)) * 100:.2f}%)")

# ==================== 8. 特征重要性分析 ====================
print("\n" + "=" * 60)
print("8. 特征重要性分析")
print("=" * 60)

# 获取特征重要性
feature_importance = best_model.feature_importances_
feature_names = [f"Feature_{i}" for i in range(X.shape[1])]

# 排序
sorted_idx = np.argsort(feature_importance)[::-1]
print("\nTop 10 重要特征:")
for i in range(min(10, len(sorted_idx))):
    idx = sorted_idx[i]
    print(f"  {i + 1}. {feature_names[idx]}: {feature_importance[idx]:.4f}")

# ==================== 9. 优化过程可视化 ====================
print("\n" + "=" * 60)
print("9. 优化过程可视化")
print("=" * 60)

import matplotlib.pyplot as plt
from skopt.plots import plot_convergence, plot_objective

# 绘制收敛曲线
fig, ax = plt.subplots(1, 2, figsize=(15, 5))

# 收敛图
plot_convergence(bayes_search.optimizer_results_, ax=ax[0])
ax[0].set_title('贝叶斯优化收敛曲线')
ax[0].set_xlabel('迭代次数')
ax[0].set_ylabel('目标函数值')

# 最佳分数随迭代变化
iterations = range(1, len(bayes_search.cv_results_['mean_test_score']) + 1)
best_scores = np.maximum.accumulate(-bayes_search.cv_results_['mean_test_score'])
ax[1].plot(iterations, best_scores, 'b-', linewidth=2)
ax[1].set_title('最佳RMSE随迭代变化')
ax[1].set_xlabel('迭代次数')
ax[1].set_ylabel('最佳RMSE')
ax[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# ==================== 10. 保存模型 ====================
print("\n" + "=" * 60)
print("10. 保存最佳模型")
print("=" * 60)

import joblib

# 保存模型
model_filename = 'xgboost_best_model.pkl'
joblib.dump(best_model, model_filename)
print(f"模型已保存为: {model_filename}")

# 保存参数信息
params_info = {
    'best_params': best_params,
    'best_score': bayes_search.best_score_,
    'test_rmse': rmse,
    'test_r2': r2
}

params_filename = 'best_params_info.pkl'
joblib.dump(params_info, params_filename)
print(f"参数信息已保存为: {params_filename}")

print("\n" + "=" * 60)
print("优化完成！")
print("=" * 60)