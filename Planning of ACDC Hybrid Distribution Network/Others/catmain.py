import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from catboost import cv, Pool
from sklearn.model_selection import KFold
# ==================== 准备数据 ====================
# 假设你的数据：X全是0-1特征，y是连续值
# X = pd.read_csv('你的拓扑特征.csv')  # shape (n_samples, n_features)
# y = pd.read_csv('你的目标值.csv')

# 模拟示例数据（你替换为自己的数据）
np.random.seed(42)
# Read data
data = pd.read_csv("100万fop.CSV")

# Split features and labels
X = data.iloc[:, :13 + 33 + 2].values
y = data.iloc[:, -1].values
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
cat_features = list(range(X.shape[1]))
# ==================== 训练模型 ====================
train_pool = Pool(X_train, y_train, cat_features=cat_features)

# 交叉验证
params = {
    'loss_function': 'RMSE',
    'iterations': 1000,
    'depth': 6,
    'learning_rate': 0.03,
    'random_seed': 42,
    'verbose': False
}

cv_results = cv(
    pool=train_pool,
    params=params,
    fold_count=5,                # 5折交叉验证
    early_stopping_rounds=50,
    verbose_eval=100
)

print(f"最佳迭代数: {cv_results['iterations'].values[-1]}")
print(f"最佳RMSE: {cv_results['test-RMSE-mean'].min():.4f}")

# ==================== 2. 用最佳参数训练最终模型 ====================
best_iterations = len(cv_results)  # 从交叉验证得到最佳轮数

final_model = CatBoostRegressor(
    iterations=best_iterations,
    learning_rate=0.03,
    depth=6,
    cat_features=cat_features,
    loss_function='RMSE',
    random_seed=42,
    verbose=100
)

final_model.fit(X_train, y_train, eval_set=(X_test, y_test))

# ==================== 3. 特征重要性分析 ====================
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': final_model.get_feature_importance()
}).sort_values('importance', ascending=False)

print("\n========== 前10重要特征 ==========")
print(feature_importance.head(10))