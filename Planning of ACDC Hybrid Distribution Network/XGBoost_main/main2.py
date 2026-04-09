import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

print("=" * 80)
print("LightGBM 训练代码")
print("=" * 80)

# 1. 读取数据

data = pd.read_csv("训练数据_可行解1.csv")

X = data.iloc[:, 1:1+13+78].values
y = data.iloc[:, -5].values
print(len(X[0]))
y = (y - 7e7) /1.2e8
# y=(y-9e3)/2.3e4

y = np.log(y)

print(f"特征形状: {X.shape}")
print(f"目标形状: {y.shape}")
print(f"目标值范围: [{y.min():.4f}, {y.max():.4f}]")

#

# 4. 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\n训练集大小: {X_train.shape}")
print(f"测试集大小: {X_test.shape}")

# 5. 创建LightGBM数据集
train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

# 6. 设置参数
params = {
    # 任务类型
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',

    # 核心参数
    'num_leaves': 13+78,  # 叶子节点数（控制复杂度）
    'max_depth': -1,  # 树的最大深度（-1表示无限制）
    'learning_rate': 0.01,  # 学习率
    'n_estimators': 30000,  # 迭代次数

    # 正则化参数
    'reg_alpha': 0.2,  # L1正则化
    'reg_lambda': 0.4,  # L2正则化

    # 采样参数
    'subsample': 0.8,  # 行采样
    'colsample_bytree': 0.8,  # 列采样
    'subsample_freq': 1,  # 采样频率

    # 其他参数
    'min_child_samples': 10,  # 叶子节点最小样本数
    'min_child_weight': 0.0006,  # 叶子节点最小权重
    'verbosity': -1,  # 输出信息
    'seed': 42,  # 随机种子

    # 性能优化
    'n_jobs': -1,  # 使用所有CPU核心
    'feature_fraction': 0.8,  # 特征采样比例
    'bagging_fraction': 0.8,  # 袋外采样比例
    'bagging_freq': 1,  # 袋外采样频率
}

print("\n模型参数:")
for key, value in params.items():
    print(f"  {key}: {value}")

# 7. 训练模型
print("\n开始训练...")
model = lgb.train(
    params,
    train_data,
    valid_sets=[train_data, test_data],
    valid_names=['train', 'eval'],
    num_boost_round=500,  # 最大迭代次数
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),  # 早停
        lgb.log_evaluation(period=50)  # 每50轮打印一次
    ]
)

print(f"\n最佳迭代次数: {model.best_iteration}")
print(f"最佳分数: {model.best_score['eval']['rmse']:.4f}")

# 8. 预测
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

# 9. 评估
train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
test_mae = mean_absolute_error(y_test, y_pred_test)
test_r2 = r2_score(y_test, y_pred_test)

print("\n" + "=" * 60)
print("模型评估结果")
print("=" * 60)
print(f"训练集 RMSE: {train_rmse:.4f}")
print(f"测试集 RMSE: {test_rmse:.4f}")
print(f"测试集 MAE: {test_mae:.4f}")
print(f"测试集 R²: {test_r2:.4f}")

# 检查过拟合
if test_rmse > train_rmse * 1.1:
    print(f"\n⚠️ 存在过拟合: 测试集RMSE比训练集高{(test_rmse / train_rmse - 1) * 100:.1f}%")
else:
    print(f"\n✅ 模型泛化良好")