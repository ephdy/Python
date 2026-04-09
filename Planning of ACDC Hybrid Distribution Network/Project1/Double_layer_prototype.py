# 定义系统参数
N = 13  # 节点数
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
r__ = [[0 for _ in range(N)] for _ in range(N)]
x__ = [[0 for _ in range(N)] for _ in range(N)]
r__vsc = [[0 for _ in range(N)] for _ in range(N)]
x__vsc = [[0 for _ in range(N)] for _ in range(N)]
for i in range(N):
    for j in range(N):
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
    Q_load[i] = P_load[i] * 0.619*1*0.8

import random
import numpy as np
from deap import base, creator, tools ,algorithms
import gurobipy as gb
import time
import multiprocessing
from collections import deque
from Gurobi_solving import *
# def Lower_layer_model_solving(W,U,x,L,mode=0):
#
#     m=gb.Model('m1')
#     #
#     if mode==1:
#         mu = m.addVar(lb=1, ub=2, vtype=gb.GRB.CONTINUOUS, name="mu")
#         delta = m.addVar(ub=0.4, vtype=gb.GRB.CONTINUOUS, name="delta")
#         m.addConstr(delta <= mu * 0.2)
#         f2=-delta
#     # 定义各节点电压
#     V = m.addVars(N, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
#     V__svc = m.addVars(N, N, T, vtype=gb.GRB.CONTINUOUS, name="V__svc")
#     for i in range(N):
#         for j in range(i + 1, N):
#             for t in range(T):
#                 m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
#                 m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
#     if mode == 1:
#         Scene_V = m.addVars(N, T, 2, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
#         Scene_V__svc = m.addVars(N, N, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
#         for scene in range(2):
#             for i in range(N):
#                 for j in range(i + 1, N):
#                     for t in range(T):
#                         m.addConstr(Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene])
#                         m.addConstr(Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene])
#     # 定义线路潮流
#     P_tran = m.addVars(N, N, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="P_tran")
#     Q_tran = m.addVars(N, N, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Q_tran")
#     for t in range(T):
#         for i in range(N):
#             m.addConstr(P_tran[i, i, t] == 0)
#             m.addConstr(Q_tran[i, i, t] == 0)
#             for j in range(i + 1, N):
#                 if i != j:
#                     m.addConstr(P_tran[i, j, t] == -P_tran[j, i, t])
#                     m.addConstr(Q_tran[i, j, t] == -Q_tran[j, i, t])
#     if mode == 1:
#         Scene_P_tran = m.addVars(N, N, T, 2,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
#         Scene_Q_tran = m.addVars(N, N, T, 2,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
#         for scene in range(2):
#             for t in range(T):
#                 for i in range(N):
#                     m.addConstr(Scene_P_tran[i, i, t, scene] == 0)
#                     m.addConstr(Scene_Q_tran[i, i, t, scene] == 0)
#                     for j in range(i + 1, N):
#                         if i != j:
#                             m.addConstr(Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene])
#                             m.addConstr(Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene])
#     # 购电功率
#     P_sub = m.addVars(24, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_sub")
#     Q_sub = m.addVars(24, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_sub")
#     if mode == 1:
#         Scene_P_sub = m.addVars(24, 2, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
#         Scene_Q_sub = m.addVars(24, 2, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")
#     # 储能充放电功率
#     P_ess_ch = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
#     P_ess_dis = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
#     # 储能约束
#     alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
#     alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
#     E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS)
#     m.addConstr(E_k[0] == 5)
#     for t in range(T):
#         m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
#         m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
#         m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
#         if t != 0:
#             m.addConstr(E_k[t] == E_k[t - 1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
#     m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
#     if mode == 1:
#         Scene_P_ess_ch = m.addVars(24, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
#         Scene_P_ess_dis = m.addVars(24, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
#         Scene_alpha__dis = m.addVars(T, 2, vtype=gb.GRB.BINARY)
#         Scene_alpha__ch = m.addVars(T, 2, vtype=gb.GRB.BINARY)
#         Scene_E_k = m.addVars(T, 2, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS)
#         for scene in range(2):
#             m.addConstr(Scene_E_k[0, scene] == 5)
#             for t in range(T):
#                 m.addConstr(Scene_alpha__ch[t,scene] + Scene_alpha__dis[t,scene] <= 1)
#                 m.addConstr(Scene_P_ess_dis[t,scene] <= Scene_alpha__dis[t,scene] * P_ess_max)
#                 m.addConstr(Scene_P_ess_ch[t,scene] <= Scene_alpha__ch[t,scene] * P_ess_max)
#                 if t != 0:
#                     m.addConstr(Scene_E_k[t,scene] == Scene_E_k[t - 1,scene] + Scene_P_ess_ch[t,scene] * 0.9 - Scene_P_ess_dis[t,scene] / 0.9)
#             m.addConstr(Scene_P_ess_ch.sum('*', scene) * 0.9 == Scene_P_ess_dis.sum('*', scene) / 0.9)
#     # DG出力
#     P_DG_813 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
#     P_DG_911 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
#     Q_DG_813 = m.addVars(2, 24, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Q_DG_813")
#     Q_DG_911 = m.addVars(2, 24, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Q_DG_911")
#
#     for t in range(T):
#         m.addConstr(P_DG_813[0, t] <= DG_total[t] * 2 / 9)
#         m.addConstr(P_DG_813[1, t] <= DG_total[t] * 2 / 9)
#         m.addConstr(P_DG_911[0, t] <= DG_total[t] * 2.5 / 9)
#         m.addConstr(P_DG_911[1, t] <= DG_total[t] * 2.5 / 9)
#     if mode == 1:
#         Scene_P_DG_813 = m.addVars(2, 24, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_813")
#         Scene_P_DG_911 = m.addVars(2, 24, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_911")
#         Scene_Q_DG_813 = m.addVars(2, 24, 2, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
#         Scene_Q_DG_911 = m.addVars(2, 24, 2, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")
#
#         for t in range(T):
#             m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2.0 / 9*(mu-delta))
#             m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2.0 / 9*(mu-delta))
#             m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9*(mu-delta))
#             m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9*(mu-delta))
#             m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2.0 / 9*(mu+delta))
#             m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2.0 / 9*(mu+delta))
#             m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9*(mu+delta))
#             m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9*(mu+delta))
#
#
#     #目标函数
#     f_op = 0
#
#     for t in range(T):
#         f_op += c_s * P_sub[t]
#         f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
#         f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[0, t])
#         f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[0, t])
#         f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[1, t])
#         f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[1, t])
#     # 有功功率平衡方程
#     for i in range(N):
#         for t in range(T):
#             if i == 0:
#                 m.addConstr(P_sub[t] - P_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(Scene_P_sub[t, 0] - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
#                     m.addConstr(Scene_P_sub[t, 1] - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
#             elif i == 5:
#                 m.addConstr(
#                     0 - P_load[t] * (n__ac[i] + n__dc[i]) + P_ess_dis[t] - P_ess_ch[t] - P_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(
#                         0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, 0] - Scene_P_ess_ch[
#                             t, 0] - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
#                     m.addConstr(
#                         0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, 1] - Scene_P_ess_ch[
#                             t, 1] - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
#             elif i == 7:
#                 m.addConstr(
#                     P_DG_813[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(
#                         Scene_P_DG_813[0, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        0) * S_base == 0)
#                     m.addConstr(
#                         Scene_P_DG_813[0, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        1) * S_base == 0)
#             elif i == 8:
#                 m.addConstr(
#                     P_DG_911[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(
#                         Scene_P_DG_911[0, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        0) * S_base == 0)
#                     m.addConstr(
#                         Scene_P_DG_911[0, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        1) * S_base == 0)
#             elif i == 10:
#                 m.addConstr(
#                     P_DG_911[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(
#                         Scene_P_DG_911[1, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        0) * S_base == 0)
#                     m.addConstr(
#                         Scene_P_DG_911[1, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        1) * S_base == 0)
#             elif i == 12:
#                 m.addConstr(
#                     P_DG_813[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(
#                         Scene_P_DG_813[1, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        0) * S_base == 0)
#                     m.addConstr(
#                         Scene_P_DG_813[1, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
#                                                                                                        1) * S_base == 0)
#             else:
#                 m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
#                     m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
#
#     # 无功功率平衡方程
#     for i in range(N):
#         for t in range(T):
#             if i == 0:
#                 m.addConstr(Q_sub[t] - Q_tran.sum(i, '*', t) * S_base == 0)
#                 if mode == 1:
#                     m.addConstr(Scene_Q_sub[t, 0] - Scene_Q_tran.sum(i, '*', t, 0) * S_base == 0)
#                     m.addConstr(Scene_Q_sub[t, 1] - Scene_Q_tran.sum(i, '*', t, 1) * S_base == 0)
#             elif i == 7:
#                 m.addConstr((Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
#                 if mode == 1:
#                     m.addConstr(
#                         (Scene_Q_DG_813[0, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
#                     m.addConstr(
#                         (Scene_Q_DG_813[0, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
#             elif i == 8:
#                 m.addConstr((Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
#                 if mode == 1:
#                     m.addConstr(
#                         (Scene_Q_DG_911[0, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
#                     m.addConstr(
#                         (Scene_Q_DG_911[0, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
#
#             elif i == 10:
#                 m.addConstr((Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
#                 if mode == 1:
#                     m.addConstr(
#                         (Scene_Q_DG_911[1, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
#                     m.addConstr(
#                         (Scene_Q_DG_911[1, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
#             elif i == 12:
#                 m.addConstr((Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
#                 if mode == 1:
#                     m.addConstr(
#                         (Scene_Q_DG_813[1, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
#                     m.addConstr(
#                         (Scene_Q_DG_813[1, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
#             else:
#                 m.addConstr((0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base)*(1-W[i])==0)
#                 if mode == 1:
#                     m.addConstr(
#                         (0 - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
#                     m.addConstr(
#                         (0 - Q_load[t] * (n__ac[i] + n__dc[i]) -
#                          Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
#     # 电压方程
#     for i in range(N):
#         for j in range(N):
#             if i != j:
#                 #
#                 S_line = S_line_k[x[i][j]]
#                 for t in range(T):
#                     m.addConstr(U[i][j]*((1-L[i][j]*W[i])*V[i,t]+(L[i][j]*W[i]-L[i][j]*W[j])*V__svc[i,j,t]-(1-L[i][j]*W[j])*V[i,t])==
#                                 (1-L[i][j])*(r__[i][j] * P_tran[i, j, t] + x__[i][j] * Q_tran[i, j, t])+
#                                 L[i][j]*(r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t]))
#                     #
#                     m.addConstr(Q_tran[i, j, t] <= L[i][j] * (Q_vsc_max - M) + M)
#                     m.addConstr(Q_tran[i, j, t] >= -1 * (L[i][j] * (Q_vsc_max - M) + M))
#                     #
#                     m.addConstr(P_tran[i, j, t] <= gama * S_line / S_base)
#                     m.addConstr(P_tran[i, j, t] >= -gama * S_line / S_base)
#
#                     m.addConstr(Q_tran[i, j, t] <= gama * S_line / S_base)
#                     m.addConstr(Q_tran[i, j, t] >= -gama * S_line / S_base)
#
#                     m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
#                     m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
#                     m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
#                     m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
#                     if mode == 1:
#                         for scene in range(2):
#                             m.addConstr(U[i][j] * (
#                                     (1 - L[i][j] * W[i]) * Scene_V[i, t, scene]
#                                     + (L[i][j] * W[i] - L[i][j] * W[j]) * Scene_V__svc[i, j, t, scene]
#                                     - (1 - L[i][j] * W[j]) * Scene_V[j, t, scene]) ==
#                                     (1 - L[i][j]) * (r__[i][j] * Scene_P_tran[i, j, t, scene] + x__[i][j] * Scene_Q_tran[i, j, t, scene])
#                                     +L[i][j] * (r__vsc[i][j] * Scene_P_tran[i, j, t, scene] - x__vsc[i][j] * Scene_Q_tran[i, j, t, scene]))
#                             #
#                             m.addConstr(Scene_Q_tran[i, j, t, scene] <= L[i][j] * (Q_vsc_max - M) + M)
#                             m.addConstr(Scene_Q_tran[i, j, t, scene] >= -1 * (L[i][j] * (Q_vsc_max - M) + M))
#                             #
#                             m.addConstr(Scene_P_tran[i, j, t, scene] <= gama * S_line / S_base)
#                             m.addConstr(Scene_P_tran[i, j, t, scene] >= -gama * S_line / S_base)
#
#                             m.addConstr(Scene_Q_tran[i, j, t, scene] <= gama * S_line / S_base)
#                             m.addConstr(Scene_Q_tran[i, j, t, scene] >= -gama * S_line / S_base)
#
#                             m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[i, j, t, scene] <= 1.41 * gama * S_line / S_base)
#                             m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[i, j, t, scene] >= -1.41 * gama * S_line / S_base)
#                             m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[i, j, t, scene] <= 1.41 * gama * S_line / S_base)
#                             m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[i, j, t, scene] >= -1.41 * gama * S_line / S_base)
#
#     if mode==1:
#         m.setObjective(f2, gb.GRB.MINIMIZE)
#     else:
#         m.setObjective(f_op, gb.GRB.MINIMIZE)
#
#     m.setParam('LogToConsole', 0)
#     m.optimize()
#     # for v in m.getVars():
#     #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
#     #         print(v.VarName, v.X)
#     if m.status == gb.GRB.OPTIMAL:
#         return m.objVal
#     else:
#         return 9e8
# ---------------------------
# 参数设置
# ---------------------------


# ---------------------------
# 工具函数
# ---------------------------
def repair_U(U, min_row=1, max_row=3):
    """
    修复邻接矩阵 U
    """
    n = U.shape[0]

    # 行和约束
    for i in range(n):
        row_sum = U[i].sum()

        if row_sum < min_row:
            zeros = [j for j in range(n) if j != i and U[i,j] == 0]
            if zeros:
                j = random.choice(zeros)
                U[i,j] = U[j,i] = 1

        elif row_sum > max_row:
            ones = [j for j in range(n) if j != i and U[i,j] == 1]
            random.shuffle(ones)
            while U[i].sum() > max_row and ones:
                j = ones.pop()
                U[i,j] = U[j,i] = 0

    # 连通性约束（所有节点都能到达根节点0）
    def bfs_connected(U, start=0):
        visited = [False]*n
        queue = deque([start])
        visited[start] = True
        while queue:
            u = queue.popleft()
            for v in range(n):
                if U[u,v] == 1 and not visited[v]:
                    visited[v] = True
                    queue.append(v)
        return visited

    visited = bfs_connected(U, 0)
    disconnected = [i for i, flag in enumerate(visited) if not flag]

    while disconnected:
        node = disconnected.pop()
        connected_nodes = [i for i, flag in enumerate(visited) if flag]
        j = random.choice(connected_nodes)
        U[node,j] = U[j,node] = 1
        visited = bfs_connected(U, 0)
        disconnected = [i for i, flag in enumerate(visited) if not flag]

    return U

def repair_individual(ind, min_U_row=1, max_U_row=3):
    """
    修复整个个体 ind = encode(W, U, X)
    """
    # 解码
    W, U, X = decode(ind)

    # -------- 修复 W --------
    # 示例：强制 W[0]=0，或者根据你自己规则
    W[0] = 0
    # 如果有其它 W 约束可在这里添加

    # -------- 修复 U --------
    U = repair_U(U, min_row=min_U_row, max_row=max_U_row)

    # -------- 修复 X --------
    # 如果 X 有约束，可在这里添加
    # 例如：保证 X[i,j] 在允许值范围内
    # X = repair_X(X)  # 可自定义

    # 重新编码
    new_ind = encode(W, U, X)
    ind[:] = new_ind  # 更新个体

    return ind
def upper_tri_indices(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]

UPPER_IDX = upper_tri_indices(N)
NUM_UPPER = len(UPPER_IDX)
CHROM_LENGTH = N + 2 * NUM_UPPER  # 编码长度 = W + U上三角 + X上三角

def decode(individual):
    """将个体向量解码为 W, U, X"""
    W = np.array(individual[:N], dtype=int)
    U_flat = np.array(individual[N:N + NUM_UPPER], dtype=int)
    X_flat = np.array(individual[N + NUM_UPPER:], dtype=int)

    U = np.zeros((N, N), dtype=int)
    X = np.zeros((N, N), dtype=int)
    for k, (i, j) in enumerate(UPPER_IDX):
        U[i, j] = U[j, i] = U_flat[k]
        X[i, j] = X[j, i] = X_flat[k]
    return W, U, X
'''
def repair_U(U):
    """修复U使其满足 1 ≤ 行和 ≤ 3"""
    n = U.shape[0]
    for i in range(n):
        row_sum = U[i].sum()
        if row_sum < 1:
            zeros = [j for j in range(n) if j != i and U[i, j] == 0]
            if zeros:
                j = random.choice(zeros)
                U[i, j] = U[j, i] = 1
        elif row_sum > 3:
            ones = [j for j in range(n) if j != i and U[i, j] == 1]
            random.shuffle(ones)
            while U[i].sum() > 3 and ones:
                j = ones.pop()
                U[i, j] = U[j, i] = 0
    return U
'''
def encode(W, U, X):
    """将 W,U,X 打包回向量"""
    genes = list(W)
    for (i, j) in UPPER_IDX:
        genes.append(U[i, j])
    for (i, j) in UPPER_IDX:
        genes.append(X[i, j])
    return genes

# ---------------------------
# 目标函数（适应度）
# ---------------------------
def evaluate(individual):
    W, U, X = decode(individual)
    U = repair_U(U)
    new_ind = encode(W, U, X)
    individual[:] = new_ind  # 更新个体（保证可行）
    L = [[0 for _ in range(N)] for _ in range(N)]
    C_line = 0
    S_vsc = 0
    S_c = 0
    for i in range(N):
        S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
        S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
        S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
        for j in range(N):
            L[i][j] = abs(W[i] - W[j])
            S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
            for k in range(kk):
                C_line += 0.5 * c_l[X[i][j]] * Length[i][j] * U[i][j]
    C_cvt = c_c * S_c + c_v * S_vsc
    C_invest = C_line + C_cvt
    C_operation = 0
    f_op = Lower_layer_solving(W, U, X,n=13,T=T,mode=0)


    # C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
    for d in range(T_p):
        C_operation += N_d * f_op / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
    f1 = C_invest + C_operation
    # f2 = Lower_layer_model_solving(W, U, X, L,1)
    z=f1
    return (z,)  # DEAP 要求返回tuple

# ---------------------------
# 注册遗传算法要素
# ---------------------------
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()
toolbox.register("attr_bool", random.randint, 0, 1)
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_bool, CHROM_LENGTH)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

toolbox.register("mate", tools.cxUniform, indpb=0.6)
toolbox.register("mutate", tools.mutFlipBit, indpb=0.3)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("evaluate", evaluate)

# ---------------------------
# 主过程
# ---------------------------
def main(seed=42, pop_size=200, generations=60, n_jobs=None):
    random.seed(seed)
    pool = multiprocessing.Pool(processes=n_jobs)
    toolbox.register("map", pool.map)
    pop = toolbox.population(n=pop_size)

    # 初始修复，确保可行
    for ind in pop:
        # W, U, X = decode(ind)
        # W[0]=0
        # U = repair_U(U)
        # ind[:] = encode(W, U, X)
        ind=repair_individual(ind)

    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("min", np.min)

    pop, log = algorithms.eaSimple(pop, toolbox,
                              cxpb=0.5, mutpb=0.3,
                              ngen=generations,
                              stats=stats,
                              halloffame=hof,
                              verbose=True)
    pool.close()
    pool.join()
    best = hof[0]
    W, U, X = decode(best)
    print("\n=== 最优可行解 ===")
    print("W:", W)
    print("U:\n", U)
    print("行和:", U.sum(axis=1))
    print("X:\n", X)
    print(f"目标值 z = {best.fitness.values[0]:.4f}")
    return pop, log, hof

if __name__ == "__main__":
    start_time = time.time()
    main(n_jobs=None)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"程序运行时间: {elapsed_time:.4f} 秒")
