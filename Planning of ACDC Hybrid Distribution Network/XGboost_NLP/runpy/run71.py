import Box3 as B
import pandas as pd
import os
import _13_nodes_distribution_network as H
path='../snap/50万样本_71.csv'
base, ext = path.rsplit('.', 1)
new_path = base + '结果' + '.' + ext
data1 = pd.read_csv(path)
X = data1.iloc[:, :13].values
Y = data1.iloc[:, 13:33 + 13].values
Z = data1.iloc[:, 33 + 13:].values
print(X.shape, Y.shape, Z.shape)
if os.path.exists(new_path):
    data2 = pd.read_csv(new_path)
    R = data2.iloc[:, :2].values
    ex = len(R)+1
else:
    ex = 0

for d in range(ex, len(Z)):
    S = X[d]
    U = Y[d]
    Gain = Z[d][0]
    Edges = []

    for k in range(len(H.Branch)):
        if U[k] == 1:
            i, j = H.Branch[k]
            Edges.append((i, j))
            Edges.append((j, i))

    # B.Draw_Grid(a, S)
    try:
        obj, Model, Solver = B.GAMS_Solve(S, Edges, Gain)
    except Exception as e:
        print(f"GAMS求解出错: {e}")
        obj, Model, Solver = 'None', 'None', 'None'  # 或设置默认值
    data=list(S) + list(U) + [Gain] + [Model,Solver,obj]
    B.save_csv(data, new_path)
