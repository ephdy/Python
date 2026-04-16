import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.metrics import r2_score

# def r2_score(y, y_pred):
#     ss_res = np.sum((y - y_pred) ** 2)
#     ss_tot = np.sum((y - np.mean(y)) ** 2)
#
#     r2 = 1 - ss_res / ss_tot
#     return r2

def r2_metric(preds, dtrain):
    labels = dtrain.get_label()
    r2 = r2_score(labels, preds)
    return 'r2', r2

# data = pd.read_csv("可行解.CSV")
# data = pd.read_csv("Loss样本.CSV")
data = pd.read_csv("新样本可行解.CSV")

X = data.iloc[:,:13+33+2].values
y = data.iloc[:, -1].values
# print(len(X[0]))
print(len(X[0]))
print(y[0])
# y = (y - 7e7) /1.2e8
# y=(y-9e3)/2.3e4

# y = np.log(y)

# X_inverse = 1 - X
# 
# # 水平拼接（按列拼接）
# X = np.hstack([X, X_inverse])

# ======================
# 2 划分训练测试集
# ======================
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=3)

# ======================


# ==========================
# 3 转换为DMatrix
# ==========================

dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

# ==========================
# 4 设置参数
# ==========================




# params = {
#     n_estimators: 800 0.9606
#   max_depth: 6
#   learning_rate: 0.29588562703937105
#   subsample: 0.936297660782539
#   colsample_bytree: 0.6777041290159844
#   colsample_bylevel: 0.962238887453326
#   reg_alpha: 0.002956012917865913
#   reg_lambda: 7.937225325439937e-08
#   min_child_weight: 8
#   gamma: 0.0009445851721057289
#   max_bin: 128
# }

params={
    # 'n_estimators': 650 0.9723
    'max_depth': 7,
    'learning_rate': 0.23667621148204962,
    'subsample': 0.6954725695655679,
    'colsample_bytree': 0.9230046269382367,
    'colsample_bylevel': 0.7992083353426866,
    'reg_alpha': 0.14397237130088078,
    'reg_lambda': 8.21245986343601e-05,
    'min_child_weight': 6,
    'gamma': 0.028830640586591783,
    'max_bin': 128
}

# params={
#     "max_depth": 8,
#     "learning_rate": 0.03484952134730888,
#     "subsample": 0.8787221369820178,
#     "colsample_bytree": 0.7778603310161449,
#     "colsample_bylevel": 0.884442066285247,
#     "reg_alpha": 0.006268241631561702,
#     "reg_lambda": 8.445847880488229e-07,
#     "min_child_weight": 6,
#     "gamma": 8.476618792715076e-07,
#     "max_bin": 384
# }

# params={
#     # 'n_estimators': 800,0.987
#     'max_depth': 6,
#     'learning_rate': 0.10207683290476766,
#     'subsample': 0.8382018861412898,
#     'colsample_bytree': 0.9985818880837355,
#     'colsample_bylevel': 0.8059215136674683,
#     'reg_alpha': 1.893870655318053e-05,
#     'reg_lambda': 8.11167247614846e-08,
#     'min_child_weight': 7,
#     'gamma': 1.1867056768959225e-06,
#     'max_bin': 320
#
# }
# num_round = 50000

# ==========================
# 5 训练模型
# ==========================
# 创建回调函数
class CustomMetricCallback(xgb.callback.TrainingCallback):
    def __init__(self, dval, y_val, period=500):  # 添加 period 参数
        self.dval = dval
        self.y_val = y_val
        self.period = period

    def after_iteration(self, model, epoch, evals_log):
        # 每 period 轮打印一次
        if (epoch + 1) % self.period == 0:
            y_pred = model.predict(self.dval)
            r2 = r2_score(self.y_val, y_pred)
            print(f"Round {epoch + 1:5d} | Validation R²: {r2:.6f}")
        return False  # False 表示继续训练

model = xgb.train(
    params,
    dtrain,
    # num_boost_round=7050,
    num_boost_round=650,
    evals=[(dtrain, 'train'), (dtest, 'val')],  # 监控数据集

    early_stopping_rounds=50,  # 连续50轮验证集效果没有提升则停止
    verbose_eval=100,  # 每10轮打印一次日志
    callbacks=[CustomMetricCallback(dtest, y_test, period=100)]
)
model.save_model('model1.ubj')
model.save_model('model1.json')
tree_dump = model.get_dump(with_stats=True)
with open('xgboost_trees.txt', 'w', encoding='utf-8') as f:
    for i, tree in enumerate(tree_dump):
        f.write(f"=== Tree {i} ===\n")
        f.write(tree)
        f.write("\n\n")  # 每棵树之间空一行
# ==========================
# 6 预测
# ==========================

y_train_pred=model.predict(dtrain)
y_test_pred=model.predict(dtest)


# x = np.arange(len(y_test))  # 或者 range(len(y1))
# y1=y_test
# y2=y_test_pred
# # 绘制曲线
# plt.figure(figsize=(12, 6))
# # plt.plot(x, y1, label='曲线1', linewidth=1.5)
# # plt.plot(x, y2, label='曲线2', linewidth=1.5)
# plt.scatter(x, y1, label='数据集1', color='blue', alpha=0.3, s=1, rasterized=True)
# plt.scatter(x, y2, label='数据集2', color='red', alpha=0.3, s=1, rasterized=True)
#
# plt.xlabel('数据点索引')
# plt.ylabel('Y值')
# plt.title('两条曲线对比')
# plt.legend()
# plt.grid(True, alpha=0.3)
# plt.tight_layout()
# plt.show()
# ==========================
# 7 计算R²
# ==========================

r2_train = r2_score(y_train, y_train_pred)
r2_test = r2_score(y_test, y_test_pred)

print(f"训练集 R² = {r2_train:.4f}")
print(f"测试集 R² = {r2_test:.4f}")
print(f"差距 = {r2_train - r2_test:.4f}")


def analyze_prediction_bias(y_test, y_pred):
    """分析预测偏差"""

    # 计算偏差统计
    bias = np.mean(y_pred - y_test)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

    print("=== 偏差分析 ===")
    print(f"平均偏差: {bias:.4f}")
    print(f"平均绝对百分比误差 (MAPE): {mape:.2f}%")

    # 绘制偏差图
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # 1. 预测值vs实际值散点图
    axes[0, 0].scatter(y_test, y_pred, alpha=0.5)
    axes[0, 0].plot([y_test.min(), y_test.max()],
                    [y_test.min(), y_test.max()], 'r--', lw=2)
    axes[0, 0].set_xlabel('实际值')
    axes[0, 0].set_ylabel('预测值')
    axes[0, 0].set_title('预测值 vs 实际值')
    axes[0, 0].grid(True, alpha=0.3)

    # 2. 残差分布
    residuals = y_test - y_pred
    axes[0, 1].hist(residuals, bins=30, edgecolor='black', alpha=0.7)
    axes[0, 1].axvline(x=0, color='r', linestyle='--')
    axes[0, 1].set_xlabel('残差')
    axes[0, 1].set_ylabel('频数')
    axes[0, 1].set_title('残差分布')
    axes[0, 1].grid(True, alpha=0.3)

    # 3. 残差vs预测值
    axes[1, 0].scatter(y_pred, residuals, alpha=0.5)
    axes[1, 0].axhline(y=0, color='r', linestyle='--')
    axes[1, 0].set_xlabel('预测值')
    axes[1, 0].set_ylabel('残差')
    axes[1, 0].set_title('残差 vs 预测值')
    axes[1, 0].grid(True, alpha=0.3)

    # 4. Q-Q图
    stats.probplot(residuals, dist="norm", plot=axes[1, 1])
    axes[1, 1].set_title('残差Q-Q图')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    return bias, mape

# bias, mape = analyze_prediction_bias(y_test, y_pred)
