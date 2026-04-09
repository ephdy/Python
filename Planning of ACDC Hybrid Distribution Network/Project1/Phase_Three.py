import gurobipy as gb
import csv
from _13_nodes_distribution_network import *

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













#
# U_upper_sum = gb.quicksum(U[i,j] for i in range(n) for j in range(i+1, n))
# max_upper_ones = n*(n-1)//2  # U 上三角最多1的数量
# n2n = max_upper_ones // 2
# U_derived = []
#
# for k in range(n2n):
#     Uk = m.addVars(n, n, vtype=gb.GRB.BINARY, name=f"U{k+1}")
#     # 对称 + 对角线约束
#     for i in range(n):
#         m.addConstr(Uk[i,i] == 0)
#     for i in range(n):
#         for j in range(i+1, n):
#             m.addConstr(Uk[i,j] == Uk[j,i])
#             m.addConstr(Uk[i,j] <= U[i,j])
#     U_derived.append(Uk)
# active = m.addVars(n2n, vtype=gb.GRB.BINARY, name="active")
#
# for k, Uk in enumerate(U_derived):
#     Uk_upper_sum = gb.quicksum(Uk[i,j] for i in range(n) for j in range(i+1, n))
#     # 如果 Uk 被激活，则去掉恰好2个1
#     m.addConstr(Uk_upper_sum == (U_upper_sum - 2) * active[k])
#
# m.addConstr(gb.quicksum(active[k] for k in range(n2n)) == U_upper_sum / 2)
#
# for k1 in range(n2n):
#     for k2 in range(k1+1, M):
#         for i in range(n):
#             for j in range(i+1, n):
#                 # D[k1,k2,i,j] 表示 Uk1[i,j] != Uk2[i,j]
#                 D = m.addVar(vtype=gb.GRB.BINARY, name=f"D_{k1}_{k2}_{i}_{j}")
#                 m.addConstr(D >= U_derived[k1][i,j] - U_derived[k2][i,j])
#                 m.addConstr(D >= U_derived[k2][i,j] - U_derived[k1][i,j])
#         # 至少有一个不同，只对激活矩阵生效
#         m.addConstr(gb.quicksum(D for i in range(n) for j in range(i+1, n)) >= active[k1] + active[k2] - 1)













# 构造上三角边索引列表（用于减少变量数）
edges = [(i, j) for i in range(n) for j in range(i+1, n)]
E = len(edges)

max_upper_ones = n * (n - 1) // 2
M_max = max_upper_ones # 候选派生矩阵槽数上界

Loss_load=m.addVars(n, 2,M_max,vtype=gb.GRB.BINARY,name="Load_loss")
for k in range(M_max):
    for i in range(n):
        if n__ac[i] == 0:
            m.addConstr(Loss_load[i, 0, k] == 0)
        if n__dc[i] == 0:
            m.addConstr(Loss_load[i, 1, k] == 0)

# active 指示第 k 个槽是否被激活（将被选为一个派生矩阵）
active = m.addVars(M_max, vtype=gb.GRB.BINARY, name="active")
del_k = m.addVars(M_max, E, vtype=gb.GRB.BINARY, name="del")

# del_k <= U and del_k <= active
for k in range(M_max):
    for ei, (i,j) in enumerate(edges):
        m.addConstr(del_k[k, ei] <= U[i,j])
        m.addConstr(del_k[k, ei] <= active[k])

# 每个 Uk 删除恰好 1 条边
for k in range(M_max):
    m.addConstr(gb.quicksum(del_k[k,ei] for ei in range(E)) == active[k])

# 删除的边必须都是不同的
for ei in range(E):
    m.addConstr(gb.quicksum(del_k[k, ei] for k in range(M_max)) <= 1)

# 活跃的派生矩阵数量 = 边数量（每条边一个 Uk）
m.addConstr(gb.quicksum(active[k] for k in range(M_max)) ==
            gb.quicksum(U[i,j] for i,j in edges))
def get_ei(i, j, edges):
    if i < j:
        return edges.index((i, j))
    else:
        return edges.index((j, i))
# Uk = U - del_k
Uk = {}
for k in range(M_max):
    for ei, (i, j) in enumerate(edges):
        Uk[k, ei] = m.addVar(vtype=gb.GRB.BINARY, name=f"Uk_{k}_{i}_{j}")
        m.addConstr(Uk[k, ei] == U[i,j] - del_k[k, ei])

# 定义各节点电压
Fault_V = m.addVars(n, T, scenes,M_max, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Fault_V")
Fault_V__svc = m.addVars(n, n, T, scenes,M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_V__svc")
for k in range(M_max):
    for scene in range(scenes):
        for t in range(T):
            for i in range(n):
                for j in range(i + 1, n):
                    m.addConstr(Fault_V__svc[i, j, t, scene, k] == Fault_V__svc[j, i, t, scene, k])
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
Fault_P_sub = m.addVars(24, scenes,M_max, ub=10, vtype=gb.GRB.CONTINUOUS, name="Fault_P_sub")
Fault_Q_sub = m.addVars(24, scenes,M_max, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Fault_Q_sub")
# 储能充放电功率
Fault_P_ess_ch = m.addVars(24, scenes,M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_P_ess_ch")
Fault_P_ess_dis = m.addVars(24, scenes,M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_P_ess_dis")
# 储能约束
Fault_alpha__dis = m.addVars(T, scenes,M_max, vtype=gb.GRB.BINARY, name="Fault_alpha__dis")
Fault_alpha__ch = m.addVars(T, scenes,M_max, vtype=gb.GRB.BINARY, name="Fault_alpha__ch")
Fault_E_k = m.addVars(T, scenes,M_max, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS, name="Fault_E_k")
for k in range(M_max):
    for scene in range(scenes):
        m.addConstr(Fault_E_k[0, scene, k] == 5)
        for t in range(T):
            m.addConstr(Fault_alpha__ch[t, scene, k] + Fault_alpha__dis[t, scene, k] <= 1)
            m.addConstr(Fault_P_ess_dis[t, scene, k] <= Fault_alpha__dis[t, scene, k] * P_ess_max)
            m.addConstr(Fault_P_ess_ch[t, scene, k] <= Fault_alpha__ch[t, scene, k] * P_ess_max)
            if t != 0:
                m.addConstr(
                    Fault_E_k[t, scene, k] == Fault_E_k[t - 1, scene, k] + Fault_P_ess_ch[t, scene, k] * 0.9 - Fault_P_ess_dis[
                        t, scene, k] / 0.9)
        m.addConstr(Fault_P_ess_ch.sum('*', scene, k) * 0.9 == Fault_P_ess_dis.sum('*', scene, k) / 0.9)

# DG出力
Fault_P_DG_813 = m.addVars(2, 24, scenes ,M_max , vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
Fault_P_DG_911 = m.addVars(2, 24, scenes ,M_max , vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
Fault_Q_DG_813 = m.addVars(2, 24, scenes ,M_max , ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Fault_Q_DG_813")
Fault_Q_DG_911 = m.addVars(2, 24, scenes ,M_max , ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Fault_Q_DG_911")
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

Fault_ee = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="Fault_ee")
Fault_ff = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="Fault_ff")
Fault_gg = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="Fault_gg")
Fault_hh = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="Fault_hh")

# 功率平衡方程
for k in range(M_max):
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_P_sub[t, scene, k] - Fault_P_tran.sum(i, '*', t, scene, k) * S_base,
                                            gb.GRB.EQUAL, 0)
                elif i == 5:
                    m.addGenConstrIndicator(active[k], 1,
                                            0 - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) + Fault_P_ess_dis[t, scene,k] -
                                            Fault_P_ess_ch[t, scene, k] - Fault_P_tran.sum(i, '*', t, scene, k) * S_base,
                                            gb.GRB.EQUAL, 0)
                elif i == 7:
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_P_DG_813[0, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k])
                                            - Fault_P_tran.sum(i, '*', t,scene, k) * S_base,
                                            gb.GRB.EQUAL, 0)
                elif i == 8:
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_P_DG_911[0, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k])
                                            - Fault_P_tran.sum(i, '*', t,scene, k) * S_base,
                                            gb.GRB.EQUAL, 0)
                elif i == 10:
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_P_DG_911[1, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k])
                                            - Fault_P_tran.sum(i, '*', t,scene, k) * S_base,
                                            gb.GRB.EQUAL, 0)
                elif i == 12:
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_P_DG_813[1, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k])
                                            - Fault_P_tran.sum(i, '*', t,scene, k) * S_base,
                                            gb.GRB.EQUAL, 0)
                else:
                    m.addGenConstrIndicator(active[k], 1,
                                            0 - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k])
                                            - Fault_P_tran.sum(i, '*', t, scene,k) * S_base,
                                            gb.GRB.EQUAL, 0)

# 无功功率平衡方程
for k in range(M_max):
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Fault_Q_sub[t, scene,k] - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base == 0)
                elif i == 7:
                    m.addConstr(Fault_Q_DG_813[0, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base <= M *  (W[i] + 1 - active[k]))
                    m.addConstr(Fault_Q_DG_813[0, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base >= -M *  (W[i] + 1 - active[k]))
                elif i == 8:
                    m.addConstr(Fault_Q_DG_911[0, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base <= M *  (W[i] + 1 - active[k]))
                    m.addConstr(Fault_Q_DG_911[0, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base >= -M *  (W[i] + 1 - active[k]))
                elif i == 10:
                    m.addConstr(Fault_Q_DG_911[1, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base <= M *  (W[i] + 1 - active[k]))
                    m.addConstr(Fault_Q_DG_911[1, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base >= -M *  (W[i] + 1 - active[k]))
                elif i == 12:
                    m.addConstr(Fault_Q_DG_813[1, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base <= M *  (W[i] + 1 - active[k]))
                    m.addConstr(Fault_Q_DG_813[1, t, scene,k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base >= -M *  (W[i] + 1 - active[k]))
                else:
                    m.addConstr(0 - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base <= M * (W[i] + 1 - active[k]))
                    m.addConstr(0 - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Fault_Q_tran.sum(i, '*', t, scene,k) * S_base >= -M * (W[i] + 1 - active[k]))

for k in range(M_max):
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    m.addConstr(Fault_P_tran[i, j, t, scene, k] <= M * U[i, j])
                    m.addConstr(Fault_P_tran[i, j, t, scene, k] >= -M * U[i, j])
                    m.addConstr(Fault_Q_tran[i, j, t, scene, k] <= M * U[i, j])
                    m.addConstr(Fault_Q_tran[i, j, t, scene, k] >= -M * U[i, j])
                    m.addConstr(Fault_Q_tran[i, j, t, scene, k] <= M * (1 - ww[i, j]))
                    m.addConstr(Fault_Q_tran[i, j, t, scene, k] >= -M * (1 - ww[i, j]))
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_P_tran[i, j, t, scene, k] <= M *Uk[k, edges.index((i, j))])
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_P_tran[i, j, t, scene, k] >= -M * Uk[k, edges.index((i, j))])
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_Q_tran[i, j, t, scene, k] <= M *Uk[k, edges.index((i, j))])
                    m.addGenConstrIndicator(active[k], 1,
                                            Fault_Q_tran[i, j, t, scene, k] >= -M * Uk[k, edges.index((i, j))])
                    # m.addGenConstrIndicator(U[i, j], 0,P_tran[i, j, t],gb.GRB.EQUAL, 0)
                    # m.addGenConstrIndicator(U[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)
                    # m.addGenConstrIndicator(ww[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)

#
Fault_E = m.addVars(n, n, T, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_E")
Fault_F = m.addVars(n, n, T, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_F")
Fault_G = m.addVars(n, n, T, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_G")
Fault_H = m.addVars(n, n, T, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_H")
Fault_wV = m.addVars(n, T, scenes, M_max, vtype=gb.GRB.CONTINUOUS, name="Fault_wV")


Lactive1 = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="Lactive1")
for i in range(n):
    for j in range(n):
        for k in range(M_max):
            m.addConstr(Lactive1[i, j, k] <= L[i, j])
            m.addConstr(Lactive1[i, j, k] <= active[k])
            m.addConstr(Lactive1[i, j, k] >= L[i, j] + active[k] - 1)
Lactive2 = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="Lactive2")
for i in range(n):
    for j in range(n):
        for k in range(M_max):
            m.addConstr(Lactive2[i, j, k] <= 1 - L[i, j])
            m.addConstr(Lactive2[i, j, k] <= active[k])
            m.addConstr(Lactive2[i, j, k] >= active[k] - L[i, j])

# # 电压方程
for k in range(M_max):
    for scene in range(scenes):
        for i in range(i+1,n):
            for t in range(T):
                m.addConstr(Fault_wV[i, t, scene, k] <= W[i] * V_max)
                m.addConstr(Fault_wV[i, t, scene, k] >= W[i] * V_min)
                m.addConstr(Fault_wV[i, t, scene, k] <= Fault_V[i, t, scene, k] - (1 - W[i]) * V_min)
                m.addConstr(Fault_wV[i, t, scene, k] >= Fault_V[i, t, scene, k] - (1 - W[i]) * V_max)

            for j in range(n):
                if i != j:
                    S_line = 0
                    for k in range(kk):
                        S_line += x[i, j, k] * S_line_k[k]
                    m.addConstr(S_line <= S_vsc_ij)

                    m.addConstr(Fault_ee[i, j, k] <= e[i, j])
                    m.addConstr(Fault_ee[i, j, k] <= U[i, j])
                    m.addConstr(Fault_ee[i, j, k] >= e[i, j] + U[i, j] - 1)
                    m.addConstr(Fault_ee[i, j, k] <= Uk[k, edges.index((i, j))])
                    m.addConstr(Fault_ee[i, j, k] >= e[i, j] + Uk[k, edges.index((i, j))] - 1)
                    m.addGenConstrIndicator(active[k], 1, Fault_ee[i, j, k] <= Uk[k, edges.index((i, j))])
                    m.addGenConstrIndicator(active[k], 1, Fault_ee[i, j, k] >= e[i, j] + Uk[k, edges.index((i, j))] - 1)

                    #
                    m.addConstr(Fault_ff[i, j, k] <= f[i, j])
                    m.addConstr(Fault_ff[i, j, k] <= U[i, j])
                    m.addConstr(Fault_ff[i, j, k] >= f[i, j] + U[i, j] - 1)
                    m.addGenConstrIndicator(active[k], 1, Fault_ff[i, j, k] <= Uk[k, edges.index((i, j))])
                    m.addGenConstrIndicator(active[k], 1, Fault_ff[i, j, k] >= f[i, j] + Uk[k, edges.index((i, j))] - 1)
                    #
                    m.addConstr(Fault_gg[i, j, k] <= g[i, j])
                    m.addConstr(Fault_gg[i, j, k] <= U[i, j])
                    m.addConstr(Fault_gg[i, j, k] >= g[i, j] + U[i, j] - 1)
                    m.addGenConstrIndicator(active[k], 1, Fault_gg[i, j, k] <= Uk[k, edges.index((i, j))])
                    m.addGenConstrIndicator(active[k], 1, Fault_gg[i, j, k] >= g[i, j] + Uk[k, edges.index((i, j))] - 1)
                    #
                    m.addConstr(Fault_hh[i, j, k] <= h[i, j])
                    m.addConstr(Fault_hh[i, j, k] <= U[i, j])
                    m.addConstr(Fault_hh[i, j, k] >= h[i, j] + U[i, j] - 1)
                    m.addGenConstrIndicator(active[k], 1, Fault_hh[i, j, k] <= Uk[k, edges.index((i, j))])
                    m.addGenConstrIndicator(active[k], 1, Fault_hh[i, j, k] >= h[i, j] + Uk[k, edges.index((i, j))] - 1)
                    for t in range(T):
                        # normal
                        m.addConstr(Fault_V__svc[i, j, t, scene, k] >= L[i, j] * V_min)
                        m.addConstr(Fault_V__svc[i, j, t, scene, k] <= Fault_wV[i, t, scene, k] + Fault_wV[j, t, scene, k])
                        # normal

                        m.addGenConstrIndicator(Fault_ee[i, j, k], 1, Fault_E[i, j, t, scene, k] == Fault_V[i, t, scene, k])
                        m.addGenConstrIndicator(Fault_ee[i, j, k], 0, Fault_E[i, j, t, scene, k] == 0)
                        #
                        m.addGenConstrIndicator(Fault_ff[i, j, k], 1, Fault_F[i, j, t, scene, k] == Fault_V__svc[i, j, t, scene, k])
                        m.addGenConstrIndicator(Fault_ff[i, j, k], 0, Fault_F[i, j, t, scene, k] == 0)
                        #
                        m.addGenConstrIndicator(Fault_gg[i, j, k], 1, Fault_G[i, j, t, scene, k] == Fault_V__svc[i, j, t, scene, k])
                        m.addGenConstrIndicator(Fault_gg[i, j, k], 0, Fault_G[i, j, t, scene, k] == 0)
                        #
                        m.addGenConstrIndicator(Fault_hh[i, j, k], 1, Fault_H[i, j, t, scene, k] == Fault_V[j, t, scene, k])
                        m.addGenConstrIndicator(Fault_hh[i, j, k], 0, Fault_H[i, j, t, scene, k] == 0)

                        #
                        m.addConstr(
                            Fault_E[i, j, t, scene, k] + Fault_F[i, j, t, scene, k] - Fault_G[i, j, t, scene, k] - Fault_H[i, j, t, scene, k]
                            - r__vsc[i][j] * Fault_P_tran[i, j, t, scene, k]
                            - x__vsc[i][j] * Fault_Q_tran[i, j, t, scene, k] <= M * Lactive1[i,j,k])
                        m.addConstr(
                            Fault_E[i, j, t, scene, k] + Fault_F[i, j, t, scene, k] - Fault_G[i, j, t, scene, k] - Fault_H[i, j, t, scene, k]
                            - r__vsc[i][j] *Fault_P_tran[i, j, t, scene, k]
                            - x__vsc[i][j] *Fault_Q_tran[i, j, t, scene, k] >= -M * Lactive1[i,j,k])
                        m.addConstr(
                            Fault_E[i, j, t, scene, k] + Fault_F[i, j, t, scene, k] - Fault_G[i, j, t, scene, k] - Fault_H[i, j, t, scene, k]
                            - r__[i][j] * Fault_P_tran[i, j, t, scene, k]
                            - x__[i][j] * Fault_Q_tran[i, j, t, scene, k] <= M * Lactive2[i,j,k])
                        m.addConstr(
                            Fault_E[i, j, t, scene, k] + Fault_F[i, j, t, scene, k] - Fault_G[i, j, t, scene, k] - Fault_H[i, j, t, scene, k]
                            - r__[i][j] * Fault_P_tran[i, j, t, scene, k]
                            - x__[i][j] * Fault_Q_tran[i, j, t, scene, k] >= -M * Lactive2[i,j,k])

                        # m.addGenConstrIndicator(L[i,j], 0,
                        #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__[i][j] * P_tran[i, j, t] - x__[i][j] * Q_tran[i, j, t],
                        #                         gb.GRB.EQUAL, 0)
                        # m.addGenConstrIndicator(L[i, j], 1,
                        #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t],
                        #                         gb.GRB.EQUAL, 0)

                        #

                        m.addConstr(Fault_Q_tran[i, j, t, scene, k] <= L[i, j] * (Q_vsc_max - M) + M)
                        m.addConstr(Fault_Q_tran[i, j, t, scene, k] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))

                        #
                        m.addConstr(Fault_P_tran[i, j, t, scene, k] * S_base <= gama * S_line)
                        m.addConstr(Fault_P_tran[i, j, t, scene, k] * S_base >= -gama * S_line)

                        m.addConstr(Fault_Q_tran[i, j, t, scene, k] <= gama * S_line / S_base)
                        m.addConstr(Fault_Q_tran[i, j, t, scene, k] >= -gama * S_line / S_base)

                        m.addConstr(
                            Fault_P_tran[i, j, t, scene, k] + Fault_Q_tran[i, j, t, scene, k] <= 1.41 * gama * S_line / S_base)
                        m.addConstr(
                            Fault_P_tran[i, j, t, scene, k] + Fault_Q_tran[i, j, t, scene, k] >= -1.41 * gama * S_line / S_base)
                        m.addConstr(
                            Fault_P_tran[i, j, t, scene, k] - Fault_Q_tran[i, j, t, scene, k] <= 1.41 * gama * S_line / S_base)
                        m.addConstr(
                            Fault_P_tran[i, j, t, scene, k] - Fault_Q_tran[i, j, t, scene, k] >= -1.41 * gama * S_line / S_base)







# m.setParam("Threads", 8)
f1=C_invest + C_operation[0]
f2=1-delta/0.4
loss_active = m.addVars(n, n, M_max, vtype=gb.GRB.BINARY, name="loss_active")
for i in range(n):
    for j in range(2):
        for k in range(M_max):
            m.addConstr(loss_active[i, j, k] <= Loss_load[i, j, k])
            m.addConstr(loss_active[i, j, k] <= active[k])
            m.addConstr(loss_active[i, j, k] >= Loss_load[i, j, k] + active[k] - 1)
f3=Loss_load.sum()
m.setObjective(f3, gb.GRB.MINIMIZE)
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


m.optimize()
Result = []
for v in m.getVars():
    Result.append([v.VarName, v.X])
    if v.varName.split('[')[0] in ['W', 'U','x','P_sub','P_ess_ch','P_ess_dis']:
        print(v.VarName, v.X)




# for i in range(m.NumObj):
#     print(f"Objective {i} value =", m.getObjective(i).getValue())
# obj0_val = m.ObjN[0].getValue()
# obj1_val = m.ObjN[1].getValue()
# # obj2_val = m.ObjNVal[2]
print('Obj:', m.objVal)
# print('Obj:', obj0_val)
# print('Obj:', obj1_val)
# print('Obj:', obj2_val)
# m.computeIIS()
# m.write("model.ilp")
with open('Result.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    for row in Result:
        writer.writerow(row)
