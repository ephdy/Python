import gurobipy as gb
import csv

from Project1.Phase_Three import M_max
from _13_nodes_distribution_network import *
import copy

m = gb.Model("mip1")
# 定义节点类型变量
W = m.addVars(n, vtype=gb.GRB.BINARY, name="W")
# for i in range(n):
#     m.addConstr(W[i] == 0)
m.addConstr(W[0] == 0)
# 定义节点连接变量
U = m.addVars(n, n, vtype=gb.GRB.BINARY, name="U")
for i in range(n):
    m.addConstr(U[i, i] == 0)
    for j in range(n):
        m.addConstr(U[i, j] == U[j, i])
# 定义线路类型变量
x = m.addVars(n, n, kk, vtype=gb.GRB.BINARY, name="x")

# 线路选型约束
for i in range(n):
    for j in range(i+1,n):
        m.addConstr(x.sum(i, j, '*') == 1)
        for k in range(kk):
            m.addConstr(x[i, j, k] == x[j, i, k])
# for i in range(n):
#     m.addConstr(W[i]==W0[i])
#     for j in range(n):
#         m.addConstr(U[i,j] == U0[i][j])
#         for k in range(kk):
#             m.addConstr(x[i, j,k] == x0[i][j][k])
# 新能源承载能力
# epsilon=m.addVar(ub=0.2,vtype=gb.GRB.CONTINUOUS, name="epsilon")
mu=m.addVar(lb=1,ub=2,vtype=gb.GRB.CONTINUOUS, name="mu")
delta=m.addVar(ub=0.4,vtype=gb.GRB.CONTINUOUS, name="delta")
m.addConstr(delta <=mu*0.2)

# 定义各节点电压
Scene_V = m.addVars(n, T,scenes, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
Scene_V__svc = m.addVars(n, n, T,scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
for scene in range(scenes):
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(Scene_V__svc[i, j, t,scene] == Scene_V__svc[j, i, t,scene])
                m.addConstr(Scene_V__svc[i, j, t,scene] == Scene_V__svc[j, i, t,scene])
# 定义线路潮流
Scene_P_tran = m.addVars(n, n, T,scenes, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
Scene_Q_tran = m.addVars(n, n, T,scenes, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
for scene in range(scenes):
    for t in range(T):
        for i in range(n):
            m.addConstr(Scene_P_tran[i, i, t, scene] == 0)
            m.addConstr(Scene_Q_tran[i, i, t, scene] == 0)
            for j in range(i + 1, n):
                if i != j:
                    m.addConstr(Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene])
                    m.addConstr(Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene])
# 购电功率
Scene_P_sub = m.addVars(24, scenes, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
Scene_Q_sub = m.addVars(24, scenes, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")
# 储能充放电功率
Scene_P_ess_ch = m.addVars(24,scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
Scene_P_ess_dis = m.addVars(24,scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
#储能约束
Scene_alpha__dis=m.addVars(T,scenes,vtype=gb.GRB.BINARY,name="Scene_alpha__dis")
Scene_alpha__ch=m.addVars(T,scenes,vtype=gb.GRB.BINARY,name="Scene_alpha__ch")
Scene_E_k=m.addVars(T,scenes,lb=0.1*S_ess,ub=0.9*S_ess,vtype=gb.GRB.CONTINUOUS,name="Scene_E_k")
for scene in range(scenes):
    m.addConstr(Scene_E_k[0, scene] == 5)
    for t in range(T):
        m.addConstr(Scene_alpha__ch[t, scene] + Scene_alpha__dis[t, scene] <= 1)
        m.addConstr(Scene_P_ess_dis[t, scene] <= Scene_alpha__dis[t, scene] * P_ess_max)
        m.addConstr(Scene_P_ess_ch[t, scene] <= Scene_alpha__ch[t, scene] * P_ess_max)
        if t != 0:
            m.addConstr(Scene_E_k[t, scene] == Scene_E_k[t - 1, scene] + Scene_P_ess_ch[t, scene] * 0.9 - Scene_P_ess_dis[t, scene] / 0.9)
    m.addConstr(Scene_P_ess_ch.sum('*',scene)*0.9 == Scene_P_ess_dis.sum('*',scene)/0.9)

# DG出力
Scene_P_DG_813 = m.addVars(2, 24, scenes, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
Scene_P_DG_911 = m.addVars(2, 24, scenes, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
Scene_Q_DG_813 = m.addVars(2, 24, scenes,ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
Scene_Q_DG_911 = m.addVars(2, 24, scenes,ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")
for t in range(T):
    m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2.0 / 9*1)
    m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2.0 / 9*1)
    m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9*1)
    m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9*1)
    m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2.0 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2.0 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_813[0, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
    m.addConstr(Scene_P_DG_813[1, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
    m.addConstr(Scene_P_DG_911[0, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
    m.addConstr(Scene_P_DG_911[1, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
# 连通性约束
flow = m.addVars(n,n, lb=1-n, ub=n-1,vtype=gb.GRB.INTEGER, name="flow")
for i in range(n):
    m.addConstr(flow[i, i] == 0)
    for j in range(n):
        if i != j:
            m.addConstr(flow[i, j] <= (n - 1) * U[i, j])
            m.addConstr(flow[i, j] >= (1 - n) * U[i, j])
            m.addConstr(flow[i, j] == -flow[j, i])
# 根节点流出约束
m.addConstr(flow.sum(0,'*')==n-1)
# 节点流平衡约束
for i in range(1,n):
    # inflow = flow.sum('*',i)
    # outflow = flow.sum(i,'*')
    m.addConstr(flow.sum('*',i) == 1)
# 中间变量
X = m.addVars(n, n, kk, vtype=gb.GRB.BINARY, name="X")  # 线性化引入辅助变量X=x*u
L = m.addVars(n, n, vtype=gb.GRB.BINARY, name="L")  # L=|w_i-w_j|
uL = m.addVars(n, n, vtype=gb.GRB.BINARY, name="uL")  # u_ij*L_ij线性化
e = m.addVars(n, n, vtype=gb.GRB.BINARY, name="e")
f = m.addVars(n, n, vtype=gb.GRB.BINARY, name="f")
g = m.addVars(n, n, vtype=gb.GRB.BINARY, name="g")
h = m.addVars(n, n, vtype=gb.GRB.BINARY, name="h")
ee = m.addVars(n, n, vtype=gb.GRB.BINARY, name="ee")
ff = m.addVars(n, n, vtype=gb.GRB.BINARY, name="ff")
gg = m.addVars(n, n, vtype=gb.GRB.BINARY, name="gg")
hh = m.addVars(n, n, vtype=gb.GRB.BINARY, name="hh")
#
Scene_E = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_E")
Scene_F = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_F")
Scene_G = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_G")
Scene_H = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_H")
Scene_wV = m.addVars(n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_wV")
# 目标函数

# 线路建设成本
C_line = 0
for i in range(n):
    for j in range(n):
        for k in range(kk):
            m.addConstr(X[i, j, k] <= x[i, j, k])
            m.addConstr(X[i, j, k] <= U[i, j])
            m.addConstr(X[i, j, k] >= x[i, j, k] + U[i, j] - 1)
            C_line += 0.5 * c_l[k] * Length[i][j] * X[i, j, k]

# 定义换流支路
# L=|w_i-w_j|线性化约束
for i in range(n):
    for j in range(n):
        m.addConstr(L[i, j] >= (W[i] - W[j]))
        m.addConstr(L[i, j] >= (W[j] - W[i]))
        m.addConstr(L[i, j] <= (W[i] + W[j]))
        m.addConstr(L[i, j] <= (2 - W[i] - W[j]))
        # m.addConstr(L[i, j] >= (W[i] - W[j]))
        # m.addConstr(L[i, j] >= (W[j] - W[i]))
        # m.addConstr(L[i, j] <= (W[i] - W[j] + M * delta))
        # m.addConstr(L[i, j] <= (W[j] - W[i] + M * (1 - delta)))

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
C_operation=[0, 0, 0]
f_op = [0, 0, 0]
for scene in range(scenes):
    if scene == 0:
        coef = 1
    elif scene == 1:
        coef = (mu - delta)
    elif scene == 2:
        coef = (mu + delta)
    for t in range(T):
        f_op[scene] += c_s * Scene_P_sub[t, scene]
        f_op[scene] += c_e * (Scene_P_ess_ch[t, scene] + Scene_P_ess_dis[t, scene])
        f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[0, t, scene])
        f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[0, t, scene])
        f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[1, t, scene])
        f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[1, t, scene])

# C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
for scene in range(scenes):
    for d in range(T_p):
        C_operation[scene] += N_d * f_op[scene] / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation[scene] += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation[scene] += beta_cvt * C_cvt / pow(1 + r, d + 1)

# 节点连接线路条数约束
for i in range(n):
    m.addConstr(U.sum('*', i) >= L_min)
    m.addConstr(U.sum('*', i) <= L_max)

# 功率平衡方程
for scene in range(scenes):
    for i in range(n):
        for t in range(T):
            if i == 0:
                m.addConstr(Scene_P_sub[t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
            elif i == 5:
                m.addConstr(
                    0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, scene] - Scene_P_ess_ch[
                        t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
            elif i == 7:
                m.addConstr(Scene_P_DG_813[0, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                           scene) * S_base == 0)
            elif i == 8:
                m.addConstr(Scene_P_DG_911[0, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                           scene) * S_base == 0)
            elif i == 10:
                m.addConstr(Scene_P_DG_911[1, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                           scene) * S_base == 0)
            elif i == 12:
                m.addConstr(Scene_P_DG_813[1, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                           scene) * S_base == 0)
            else:
                m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)

# 无功功率平衡方程
for scene in range(scenes):
    for i in range(n):
        for t in range(T):
            if i == 0:
                m.addConstr(Scene_Q_sub[t, scene] - Scene_Q_tran.sum(i, '*', t, scene) * S_base == 0)
            elif i == 7:
                m.addGenConstrIndicator(W[i], 0,
                                        Scene_Q_DG_813[0, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(
                                            i, '*', t, scene) * S_base,
                                        gb.GRB.EQUAL, 0)
            elif i == 8:
                m.addGenConstrIndicator(W[i], 0,
                                        Scene_Q_DG_911[0, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(
                                            i, '*', t, scene) * S_base,
                                        gb.GRB.EQUAL, 0)
            elif i == 10:
                m.addGenConstrIndicator(W[i], 0,
                                        Scene_Q_DG_911[1, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(
                                            i, '*', t, scene) * S_base,
                                        gb.GRB.EQUAL, 0)
            elif i == 12:
                m.addGenConstrIndicator(W[i], 0,
                                        Scene_Q_DG_911[1, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(
                                            i, '*', t, scene) * S_base,
                                        gb.GRB.EQUAL, 0)
            else:
                m.addGenConstrIndicator(W[i], 0,
                                        0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, scene) * S_base,
                                        gb.GRB.EQUAL, 0)

ww = m.addVars(n, n, vtype=gb.GRB.BINARY, name="ww")  # u_ij*L_ij线性化
for i in range(n):
    for j in range(i+1,n):
        m.addConstr(ww[i, j] == ww[j, i])
        m.addConstr(ww[i, j] <= W[i])
        m.addConstr(ww[i, j] <= W[j])
        m.addConstr(ww[i, j] >= W[i] + W[j] - 1)


for scene in range(scenes):
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(Scene_P_tran[i, j, t, scene] <= M * U[i, j])
                m.addConstr(Scene_P_tran[i, j, t, scene] >= -M * U[i, j])
                m.addConstr(Scene_Q_tran[i, j, t, scene] <= M * U[i, j])
                m.addConstr(Scene_Q_tran[i, j, t, scene] >= -M * U[i, j])
                m.addConstr(Scene_Q_tran[i, j, t, scene] <= M * (1 - ww[i, j]))
                m.addConstr(Scene_Q_tran[i, j, t, scene] >= -M * (1 - ww[i, j]))
                # m.addGenConstrIndicator(U[i, j], 0,P_tran[i, j, t],gb.GRB.EQUAL, 0)
                # m.addGenConstrIndicator(U[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)
                # m.addGenConstrIndicator(ww[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)


#
# # 电压方程
for scene in range(scenes):
    for i in range(n):
        # m.addConstr(wV[i, t] <= W[i] * V_max)
        # m.addConstr(wV[i, t] >= -W[i] * V_max)
        # m.addConstr(wV[i, t] -V[i, t]<= (1 - W[i]) * V_max)
        # m.addConstr(wV[i, t] -V[i, t]>= -1*(1 - W[i]) * V_max)
        for t in range(T):
            m.addConstr(Scene_wV[i, t, scene] <= W[i] * V_max)
            m.addConstr(Scene_wV[i, t, scene] >= W[i] * V_min)
            m.addConstr(Scene_wV[i, t, scene] <= Scene_V[i, t, scene] - (1 - W[i]) * V_min)
            m.addConstr(Scene_wV[i, t, scene] >= Scene_V[i, t, scene] - (1 - W[i]) * V_max)

        for j in range(n):
            if i != j:
                m.addConstr(f[i, j] <= L[i, j])
                m.addConstr(f[i, j] <= W[i])
                m.addConstr(f[i, j] >= L[i, j] + W[i] - 1)
                #
                m.addConstr(g[i, j] <= L[i, j])
                m.addConstr(g[i, j] <= W[j])
                m.addConstr(g[i, j] >= L[i, j] + W[j] - 1)
                #
                m.addConstr(e[i, j] + f[i, j] == 1)
                m.addConstr(g[i, j] + h[i, j] == 1)
                #

                m.addConstr(ee[i, j] <= e[i, j])
                m.addConstr(ee[i, j] <= U[i, j])
                m.addConstr(ee[i, j] >= e[i, j] + U[i, j] - 1)
                #
                m.addConstr(ff[i, j] <= f[i, j])
                m.addConstr(ff[i, j] <= U[i, j])
                m.addConstr(ff[i, j] >= f[i, j] + U[i, j] - 1)
                #
                m.addConstr(gg[i, j] <= g[i, j])
                m.addConstr(gg[i, j] <= U[i, j])
                m.addConstr(gg[i, j] >= g[i, j] + U[i, j] - 1)
                #
                m.addConstr(hh[i, j] <= h[i, j])
                m.addConstr(hh[i, j] <= U[i, j])
                m.addConstr(hh[i, j] >= h[i, j] + U[i, j] - 1)

                #
                S_line = 0
                for k in range(kk):
                    S_line += x[i, j, k] * S_line_k[k]
                m.addConstr(S_line <= S_vsc_ij)

                for t in range(T):
                    # normal
                    m.addConstr(Scene_V__svc[i, j, t, scene] >= L[i, j] * V_min)
                    m.addConstr(Scene_V__svc[i, j, t, scene] <= Scene_wV[i, t, scene] + Scene_wV[j, t, scene])
                    # normal

                    m.addGenConstrIndicator(ee[i, j], 1, Scene_E[i, j, t, scene] == Scene_V[i, t, scene])
                    m.addGenConstrIndicator(ee[i, j], 0, Scene_E[i, j, t, scene] == 0)
                    #
                    m.addGenConstrIndicator(ff[i, j], 1, Scene_F[i, j, t, scene] == Scene_V__svc[i, j, t, scene])
                    m.addGenConstrIndicator(ff[i, j], 0, Scene_F[i, j, t, scene] == 0)
                    #
                    m.addGenConstrIndicator(gg[i, j], 1, Scene_G[i, j, t, scene] == Scene_V__svc[i, j, t, scene])
                    m.addGenConstrIndicator(gg[i, j], 0, Scene_G[i, j, t, scene] == 0)
                    #
                    m.addGenConstrIndicator(hh[i, j], 1, Scene_H[i, j, t, scene] == Scene_V[j, t, scene])
                    m.addGenConstrIndicator(hh[i, j], 0, Scene_H[i, j, t, scene] == 0)

                    #
                    m.addConstr(
                        Scene_E[i, j, t, scene] + Scene_F[i, j, t, scene] - Scene_G[i, j, t, scene] - Scene_H[i, j, t, scene] -
                        r__vsc[i][j] *
                        Scene_P_tran[i, j, t, scene] - x__vsc[i][j] *
                        Scene_Q_tran[i, j, t, scene] <= M * (1 - L[i, j]))
                    m.addConstr(
                        Scene_E[i, j, t, scene] + Scene_F[i, j, t, scene] - Scene_G[i, j, t, scene] - Scene_H[i, j, t, scene] -
                        r__vsc[i][j] *
                        Scene_P_tran[i, j, t, scene] - x__vsc[i][j] *
                        Scene_Q_tran[i, j, t, scene] >= M * (L[i, j] - 1))
                    m.addConstr(
                        Scene_E[i, j, t, scene] + Scene_F[i, j, t, scene] - Scene_G[i, j, t, scene] - Scene_H[i, j, t, scene] - r__[i][
                            j] *
                        Scene_P_tran[i, j, t, scene] - x__[i][j] *
                        Scene_Q_tran[i, j, t, scene] <= M * L[i, j])
                    m.addConstr(
                        Scene_E[i, j, t, scene] + Scene_F[i, j, t, scene] - Scene_G[i, j, t, scene] - Scene_H[i, j, t, scene] - r__[i][
                            j] *
                        Scene_P_tran[i, j, t, scene] - x__[i][j] *
                        Scene_Q_tran[i, j, t, scene] >= -1 * M * L[i, j])

                    # m.addGenConstrIndicator(L[i,j], 0,
                    #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__[i][j] * P_tran[i, j, t] - x__[i][j] * Q_tran[i, j, t],
                    #                         gb.GRB.EQUAL, 0)
                    # m.addGenConstrIndicator(L[i, j], 1,
                    #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t],
                    #                         gb.GRB.EQUAL, 0)

                    #

                    m.addConstr(Scene_Q_tran[i, j, t, scene] <= L[i, j] * (Q_vsc_max - M) + M)
                    m.addConstr(Scene_Q_tran[i, j, t, scene] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))


                    #
                    m.addConstr(Scene_P_tran[i, j, t, scene] * S_base <= gama * S_line)
                    m.addConstr(Scene_P_tran[i, j, t, scene] * S_base >= -gama * S_line)

                    m.addConstr(Scene_Q_tran[i, j, t, scene] <= gama * S_line / S_base)
                    m.addConstr(Scene_Q_tran[i, j, t, scene] >= -gama * S_line / S_base)

                    m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[i, j, t, scene] <= 1.41 * gama * S_line / S_base)
                    m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[i, j, t, scene] >= -1.41 * gama * S_line / S_base)
                    m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[i, j, t, scene] <= 1.41 * gama * S_line / S_base)
                    m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[i, j, t, scene] >= -1.41 * gama * S_line / S_base)

m._Uvars = [U[i, j] for i in range(n) for j in range(n)]
m._Wvars = [W[i] for i in range(n)]
m._Lvars = [L[i, j] for i in range(n) for j in range(n)]
def my_callback(model, where):
    if where == gb.GRB.Callback.MIPSOL:
        # 获取当前解
        U_sol = model.cbGetSolution(model._Uvars)
        W_sol = model.cbGetSolution(model._Wvars)
        L_sol = model.cbGetSolution(model._Lvars)
        print("U[0] row =", U_sol[0:n])
        U_1_index=find_upper_right_ones(U_sol)
        M_max = len(U_1_index)
        Loss_load = m.addVars(n, 2, M_max, vtype=gb.GRB.BINARY, name="Load_loss")
        for k in range(M_max):
            for i in range(n):
                if n__ac[i] == 0:
                    m.addConstr(Loss_load[i, 0, k] == 0)
                if n__dc[i] == 0:
                    m.addConstr(Loss_load[i, 1, k] == 0)
        U_lack_1 = []
        for i in U_1_index:
            U_new = copy.deepcopy(U)
            U_new[i[0]][i[1]] = 0
            U_new[i[1]][i[0]] = 0
            U_lack_1.append(U_new)
        # 定义各节点电压
        Fault_V = m.addVars(n, T, scenes, M_max, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Fault_V")
        Fault_V__svc = m.addVars(n, n, T, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_V__svc")
        for k in range(M_max):
            for scene in range(scenes):
                for t in range(T):
                    for i in range(n):
                        for j in range(i + 1, n):
                            m.addConstr(Fault_V__svc[i, j, t, scene, k] == Fault_V__svc[j, i, t, scene, k])
        # 定义线路潮流
        Fault_P_tran = m.addVars(n, n, T, scenes, M_max, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Fault_P_tran")
        Fault_Q_tran = m.addVars(n, n, T, scenes, M_max, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Fault_Q_tran")
        for k in range(M_max):
            for scene in range(scenes):
                for t in range(T):
                    for i in range(n):
                        m.addConstr(Fault_P_tran[i, i, t, scene, k] == 0)
                        m.addConstr(Fault_Q_tran[i, i, t, scene, k] == 0)
                        for j in range(i + 1, n):
                            if i != j:
                                m.addConstr(Fault_P_tran[i, j, t, scene, k] == -Fault_P_tran[j, i, t, scene, k])
                                m.addConstr(Fault_Q_tran[i, j, t, scene, k] == -Fault_Q_tran[j, i, t, scene, k])
        # 购电功率
        Fault_P_sub = m.addVars(24, scenes, M_max, ub=10, vtype=gb.GRB.CONTINUOUS, name="Fault_P_sub")
        Fault_Q_sub = m.addVars(24, scenes, M_max, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Fault_Q_sub")
        # 储能充放电功率
        Fault_P_ess_ch = m.addVars(24, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_P_ess_ch")
        Fault_P_ess_dis = m.addVars(24, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_P_ess_dis")
        # 储能约束
        Fault_alpha__dis = m.addVars(T, scenes, M_max, vtype=gb.GRB.BINARY, name="Fault_alpha__dis")
        Fault_alpha__ch = m.addVars(T, scenes, M_max, vtype=gb.GRB.BINARY, name="Fault_alpha__ch")
        Fault_E_k = m.addVars(T, scenes, M_max, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS,
                              name="Fault_E_k")
        for k in range(M_max):
            for scene in range(scenes):
                m.addConstr(Fault_E_k[0, scene, k] == 5)
                for t in range(T):
                    m.addConstr(Fault_alpha__ch[t, scene, k] + Fault_alpha__dis[t, scene, k] <= 1)
                    m.addConstr(Fault_P_ess_dis[t, scene, k] <= Fault_alpha__dis[t, scene, k] * P_ess_max)
                    m.addConstr(Fault_P_ess_ch[t, scene, k] <= Fault_alpha__ch[t, scene, k] * P_ess_max)
                    if t != 0:
                        m.addConstr(
                            Fault_E_k[t, scene, k] == Fault_E_k[t - 1, scene, k] + Fault_P_ess_ch[t, scene, k] * 0.9 -
                            Fault_P_ess_dis[
                                t, scene, k] / 0.9)
                m.addConstr(Fault_P_ess_ch.sum('*', scene, k) * 0.9 == Fault_P_ess_dis.sum('*', scene, k) / 0.9)

        # DG出力
        Fault_P_DG_813 = m.addVars(2, 24, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
        Fault_P_DG_911 = m.addVars(2, 24, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
        Fault_Q_DG_813 = m.addVars(2, 24, scenes, M_max, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Fault_Q_DG_813")
        Fault_Q_DG_911 = m.addVars(2, 24, scenes, M_max, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Fault_Q_DG_911")
        for k in range(M_max):
            for t in range(T):
                m.addConstr(Fault_P_DG_813[0, t, 0, k] <= DG_total[t] * 2.0 / 9 * 1)
                m.addConstr(Fault_P_DG_813[1, t, 0, k] <= DG_total[t] * 2.0 / 9 * 1)
                m.addConstr(Fault_P_DG_911[0, t, 0, k] <= DG_total[t] * 2.5 / 9 * 1)
                m.addConstr(Fault_P_DG_911[1, t, 0, k] <= DG_total[t] * 2.5 / 9 * 1)
                m.addConstr(Fault_P_DG_813[0, t, 1, k] <= DG_total[t] * 2.0 / 9 * (mu - delta))
                m.addConstr(Fault_P_DG_813[1, t, 1, k] <= DG_total[t] * 2.0 / 9 * (mu - delta))
                m.addConstr(Fault_P_DG_911[0, t, 1, k] <= DG_total[t] * 2.5 / 9 * (mu - delta))
                m.addConstr(Fault_P_DG_911[1, t, 1, k] <= DG_total[t] * 2.5 / 9 * (mu - delta))
                m.addConstr(Fault_P_DG_813[0, t, 2, k] <= DG_total[t] * 2.0 / 9 * (mu + delta))
                m.addConstr(Fault_P_DG_813[1, t, 2, k] <= DG_total[t] * 2.0 / 9 * (mu + delta))
                m.addConstr(Fault_P_DG_911[0, t, 2, k] <= DG_total[t] * 2.5 / 9 * (mu + delta))
                m.addConstr(Fault_P_DG_911[1, t, 2, k] <= DG_total[t] * 2.5 / 9 * (mu + delta))
        # 有功功率平衡方程
        for k in range(M_max):
            for scene in range(scenes):
                for i in range(n):
                    for t in range(T):
                        if i == 0:
                            m.addConstr(Fault_P_sub[t, scene, k] - Fault_P_tran.sum(i, '*', t, scene, k) * S_base == 0)
                        elif i == 5:
                            m.addConstr(
                                0 - P_load[t] * (Loss_load[i, 0, k] + Loss_load[i, 1, k]) + Fault_P_ess_dis[t, scene, k] -
                                Fault_P_ess_ch[
                                    t, scene, k] - Fault_P_tran.sum(i, '*', t, scene, k) * S_base == 0)
                        elif i == 7:
                            m.addConstr(
                                Fault_P_DG_813[0, t, scene, k] - P_load[t] * (
                                            Loss_load[i, 0, k] + Loss_load[i, 1, k]) - Fault_P_tran.sum(i, '*', t,
                                                                                                  scene, k) * S_base == 0)
                        elif i == 8:
                            m.addConstr(
                                Fault_P_DG_911[0, t, scene, k] - P_load[t] * (
                                            Loss_load[i, 0, k] + Loss_load[i, 1, k]) - Fault_P_tran.sum(i, '*', t,
                                                                                                  scene, k) * S_base == 0)
                        elif i == 10:
                            m.addConstr(
                                Fault_P_DG_911[1, t, scene, k] - P_load[t] * (
                                            Loss_load[i, 0, k] + Loss_load[i, 1, k]) - Fault_P_tran.sum(i, '*', t,
                                                                                                  scene, k) * S_base == 0)
                        elif i == 12:
                            m.addConstr(
                                Fault_P_DG_813[1, t, scene, k] - P_load[t] * (
                                            Loss_load[i, 0, k] + Loss_load[i, 1, k]) - Fault_P_tran.sum(i, '*', t,
                                                                                                  scene, k) * S_base == 0)
                        else:
                            m.addConstr(
                                0 - P_load[t] * (Loss_load[i, 0, k] + Loss_load[i, 1, k]) - Fault_P_tran.sum(i, '*', t,
                                                                                                       scene, k) * S_base == 0)
        # 无功功率平衡方程
        for k in range(M_max):
            for scene in range(scenes):
                for i in range(n):
                    for t in range(T):
                        if i == 0:
                            m.addConstr(Fault_Q_sub[t, scene, k] - Fault_Q_tran.sum(i, '*', t, scene, k) * S_base == 0)
                        elif i == 7:
                            m.addConstr(
                                (Fault_Q_DG_813[0, t, scene, k] - Q_load[t] * (Loss_load[i, 0, k] + Loss_load[i, 1, k]) -
                                 Fault_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W_sol[i]) == 0)
                        elif i == 8:
                            m.addConstr(
                                (Fault_Q_DG_911[0, t, scene, k] - Q_load[t] * (Loss_load[i, 0, k] + Loss_load[i, 1, k]) -
                                 Fault_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W_sol[i]) == 0)
                        elif i == 10:
                            m.addConstr(
                                (Fault_Q_DG_911[1, t, scene, k] - Q_load[t] * (Loss_load[i, 0, k] + Loss_load[i, 1, k]) -
                                 Fault_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W_sol[i]) == 0)
                        elif i == 12:
                            m.addConstr(
                                (Fault_Q_DG_813[1, t, scene, k] - Q_load[t] * (Loss_load[i, 0, k] + Loss_load[i, 1, k]) -
                                 Fault_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W_sol[i]) == 0)
                        else:
                            m.addConstr(
                                (0 - Q_load[t] * (Loss_load[i, 0, k] + Loss_load[i, 1, k]) -
                                 Fault_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W_sol[i]) == 0)
        #
        for k in range(M_max):
            for scene in range(scenes):
                for i in range(n):
                    for j in range(i + 1, n):
                        for t in range(T):
                            if U[i][j] == 0:
                                m.addConstr(Fault_P_tran[i, j, t, scene, k] == 0, name='联通潮流约束1')
                                m.addConstr(Fault_Q_tran[i, j, t, scene, k] == 0, name='联通潮流约束2')
                            if W_sol[i] * W_sol[j] == 1:
                                m.addConstr(Fault_Q_tran[i, j, t, scene, k] == 0, name='换流无功约束')
        for k in range(M_max):    # # 电压方程
            for scene in range(scenes):
                for i in range(n):
                    for j in range(n):
                        if i != j:
                            S_line = 0
                            for k in range(kk):
                                S_line += x[i, j, k] * S_line_k[k]
                            m.addConstr(S_line <= S_vsc_ij)
                            for t in range(T):
                                m.addConstr(U[i][j] * (
                                        (1 - L_sol[i][j] * W_sol[i]) * Fault_V[i, t, scene, k]
                                        + (L_sol[i][j] * W_sol[i] - L_sol[i][j] * W_sol[j]) * Fault_V__svc[i, j, t, scene, k]
                                        - (1 - L_sol[i][j] * W_sol[j]) * Fault_V[j, t, scene, k]) ==
                                            (1 - L_sol[i][j]) * (
                                                    r__[i][j] * Fault_P_tran[i, j, t, scene, k] + x__[i][j] * Fault_Q_tran[
                                                i, j, t, scene, k])
                                            + L_sol[i][j] * (r__vsc[i][j] * Fault_P_tran[i, j, t, scene, k] - x__vsc[i][j] *
                                                         Fault_Q_tran[i, j, t, scene, k]), name='电压方程')
                                # VSC约束
                                m.addConstr(Fault_Q_tran[i, j, t, scene, k] <= L_sol[i][j] * (Q_vsc_max - M) + M,
                                            name='VSC无功约束1')
                                m.addConstr(Fault_Q_tran[i, j, t, scene, k] >= -1 * (L_sol[i][j] * (Q_vsc_max - M) + M),
                                            name='VSC无功约束2')
                                # 传输容量约束
                                m.addConstr(Fault_P_tran[i, j, t, scene, k] <= gama * S_line / S_base,
                                            name='传输容量约束1')
                                m.addConstr(Fault_P_tran[i, j, t, scene, k] >= -gama * S_line / S_base,
                                            name='传输容量约束2')

                                m.addConstr(Fault_Q_tran[i, j, t, scene, k] <= gama * S_line / S_base,
                                            name='传输容量约束3')
                                m.addConstr(Fault_Q_tran[i, j, t, scene, k] >= -gama * S_line / S_base,
                                            name='传输容量约束4')

                                m.addConstr(Fault_P_tran[i, j, t, scene, k] + Fault_Q_tran[
                                    i, j, t, scene, k] <= 1.41 * gama * S_line / S_base, name='传输容量约束5')
                                m.addConstr(Fault_P_tran[i, j, t, scene, k] + Fault_Q_tran[
                                    i, j, t, scene, k] >= -1.41 * gama * S_line / S_base, name='传输容量约束6')
                                m.addConstr(Fault_P_tran[i, j, t, scene, k] - Fault_Q_tran[
                                    i, j, t, scene, k] <= 1.41 * gama * S_line / S_base, name='传输容量约束7')
                                m.addConstr(Fault_P_tran[i, j, t, scene, k] - Fault_Q_tran[
                                    i, j, t, scene, k] >= -1.41 * gama * S_line / S_base, name='传输容量约束8')
        f3=(15*M_max-Loss_load.sum())/15/M_max
        m.setObjective(f1 + f2 + f3, gb.GRB.MINIMIZE)
        m.update()  # 更新模型
def find_upper_right_ones(arr):
    n = len(arr)
    result = []
    for i in range(n):
        for j in range(i+1, n):
            if arr[i][j] == 1:
                result.append((i, j))
    return result

# m.setParam("Threads", 8)
f1=(C_invest + 0.8*C_operation[0]+0.1*C_operation[1]+0.1*C_operation[2]-1.037e8)/5e7
f2=1-delta/0.4
# loss_active = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="loss_active")
# for i in range(n):
#     for j in range(n):
#         for k in range(M_max):
#             m.addConstr(loss_active[i, j, k] <= Loss_load[i, j, k])
#             m.addConstr(loss_active[i, j, k] <= active[k])
#             m.addConstr(loss_active[i, j, k] >= Loss_load[i, j, k] + active[k] - 1)
# f3=Loss_load.sum()
m.setObjective(f1+f2, gb.GRB.MINIMIZE)
# m.setObjectiveN(f1,index=0,
#                     priority=2,
#                     weight=1.0,
#                     name="f1")
# m.setObjectiveN(f2,index=1,
#                     priority=3,
#                     weight=1.0,
#                     name="f2")



# m.setParam('MIPFocus', 1)         # 优先找到可行解
# m.setParam('Heuristics', 0.2)     # 适当增加启发式
# m.setParam('Cuts', 2)             # 更积极的 cut
# m.setParam('Threads', 多核数)      # 保持多线程
# m.setParam('NodefileStart', 0.5)  # 提前使用磁盘，防止内存爆掉


m.optimize(my_callback)
# Result = []
# for v in m.getVars():
#     Result.append([v.VarName, v.X])
#     if v.varName.split('[')[0] in ['W', 'U','x','P_sub','P_ess_ch','P_ess_dis']:
#         print(v.VarName, v.X)




# for i in range(m.NumObj):
#     print(f"Objective {i} value =", m.getObjective(i).getValue())
print('Obj:', m.objVal)

