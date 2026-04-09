import gurobipy as gb
import csv
import numpy as np
import random
from typing import List, Tuple, Dict
import matplotlib.pyplot as plt
import time
# 定义系统参数
n = 13  # 节点数
kk = 2  # 线路选型种类
N_d, T_line, T_cvt, T_p, T = 365, 40, 45, 40, 24
beta_line, beta_cvt = 0.05, 0.05  # 线路、换流器年维护费用系数
r = 0.075  # 贴现率
c_v, c_c, c_s, c_d, c_e = 1154.13e3, 1018.35e3, 400, 400, 10
L_min, L_max = 1, 3
M = 1000
S_vsc_ij = 5
S_c_load, S_c_wind, S_c_pv = 3, 3, 3
P_ess_max = 2.5
Q_vsc_max = 1
S_base = 10
V_min, V_max = 0.95, 1.05
gama = 0.8
S_ess = 10
Length = [
    [0.00, 1.61, 1.61, 3.22, 2.25, 3.22, 3.86, 3.86, 5.47, 4.51, 5.47, 6.11, 6.11],
    [1.61, 0.00, 2.25, 1.61, 1.61, 3.86, 2.25, 3.22, 3.86, 3.86, 4.83, 4.51, 5.47],
    [1.61, 2.25, 0.00, 3.86, 1.61, 1.61, 3.22, 2.25, 4.83, 3.86, 3.86, 5.47, 4.51],
    [3.22, 1.61, 3.86, 0.00, 2.25, 4.51, 1.61, 4.51, 2.25, 3.22, 5.47, 3.86, 4.83],
    [2.25, 1.61, 1.61, 2.25, 0.00, 2.25, 1.61, 1.61, 3.22, 2.25, 3.22, 3.86, 3.86],
    [3.22, 3.86, 1.61, 4.51, 2.25, 0.00, 3.86, 1.61, 5.47, 3.22, 2.25, 4.83, 3.86],
    [3.86, 2.25, 3.22, 1.61, 1.61, 3.86, 0.00, 2.25, 1.61, 1.61, 3.86, 2.25, 3.22],
    [3.86, 3.22, 2.25, 3.86, 1.61, 1.61, 2.25, 0.00, 3.86, 1.61, 1.61, 3.22, 2.25],
    [5.47, 3.86, 4.83, 2.25, 3.22, 5.47, 1.61, 3.86, 0.00, 2.25, 4.51, 1.61, 3.86],
    [4.51, 3.86, 3.86, 3.22, 2.25, 3.22, 1.61, 1.61, 2.25, 0.00, 2.25, 1.61, 1.61],
    [5.47, 4.83, 3.86, 5.47, 3.22, 2.25, 3.86, 1.61, 4.51, 2.25, 0.00, 3.86, 1.61],
    [6.11, 4.51, 5.47, 3.86, 3.86, 4.83, 2.25, 3.22, 1.61, 1.61, 3.86, 0.00, 2.25],
    [6.11, 5.47, 4.51, 4.83, 3.86, 3.86, 3.22, 2.25, 3.86, 1.61, 1.61, 2.25, 0.00]
]

# 线路阻抗
r__ = [[0 for _ in range(n)] for _ in range(n)]
x__ = [[0 for _ in range(n)] for _ in range(n)]
r__vsc = [[0 for _ in range(n)] for _ in range(n)]
x__vsc = [[0 for _ in range(n)] for _ in range(n)]
for i in range(n):
    for j in range(n):
        if j != i:
            r__[i][j] = Length[i][j] * 0.0598
            r__vsc[i][j] = r__[i][j]+0.2889
            x__[i][j] = Length[i][j] * 0.0979
            x__vsc[i][j] = x__[i][j]+0.7548

# 线路选材成本和容量
c_l = [147.648e3, 295.296e3]
S_line_k = [2.5, 5]

# 节点资源情况
n__ac =   [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1]
n__dc =   [0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0]
n__wind = [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0]
n__pv =   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
n__ess =  [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
#          1  2  3  4  5  6  7  8  9 10 11 12 13

# 24小时P、Q,DG最大出力
P_load = [6.40,6.20,6.00,5.90,5.80,5.60,5.50,5.60,5.90,6.40,6.80,7.00,7.20,7.30,7.00,6.60,6.80,7.50,7.90,7.80,7.60,7.20,6.90,6.60]
DG_total=[6.20,6.00,5.80,5.60,5.50,5.40,5.50,5.20,4.80,4.60,4.50,4.70,5.00,5.50,6.20,6.80,7.00,6.30,6.50,6.40,6.10,6.00,6.20,6.50]
#           0    1    2    3    4    5    6    7    8    9    10   11   12   13   14   15   16   17   18   19   20   21   22   23
Q_load = [0 for _ in range(T)]
for i in range(T):
    P_load[i] = P_load[i] / (sum(n__ac) + sum(n__dc))
    Q_load[i] = P_load[i] * 0.619*0.8
def Lower_layer_model_solving(W,U,x,L):

    m=gb.Model('m1')
    # 定义各节点电压
    V = m.addVars(n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
    V__svc = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="V__svc")
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])

    # 定义线路潮流
    P_tran = m.addVars(n, n, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="P_tran")
    Q_tran = m.addVars(n, n, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Q_tran")
    for t in range(T):
        for i in range(n):
            m.addConstr(P_tran[i, i, t] == 0)
            m.addConstr(Q_tran[i, i, t] == 0)
            for j in range(i + 1, n):
                if i != j:
                    m.addConstr(P_tran[i, j, t] == -P_tran[j, i, t])
                    m.addConstr(Q_tran[i, j, t] == -Q_tran[j, i, t])
    # 购电功率
    P_sub = m.addVars(24, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_sub")
    Q_sub = m.addVars(24, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_sub")
    # 储能充放电功率
    P_ess_ch = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
    P_ess_dis = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
    # 储能约束
    alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
    alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
    E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS)
    m.addConstr(E_k[0] == 5)
    for t in range(T):
        m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
        m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
        m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
        if t != 0:
            m.addConstr(E_k[t] == E_k[t - 1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
    # DG出力
    P_DG_813 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
    P_DG_911 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
    Q_DG_813 = m.addVars(2, 24, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Q_DG_813")
    Q_DG_911 = m.addVars(2, 24, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Q_DG_911")

    for t in range(T):
        m.addConstr(P_DG_813[0, t] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG_813[1, t] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG_911[0, t] <= DG_total[t] * 2.5 / 9)
        m.addConstr(P_DG_911[1, t] <= DG_total[t] * 2.5 / 9)

    f_op = 0

    for t in range(T):
        f_op += c_s * P_sub[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
        f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[0, t])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[0, t])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[1, t])
        f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[1, t])
    # 有功功率平衡方程
    for i in range(n):
        for t in range(T):
            if i == 0:
                m.addConstr(P_sub[t] - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 5:
                m.addConstr(
                    0 - P_load[t] * (n__ac[i] + n__dc[i]) + P_ess_dis[t] - P_ess_ch[t] - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 7:
                m.addConstr(
                    P_DG_813[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 8:
                m.addConstr(
                    P_DG_911[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 10:
                m.addConstr(
                    P_DG_911[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 12:
                m.addConstr(
                    P_DG_813[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            else:
                m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)

    # 无功功率平衡方程
    for i in range(n):
        for t in range(T):
            if i == 0:
                m.addConstr(Q_sub[t] - Q_tran.sum(i, '*', t) * S_base == 0)
            elif i == 7:
                m.addConstr((Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            elif i == 8:
                m.addConstr((Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            elif i == 10:
                m.addConstr((Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            elif i == 12:
                m.addConstr((Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            else:
                m.addConstr((0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base)*(1-W[i])==0)
    # 电压方程
    for i in range(n):
        for j in range(n):
            if i != j:
                #
                S_line = S_line_k[x[i][j]]
                for t in range(T):
                    m.addConstr(U[i][j]*((1-L[i][j]*W[i])*V[i,t]+(L[i][j]*W[i]-L[i][j]*W[j])*V__svc[i,j,t]-(1-L[i][j]*W[j])*V[i,t])==
                                (1-L[i][j])*(r__[i][j] * P_tran[i, j, t] + x__[i][j] * Q_tran[i, j, t])+
                                L[i][j]*(r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t]))
                    #
                    m.addConstr(Q_tran[i, j, t] <= L[i][j] * (Q_vsc_max - M) + M)
                    m.addConstr(Q_tran[i, j, t] >= -1 * (L[i][j] * (Q_vsc_max - M) + M))
                    #
                    m.addConstr(P_tran[i, j, t] <= gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] >= -gama * S_line / S_base)

                    m.addConstr(Q_tran[i, j, t] <= gama * S_line / S_base)
                    m.addConstr(Q_tran[i, j, t] >= -gama * S_line / S_base)

                    m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
    m.setObjective(f_op, gb.GRB.MINIMIZE)
    m.optimize()
    # for v in m.getVars():
    #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
    #         print(v.VarName, v.X)
    if m.status == gb.GRB.OPTIMAL:
        return m.objVal
    else:
        return 9e13


_W=[0,0,1,0,1,0,0,0,0,0,1,1,1]
_U=[[0,1,0,0,0,0,0,0,0,0,0,0,0],[1,0,0,1,0,0,0,0,0,0,0,0,0],[0,0,0,0,1,0,0,0,0,0,0,0,0],[0,1,0,0,0,0,1,0,0,0,0,0,0],
   [0,0,1,0,0,0,0,0,0,0,1,0,0],[0,0,0,0,0,1,0,1,0,0,0,0,0],[0,0,0,1,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,0,0,0,1,1,0,0],
   [0,0,0,0,0,0,1,0,0,0,0,0,0],[0,0,0,0,0,0,1,1,0,0,0,0,0],[0,0,0,0,1,0,0,1,0,0,0,0,1],[0,0,0,0,0,0,0,0,0,0,0,0,1],
   [0,0,0,0,0,0,0,0,0,0,1,1,0]]
_x=[[[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],[[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],
   [[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],[[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],
   [[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],[[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],
   [[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],[[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],
   [[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],[[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],
   [[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],[[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]],
   [[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0],[1,0]]]
for i in range(n):
    for j in range(n):
        _x[i][j]=0

_L = [[0 for _ in range(n)] for _ in range(n)]
for i in range(n):
    for j in range(n):
        _L[i][j] = abs(_W[i] - _W[j])

C_line = 0
for i in range(n):
    for j in range(n):
            C_line += 0.5 * c_l[_x[i][j]] * Length[i][j]*_U[i][j]

S_vsc = 0
for i in range(n):
    for j in range(n):
        S_vsc += 0.5 * S_vsc_ij * _U[i][j]* _L[i][j]
S_c = 0
for i in range(n):
    S_c = S_c + S_c_load * (n__ac[i] * _W[i] + n__dc[i] * (1 - _W[i]))
    S_c = S_c + S_c_wind * (_W[i] + 2 * (1 - _W[i])) * n__wind[i]
    S_c = S_c + S_c_pv * (1 - _W[i]) * n__pv[i]
C_cvt = c_c * S_c + c_v * S_vsc

C_invest = C_line + C_cvt


C_operation=0
f_op=Lower_layer_model_solving(_W,_U,_x,_L)
# C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
for d in range(T_p):
    C_operation += N_d * f_op / pow(1 + r, d + 1)
for d in range(T_line):
    C_operation += beta_line * C_line / pow(1 + r, d + 1)
for d in range(T_cvt):
    C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
print(C_operation+C_invest)
print(C_line)
print(C_cvt)
'''


class IntegerOptimizationGA:
    def __init__(self, n: int, pop_size: int = 100, crossover_rate: float = 0.8,
                 mutation_rate: float = 0.2, max_generations: int = 500):
        """
        初始化遗传算法参数

        Args:
            n: 问题规模
            pop_size: 种群大小
            crossover_rate: 交叉概率
            mutation_rate: 变异概率
            max_generations: 最大迭代次数
        """
        self.n = n
        self.pop_size = pop_size
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.max_generations = max_generations

        # 决策变量维度
        self.W_dim = n  # 1*n
        self.U_dim = (n, n)  # n*n 对称
        # self.x_dim = (n, n, 2)  # n*n*2 对称
        self.x_dim = (n, n)  # n*n*2 对称

    def create_individual(self) -> Dict:
        """
        创建一个个体的染色体

        Returns:
            包含所有决策变量的字典
        """
        # W: 1*n 0-1变量
        W = np.random.randint(0, 2, self.W_dim)

        # U: n*n 对称0-1矩阵
        U = np.random.randint(0, 2, self.U_dim)
        U = np.triu(U)  # 取上三角
        U = U + U.T - np.diag(np.diag(U))  # 构建对称矩阵

        # x: n*n*2 对称三维数组
        x = np.random.randint(0, 2, self.x_dim)
        # 确保对称性: x[i,j,k] = x[j,i,k]
        x = np.triu(x)  # 取上三角
        x = x + x.T - np.diag(np.diag(x))  # 构建对称矩阵
        # for i in range(self.n):
        #     for j in range(i + 1, self.n):
        #         x[j, i] = x[i, j]

        return {'W': W, 'U': U, 'x': x}

    def population_initialization(self) -> List[Dict]:
        """初始化种群"""
        return [self.create_individual() for _ in range(self.pop_size)]#返回初始解集

    def objective_function(self, individual: Dict) -> float:
        """
        目标函数 - 这里需要根据你的具体问题来定义

        Args:
            individual: 个体染色体

        Returns:
            目标函数值z (最小化)
        """
        W = individual['W']
        U = individual['U']
        x = individual['x']
        L = [[0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                L[i][j] = abs(W[i] - W[j])
        # 示例目标函数 - 请根据你的具体问题修改

        C_line = 0
        for i in range(n):
            for j in range(n):
                for k in range(kk):

                    C_line += 0.5 * c_l[x[i][j]] * Length[i][j] * U[i][j]

        S_vsc = 0
        for i in range(n):
            for j in range(n):
                S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
        S_c = 0
        for i in range(n):
            S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
            S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
            S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
        C_cvt = c_c * S_c + c_v * S_vsc
        C_invest = C_line + C_cvt
        C_operation = 0
        # f_op=0
        # try:
        #     f_op = Lower_layer_model_solving(W, U, x,L)
        # except :
        #     f_op = 9e9
        #
        #
        #
        # # C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
        # for d in range(T_p):
        #     C_operation += N_d * f_op / pow(1 + r, d + 1)
        # for d in range(T_line):
        #     C_operation += beta_line * C_line / pow(1 + r, d + 1)
        # for d in range(T_cvt):
        #     C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
        z = C_invest+C_operation

        # 可以添加约束惩罚项
        penalty = self.constraint_violation(individual)
        z += penalty * 9e13  # 惩罚系数

        return z

    def constraint_violation(self, individual: Dict) -> float:
        """
        计算约束违反程度

        Args:
            individual: 个体染色体

        Returns:
            约束违反程度
        """
        W = individual['W']
        U = individual['U']
        x = individual['x']

        violation = 0

        # 检查U的对称性约束
        U_symmetry_violation = np.sum(np.abs(U - U.T)) / 2
        violation += U_symmetry_violation

        # 检查x的对称性约束
        x_symmetry_violation = 0
        x_symmetry_violation = np.sum(np.abs(x - x.T)) / 2
        # for i in range(self.n):
        #     for j in range(self.n):
                # for k in range(2):
                #     if x[i, j, k] != x[j, i, k]:
                #         x_symmetry_violation += 1
        violation += x_symmetry_violation

        # # 节点连接线路条数约束
        U_connection_lines_violation=0
        for i in range(self.n):
            if sum(U[i]<L_min):
                U_connection_lines_violation+=1
            elif sum(U[i]>L_max):
                U_connection_lines_violation+=1
        violation +=U_connection_lines_violation
        # # 线路选型约束
        # x_kinds_violation = 0
        # for i in range(self.n):
        #     for j in range(self.n):
        #         if sum(x[i][j])!=1:
        #             x_kinds_violation+=1
        # violation += x_kinds_violation

        return violation

    def selection(self, population: List[Dict], fitness: List[float]) -> List[Dict]:
        """
        锦标赛选择

        Args:
            population: 种群
            fitness: 适应度值

        Returns:
            被选择的个体
        """
        selected = []
        tournament_size = 3

        for _ in range(self.pop_size):
            # 随机选择tournament_size个个体进行比赛
            tournament_indices = random.sample(range(len(population)), tournament_size)
            tournament_fitness = [fitness[i] for i in tournament_indices]

            # 选择适应度最好的 (最小化问题，所以找最小值)
            winner_idx = tournament_indices[np.argmin(tournament_fitness)]
            selected.append(population[winner_idx])

        return selected

    def crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        """
        交叉操作

        Args:
            parent1, parent2: 父代个体

        Returns:
            两个子代个体
        """
        if random.random() > self.crossover_rate:
            return parent1.copy(), parent2.copy()

        child1 = {}
        child2 = {}

        # W的交叉 (单点交叉)
        W1, W2 = self._crossover_1d(parent1['W'], parent2['W'])
        child1['W'] = W1
        child2['W'] = W2

        # U的交叉 (考虑到对称性)
        U1, U2 = self._crossover_symmetric_matrix(parent1['U'], parent2['U'])
        child1['U'] = U1
        child2['U'] = U2

        # x的交叉 (考虑到对称性)
        # x1, x2 = self._crossover_3d_symmetric(parent1['x'], parent2['x'])
        x1, x2 = self._crossover_symmetric_matrix(parent1['x'], parent2['x'])
        child1['x'] = x1
        child2['x'] = x2

        return child1, child2

    def _crossover_1d(self, arr1: np.ndarray, arr2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """一维数组交叉"""
        crossover_point = random.randint(1, len(arr1) - 1)
        child1 = np.concatenate([arr1[:crossover_point], arr2[crossover_point:]])
        child2 = np.concatenate([arr2[:crossover_point], arr1[crossover_point:]])
        return child1, child2

    def _crossover_symmetric_matrix(self, mat1: np.ndarray, mat2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """对称矩阵交叉"""
        n = mat1.shape[0]
        # 只交叉上三角部分，然后构建对称矩阵
        triu_indices = np.triu_indices(n)

        child1_upper = mat1[triu_indices].copy()
        child2_upper = mat2[triu_indices].copy()

        crossover_point = random.randint(1, len(child1_upper) - 1)

        # 交叉
        temp = child1_upper[crossover_point:].copy()
        child1_upper[crossover_point:] = child2_upper[crossover_point:]
        child2_upper[crossover_point:] = temp

        # 重建对称矩阵
        child1 = np.zeros((n, n))
        child2 = np.zeros((n, n))

        child1[triu_indices] = child1_upper
        child2[triu_indices] = child2_upper

        child1 = child1 + child1.T - np.diag(np.diag(child1))
        child2 = child2 + child2.T - np.diag(np.diag(child2))

        return child1.astype(int), child2.astype(int)

    def _crossover_3d_symmetric(self, arr3d1: np.ndarray, arr3d2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """对称三维数组交叉"""
        n = arr3d1.shape[0]
        child1 = arr3d1.copy()
        child2 = arr3d2.copy()

        # 对每个二维切片进行对称交叉
        for k in range(arr3d1.shape[2]):
            slice1, slice2 = self._crossover_symmetric_matrix(arr3d1[:, :, k], arr3d2[:, :, k])
            child1[:, :, k] = slice1
            child2[:, :, k] = slice2

        return child1, child2

    def mutation(self, individual: Dict) -> Dict:
        """
        变异操作

        Args:
            individual: 要变异的个体

        Returns:
            变异后的个体
        """
        mutated = individual.copy()

        # W的变异
        if random.random() < self.mutation_rate:
            idx = random.randint(0, self.n - 1)
            mutated['W'][idx] = 1 - mutated['W'][idx]

        # U的变异 (保持对称性)
        if random.random() < self.mutation_rate:
            i, j = random.randint(0, self.n - 1), random.randint(0, self.n - 1)
            new_value = 1 - mutated['U'][i, j]
            mutated['U'][i, j] = new_value
            mutated['U'][j, i] = new_value  # 保持对称

        # x的变异 (保持对称性)
        if random.random() < self.mutation_rate:
            i, j = random.randint(0, self.n - 1), random.randint(0, self.n - 1)
            new_value = 1 - mutated['x'][i, j]
            mutated['x'][i, j] = new_value
            mutated['x'][j, i] = new_value  # 保持对称
        # if random.random() < self.mutation_rate:
        #     i, j = random.randint(0, self.n - 1), random.randint(0, self.n - 1)
        #     k = random.randint(0, 1)
        #     new_value = 1 - mutated['x'][i, j, k]
        #     mutated['x'][i, j, k] = new_value
        #     mutated['x'][j, i, k] = new_value  # 保持对称

        return mutated

    def run(self) -> Tuple[Dict, float, List[float]]:
        """
        运行遗传算法

        Returns:
            best_individual: 最优个体
            best_fitness: 最优适应度
            fitness_history: 适应度历史
        """
        # 初始化种群
        population = self.population_initialization()
        best_fitness = float('inf')
        best_individual = None
        fitness_history = []

        for generation in range(self.max_generations):
            # 计算适应度
            fitness = [self.objective_function(ind) for ind in population]

            # 更新最优解
            current_best_fitness = min(fitness)
            if current_best_fitness < best_fitness:
                best_fitness = current_best_fitness
                best_individual = population[np.argmin(fitness)].copy()

            fitness_history.append(best_fitness)

            # 选择
            selected = self.selection(population, fitness)

            # 交叉和变异
            new_population = []
            for i in range(0, len(selected), 2):
                if i + 1 < len(selected):
                    child1, child2 = self.crossover(selected[i], selected[i + 1])
                    new_population.extend([self.mutation(child1), self.mutation(child2)])
                else:
                    new_population.append(self.mutation(selected[i]))

            population = new_population

            # 精英保留
            if best_individual is not None:
                population[0] = best_individual.copy()

            if generation % 50 == 0:
                print(f"Generation {generation}, Best Fitness: {best_fitness:.4f}")

        return best_individual, best_fitness, fitness_history


# 使用示例
def main():

    # 设置参数
    n = 13  # 问题规模
    ga = IntegerOptimizationGA(n=n, pop_size=100, max_generations=50)

    # 运行算法
    best_solution, best_fitness, fitness_history = ga.run()

    print(f"\n最优解的目标函数值: {best_fitness:.4f}")
    print(f"W: {best_solution['W']}")
    print(f"U矩阵:")
    print(best_solution['U'])
    print(f"x的形状: {best_solution['x'].shape}")

    # 绘制收敛曲线
    plt.figure(figsize=(10, 6))
    plt.plot(fitness_history)
    plt.title('Genetic Algorithm Convergence')
    plt.xlabel('Generation')
    plt.ylabel('Best Fitness')
    plt.grid(True)
    plt.show()

    # 验证约束满足情况
    violation = ga.constraint_violation(best_solution)
    print(f"约束违反程度: {violation}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"程序运行时间: {elapsed_time:.4f} 秒")
'''