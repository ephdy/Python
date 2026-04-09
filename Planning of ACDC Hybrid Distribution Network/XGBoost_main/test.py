from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
import xgboost as xgb
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
data = pd.read_csv("训练数据_可行解.csv")

X = data.iloc[:, 1:92].values
y = data.iloc[:, -1].values
y = (y - 7e7) /1.2e8
y = np.log(y)


# ======================
# 2 划分训练测试集
# ======================
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
# 定义参数网格
param_grid = {
    'max_depth': [6, 8, 10, 12],
    'learning_rate': [0.01, 0.03, 0.05, 0.1],
    'n_estimators': [500, 1000, 2000],
    'subsample': [0.7, 0.8, 0.9, 1.0],
    'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
    'min_child_weight': [1, 3, 5],
    'gamma': [0, 0.1, 0.2],
    'reg_alpha': [0, 0.1, 1],
    'reg_lambda': [1, 2, 3]
}

# 创建XGBoost回归器
xgb_model = xgb.XGBRegressor(objective='reg:squarederror', tree_method='hist')

# 随机搜索（更高效）
random_search = RandomizedSearchCV(
    xgb_model,
    param_distributions=param_grid,
    n_iter=50,  # 尝试50种组合
    cv=5,
    scoring='r2',
    n_jobs=-1,
    verbose=1,
    random_state=42
)

random_search.fit(X_train, y_train)

print("最佳参数:", random_search.best_params_)
print("最佳R²:", random_search.best_score_)

# 使用最佳参数
best_model = random_search.best_estimator_
y_pred_best = best_model.predict(X_test)