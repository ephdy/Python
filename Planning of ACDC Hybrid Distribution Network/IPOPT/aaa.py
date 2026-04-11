import math
from _13_nodes_distribution_network import *
import pandas as pd
import time
import numpy as np
import os
import matplotlib.pyplot as plt

def Draw_Grid(U=None,W=None):
    if W is None:
        W = [0] * len(coordinate)
    elif len(W) != len(coordinate):
        W = [0] * len(coordinate)
    # 根据W值设置颜色
    colors = ['blue' if w == 0 else 'red' for w in W]

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

    # 分离坐标
    x = [p[0] for p in coordinate]
    y = [p[1] for p in coordinate]

    # 分别绘制圆点和三角形，以便添加图例
    circle_x = [x[i] for i in range(len(x)) if n__wind[i] == 0 and n__pv[i]==0]
    circle_y = [y[i] for i in range(len(y)) if n__wind[i] == 0 and n__pv[i]==0]
    triangle_x = [x[i] for i in range(len(x)) if n__wind[i] == 1 or n__pv[i]==1]
    triangle_y = [y[i] for i in range(len(y)) if n__wind[i] == 1 or n__pv[i]==1]


    # 设置颜色
    colors = ['blue' if w == 0 else 'red' for w in W]
    colors_circle=[colors[i] for i in range(len(colors)) if n__wind[i] == 0 and n__pv[i]==0]
    colors_triangle =[colors[i] for i in range(len(colors)) if n__wind[i] == 1 or n__pv[i]==1]

    # 绘图
    fig, ax = plt.subplots(figsize=(12, 10))

    edges=[]
    if U is not None:
        for i in range(len(U)):
            if U[i] == 1:
                edges.append(Branch[i])

    # 绘制边
    if edges is not None:
        for edge in edges:
            if isinstance(edge, (tuple, list)) and len(edge) == 2:
                i, j = edge
                # i,j直接从0开始，不需要减1
                xi, yi = coordinate[i]
                xj, yj = coordinate[j]

                # 计算两点之间的距离
                dist = math.sqrt((xj - xi) ** 2 + (yj - yi) ** 2)

                # 如果两点距离较远，使用弯曲曲线
                if dist > q * 1.5:
                    # 计算中点
                    mx = (xi + xj) / 2
                    my = (yi + yj) / 2

                    # 计算垂直方向偏移
                    dx = xj - xi
                    dy = yj - yi
                    perp_x = -dy
                    perp_y = dx
                    length = math.sqrt(perp_x ** 2 + perp_y ** 2)
                    if length > 0:
                        perp_x /= length
                        perp_y /= length

                    # 弯曲程度
                    curvature = dist * 0.3
                    offset_x = perp_x * curvature
                    offset_y = perp_y * curvature

                    # 贝塞尔曲线控制点
                    ctrl1_x = mx - offset_x * 0.5
                    ctrl1_y = my - offset_y * 0.5
                    ctrl2_x = mx + offset_x * 0.5
                    ctrl2_y = my + offset_y * 0.5

                    # 绘制贝塞尔曲线
                    from matplotlib.path import Path
                    import matplotlib.patches as patches

                    verts = [(xi, yi), (ctrl1_x, ctrl1_y), (ctrl2_x, ctrl2_y), (xj, yj)]
                    codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
                    path = Path(verts, codes)
                    patch = patches.PathPatch(path, facecolor='none', edgecolor='gray',
                                              linewidth=1.5, alpha=0.6)
                    ax.add_patch(patch)
                else:
                    # 距离较近，画直线
                    ax.plot([xi, xj], [yi, yj], 'gray', linewidth=1.5, alpha=0.6)

    # # 绘制点
    # ax.scatter(x, y, c=colors, s=200, edgecolors='black', linewidth=1.5, zorder=5)

    # 绘制圆点
    if circle_x:
        ax.scatter(circle_x, circle_y, marker='o', c=colors_circle, s=150,
                    edgecolors='black', linewidth=1.5, zorder=5, label='n[i]=0 (圆点)')

        # 绘制三角形
    if triangle_x:
        ax.scatter(triangle_x, triangle_y, marker='^', c=colors_triangle, s=150,
                    edgecolors='black', linewidth=1.5, zorder=5, label='n[i]=1 (三角形)')

    # 添加标签（节点编号从0开始）
    for i, (xi, yi) in enumerate(coordinate):
        ax.annotate(str(i), (xi, yi), xytext=(8, 8), textcoords='offset points',
                    fontsize=12, fontweight='bold')

    # 设置图形
    ax.grid(True, alpha=0.3)
    margin = q * 0.5
    ax.set_xlim(-margin, max(x) + margin)
    ax.set_ylim(-margin, max(y) + margin)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(f'13 Points (Nodes 0-12, q={q})', fontsize=14)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')

    plt.tight_layout()
    plt.show()
    pass


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

def get_data2(S=None,Edges=None,U=None):



    A=np.zeros((13,33))
    yac=np.zeros(33, dtype=complex)
    ydc = np.zeros(33)
    ex_ac=np.zeros(33)
    ex_dc=np.zeros(33)
    for k in range(33):
        if U[k]==1:
            a,b=Branch[k]
            yac[k]=1/(r_line[a][b][0]+x_line[a][b][0]*1j)
            ydc[k]=1/r_line[a][b][0]
            A[a,k]=1
            A[b,k]=-1
            if S[a]==0 and S[b]==0:
                ex_ac[k]=1
            elif S[a]==1 and S[b]==1:
                ex_dc[k]=1
    Y=A@np.diag(yac*ex_ac-ydc*ex_dc)@A.T
    print(Y)
    return Y

    # G = np.zeros(33)
    # B = np.zeros(33)
    # for k in range(33):
    #     I, J = Branch[k]
    #     R, X = r_line[I][J][0], x_line[I][J][0]
    #     denom = R ** 2 + X ** 2
    #     G[k] = R / denom
    #     B[k] = -X / denom
    # print(G)
    # print(B)
def get_data3(S=None,Edges=None,U=None):
    A = np.zeros((13, 33))
    yac = np.zeros(33, dtype=complex)
    ydc = np.zeros(33)
    for k in range(33):
        a, b = Branch[k]
        A[a, k] = 1
        A[b, k] = -1
        yac[k] = 1 / (r_line[a][b][0] + x_line[a][b][0] * 1j)
        ydc[k] = 1 / r_line[a][b][0]



    N1=np.diag(1-S)
    N2=np.diag(S)
    M=np.diag(U)
    map1=np.zeros((33,13))
    map2 = np.zeros((33, 13))
    for k in range(len(Branch)):
        i, j = Branch[k]
        map1[k, i] = 1
        map2[k, j] = 1
    M1 = np.diag(map1 @ (1-S)) @ np.diag(map2 @ (1-S))
    M2=np.diag(map1 @ S)@np.diag(map2 @ S)
    # print(M1)
    # print(np.sum(M1))
    # print(np.sum(M2))
    # for i in range (len(M1)):
    #     if M12[i]==1:
    #         print(Branch[i])
    map2=np.zeros((33,13))
    A1=A@M@M1
    print(A1)
    Yb1=A1@np.diag(yac)@A1.T

    print(Yb1)


def dict_to_matrix(d, n):
    M = np.zeros((n, n))
    for (i, j), v in d.items():
        M[i, j] = v
    return M

def count_off_diagonal_nonzero_v2(A):
    total_nnz = np.count_nonzero(A)
    print('total_nnz:', total_nnz)
    diag_nnz = np.count_nonzero(np.diag(A))
    print('diag_nnz:', diag_nnz)
    return total_nnz - diag_nnz

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
        Y2=get_data2(S,Edges,U)
        data=get_data(S, Edges)
        G1=dict_to_matrix(data['G'], 13)
        B1=dict_to_matrix(data['B'], 13)
        R1=dict_to_matrix(data['R'], 13)

        Y1=G1+B1*1j
        # for i in range(13):
        #     for j in range(13):
        #         print(Y1[i,j],Y2[i,j])
        get_data3(S,Edges,U)
        end = time.time()
        Draw_Grid(U, S)


        print('求解耗时', time.time() - start)
        start = time.time()

if __name__ == '__main__':
    fun3('./snap/50万样本_1.csv')



