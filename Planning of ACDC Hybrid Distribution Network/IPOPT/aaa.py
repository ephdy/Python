
from _13_nodes_distribution_network import *
import pandas as pd
import time
import numpy as np
import os

def get_data(S,Edges):
    data={}

    # ---------- 1. 线路导纳 ----------
    G = {}
    B = {}
    for i, j in Edges:
        R, X = r_line[i][j][0], x_line[i][j][0]
        denom = R ** 2 + X ** 2
        G[(i, j)] = -R / denom
        B[(i, j)] = X / denom


    # ---------- 2. 节点自导纳 ----------
    for node in nodes:
        Ri = Xi = 0
        for i, j in Edges:
            if i == node and S[i] == 0 and S[j] == 0:
                R, X = r_line[i][j][0], x_line[i][j][0]
                denom = R**2 + X**2
                Ri += R / denom
                Xi += -X / denom

        G[(node, node)] = Ri
        B[(node, node)] = Xi

    data['G'], data['B'] = G, B

    # ---------- 3. 电阻矩阵 ----------
    data['R'] = {
        (i, j): 1 / (r_line[i][j][1] if S[i] != S[j] else r_line[i][j][0])
        for i, j in Edges
    }

    return data

def get_data2(S,Edges,U):
    J=np.ones((13,33))
    a=J@np.diag(U)
    print(a)



def fun3(path):
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
        ex = len(R) + 1
    else:
        ex = 0
    start = time.time()
    for d in range(1):
        S = X[d]
        U = Y[d]
        Gain = Z[d][0]
        Edges = []

        for k in range(len(Branch)):
            if U[k] == 1:
                i, j = Branch[k]
                Edges.append((i, j))
                Edges.append((j, i))
        # get_data2(S,Edges,U)
        get_data(S, Edges)
        print('求解耗时', time.time() - start)
        start = time.time()

if __name__ == '__main__':

    fun3('./snap/50万样本_1.csv')



