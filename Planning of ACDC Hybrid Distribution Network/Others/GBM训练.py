import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.metrics import r2_score

# 自定义 R2
def r2_metric(y_true, y_pred):
    return 'r2', r2_score(y_true, y_pred), True  # True 表示越大越好
# =========================
# 1. 数据加载（你自己替换）


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

# =========================
# 3. 模型参数（你的参数）
# =========================
params = {
    'max_depth': 9,
    'num_leaves': 183,
    'min_data_in_leaf': 17,
    'min_child_samples': 10,

    'subsample': 0.8942535486641959,
    'subsample_freq': 5,
    'colsample_bytree': 0.6208036507335116,

    'lambda_l1': 2.544857149867862e-08,
    'lambda_l2': 1.870148561079944e-07,
    'min_split_gain': 0.3793055673982327,

    'learning_rate': 0.017620216315733704,

    'n_estimators': 1500,
    'max_bin': 2,   # 关键：0-1特征
    'boosting_type': 'gbdt',

    'objective': 'regression',
    'metric': 'rmse',

    'verbose': -1,
    'random_state': 42,
    'n_jobs': -1,
    'force_col_wise': True
}

# =========================
# 4. 训练模型
# =========================
model = lgb.LGBMRegressor(**params)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    eval_metric=['rmse', r2_metric],
    callbacks=[
        lgb.early_stopping(stopping_rounds=100),
        lgb.log_evaluation(100)
    ]

)

# =========================
# 5. 预测与评估
# =========================
y_pred = model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae = mean_absolute_error(y_test, y_pred)

print(f"RMSE: {rmse:.6f}")
print(f"MAE : {mae:.6f}")

# =========================
# 6. 保存模型
# =========================
model.booster_.save_model("lgb_model.txt")

# 如果你后面要转 MILP，这个文件会用到