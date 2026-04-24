import gurobipy as gb
import numpy as np
import pandas as pd
import os
from _13_nodes_distribution_network import *
1
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

def fun3(path):
    data1 = pd.read_csv(path)
    X = data1.iloc[:, :13].values
    Y = data1.iloc[:, 13:33 + 13].values
    Z = data1.iloc[:, 33 + 13:].values
    print(X.shape, Y.shape, Z.shape)

    for d in range(1):
        S = X[d]
        U = Y[d]
        Edges = []

        for k in range(len(Branch)):
            if U[k] == 1:
                i, j = Branch[k]
                Edges.append((i, j))
                Edges.append((j, i))
        return get_data(S, Edges),U

def convert(sparse_dict):
    # 自动找出最大行索引和最大列索引
    rows = [key[0] for key in sparse_dict.keys()]
    cols = [key[1] for key in sparse_dict.keys()]
    max_row = max(rows) + 1  # +1 因为索引从0开始
    max_col = max(cols) + 1

    # 创建零矩阵并填充
    matrix = np.zeros((max_row, max_col))
    for (row, col), value in sparse_dict.items():
        matrix[row, col] = value

    print(f"矩阵维度: {matrix.shape}")
    print(matrix)
    return matrix
G0,p=fun3('./snap/50万样本_1.csv')
G=convert(G0['G'])

print(p)
m = gb.Model("mip1")

b = m.addMVar(shape=(33, 13), lb=-gb.GRB.INFINITY,name="b")
a = m.addMVar(shape=(13, 33) , name="a")

m.addConstr(a@np.diag(p)@b==G)
m.setObjective(2, gb.GRB.MINIMIZE)
m.Params.NonConvex = 2
m.optimize()
if m.status == gb.GRB.INFEASIBLE:
    print("模型不可行，正在计算 IIS...")
    m.computeIIS()  # 计算不可约不一致子系统
    m.write("model_iis.ilp")  # 导出为 ILP 文件
    print("IIS 已导出至 'model_iis.ilp'")