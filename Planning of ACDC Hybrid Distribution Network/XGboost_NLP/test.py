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
tile=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48]
save_csv(tile, '新组合3.csv')
# Gain=[0.8, 0.9, 0.96, 1, 1.08, 1.1, 1.1199999999999999, 1.2, 1.26, 1.32, 1.4, 1.44, 1.54, 1.68]
while count<1e6:
    # random_indices1 = np.random.choice(len(X), size=3, replace=False)
    # S_rows = X[random_indices1]
    # random_indices2 = np.random.choice(len(Y), size=20, replace=False)
    # U_rows = Y[random_indices2]
    S_rows = random.sample(X, 3)
    U_rows =random.sample(Y, 20)
    # Gain = random.sample(Gain, 4)
    for i in S_rows:
        for j in U_rows:
            for k in [0,0.1]:
                for l in [0.2,0.1]:
                    save_csv(i+j+[k,l], '新组合3.csv')

    count+=3*20*4



