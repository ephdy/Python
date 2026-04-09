
from _13_nodes_distribution_network import *
from concurrent.futures import ProcessPoolExecutor
import gurobipy as gb
import numpy as np
import concurrent.futures
import pandas as pd
import csv
from datetime import datetime
import copy
import heapq

def is_tree_adjacency_matrix(U):
    """
    检测对称邻接矩阵是否表示一棵树

    参数:
    U: 对称邻接矩阵 (numpy array)，U[i][j] > 0 表示存在边

    返回:
    (is_tree, message): (是否树, 详细信息)
    """

    # 1. 基本检查
    if not isinstance(U, np.ndarray):
        U = np.array(U)

    n = len(U)  # 节点数

    # 2. 检查矩阵是否为方阵且对称
    if U.shape[0] != U.shape[1]:
        return False, "矩阵不是方阵"

    if not np.allclose(U, U.T):
        return False, "矩阵不是对称的"

    # 3. 统计边数
    edges = []
    edge_count = 0
    for i in range(n):
        for j in range(i + 1, n):  # 只检查上三角避免重复
            if U[i][j] != 0:
                edges.append((i, j))
                edge_count += 1

    # 4. 树的必要条件：边数 = 节点数 - 1
    if edge_count != n - 1:
        return False, f"边数 ({edge_count}) ≠ 节点数-1 ({n - 1})"

    # 5. 使用并查集检测连通性和环
    parent = list(range(n))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        root_x, root_y = find(x), find(y)
        if root_x == root_y:
            return False  # 发现环
        parent[root_x] = root_y
        return True

    # 检查每条边
    for u, v in edges:
        if not union(u, v):
            return False, f"发现环: 边 ({u}, {v}) 创建了循环"

    # 6. 检查是否所有节点都在同一个连通分量中
    roots = set(find(i) for i in range(n))
    if len(roots) > 1:
        return False, f"图不连通，有 {len(roots)} 个连通分量"

    return True, "这是一个有效的树结构"


def encode(solution, n):
    idx = 0

    W_values = solution[idx:idx + n]
    idx += n
    U_values = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            val = solution[idx]
            U_values[i, j] = val
            U_values[j, i] = val
            idx += 1
    C_values = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            val = solution[idx]
            C_values[i, j] = val
            C_values[j, i] = val
            idx += 1
    return list(map(int,W_values)), U_values.astype(int), C_values.astype(int)

def save_csv(data):
    new_df = pd.DataFrame([data])
    new_df.to_csv('抽样数据NEW.CSV', mode='a', header=False, index=False, encoding='utf-8')

def print_variables_by_pattern(model, pattern='P'):
    """
    按模式打印变量值

    参数:
    model: Gurobi模型
    pattern: 变量名包含的字符串，如 'P', 'Q', 'I', 'u'
    """
    print(f"\n包含 '{pattern}' 的变量:")
    print("-" * 50)

    count = 0
    for v in model.getVars():
        if pattern in v.VarName:
            if hasattr(v, 'X'):  # 确保变量有值
                print(f"  {v.VarName} = {v.X:.6f}")
            else:
                print(f"  {v.VarName} = (未求解)")
            count += 1

    if count == 0:
        print(f"  没有找到包含 '{pattern}' 的变量")
    else:
        print(f"  共找到 {count} 个变量")


    print('Obj:', model.objVal)
    if model.Status == gb.GRB.OPTIMAL or model.Status == gb.GRB.SUBOPTIMAL:
        for v in m.getVars():
            if v.VarName.startswith('P_ess'):  # 只打印以P_开头的变量
                print(f"  {v.VarName} = {v.X:.6f}")
    else:
        print("求解失败，无法打印变量值")
        print_variables_by_pattern(model, pattern='E_k')


# 测试不同线程配置
def test_thread_scaling():
    for threads in [1, 2, 4, 8, 0]:  # 0=auto
        model = gb.Model()
        model.Params.Threads = threads
        model.Params.LogToConsole = 0

        start = time.time()
        # 求解你的问题
        solve_time = time.time() - start
        print(f"线程数 {threads}: {solve_time:.2f}秒")

def print_variables_by_pattern(model, pattern='P'):
    """
    按模式打印变量值

    参数:
    model: Gurobi模型
    pattern: 变量名包含的字符串，如 'P', 'Q', 'I', 'u'
    """
    print(f"\n包含 '{pattern}' 的变量:")
    print("-" * 50)

    count = 0
    for v in model.getVars():
        if pattern in v.VarName:
            if hasattr(v, 'X'):  # 确保变量有值
                print(f"  {v.VarName} = {v.X:.6f}")
            else:
                print(f"  {v.VarName} = (未求解)")
            count += 1

    if count == 0:
        print(f"  没有找到包含 '{pattern}' 的变量")
    else:
        print(f"  共找到 {count} 个变量")

def Sampling(Fitness):
    m = gb.Model("mip1")
    # 定义规划变量
    # 定义节点类型变量
    W = m.addVars(n, vtype=gb.GRB.BINARY, name="W")
    m.addConstr(W[0] == 0)  #根节点为交流
    # 定义节点连接变量
    U = m.addVars(n, n, vtype=gb.GRB.BINARY, name="U")
    for i in range(n):
        m.addConstr(U[i, i] == 0)
        for j in range(i+1,n):
            m.addConstr(U[i, j] == U[j, i])
    # 定义线路类型变量
    x = m.addVars(n, n, vtype=gb.GRB.BINARY, name="x")

    #  上层模型约束
    #1 节点连接线路条数约束
    for i in range(n):
        m.addConstr(U.sum('*', i) >= L_min)
        m.addConstr(U.sum('*', i) <= L_max)
    #2 线路选型约束
    '''
    for i in range(n):
        for j in range(i + 1, n):
            m.addConstr(x.sum(i, j, '*') == 1)
            for k in range(k_line):
                m.addConstr(x[i, j, k] == x[j, i, k])
    '''
    # 3 连通性约束
    Virtual_flow = m.addVars(n, n, lb=1 - n, ub=n - 1, vtype=gb.GRB.INTEGER, name="Virtual_flow")
    for i in range(n):
        m.addConstr(Virtual_flow[i, i] == 0)
        for j in range(n):
            if i != j:
                m.addConstr(Virtual_flow[i, j] <= (n - 1) * U[i, j])
                m.addConstr(Virtual_flow[i, j] >= (1 - n) * U[i, j])
                m.addConstr(Virtual_flow[i, j] == -Virtual_flow[j, i])
    m.addConstr(Virtual_flow.sum(0, '*') == n - 1)
    for i in range(1, n):
        m.addConstr(Virtual_flow.sum('*', i) == 1)

    # 定义换流支路
    L = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_L")  # L=|w_i-w_j|
    for i in range(n):
        for j in range(n):
            m.addConstr(L[i, j] >= (W[i] - W[j]))
            m.addConstr(L[i, j] >= (W[j] - W[i]))
            m.addConstr(L[i, j] <= (W[i] + W[j]))
            m.addConstr(L[i, j] <= (2 - W[i] - W[j]))

    # 定义各节点电压
    '''
    V = m.addVars(n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
    V__svc = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="V__svc")
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
    '''
    V2 = m.addVars(n, T, lb=0.95*0.95, ub=1.05*1.05, vtype=gb.GRB.CONTINUOUS, name="V2")
    V2__svc = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="V2__svc")
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(V2__svc[i, j, t] == V2__svc[j, i, t])
    # 支路阻抗
    '''
    r_line = m.addVars(n, n, vtype=gb.GRB.CONTINUOUS, name="r_line")
    x_line = m.addVars(n, n, vtype=gb.GRB.CONTINUOUS, name="x_line")
    for i in range(n):
        m.addConstr(r_line[i, i] == 0)
        m.addConstr(x_line[i, i] == 0)
        for j in range(i + 1,n):
            m.addConstr(r_line[i, j] == r_line[j, i])
            m.addConstr(x_line[i, j] == x_line[j, i])

            m.addConstr(r_line[i, j] >= r__[i][j] - M * L[i, j])
            m.addConstr(r_line[i, j] <= r__[i][j] + M * L[i, j])
            m.addConstr(r_line[i, j] >= r__vsc[i][j] - M * (1 - L[i, j]))
            m.addConstr(r_line[i, j] <= r__vsc[i][j] + M * (1 - L[i, j]))

            m.addConstr(x_line[i, j] >= x__[i][j] - M * L[i, j])
            m.addConstr(x_line[i, j] <= x__[i][j] + M * L[i, j])
            m.addConstr(x_line[i, j] >= x__vsc[i][j] - M * (1 - L[i, j]))
            m.addConstr(x_line[i, j] <= x__vsc[i][j] + M * (1 - L[i, j]))
    '''

    # 定义线路潮流
    P_tran = m.addVars(n, n, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="P_tran")
    Q_tran = m.addVars(n, n, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Q_tran")
    I2=m.addVars(n, n, T, lb=0, vtype=gb.GRB.CONTINUOUS, name="I2")
    z = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="z")
    for i in range(n):
        for j in range(n):
            for t in range(T):
                m.addConstr(I2[i,j,t] <= M * U[i,j])
                m.addConstr(z[i, j, t] <= I2[i, j, t])
                m.addConstr(z[i, j, t] <= 1 * L[i, j])
                m.addConstr(z[i, j, t] >= I2[i, j, t] - 1 * (1 - L[i, j]))
                m.addConstr(z[i, j, t] >= 0)
    for t in range(T):
        for i in range(n):
            m.addConstr(P_tran[i, i, t] == 0)
            m.addConstr(Q_tran[i, i, t] == 0)
            for j in range(i + 1, n):
                if i != j:
                    m.addConstr(P_tran[i,j,t] + P_tran[j,i,t] ==-( r__[i][j]*I2[i,j,t] + 0.2889*z[i,j,t] ))
                    m.addConstr(Q_tran[i, j, t] +Q_tran[j, i, t] == -( x__[i][j]*I2[i,j,t] + 0.7548*z[i,j,t] ))
    # 购电功率
    P_buy = m.addVars(24, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_buy")
    Q_buy = m.addVars(24, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_buy")
    # 储能充放电功率
    P_ess_ch = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
    P_ess_dis = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
    alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
    alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
    E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS)
    # DG出力
    P_DG = m.addVars(n, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG")
    Q_DG = m.addVars(n, 24, vtype=gb.GRB.CONTINUOUS, name="Q_DG")
    for t in range(T):
        for i in range(n):
            if i not in [7,12,8,10]:
                m.addConstr(P_DG[i, t] == 0)
                m.addConstr(Q_DG[i, t] == 0)
        m.addConstr(P_DG[7, t] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG[12, t] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG[8, t] <= DG_total[t] * 2.5 / 9)
        m.addConstr(P_DG[10, t] <= DG_total[t] * 2.5 / 9)
        m.addConstr(Q_DG[7, t] <= 2.0)
        m.addConstr(Q_DG[12, t] <= 2.0)
        m.addConstr(Q_DG[8, t] <= 2.5)
        m.addConstr(Q_DG[10, t] <= 2.5)

    #

    # 中间变量
    tmp_e = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_e")
    tmp_f = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_f")
    tmp_g = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_g")
    tmp_h = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_h")
    tmp_ee = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_ee")
    tmp_ff = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_ff")
    tmp_gg = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_gg")
    tmp_hh = m.addVars(n, n, vtype=gb.GRB.BINARY, name="tmp_hh")
    tmp_E = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="tmp_E")
    tmp_F = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="tmp_F")
    tmp_G = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="tmp_G")
    tmp_H = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="tmp_H")
    tmp_wV2 = m.addVars(n, T, vtype=gb.GRB.CONTINUOUS, name="tmp_wV")
    tmp_ww = m.addVars(n, n, vtype=gb.GRB.BINARY, name="ww")  # u_ij*L_ij线性化
    tmp_LP = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="tmp_LP")
    tmp_LQ = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="tmp_LQ")

    # 下层模型约束
    #5 储能约束
    m.addConstr(E_k[0] == 5)
    for t in range(T):
        m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
        m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
        m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
        if t != 0:
            m.addConstr(E_k[t] == E_k[t - 1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    # m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
    m.addConstr(E_k[0]==E_k[T-1])

    #1 节点功率平衡方程
    for i in range(n):
        for t in range(T):
            P_out = gb.quicksum(P_tran[i, j, t] for j in range(n))
            P_in = gb.quicksum(P_tran[k, i, t] - (r__[i][k]*I2[k,i,t]+0.2889*z[k, i,t]) for k in range(n))
            m.addConstr(P_buy[t]*n__buy[i] + P_DG[i, t] + (P_ess_dis[t] - P_ess_ch[t])*n__ess[i] -
                            P_load[t] * (n__ac[i] + n__dc[i]) - (P_out-P_in) * S_base == 0)

            Q_out = gb.quicksum(Q_tran[i, j, t] for j in range(n))
            Q_in = gb.quicksum(Q_tran[k, i, t] - (x__[i][k]*I2[k,i,t]+0.7548*z[k, i,t]) for k in range(n))
            m.addGenConstrIndicator(W[i], 0,
                                    Q_buy[t] * n__buy[i] +Q_DG[i, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - (Q_out-Q_in) * S_base,
                                    gb.GRB.EQUAL, 0)



    for i in range(n):
        for j in range(i + 1, n):
            m.addConstr(tmp_ww[i, j] == tmp_ww[j, i])
            m.addConstr(tmp_ww[i, j] <= W[i])
            m.addConstr(tmp_ww[i, j] <= W[j])
            m.addConstr(tmp_ww[i, j] >= W[i] + W[j] - 1)

    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(P_tran[i, j, t] <= M * U[i, j])
                m.addConstr(P_tran[i, j, t] >= -M * U[i, j])
                m.addConstr(Q_tran[i, j, t] <= M * U[i, j])
                m.addConstr(Q_tran[i, j, t] >= -M * U[i, j])
                m.addConstr(Q_tran[i, j, t] <= M * (1 - tmp_ww[i, j]))
                m.addConstr(Q_tran[i, j, t] >= -M * (1 - tmp_ww[i, j]))
                # m.addGenConstrIndicator(U[i, j], 0,P_tran[i, j, t],gb.GRB.EQUAL, 0)
                # m.addGenConstrIndicator(U[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)
                # m.addGenConstrIndicator(ww[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)

    #
    #2 电压方程
    for i in range(n):
        for j in range(n):
            for t in range(T):
                m.addConstr(tmp_LP[i, j, t] <= 1 * L[i,j])
                m.addConstr(tmp_LP[i, j, t] >= -1 * L[i,j])
                m.addConstr(tmp_LP[i, j, t] <= P_tran[i,j,t] +1*(1-L[i,j]))
                m.addConstr(tmp_LP[i, j, t] >= P_tran[i,j,t] - 1*(1-L[i,j]))

                m.addConstr(tmp_LQ[i, j, t] <= 1 * L[i, j])
                m.addConstr(tmp_LQ[i, j, t] >= -1 * L[i, j])
                m.addConstr(tmp_LQ[i, j, t] <= Q_tran[i, j, t] +1*(1 - L[i, j]))
                m.addConstr(tmp_LQ[i, j, t] >= Q_tran[i, j, t] - 1 * (1 - L[i, j]))

    for i in range(n):
        for t in range(T):
            m.addConstr(tmp_wV2[i, t] <= W[i] * V2_max)
            m.addConstr(tmp_wV2[i, t] >= W[i] * V2_min)
            m.addConstr(tmp_wV2[i, t] <= V2[i, t] - (1 - W[i]) * V2_min)
            m.addConstr(tmp_wV2[i, t] >= V2[i, t] - (1 - W[i]) * V2_max)
    for i in range(n):
        for j in range(n):
            if i != j:
                m.addConstr(tmp_f[i, j] <= L[i, j])
                m.addConstr(tmp_f[i, j] <= W[i])
                m.addConstr(tmp_f[i, j] >= L[i, j] + W[i] - 1)
                #
                m.addConstr(tmp_g[i, j] <= L[i, j])
                m.addConstr(tmp_g[i, j] <= W[j])
                m.addConstr(tmp_g[i, j] >= L[i, j] + W[j] - 1)
                #
                m.addConstr(tmp_e[i, j] + tmp_f[i, j] == 1)
                m.addConstr(tmp_g[i, j] + tmp_h[i, j] == 1)
                #

                m.addConstr(tmp_ee[i, j] <= tmp_e[i, j])
                m.addConstr(tmp_ee[i, j] <= U[i, j])
                m.addConstr(tmp_ee[i, j] >= tmp_e[i, j] + U[i, j] - 1)
                #
                m.addConstr(tmp_ff[i, j] <= tmp_f[i, j])
                m.addConstr(tmp_ff[i, j] <= U[i, j])
                m.addConstr(tmp_ff[i, j] >= tmp_f[i, j] + U[i, j] - 1)
                #
                m.addConstr(tmp_gg[i, j] <= tmp_g[i, j])
                m.addConstr(tmp_gg[i, j] <= U[i, j])
                m.addConstr(tmp_gg[i, j] >= tmp_g[i, j] + U[i, j] - 1)
                #
                m.addConstr(tmp_hh[i, j] <= tmp_h[i, j])
                m.addConstr(tmp_hh[i, j] <= U[i, j])
                m.addConstr(tmp_hh[i, j] >= tmp_h[i, j] + U[i, j] - 1)

                #


                for t in range(T):
                    #
                    m.addConstr(V2__svc[i, j, t] >= L[i, j] * V2_min)
                    m.addConstr(V2__svc[i, j, t] <= tmp_wV2[i, t] + tmp_wV2[j, t])
                    #

                    m.addGenConstrIndicator(tmp_ee[i, j], True, tmp_E[i, j, t] == V2[i, t])
                    m.addGenConstrIndicator(tmp_ee[i, j], 0, tmp_E[i, j, t] == 0)
                    #
                    m.addGenConstrIndicator(tmp_ff[i, j], True, tmp_F[i, j, t] == V2__svc[i, j, t])
                    m.addGenConstrIndicator(tmp_ff[i, j], 0, tmp_F[i, j, t] == 0)
                    #
                    m.addGenConstrIndicator(tmp_gg[i, j], True, tmp_G[i, j, t] == V2__svc[i, j, t])
                    m.addGenConstrIndicator(tmp_gg[i, j], 0, tmp_G[i, j, t] == 0)
                    #
                    m.addGenConstrIndicator(tmp_hh[i, j], True, tmp_H[i, j, t] == V2[j, t])
                    m.addGenConstrIndicator(tmp_hh[i, j], 0, tmp_H[i, j, t] == 0)

                    #
                    m.addConstr(
                        tmp_E[i, j, t] + tmp_F[i, j, t] - tmp_G[i, j, t] - tmp_H[i, j, t]
                        - 2*(r__vsc[i][j] * P_tran[i, j, t]+x__vsc[i][j] *Q_tran[i, j, t])+(r__vsc[i][j]*r__vsc[i][j]+x__vsc[i][j]*x__vsc[i][j])*I2[i,j,t]<= M * (1 - L[i, j]))
                    m.addConstr(
                        tmp_E[i, j, t] + tmp_F[i, j, t] - tmp_G[i, j, t] - tmp_H[i, j, t]
                        - 2*(r__vsc[i][j] * P_tran[i, j, t]+x__vsc[i][j] *Q_tran[i, j, t])+(r__vsc[i][j]*r__vsc[i][j]+x__vsc[i][j]*x__vsc[i][j])*I2[i,j,t]>= M * (L[i, j] - 1))
                    m.addConstr(
                        tmp_E[i, j, t] + tmp_F[i, j, t] - tmp_G[i, j, t] - tmp_H[i, j, t]
                        - 2*(r__[i][j] * P_tran[i, j, t]+x__[i][j] *Q_tran[i, j, t])+(r__[i][j]*r__[i][j]+x__[i][j]*x__[i][j])*I2[i,j,t]<= M * L[i, j])
                    m.addConstr(
                        tmp_E[i, j, t] + tmp_F[i, j, t] - tmp_G[i, j, t] - tmp_H[i, j, t]
                        - 2*(r__[i][j] * P_tran[i, j, t]+x__[i][j] *Q_tran[i, j, t])+(r__[i][j]*r__[i][j]+x__[i][j]*x__[i][j])*I2[i,j,t]>= -1 * M * L[i, j])

                    lhs = 4 * P_tran[i, j, t] * P_tran[i, j, t] + 4 * Q_tran[i, j, t] * Q_tran[i, j, t] + (I2[i, j, t] - V2[i,t]) * (I2[i, j, t] - V2[i, t])
                    rhs = (I2[i, j, t] + V2[i,t]) * (I2[i, j, t] + V2[i, t])
                    m.addConstr(lhs <= rhs)
                    # m.addGenConstrIndicator(L[i,j], 0,
                    #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__[i][j] * P_tran[i, j, t] - x__[i][j] * Q_tran[i, j, t],
                    #                         gb.GRB.EQUAL, 0)
                    # m.addGenConstrIndicator(L[i, j], 1,
                    #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t],
                    #                         gb.GRB.EQUAL, 0)
    for i in range(n):
        for j in range(n):
            if i != j:
                S_line = 2.5 + 2.5 * x[i, j]
                m.addConstr(S_line <= S_vsc_ij)
                #3 VSC无功补偿能力约束
                m.addConstr(Q_tran[i, j, t] <= L[i, j] * (Q_vsc_max - M) + M)
                m.addConstr(Q_tran[i, j, t] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))

                #4 系统安全运行约束
                m.addConstr(P_tran[i, j, t] * S_base <= gama * S_line)
                m.addConstr(P_tran[i, j, t] * S_base >= -gama * S_line)

                m.addConstr(Q_tran[i, j, t] <= gama * S_line / S_base)
                m.addConstr(Q_tran[i, j, t] >= -gama * S_line / S_base)

                m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
                m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)

    # 目标函数
    X = m.addVars(n, n, vtype=gb.GRB.BINARY, name="X")  # 线性化引入辅助变量X=x*u
    uL = m.addVars(n, n, vtype=gb.GRB.BINARY, name="uL")
    xX =m.addVars(n, n, vtype=gb.GRB.BINARY, name="xX")

    # 线路建设成本
    C_line = 0
    for i in range(n):
        for j in range(n):
            m.addConstr(X[i, j] <= x[i, j])
            m.addConstr(X[i, j] <= U[i, j])
            m.addConstr(X[i, j] >= x[i, j] + U[i, j] - 1)

            m.addConstr(xX[i, j] <= x[i, j])
            m.addConstr(xX[i, j] <= X[i, j])
            m.addConstr(xX[i, j] >= x[i, j] + X[i, j] - 1)
            #C_line += 0.5 * (c_l[0]+(c_l[1]-c_l[0])*x[i,j]) * Length[i][j] * X[i, j]
            C_line += 0.5 * Length[i][j] * (c_l[0] * X[i, j] + (c_l[1] - c_l[0]) * xX[i, j])


    # 换流器安装成本
    # U*L线性化约束
    for i in range(n):
        for j in range(n):
            m.addConstr(uL[i, j] <= U[i, j])
            m.addConstr(uL[i, j] <= L[i, j])
            m.addConstr(uL[i, j] >= U[i, j] + L[i, j] - 1)
    S_vsc = 0
    for i in range(n):
        for j in range(n):
            S_vsc += 0.5 * S_vsc_ij * uL[i, j]
    S_c = 0
    for i in range(n):
        S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
        S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
        S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]

    C_cvt = c_c * S_c + c_v * S_vsc

    C_invest = C_line + C_cvt
    # 运行成本
    C_operation = 0
    f_op = 0

    for t in range(T):
        f_op += c_s * P_buy[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
        f_op += c_d * (DG_total[t] * 2.0 / 9 - P_DG[7, t])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG[8, t])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG[10, t])
        f_op += c_d * (DG_total[t] * 2.0 / 9 - P_DG[12, t])

    # C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
    for d in range(T_p):
        C_operation += N_d * f_op / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)




    m.setObjective(C_operation+C_invest, gb.GRB.MINIMIZE)
    # 检查问题规模
    print(f"变量数: {m.numVars}")
    print(f"约束数: {m.numConstrs}")
    print(f"非零元素: {m.numNZs}")
    m.Params.Threads = 0  # 0表示自动选择最优线程数
    # 针对不同问题类型优化参数
    # m.Params.Method = 2        # 内点法对于大规模问题可能更好
    # m.Params.Crossover = 0     # 禁用交叉，对于纯线性问题
    # m.Params.Presolve = 2      # 积极的预处理
    # m.Params.MIPFocus = 1      # 侧重找到更好可行解
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    Result = []
    for v in m.getVars():
        Result.append([v.VarName, v.X])
        if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_buy', 'P_ess_ch', 'P_ess_dis']:
            print(v.VarName, v.X)
    print('Obj:', m.objVal)

    with open('Result.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for row in Result:
            writer.writerow(row)

    # 测试不同线程配置
    def test_thread_scaling():
        for threads in [1, 2, 4, 8, 0]:  # 0=auto
            model = gb.Model()
            model.Params.Threads = threads
            model.Params.LogToConsole = 0

            start = time.time()
            # 求解你的问题
            solve_time = time.time() - start
            print(f"线程数 {threads}: {solve_time:.2f}秒")

    def diagnose_gurobi_performance():
        model = gb.Model()

        # 1. 检查默认参数
        print("=== Gurobi 配置 ===")
        print(f"Threads: {model.Params.Threads}")
        print(f"Method: {model.Params.Method}")
        print(f"Presolve: {model.Params.Presolve}")

        # 2. 检查系统信息
        print("\n=== 系统信息 ===")
        import platform
        print(f"CPU: {platform.processor()}")
        print(f"Arch: {platform.machine()}")

        # 3. 运行基准测试
        print("\n=== 性能测试 ===")
        import time
        start = time.time()
        # 添加一个简单测试问题...
        # test_performance()
        print(f"求解时间: {time.time() - start:.2f}秒")

def Operation2(W,U,C):#潮流
    m = gb.Model("mip1")

    # 定义换流支路
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])
    L = [[abs(W[i] - W[j]) for j in range(n)] for i in range(n)]

    # 构建支路列表
    root=0
    branches = []
    for i in range(n):
        for j in range(i + 1, n):
            if U[i][j] == 1:
                branches.append((i, j))
    # 构建网络的树形结构（从根节点开始BFS）
    parent = {}
    children = {i: [] for i in range(n)}
    visited = [False] * n
    queue = [root]
    visited[root] = True

    while queue:
        node = queue.pop(0)
        for i in range(n):
            if U[node][i] == 1 and not visited[i]:
                parent[i] = node
                children[node].append(i)
                visited[i] = True
                queue.append(i)

    # 定义各节点电压
    V = {}
    for t in range(T):
        for i in range(n):
            V[(i, t)] = m.addVar(lb=0.95**2, ub=1.05**2, vtype=gb.GRB.CONTINUOUS, name=f"V_{i}_{t}")

    # 定义线路潮流
    # 支路有功功率 P[i,j,t]
    P = {}
    # 支路无功功率 Q[i,j,t]
    Q = {}
    # 支路电流平方 I[i,j,t]
    I = {}
    # 换流电压 V_svc[i,j,t]
    V_svc = {}

    for i, j in branches:
        for t in range(T):
            P[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"P_{i}_{j}_{t}")
            Q[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"Q_{i}_{j}_{t}")
            I[(i, j, t)] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"I_{i}_{j}_{t}")
            V_svc[(i, j, t)] = m.addVar(lb=0, vtype=gb.GRB.CONTINUOUS, name=f"V_svc_{i}_{j}_{t}")
    m.update()
    # 购电功率
    P_buy={}
    Q_buy={}
    for t in range(T):
        P_buy[t] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"P_buy_{t}")
        Q_buy[t] = m.addVar(lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name=f"Q_buy_{t}")
    # 储能充放电功率
    P_ess_ch = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
    P_ess_dis = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
    alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
    alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
    E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS, name="E_k")
    # DG出力
    P_DG={}
    Q_DG={}
    for i in range(n):
        for t in range(T):
            if i in [7,12,8,10]:
                P_DG[(i,t)]=m.addVar(vtype=gb.GRB.CONTINUOUS,name=f"P_DG_{i}_{t}" )
                Q_DG[(i, t)] = m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"Q_DG_{i}_{t}")
            else:
                P_DG[(i, t)] = 0
                Q_DG[(i, t)]=0
    for t in range(T):
        m.addConstr(P_DG[(7, t)] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG[(12, t)] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG[(8, t)] <= DG_total[t] * 2.5 / 9)
        m.addConstr(P_DG[(10, t)] <= DG_total[t] * 2.5 / 9)
        m.addConstr(Q_DG[9,t] <= 2.0)
        m.addConstr(Q_DG[(12, t)] <= 2.0)
        m.addConstr(Q_DG[(8, t)] <= 2.5)
        m.addConstr(Q_DG[(10, t)] <= 2.5)

    # 模型约束
    #1 节点功率平衡方程
    for k in range(n):
        for t in range(T):
            if k == root:
                # 根节点
                P_out = 0
                Q_out = 0

                for child in children[k]:
                    if (k, child) in [(a, b) for a, b in branches]:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in [(a, b) for a, b in branches]:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]

                m.addConstr(P_buy[t] == P_out * S_base, f"P_{k}_{t}")
                m.addConstr(Q_buy[t] == Q_out * S_base, f"Q_{k}_{t}")

            else:
                # 非根节点
                parent_node = parent[k]

                # 从父节点流入的功率
                if (parent_node, k) in [(a, b) for a, b in branches]:
                    P_in = P[(parent_node, k, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                    Q_in = Q[(parent_node, k, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                elif (k, parent_node) in [(a, b) for a, b in branches]:
                    P_in = -P[(k, parent_node, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                    Q_in = -Q[(k, parent_node, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                else:
                    continue

                # 流出到子节点的功率
                P_out = 0
                Q_out = 0
                for child in children[k]:
                    if (k, child) in [(a, b) for a, b in branches]:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in [(a, b) for a, b in branches]:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]

                P_total=P_DG[(k, t)] + (P_ess_dis[t] - P_ess_ch[t])*n__ess[k] -P_load[t] * (n__ac[k] + n__dc[k])
                Q_total=Q_DG[k, t] -Q_load[t] * (n__ac[k] + n__dc[k])
                m.addConstr(P_in * S_base + P_total == P_out * S_base , f"P_{k}_{t}")
                m.addConstr(Q_in * S_base + Q_total == Q_out * S_base, f"Q_{k}_{t}")

    #
    #2 电压方程

    for i, j in branches:
        for t in range(T):
            m.addConstr(V_svc[i, j, t] >= V_min ** 2 * L[i][j])
            m.addConstr(V_svc[i, j, t] <= W[i]*V[i,t] + W[j]*V[j,t])

            R=r_line[i][j][L[i][j]]
            X=x_line[i][j][L[i][j]]

            f = L[i][j] * W[i]
            e=1-f
            g = L[i][j] * W[j]
            h=1-g
            if j in parent and parent[j] == i:
                # i是父节点，j是子节点
                m.addConstr(
                    2 * (R * P[(i, j, t)] + X * Q[(i, j, t)])-(R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e*V[(i, t)] + (f-g) * V_svc[(i,j,t)] - h*V[(j, t)],
                    f"Vc_{i}_{j}_{t}"
                )
            elif i in parent and parent[i] == j:
                # j是父节点，i是子节点
                m.addConstr(
                    - 2 * (R * P[(i, j, t)] + X * Q[(i, j, t)]) - (R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e*V[(j, t)] + (f-g) * V_svc[(i,j,t)]- h*V[(i, t)],
                    f"Vc_{i}_{j}_{t}"
                )
    #2 二阶锥约束
    for i, j in branches:
        for t in range(T):
            # 确定父节点
            if j in parent and parent[j] == i:
                parent_node = i
            elif i in parent and parent[i] == j:
                parent_node = j
            else:
                parent_node = i

            # 旋转锥约束
            m.addQConstr(
                I[(i, j, t)] * V[(parent_node, t)] >=
                P[(i, j, t)] * P[(i, j, t)] + Q[(i, j, t)] * Q[(i, j, t)],
                f"soc_{i}_{j}_{t}"
            )

    #3 VSC无功补偿能力约束
    for i, j in branches:
        for t in range(T):
            m.addConstr(Q[(i, j, t)] <= L[i][j] * (Q_vsc_max-M) + M)

    # 4 系统安全运行约束
    for i, j in branches:
        S_line = 2.5 + 2.5 * C[i][j]
        for t in range(T):
            m.addConstr(P[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(P[(i, j, t)] * S_base >= -gama * S_line)

            m.addConstr(Q[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(Q[(i, j, t)] * S_base >= -gama * S_line)

            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)

    # 5 储能约束
    m.addConstr(E_k[0] == 5)
    m.addConstr(P_ess_ch[0] == 0)
    m.addConstr(P_ess_dis[0] == 0)
    for t in range(T):
        m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
        m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
        m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
        if t != 0:
            m.addConstr(E_k[t] == E_k[t-1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
    #m.addConstr(E_k[0] == E_k[T - 1])

    # 目标函数

    # 投资成本
    C_line = 0
    S_vsc = 0
    S_c = 0
    for i in range(n):
        S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
        S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
        S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
        for j in range(n):
            S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
            C_line += 0.5 * c_l[C[i][j]] * Length[i][j] * U[i][j]
    C_cvt = c_c * S_c + c_v * S_vsc
    C_invest = C_line + C_cvt


    # 运行成本
    C_operation = 0
    f_op = 0

    for t in range(T):
        f_op += c_s * P_buy[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
        f_op += c_d * (DG_total[t] * 2.0 / 9 - P_DG[(7, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG[(8, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG[(10, t)])
        f_op += c_d * (DG_total[t] * 2.0 / 9 - P_DG[(12, t)])

    for d in range(T_p):
        C_operation += N_d * f_op / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)

    m.setObjective(C_operation, gb.GRB.MINIMIZE)
    # 检查问题规模
    # print(f"变量数: {m.numVars}")
    # print(f"约束数: {m.numConstrs}")
    # print(f"非零元素: {m.numNZs}")
    # m.Params.Threads = 0  # 0表示自动选择最优线程数
    # 针对不同问题类型优化参数
    # m.Params.Method = 2        # 内点法对于大规模问题可能更好
    # m.Params.Crossover = 0     # 禁用交叉，对于纯线性问题
    # m.Params.Presolve = 2      # 积极的预处理
    # m.Params.MIPFocus = 1      # 侧重找到更好可行解
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    if m.status == gb.GRB.INFEASIBLE:
        print("模型不可行，正在计算 IIS...")
        m.computeIIS()  # 计算不可约不一致子系统
        m.write("model_iis.ilp")  # 导出为 ILP 文件
        print("IIS 已导出至 'model_iis.ilp'")

    print('Obj:', m.objVal)
    if m.Status == gb.GRB.OPTIMAL or m.Status == gb.GRB.SUBOPTIMAL:
        for v in m.getVars():
            if v.VarName.startswith('P_ess'):  # 只打印以P_开头的变量
                print(f"  {v.VarName} = {v.X:.6f}")
    else:
        print("求解失败，无法打印变量值")
    print_variables_by_pattern(m, pattern='E_k')


def Operation3(X,f_DG):#潮流
    W,U,C= encode(X, n)


    m = gb.Model("mip1")

    # 定义换流支路
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])
    L = [[abs(W[i] - W[j]) for j in range(n)] for i in range(n)]

    # 构建支路列表
    root=0
    branches = []
    for i in range(n):
        for j in range(i + 1, n):
            if U[i][j] == 1:
                branches.append((i, j))
    # 构建网络的树形结构（从根节点开始BFS）
    parent = {}
    children = {i: [] for i in range(n)}
    visited = [False] * n
    queue = [root]
    visited[root] = True

    while queue:
        node = queue.pop(0)
        for i in range(n):
            if U[node][i] == 1 and not visited[i]:
                parent[i] = node
                children[node].append(i)
                visited[i] = True
                queue.append(i)

    # 定义各节点电压
    V = {}
    for t in range(T):
        for i in range(n):
            V[(i, t)] = m.addVar(lb=0.95**2, ub=1.05**2, vtype=gb.GRB.CONTINUOUS, name=f"V_{i}_{t}")

    # 定义线路潮流
    # 支路有功功率 P[i,j,t]
    P = {}
    # 支路无功功率 Q[i,j,t]
    Q = {}
    # 支路电流平方 I[i,j,t]
    I = {}
    # 换流电压 V_svc[i,j,t]
    V_svc = {}

    for i, j in branches:
        for t in range(T):
            P[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"P_{i}_{j}_{t}")
            Q[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"Q_{i}_{j}_{t}")
            I[(i, j, t)] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"I_{i}_{j}_{t}")
            V_svc[(i, j, t)] = m.addVar(lb=0, vtype=gb.GRB.CONTINUOUS, name=f"V_svc_{i}_{j}_{t}")
    m.update()
    # 购电功率
    P_buy={}
    Q_buy={}
    for t in range(T):
        P_buy[t] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"P_buy_{t}")
        Q_buy[t] = m.addVar(lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name=f"Q_buy_{t}")
    # 储能充放电功率
    P_ess_ch = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
    P_ess_dis = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
    alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
    alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
    E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS, name="E_k")
    # DG出力
    P_DG={}
    Q_DG={}
    for i in range(n):
        for t in range(T):
            if i in [7,12,8,10]:
                P_DG[(i,t)]=m.addVar(vtype=gb.GRB.CONTINUOUS,name=f"P_DG_{i}_{t}" )
                Q_DG[(i, t)] = m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"Q_DG_{i}_{t}")
            else:
                P_DG[(i, t)] = 0
                Q_DG[(i, t)]=0
    for t in range(T):
        m.addConstr(P_DG[(7, t)] <= DG_total[t] * 2 / 9 *f_DG)
        m.addConstr(P_DG[(12, t)] <= DG_total[t] * 2 / 9 *f_DG)
        m.addConstr(P_DG[(8, t)] <= DG_total[t] * 2.5 / 9 *f_DG)
        m.addConstr(P_DG[(10, t)] <= DG_total[t] * 2.5 / 9 *f_DG)
        m.addConstr(Q_DG[(7,t)] <= 2.0)
        m.addConstr(Q_DG[(12, t)] <= 2.0)
        m.addConstr(Q_DG[(8, t)] <= 2.5)
        m.addConstr(Q_DG[(10, t)] <= 2.5)

    # 模型约束
    #1 节点功率平衡方程
    for k in range(n):
        for t in range(T):
            if k == root:
                # 根节点
                P_out = 0
                Q_out = 0

                for child in children[k]:
                    if (k, child) in [(a, b) for a, b in branches]:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in [(a, b) for a, b in branches]:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]

                m.addConstr(P_buy[t] == P_out * S_base, f"P_{k}_{t}")
                m.addConstr(Q_buy[t] == Q_out * S_base, f"Q_{k}_{t}")

            else:
                # 非根节点
                try:
                    parent_node = parent[k]
                except:
                    return None

                # 从父节点流入的功率
                if (parent_node, k) in [(a, b) for a, b in branches]:
                    P_in = P[(parent_node, k, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                    Q_in = Q[(parent_node, k, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                elif (k, parent_node) in [(a, b) for a, b in branches]:
                    P_in = -P[(k, parent_node, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                    Q_in = -Q[(k, parent_node, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                else:
                    continue

                # 流出到子节点的功率
                P_out = 0
                Q_out = 0
                for child in children[k]:
                    if (k, child) in [(a, b) for a, b in branches]:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in [(a, b) for a, b in branches]:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]

                P_total=P_DG[(k, t)] + (P_ess_dis[t] - P_ess_ch[t])*n__ess[k] -P_load[t] * (n__ac[k] + n__dc[k])
                Q_total=Q_DG[k, t] -Q_load[t] * (n__ac[k] + n__dc[k])
                m.addConstr(P_in * S_base + P_total == P_out * S_base , f"P_{k}_{t}")
                m.addConstr(Q_in * S_base + Q_total == Q_out * S_base, f"Q_{k}_{t}")

    #
    #2 电压方程

    for i, j in branches:
        for t in range(T):
            m.addConstr(V_svc[i, j, t] >= V_min ** 2 * L[i][j])
            m.addConstr(V_svc[i, j, t] <= W[i]*V[i,t] + W[j]*V[j,t])

            R=r_line[i][j][L[i][j]]
            X=x_line[i][j][L[i][j]]

            f = L[i][j] * W[i]
            e=1-f
            g = L[i][j] * W[j]
            h=1-g
            if j in parent and parent[j] == i:
                # i是父节点，j是子节点
                m.addConstr(
                    2 * (R * P[(i, j, t)] + X * Q[(i, j, t)])-(R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e*V[(i, t)] + (f-g) * V_svc[(i,j,t)] - h*V[(j, t)],
                    f"Vc_{i}_{j}_{t}"
                )
            elif i in parent and parent[i] == j:
                # j是父节点，i是子节点
                m.addConstr(
                    - 2 * (R * P[(i, j, t)] + X * Q[(i, j, t)]) - (R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e*V[(j, t)] + (f-g) * V_svc[(i,j,t)]- h*V[(i, t)],
                    f"Vc_{i}_{j}_{t}"
                )
    #2 二阶锥约束
    for i, j in branches:
        for t in range(T):
            # 确定父节点
            if j in parent and parent[j] == i:
                parent_node = i
            elif i in parent and parent[i] == j:
                parent_node = j
            else:
                parent_node = i

            # 旋转锥约束
            m.addQConstr(
                I[(i, j, t)] * V[(parent_node, t)] >=
                P[(i, j, t)] * P[(i, j, t)] + Q[(i, j, t)] * Q[(i, j, t)],
                f"soc_{i}_{j}_{t}"
            )

    #3 VSC无功补偿能力约束
    for i, j in branches:
        for t in range(T):
            m.addConstr(Q[(i, j, t)] <= L[i][j] * (Q_vsc_max-M) + M)

    # 4 系统安全运行约束
    for i, j in branches:
        S_line = 2.5 + 2.5 * C[i][j]
        for t in range(T):
            m.addConstr(P[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(P[(i, j, t)] * S_base >= -gama * S_line)

            m.addConstr(Q[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(Q[(i, j, t)] * S_base >= -gama * S_line)

            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)

    # 5 储能约束
    m.addConstr(E_k[0] == 5)
    m.addConstr(P_ess_ch[0] == 0)
    m.addConstr(P_ess_dis[0] == 0)
    for t in range(T):
        m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
        m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
        m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
        if t != 0:
            m.addConstr(E_k[t] == E_k[t-1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
    #m.addConstr(E_k[0] == E_k[T - 1])

    # 目标函数

    # 投资成本
    # C_line = 0
    # S_vsc = 0
    # S_c = 0
    # for i in range(n):
    #     S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
    #     S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
    #     S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
    #     for j in range(n):
    #         S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
    #         C_line += 0.5 * c_l[C[i][j]] * Length[i][j] * U[i][j]
    # C_cvt = c_c * S_c + c_v * S_vsc
    # C_invest = C_line + C_cvt


    # 运行成本
    # C_operation = 0
    f_op = 0


    for t in range(T):
        f_op += c_s * P_buy[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
        f_op += c_d * (DG_total[t] * 2.0 / 9 *f_DG - P_DG[(7, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 *f_DG - P_DG[(8, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 *f_DG - P_DG[(10, t)])
        f_op += c_d * (DG_total[t] * 2.0 / 9 *f_DG - P_DG[(12, t)])

    # for d in range(T_p):
    #     C_operation += N_d * f_op / pow(1 + r, d + 1)
    # for d in range(T_line):
    #     C_operation += beta_line * C_line / pow(1 + r, d + 1)
    # for d in range(T_cvt):
    #     C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
    m.setParam("OutputFlag", 0)

    m.setParam("Threads", 0)
    m.setObjective(f_op, gb.GRB.MINIMIZE)
    # 检查问题规模
    # print(f"变量数: {m.numVars}")
    # print(f"约束数: {m.numConstrs}")
    # print(f"非零元素: {m.numNZs}")
    # m.Params.Threads = 0  # 0表示自动选择最优线程数
    # 针对不同问题类型优化参数
    # m.Params.Method = 2        # 内点法对于大规模问题可能更好
    # m.Params.Crossover = 0     # 禁用交叉，对于纯线性问题
    # m.Params.Presolve = 2      # 积极的预处理
    # m.Params.MIPFocus = 1      # 侧重找到更好可行解
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    if m.status == gb.GRB.INFEASIBLE:
        print("模型不可行，正在计算 IIS...")
        m.computeIIS()  # 计算不可约不一致子系统
        m.write("model_iis.ilp")  # 导出为 ILP 文件
        print("IIS 已导出至 'model_iis.ilp'")
    if m.status == gb.GRB.OPTIMAL:
        C_buy = 0
        C_ess = 0
        C_DG = 0

        # 提取变量值并计算成本
        for t in range(T):
            # 获取购电变量值
            P_buy_t = P_buy[t].X if hasattr(P_buy[t], 'X') else P_buy[t]
            C_buy += c_s * P_buy_t

            # 获取储能充放电变量值
            P_ess_ch_t = P_ess_ch[t].X if hasattr(P_ess_ch[t], 'X') else P_ess_ch[t]
            P_ess_dis_t = P_ess_dis[t].X if hasattr(P_ess_dis[t], 'X') else P_ess_dis[t]
            C_ess += c_e * (P_ess_ch_t + P_ess_dis_t)

            # 计算 DG 成本（注意：这里的逻辑可能需要根据实际情况调整）
            # 假设 DG_total[t] 是已知参数，f_DG 是已知参数
            term1 = DG_total[t] * 2.0 / 9 * f_DG - P_DG[(7, t)].X
            term2 = DG_total[t] * 2.5 / 9 * f_DG - P_DG[(8, t)].X
            term3 = DG_total[t] * 2.5 / 9 * f_DG - P_DG[(10, t)].X
            term4 = DG_total[t] * 2.0 / 9 * f_DG - P_DG[(12, t)].X

            C_DG += c_d * (term1 + term2 + term3 + term4)
        return [m.objVal,C_buy,C_ess,C_DG]
    else:
        return None




def Operation4(W, U, C, f_DG, root=0, Open_circuit=None):

    import gurobipy as gb

    #1 处理支路断开
    U_work = copy.deepcopy(U)

    if Open_circuit is not None:
        i, j = Open_circuit
        U_work[i][j] = 0
        U_work[j][i] = 0

    #2 找出所有连通分量
    visited = [False] * n
    sub_networks = []
    for start_node in range(n):
        if not visited[start_node]:
            # BFS
            component_nodes = []
            queue = [start_node]
            visited[start_node] = True

            while queue:
                node = queue.pop(0)
                component_nodes.append(node)
                for neighbor in range(n):
                    if U_work[node][neighbor] == 1 and not visited[neighbor]:
                        visited[neighbor] = True
                        queue.append(neighbor)

            # 确定根节点
            if root in component_nodes:
                sub_root = root
            else:
                # 优先选择DG节点作为根节点，且节点10优先
                dg_nodes = [7, 12, 8, 10]
                dg_in_component = [node for node in component_nodes if node in dg_nodes]

                if dg_in_component:
                    if 10 in dg_in_component:
                        sub_root = 10
                    elif 8 in dg_in_component:
                        sub_root = 8
                    elif 7 in dg_in_component:
                        sub_root = 7
                    elif 12 in dg_in_component:
                        sub_root = 12
                else:
                    # 没有DG节点，选择度数最大的节点
                    max_degree = -1
                    sub_root = component_nodes[0]
                    for node in component_nodes:
                        degree = sum(1 for nb in range(n) if U_work[node][nb] == 1)
                        if degree > max_degree:
                            max_degree = degree
                            sub_root = node

            sub_networks.append({
                'nodes': component_nodes,
                'root': sub_root
            })
    #3 子网络求解
    if len(sub_networks) == 1:
        return solve_network(W, U_work, C, f_DG, root, sub_networks[0]['nodes'])/15
    else:
        total_objective = 0
        for net_idx, network in enumerate(sub_networks):

            net_result = solve_network(
                W, U_work, C, f_DG,
                root=network['root'],
                nodes=network['nodes']
            )

            if net_result == 'infeasible':
                return 'infeasible'
            total_objective += net_result

        return total_objective/15

def Cal_Loss(X):
    W, U, C = encode(X, n)
    edges=[]
    Loss=[]
    for i in range (n):
        for j in range (i+1,n):
            if U[i][j] == 1:
                edges.append((i, j))
    for i,j in edges:

        loss=Operation4(W, U, C, 1, root=0, Open_circuit=(i,j))
        Loss.append(loss)
        if (i in [5,7,8,10,12])or(j in [5,7,8,10,12]):
            pass
    return sum(Loss)/len(Loss)

def solve_network(W, U_work, C, f_DG, root, nodes):


    m = gb.Model(f"Subnetwork_Root{root}")

    # Loss_load变量
    Loss_load = m.addVars(n, 2, vtype=gb.GRB.BINARY, name='Loss_load')
    for i in range(n):
        if n__ac[i] == 0:
            m.addConstr(Loss_load[i, 0] == 0)
        if n__dc[i] == 0:
            m.addConstr(Loss_load[i, 1] == 0)

    # 定义换流支路
    L = [[abs(W[i] - W[j]) for j in range(n)] for i in range(n)]

    # ========== 构建该子网络的支路列表和树形结构 ==========
    branches = []
    for i in nodes:
        for j in nodes:
            if j > i and U_work[i][j] == 1:
                branches.append((i, j))

    # 构建树形结构
    parent = {}
    children = {i: [] for i in nodes}
    visited_sub = {i: False for i in nodes}
    queue = [root]
    visited_sub[root] = True

    while queue:
        node = queue.pop(0)
        for i in nodes:
            if U_work[node][i] == 1 and not visited_sub[i]:
                parent[i] = node
                children[node].append(i)
                visited_sub[i] = True
                queue.append(i)
    # 定义各节点电压（只定义子网络中的节点）
    V = {}
    for t in range(T):
        for i in nodes:
            V[(i, t)] = m.addVar(lb=V_min ** 2, ub=V_max ** 2, vtype=gb.GRB.CONTINUOUS, name=f"V_{i}_{t}")

    # 定义线路潮流
    P = {}
    Q = {}
    I = {}
    V_svc = {}

    for i, j in branches:
        for t in range(T):
            P[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"P_{i}_{j}_{t}")
            Q[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"Q_{i}_{j}_{t}")
            I[(i, j, t)] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"I_{i}_{j}_{t}")
            V_svc[(i, j, t)] = m.addVar(lb=0, vtype=gb.GRB.CONTINUOUS, name=f"V_svc_{i}_{j}_{t}")

    m.update()

    # 购电功率（只在根节点所在子网络有购电）
    P_buy = {}
    Q_buy = {}
    for t in range(T):
        P_buy[t] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"P_buy_{t}")
        Q_buy[t] = m.addVar(lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name=f"Q_buy_{t}")

    # 储能充放电功率（如果储能节点在子网络中）
    P_ess_ch = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
    P_ess_dis = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
    alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
    alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
    E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS, name="E_k")

    # DG出力（只定义子网络中的DG节点）
    P_DG = {}
    Q_DG = {}
    for i in nodes:
        for t in range(T):
            if i in [7, 12, 8, 10]:
                P_DG[(i, t)] = m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"P_DG_{i}_{t}")
                Q_DG[(i, t)] = m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"Q_DG_{i}_{t}")
            else:
                P_DG[(i, t)] = 0
                Q_DG[(i, t)] = 0

    # DG约束
    for t in range(T):
        if 7 in nodes:
            m.addConstr(P_DG[(7, t)] <= DG_total[t] * 2 / 9 * f_DG)
        if 12 in nodes:
            m.addConstr(P_DG[(12, t)] <= DG_total[t] * 2 / 9 * f_DG)
        if 8 in nodes:
            m.addConstr(P_DG[(8, t)] <= DG_total[t] * 2.5 / 9 * f_DG)
        if 10 in nodes:
            m.addConstr(P_DG[(10, t)] <= DG_total[t] * 2.5 / 9 * f_DG)
        if 9 in nodes:
            m.addConstr(Q_DG[9, t] <= 2.0)
        if 12 in nodes:
            m.addConstr(Q_DG[(12, t)] <= 2.0)
        if 8 in nodes:
            m.addConstr(Q_DG[(8, t)] <= 2.5)
        if 10 in nodes:
            m.addConstr(Q_DG[(10, t)] <= 2.5)

    # ========== 模型约束 ==========

    # 1 节点功率平衡方程（只处理子网络中的节点）
    for k in nodes:
        for t in range(T):
            if k == root:
                # 根节点
                P_out = 0
                Q_out = 0

                for child in children.get(k, []):
                    if (k, child) in branches:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in branches:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]
                P_total = P_buy[t] * n__buy[k] + P_DG.get((k, t), 0) + (P_ess_dis[t] - P_ess_ch[t]) * n__ess[k] - \
                          P_load[t] * (
                                  Loss_load[k, 0] + Loss_load[k, 1] )
                Q_total = Q_buy[t] * n__buy[k] + Q_DG.get((k, t), 0) - Q_load[t] * (
                        Loss_load[k, 0] + Loss_load[k, 1])
                if len(nodes)>1:
                    m.addConstr(P_total == P_out * S_base, f"P_root_{k}_{t}")
                    m.addConstr(Q_total == Q_out * S_base, f"Q_root_{k}_{t}")
                else:
                    m.addConstr(P_total == 0, f"P_root_{k}_{t}")
                    m.addConstr(Q_total == 0, f"Q_root_{k}_{t}")



            elif k in parent:
                # 非根节点
                parent_node = parent[k]

                # 从父节点流入的功率
                if (parent_node, k) in branches:
                    P_in = P[(parent_node, k, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                    Q_in = Q[(parent_node, k, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                elif (k, parent_node) in branches:
                    P_in = -P[(k, parent_node, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                    Q_in = -Q[(k, parent_node, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                else:
                    continue

                # 流出到子节点的功率
                P_out = 0
                Q_out = 0
                for child in children.get(k, []):
                    if (k, child) in branches:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in branches:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]

                P_total = P_DG.get((k, t), 0) + (P_ess_dis[t] - P_ess_ch[t]) * n__ess[k] - P_load[t] * (
                            Loss_load[k, 0] + Loss_load[k, 1])
                Q_total = Q_DG.get((k, t), 0) - Q_load[t] * (Loss_load[k, 0] + Loss_load[k, 1])

                m.addConstr(P_in * S_base + P_total == P_out * S_base, f"P_{k}_{t}")
                m.addConstr(Q_in * S_base + Q_total == Q_out * S_base, f"Q_{k}_{t}")

    # 2 电压方程（只处理子网络中的支路）
    for i, j in branches:
        for t in range(T):
            m.addConstr(V_svc[i, j, t] >= V_min ** 2 * L[i][j])
            m.addConstr(V_svc[i, j, t] <= W[i] * V[i, t] + W[j] * V[j, t])

            R = r_line[i][j][L[i][j]]
            X = x_line[i][j][L[i][j]]

            f = L[i][j] * W[i]
            e = 1 - f
            g = L[i][j] * W[j]
            h = 1 - g

            if j in parent and parent[j] == i:
                m.addConstr(
                    2 * (R * P[(i, j, t)] + X * Q[(i, j, t)]) - (R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e * V[(i, t)] + (f - g) * V_svc[(i, j, t)] - h * V[(j, t)],
                    f"Vc_{i}_{j}_{t}"
                )
            elif i in parent and parent[i] == j:
                m.addConstr(
                    -2 * (R * P[(i, j, t)] + X * Q[(i, j, t)]) - (R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e * V[(j, t)] + (f - g) * V_svc[(i, j, t)] - h * V[(i, t)],
                    f"Vc_{i}_{j}_{t}"
                )

    # 2 二阶锥约束
    for i, j in branches:
        for t in range(T):
            if j in parent and parent[j] == i:
                parent_node = i
            elif i in parent and parent[i] == j:
                parent_node = j
            else:
                parent_node = i

            m.addQConstr(
                I[(i, j, t)] * V[(parent_node, t)] >=
                P[(i, j, t)] * P[(i, j, t)] + Q[(i, j, t)] * Q[(i, j, t)],
                f"soc_{i}_{j}_{t}"
            )

    # 3 VSC无功补偿能力约束
    for i, j in branches:
        for t in range(T):
            m.addConstr(Q[(i, j, t)] <= L[i][j] * (Q_vsc_max - M) + M)

    # 4 系统安全运行约束
    for i, j in branches:
        S_line = 2.5 + 2.5 * C[i][j]
        for t in range(T):
            m.addConstr(P[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(P[(i, j, t)] * S_base >= -gama * S_line)
            m.addConstr(Q[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(Q[(i, j, t)] * S_base >= -gama * S_line)

            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)

    # 5 储能约束（保持不变）
    m.addConstr(E_k[0] == 5)
    m.addConstr(P_ess_ch[0] == 0)
    m.addConstr(P_ess_dis[0] == 0)
    for t in range(T):
        m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
        m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
        m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
        if t != 0:
            m.addConstr(E_k[t] == E_k[t - 1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)

    # ========== 目标函数 ==========

    # 投资成本（只计算子网络中的线路和节点）
    C_line = 0
    S_vsc = 0
    S_c = 0

    for i in nodes:
        S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
        S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
        S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]

        for j in nodes:
            if U_work[i][j] == 1:
                S_vsc += 0.5 * S_vsc_ij * U_work[i][j] * L[i][j]
                C_line += 0.5 * c_l[C[i][j]] * Length[i][j] * U_work[i][j]

    C_cvt = c_c * S_c + c_v * S_vsc
    C_invest = C_line + C_cvt

    # 运行成本
    C_operation = 0
    f_op = 0

    for t in range(T):
        f_op += c_s * P_buy[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])

        # DG惩罚项（只考虑子网络中存在的DG节点）
        if 7 in nodes:
            f_op += c_d * (DG_total[t] * 2.0 / 9 * f_DG - P_DG[(7, t)])
        if 8 in nodes:
            f_op += c_d * (DG_total[t] * 2.5 / 9 * f_DG - P_DG[(8, t)])
        if 10 in nodes:
            f_op += c_d * (DG_total[t] * 2.5 / 9 * f_DG - P_DG[(10, t)])
        if 12 in nodes:
            f_op += c_d * (DG_total[t] * 2.0 / 9 * f_DG - P_DG[(12, t)])

    for d in range(T_p):
        C_operation += N_d * f_op / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)

    f3 = sum(n__ac[i] for i in nodes) + sum(n__dc[i] for i in nodes) - sum(Loss_load[i, 0] + Loss_load[i, 1] for i in nodes)

    m.setObjective(f3, gb.GRB.MINIMIZE)
    m.setParam('LogToConsole', 0)
    # 求解
    m.Params.Threads = 0
    m.optimize()


    if m.status == gb.GRB.INFEASIBLE:
        print(f"子网络 (根节点{root}) 不可行")
        m.computeIIS()
        m.write(f"subnetwork_root{root}_iis.ilp")
        return 'infeasible'
    elif m.status == gb.GRB.OPTIMAL:
        # print(f"子网络 (根节点{root}) 目标值: {m.objVal}")
        return m.objVal
    else:
        return 'infeasible'


def get_X(model,Q1,Q2,h1,h2,all_vars,num_vars):
    f1=gb.quicksum(h1[i] * all_vars[i] for i in range(n) if h1[i] != 0)+gb.quicksum(
        Q1[i][j] * all_vars[i] * all_vars[j]
        for i in range(n)
        for j in range(n)
        if Q1[i][j] != 0
    )
    f2=gb.quicksum(h2[i] * all_vars[i+n] for i in range(num_vars-n) if h2[i] != 0)+gb.quicksum(
        Q2[i][j] * all_vars[i+n] * all_vars[j+n]
        for i in range(num_vars-n)
        for j in range(num_vars-n)
        if Q2[i][j] != 0
    )
    model.setObjective(f1+f2, gb.GRB.MINIMIZE)
    model.optimize()
    if model.status != gb.GRB.OPTIMAL:
        return None
    return [1 if var.X > 0.5 else 0 for var in all_vars]


def Loading_constraints(model,path,all_vars,num_vars):
    data=[]
    try:
        with open(path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)

            # 跳过第一行标题
            next(csv_reader, None)

            # 读取剩余的所有行
            for row in csv_reader:
                data.append(row)

    except FileNotFoundError:
        print(f"错误：文件 '{path}' 未找到")
    except Exception as e:
        print(f"读取文件时出错：{e}")
    for dt in data:
        model.addConstr(gb.quicksum((1 - all_vars[i]) if dt[i+1] == 1 else all_vars[i] for i in range(num_vars)) >= 1)
    print('Loaded!')
    return model


def Planning_sampling(N,Val):

    master = gb.Model("UP_layer")
    # 定义规划变量
    # 定义节点类型变量
    W = master.addVars(n, vtype=gb.GRB.BINARY, name="W")
    master.addConstr(W[0] == 0)  # 根节点为交流
    # 定义节点连接变量
    U = master.addVars(n, n, vtype=gb.GRB.BINARY, name="U")
    for i in range(n):
        master.addConstr(U[i, i] == 0)
        for j in range(i + 1, n):
            master.addConstr(U[i, j] == U[j, i])
    # 定义线路类型变量
    C = master.addVars(n, n, vtype=gb.GRB.BINARY, name="C")
    #  上层模型约束
    #1 节点连接线路条数约束
    for i in range(n):
        master.addConstr(U.sum('*', i) >= L_min)
        master.addConstr(U.sum('*', i) <= L_max)
    #2 线路选型约束
    '''
    for i in range(n):
        for j in range(i + 1, n):
            master.addConstr(x.sum(i, j, '*') == 1)
            for k in range(k_line):
                master.addConstr(x[i, j, k] == x[j, i, k])
    '''
    #3 连通性约束
    Virtual_flow = master.addVars(n, n, lb=1 - n, ub=n - 1, vtype=gb.GRB.INTEGER, name="Virtual_flow")
    for i in range(n):
        master.addConstr(Virtual_flow[i, i] == 0)
        for j in range(n):
            if i != j:
                master.addConstr(Virtual_flow[i, j] <= (n - 1) * U[i, j])
                master.addConstr(Virtual_flow[i, j] >= (1 - n) * U[i, j])
                master.addConstr(Virtual_flow[i, j] == -Virtual_flow[j, i])
    master.addConstr(Virtual_flow.sum(0, '*') == n - 1)
    for i in range(1, n):
        master.addConstr(Virtual_flow.sum('*', i) == 1)
    master.addConstr(gb.quicksum(U[i,j] for i in range(n) for j in range(i+1, n)) == n-1)
    master.setParam('OutputFlag', 0)
    all_vars = []
    for i in range(n):
        all_vars.append(W[i])
    for i in range(n):
        for j in range(i + 1, n):
            all_vars.append(U[i, j])
    for i in range(n):
        for j in range(i + 1, n):
            all_vars.append(C[i, j])
    num_vars=len(all_vars)
    samples = []
    best_value=Val
    master.setParam("Threads", 0)
    master=Loading_constraints(master, '../抽样数据.CSV', all_vars,num_vars)
    k=0
    while len(samples) < N:
        if k>7:
            k=0
            print(datetime.now())
        else:
            k+=1
        h1 = np.random.uniform(-1, 1, 13)
        h2 = np.random.uniform(0, 1, num_vars - 13)
        A1 = np.random.rand(num_vars, 13) * 2 - 1
        A2 = np.random.rand(num_vars, num_vars - 13)
        Temp_1=A1.T @ A1
        Temp_2=A2.T @ A2
        Q1 = Temp_1 / np.max(np.abs(Temp_1))
        Q2 = Temp_2 / np.max(np.abs(Temp_2))
        X = get_X(master, Q1, Q2, h1, h2, all_vars, num_vars)
        if X is not None:
            f_op = Operation3(X, 1)
            if f_op is not None:
                samples.append([0] + X + [0, 0, f_op])
                save_csv([0] + X + [0, 0, f_op])
            else:
                save_csv([0] + X + [0, 0, 1e9])
            # best_value = f_op
            master.addConstr(gb.quicksum((1 - all_vars[i]) if X[i] == 1 else all_vars[i] for i in range(num_vars)) >= 1)
            print(len(samples))
            if len(samples) >= N:
                break




            # W, U, C = encode(X, n)
            # f_op = Operation3(W, U, C, 1)
            # if f_op == None:
            #     pass
            # else:
            #     samples.append((X))
            #     save_csv([0] + X + [0, 0, f_op])
            #     print(len(samples))
            #



def dijkstra_with_adj_dist(adj_matrix, dist_matrix, start, target):
    """
    使用邻接矩阵和距离矩阵求最短路径
    """
    n = len(adj_matrix)

    # 初始化距离数组
    distances = [float('inf')] * n
    distances[start] = 0

    # 优先队列：(距离, 节点)
    pq = [(0, start)]

    while pq:
        current_dist, current = heapq.heappop(pq)

        # 如果当前距离大于记录的最小距离，跳过
        if current_dist > distances[current]:
            continue

        # 到达目标节点
        if current == target:
            return current_dist

        # 遍历所有邻接节点
        for neighbor in range(n):
            if adj_matrix[current][neighbor] == 1:  # 有连接
                new_dist = current_dist + dist_matrix[current][neighbor]
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    heapq.heappush(pq, (new_dist, neighbor))

    return -1  # 不可达

def feature(X):
    feat=[]
    W,U,C = encode(X,n)
    edges=[]
    z=[]
    for i in range(n):
        for j in range(i+1,n):
            edges.append((i, j))
    for i,j in edges:
        if W[i] != W[j]:
            z.append(r_line[i][j][1])
            z.append(x_line[i][j][1])
            z.append(r_line[i][j][1] ** 2)
            z.append(x_line[i][j][1] ** 2)
        else:
            z.append(r_line[i][j][0])
            z.append(x_line[i][j][0])
            z.append(r_line[i][j][0] ** 2)
            z.append(x_line[i][j][0] ** 2)
    feat+=z

    deg=[]
    for i in range(n):
        deg.append(np.sum(U[i]).item())

    feat+=deg

    road=[]
    for i in range(n):
        if i not in [0,7,8,10,12]:
            road.append(dijkstra_with_adj_dist(U, Length, i, 0))
            road.append(dijkstra_with_adj_dist(C, Length, i, 7))
            road.append(dijkstra_with_adj_dist(U, Length, i, 8))
            road.append(dijkstra_with_adj_dist(C, Length, i, 10))
            road.append(dijkstra_with_adj_dist(U, Length, i, 12))
    feat+=road

    return feat











