import Box3 as B
import pandas as pd

import _13_nodes_distribution_network as H
path='./snap/50万样本_1.csv'
base, ext = path.rsplit('.', 1)
new_path = base + '结果' + '.' + ext
data1 = pd.read_csv(path)
X = data1.iloc[:, :13].values
Y = data1.iloc[:, 13:33 + 13].values
Z = data1.iloc[:, 33 + 13:].values
print(X.shape, Y.shape, Z.shape)
# print(X[94])
# print(Y[94])


for d in range(len(Z)):
    S = X[d]
    U = Y[d]
    Gain = Z[d][0]
    Edges = []
    print(Gain)
    for k in range(len(H.Branch)):
        if U[k] == 1:
            i, j = H.Branch[k]
            Edges.append((i, j))
            Edges.append((j, i))

    # B.Draw_Grid(a, S)
    obj,Model,Solver=B.GAMS_Solve(S, Edges, Gain)
    data=list(S) + list(U) + [Gain] + [Model,Solver,obj]
    print(d, B.GAMS_Solve(S, Edges, Gain))
    B.save_csv(data, new_path)
