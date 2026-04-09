from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
import xgboost as xgb
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
import seaborn as sns
data = pd.read_csv("训练数据_可行解.csv")

X = data.iloc[:, 1:92].values
y = data.iloc[:, -1].values

y = np.log(y)



# ======================
# 2 划分训练测试集
# ======================
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def explore_data(X, y, feature_names=None):
    """探索数据特征"""

    if isinstance(X, pd.DataFrame):
        df = X.copy()
    else:
        if feature_names is None:
            feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        df = pd.DataFrame(X, columns=feature_names)

    df['target'] = y

    print("=== 数据概览 ===")
    print(f"样本数: {df.shape[0]}")
    print(f"特征数: {df.shape[1] - 1}")
    print("\n=== 特征统计 ===")
    print(df.describe())

    # 1. 查看特征分布
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    axes = axes.ravel()

    for i, col in enumerate(df.columns[:-1]):
        if i < 9:
            axes[i].hist(df[col], bins=30, edgecolor='black', alpha=0.7)
            axes[i].set_title(f'{col} 分布')
            axes[i].set_xlabel('值')
            axes[i].set_ylabel('频数')

    plt.tight_layout()
    plt.show()

    # 2. 查看特征与目标的相关性
    plt.figure(figsize=(12, 8))
    correlation = df.corr()
    sns.heatmap(correlation, annot=True, cmap='coolwarm', center=0)
    plt.title('特征相关性矩阵')
    plt.show()

    return df

# 使用
df = explore_data(X_train, y_train)
print(df.head())