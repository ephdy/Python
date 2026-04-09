import Box3 as B
import pandas as pd
import time
import _13_nodes_distribution_network as H
import numpy as np

def fun1():
    data1 = pd.read_csv('节点类型.csv')
    data2 = pd.read_csv('受限邻接矩阵结果.CSV')
    X = data1.iloc[:, :13].values
    Y = data2.iloc[:, :33].values
    # print(X[94])
    # print(Y[94])
    S = X[232]
    start = time.time()
    for d in range(1):
        a = Y[d]
        Edges = []
        for k in range(len(H.Branch)):
            if a[k] == 1:
                i, j = H.Branch[k]
                Edges.append((i, j))
                Edges.append((j, i))

        # Draw_Grid(a,S)
        # print(c)
        for j in np.arange(1.1, 1.9, 0.05):
            print(d, j, B.GAMS_Solve(S, Edges, float(j)))

        print('求解耗时', time.time() - start)
        start = time.time()

def fun2():
    data1 = pd.read_csv('./snap/50万样本.csv')
    X = data1.iloc[:, :13].values
    Y = data1.iloc[:, 13:33 + 13].values
    Z = data1.iloc[:, 33 + 13:].values
    print(X.shape, Y.shape, Z.shape)


    start = time.time()
    for d in range(len(Z)):
        S = X[d]
        a = Y[d]
        Gain = Z[d][0]
        Edges = []
        print(Gain)
        for k in range(len(H.Branch)):
            if a[k] == 1:
                i, j = H.Branch[k]
                Edges.append((i, j))
                Edges.append((j, i))

        # B.Draw_Grid(a, S)
        print(d, B.GAMS_Solve(S, Edges, Gain))

        print('求解耗时', time.time() - start)
        start = time.time()

if __name__ == '__main__':
    fun2()