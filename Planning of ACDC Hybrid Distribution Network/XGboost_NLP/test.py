import pandas as pd
import numpy as np
import random

def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')

data1 = pd.read_csv('节点类型.csv')
data2 = pd.read_csv('10万样本_蓄水池.csv')
X = data1.iloc[:, :13].values.tolist()
Y = data2.iloc[:, :33].values.tolist()
count=0
Gain=[0.8, 0.9, 0.96, 1, 1.08, 1.1, 1.1199999999999999, 1.2, 1.26, 1.32, 1.4, 1.44, 1.54, 1.68]
while count<5e6:
    # random_indices1 = np.random.choice(len(X), size=3, replace=False)
    # S_rows = X[random_indices1]
    # random_indices2 = np.random.choice(len(Y), size=20, replace=False)
    # U_rows = Y[random_indices2]
    S_rows = random.sample(X, 3)
    U_rows =random.sample(Y, 20)
    Gain = random.sample(Gain, 4)
    for i in S_rows:
        for j in U_rows:
            for k in Gain:
                print()
                save_csv(i+j+[k], '新组合.csv')

    count+=3*20*4



