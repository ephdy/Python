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
V = m.addVars(n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
V__svc = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="V__svc")
for i in range(n):
    for j in range(i+1,n):
        for t in range(T):
            m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
            m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
#
Scene_V = m.addVars(n, T,2, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
Scene_V__svc = m.addVars(n, n, T,2, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
for scene in range(2):
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(Scene_V__svc[i, j, t,scene] == Scene_V__svc[j, i, t,scene])
                m.addConstr(Scene_V__svc[i, j, t,scene] == Scene_V__svc[j, i, t,scene])
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
Scene_P_tran = m.addVars(n, n, T, 2, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
Scene_Q_tran = m.addVars(n, n, T, 2, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
for scene in range(2):
    for t in range(T):
        for i in range(n):
            m.addConstr(Scene_P_tran[i, i, t, scene] == 0)
            m.addConstr(Scene_Q_tran[i, i, t, scene] == 0)
            for j in range(i + 1, n):
                if i != j:
                    m.addConstr(Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene])
                    m.addConstr(Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene])
# 购电功率
P_sub = m.addVars(24, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_sub")
Q_sub = m.addVars(24, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_sub")
Scene_P_sub = m.addVars(24, 2, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
Scene_Q_sub = m.addVars(24, 2, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")
# 储能充放电功率
P_ess_ch = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
P_ess_dis = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
Scene_P_ess_ch = m.addVars(24,2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
Scene_P_ess_dis = m.addVars(24,2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
#储能约束
alpha__dis=m.addVars(T,vtype=gb.GRB.BINARY,name="alpha__dis")
alpha__ch=m.addVars(T,vtype=gb.GRB.BINARY,name="alpha__ch")
E_k=m.addVars(T,lb=0.1*S_ess,ub=0.9*S_ess,vtype=gb.GRB.CONTINUOUS,name="E_k")
m.addConstr(E_k[0]==5)
for t in range(T):
    m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
    m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
    m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
    if t !=0:
        m.addConstr(E_k[t]==E_k[t-1]+P_ess_ch[t]*0.9-P_ess_dis[t]/0.9)
m.addConstr(gb.quicksum(P_ess_ch)*0.9 == gb.quicksum(P_ess_dis)/0.9)
#
Scene_alpha__dis=m.addVars(T,2,vtype=gb.GRB.BINARY,name="Scene_alpha__dis")
Scene_alpha__ch=m.addVars(T,2,vtype=gb.GRB.BINARY,name="Scene_alpha__ch")
Scene_E_k=m.addVars(T,2,lb=0.1*S_ess,ub=0.9*S_ess,vtype=gb.GRB.CONTINUOUS,name="Scene_E_k")
m.addConstr(Scene_E_k[0,0]==5)
m.addConstr(Scene_E_k[0,1]==5)
for scene in range(2):
    for t in range(T):
        m.addConstr(Scene_alpha__ch[t, scene] + Scene_alpha__dis[t, scene] <= 1)
        m.addConstr(Scene_P_ess_dis[t, scene] <= Scene_alpha__dis[t, scene] * P_ess_max)
        m.addConstr(Scene_P_ess_ch[t, scene] <= Scene_alpha__ch[t, scene] * P_ess_max)
        if t != 0:
            m.addConstr(Scene_E_k[t, scene] == Scene_E_k[t - 1, scene] + Scene_P_ess_ch[t, scene] * 0.9 - Scene_P_ess_dis[t, scene] / 0.9)
m.addConstr(Scene_P_ess_ch.sum('*',0)*0.9 == Scene_P_ess_dis.sum('*',0)/0.9)
m.addConstr(Scene_P_ess_ch.sum('*',1)*0.9 == Scene_P_ess_dis.sum('*',1)/0.9)
# DG出力
P_DG_813 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
P_DG_911 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
Q_DG_813 = m.addVars(2, 24,ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Q_DG_813")
Q_DG_911 = m.addVars(2, 24,ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Q_DG_911")
for t in range(T):
    m.addConstr(P_DG_813[0,t] <= DG_total[t] * 2 / 9)
    m.addConstr(P_DG_813[1,t] <= DG_total[t] * 2 / 9)
    m.addConstr(P_DG_911[0,t] <= DG_total[t] * 2.5 / 9)
    m.addConstr(P_DG_911[1,t] <= DG_total[t] * 2.5 / 9)
#
Scene_P_DG_813 = m.addVars(2, 24, 2, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
Scene_P_DG_911 = m.addVars(2, 24, 2, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
Scene_Q_DG_813 = m.addVars(2, 24, 2,ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
Scene_Q_DG_911 = m.addVars(2, 24, 2,ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")
for t in range(T):
    m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9*(mu-delta))
    m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2 / 9*(mu+delta))
    m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2 / 9*(mu+delta))
    m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9*(mu+delta))
    m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9*(mu+delta))
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
E = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="E")
F = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="F")
G = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="G")
H = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="H")
wV = m.addVars(n, T, vtype=gb.GRB.CONTINUOUS, name="wV")
#
Scene_E = m.addVars(n, n, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_E")
Scene_F = m.addVars(n, n, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_F")
Scene_G = m.addVars(n, n, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_G")
Scene_H = m.addVars(n, n, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_H")
Scene_wV = m.addVars(n, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_wV")
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
C_operation=0
f_op = 0

for t in range(T):
    f_op += c_s * P_sub[t]
    f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
    f_op += c_d * (DG_total[t]*2/9 - P_DG_813[0, t])
    f_op += c_d * (DG_total[t]*2.5/9 - P_DG_911[0, t])
    f_op += c_d * (DG_total[t]*2.5/9 - P_DG_911[1, t])
    f_op += c_d * (DG_total[t]*2/9 - P_DG_813[1, t])

# C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
for d in range(T_p):
    C_operation += N_d * f_op / pow(1 + r, d + 1)
for d in range(T_line):
    C_operation += beta_line * C_line / pow(1 + r, d + 1)
for d in range(T_cvt):
    C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)

# 节点连接线路条数约束
for i in range(n):
    m.addConstr(U.sum('*', i) >= L_min)
    m.addConstr(U.sum('*', i) <= L_max)

# 功率平衡方程
for i in range(n):
    for t in range(T):
        if i == 0:
            m.addConstr(P_sub[t] - P_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(Scene_P_sub[t, 0] - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(Scene_P_sub[t, 1] - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
        elif i == 5:
            m.addConstr(
                0 - P_load[t] * (n__ac[i] + n__dc[i]) + P_ess_dis[t] - P_ess_ch[t] - P_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(
                0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, 0] - Scene_P_ess_ch[t, 0] - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(
                0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, 1] - Scene_P_ess_ch[t, 1] - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
        elif i == 7:
            m.addConstr(P_DG_813[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(Scene_P_DG_813[0, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(Scene_P_DG_813[0, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
        elif i == 8:
            m.addConstr(P_DG_911[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(Scene_P_DG_911[0, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(Scene_P_DG_911[0, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
        elif i == 10:
            m.addConstr(P_DG_911[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(Scene_P_DG_911[1, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(Scene_P_DG_911[1, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
        elif i == 12:
            m.addConstr(P_DG_813[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(Scene_P_DG_813[1, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(Scene_P_DG_813[1, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
        else:
            m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)

# 无功功率平衡方程
for i in range(n):
    for t in range(T):
        if i == 0:
            m.addConstr(Q_sub[t] - Q_tran.sum(i, '*', t) * S_base == 0)
            m.addConstr(Scene_Q_sub[t, 0] - Scene_Q_tran.sum(i, '*', t, 0) * S_base == 0)
            m.addConstr(Scene_Q_sub[t, 1] - Scene_Q_tran.sum(i, '*', t, 1) * S_base == 0)
        elif i == 7:
            m.addGenConstrIndicator(W[i], 0,
                                    Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base, gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_813[0, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t,0) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_813[0, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t,1) * S_base,
                                    gb.GRB.EQUAL, 0)
            # m.addConstr(Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base <= M * W[i])
            # m.addConstr(Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base >= -M * W[i])
        elif i == 8:
            m.addGenConstrIndicator(W[i], 0,
                                    Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_911[0, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 0) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_911[0, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 1) * S_base,
                                    gb.GRB.EQUAL, 0)
            # m.addConstr(Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base <= M * W[i])
            # m.addConstr(Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base >= -M * W[i])
        elif i == 10:
            m.addGenConstrIndicator(W[i], 0,
                                    Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_911[1, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 0) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_911[1, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 1) * S_base,
                                    gb.GRB.EQUAL, 0)
            # m.addConstr(Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base <= M * W[i])
            # m.addConstr(Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base >= -M * W[i])
        elif i == 12:
            m.addGenConstrIndicator(W[i], 0,
                                    Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_911[1, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 0) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    Scene_Q_DG_911[1, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 1) * S_base,
                                    gb.GRB.EQUAL, 0)
            # m.addConstr(Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base <= M * W[i])
            # m.addConstr(Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base >= -M * W[i])
        else:
            m.addGenConstrIndicator(W[i], 0,
                                    0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 0) * S_base,
                                    gb.GRB.EQUAL, 0)
            m.addGenConstrIndicator(W[i], 0,
                                    0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Scene_Q_tran.sum(i, '*', t, 1) * S_base,
                                    gb.GRB.EQUAL, 0)
            # m.addConstr(0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base <= M * W[i])
            # m.addConstr(0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base >= -M * W[i])

ww = m.addVars(n, n, vtype=gb.GRB.BINARY, name="ww")  # u_ij*L_ij线性化
for i in range(n):
    for j in range(i+1,n):
        m.addConstr(ww[i, j] == ww[j, i])
        m.addConstr(ww[i, j] <= W[i])
        m.addConstr(ww[i, j] <= W[j])
        m.addConstr(ww[i, j] >= W[i] + W[j] - 1)


for i in range(n):
    for j in range(i+1,n):
        for t in range(T):
            m.addConstr(P_tran[i, j, t] <=  M* U[i, j])
            m.addConstr(P_tran[i, j, t] >= -M * U[i, j])
            m.addConstr(Q_tran[i, j, t] <= M * U[i, j])
            m.addConstr(Q_tran[i, j, t] >= -M * U[i, j])
            m.addConstr(Q_tran[i, j, t] <= M * (1-ww[i, j]))
            m.addConstr(Q_tran[i, j, t] >= -M * (1-ww[i, j]))
            m.addConstr(Scene_P_tran[i, j, t, 0] <= M * U[i, j])
            m.addConstr(Scene_P_tran[i, j, t, 0] >= -M * U[i, j])
            m.addConstr(Scene_Q_tran[i, j, t, 0] <= M * U[i, j])
            m.addConstr(Scene_Q_tran[i, j, t, 0] >= -M * U[i, j])
            m.addConstr(Scene_Q_tran[i, j, t, 0] <= M * (1 - ww[i, j]))
            m.addConstr(Scene_Q_tran[i, j, t, 0] >= -M * (1 - ww[i, j]))
            m.addConstr(Scene_P_tran[i, j, t, 1] <= M * U[i, j])
            m.addConstr(Scene_P_tran[i, j, t, 1] >= -M * U[i, j])
            m.addConstr(Scene_Q_tran[i, j, t, 1] <= M * U[i, j])
            m.addConstr(Scene_Q_tran[i, j, t, 1] >= -M * U[i, j])
            m.addConstr(Scene_Q_tran[i, j, t, 1] <= M * (1 - ww[i, j]))
            m.addConstr(Scene_Q_tran[i, j, t, 1] >= -M * (1 - ww[i, j]))
            # m.addGenConstrIndicator(U[i, j], 0,P_tran[i, j, t],gb.GRB.EQUAL, 0)
            # m.addGenConstrIndicator(U[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)
            # m.addGenConstrIndicator(ww[i, j], 0, Q_tran[i, j, t], gb.GRB.EQUAL, 0)


#
# # 电压方程
for i in range(n):
    # m.addConstr(wV[i, t] <= W[i] * V_max)
    # m.addConstr(wV[i, t] >= -W[i] * V_max)
    # m.addConstr(wV[i, t] -V[i, t]<= (1 - W[i]) * V_max)
    # m.addConstr(wV[i, t] -V[i, t]>= -1*(1 - W[i]) * V_max)
    for t in range(T):
        m.addConstr(wV[i, t] <= W[i] * V_max)
        m.addConstr(wV[i, t] >= W[i] * V_min)
        m.addConstr(wV[i, t] <= V[i, t] - (1 - W[i]) * V_min)
        m.addConstr(wV[i, t] >= V[i, t] - (1 - W[i]) * V_max)
        m.addConstr(Scene_wV[i, t, 0] <= W[i] * V_max)
        m.addConstr(Scene_wV[i, t, 0] >= W[i] * V_min)
        m.addConstr(Scene_wV[i, t, 0] <= Scene_V[i, t, 0] - (1 - W[i]) * V_min)
        m.addConstr(Scene_wV[i, t, 0] >= Scene_V[i, t, 0] - (1 - W[i]) * V_max)
        m.addConstr(Scene_wV[i, t, 1] <= W[i] * V_max)
        m.addConstr(Scene_wV[i, t, 1] >= W[i] * V_min)
        m.addConstr(Scene_wV[i, t, 1] <= Scene_V[i, t, 1] - (1 - W[i]) * V_min)
        m.addConstr(Scene_wV[i, t, 1] >= Scene_V[i, t, 1] - (1 - W[i]) * V_max)


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
                m.addConstr(V__svc[i, j, t] >= L[i, j] * V_min)
                m.addConstr(V__svc[i, j, t] <= wV[i, t] + wV[j, t])
                # Scene
                m.addConstr(Scene_V__svc[i, j, t, 0] >= L[i, j] * V_min)
                m.addConstr(Scene_V__svc[i, j, t, 0] <= Scene_wV[i, t, 0] + Scene_wV[j, t, 0])
                m.addConstr(Scene_V__svc[i, j, t, 1] >= L[i, j] * V_min)
                m.addConstr(Scene_V__svc[i, j, t, 1] <= Scene_wV[i, t, 1] + Scene_wV[j, t, 1])
                # normal

                # m.addConstr(E[i, j, t] <= ee[i, j] * V_max)
                # m.addConstr(E[i, j, t] >= -ee[i, j] * V_max)
                # m.addConstr(E[i, j, t] - V[i, t] <= (1 - ee[i, j]) * V_max)
                # m.addConstr(E[i, j, t] - V[i, t] >= (ee[i, j] - 1) * V_max)
                # m.addConstr(E[i, j, t] <= ee[i, j] * V_max)
                # m.addConstr(E[i, j, t] >= ee[i, j] * V_min)
                # m.addConstr(E[i, j, t] <= V[i, t]-(1 - ee[i, j]) * V_min)
                # m.addConstr(E[i, j, t] >= V[i, t]-(1 - ee[i, j]) * V_max)
                m.addGenConstrIndicator(ee[i, j], 1, E[i, j, t] == V[i, t])
                m.addGenConstrIndicator(ee[i, j], 0, E[i, j, t] == 0)
                # Scene
                m.addGenConstrIndicator(ee[i, j], 1, Scene_E[i, j, t, 0] == Scene_V[i, t, 0])
                m.addGenConstrIndicator(ee[i, j], 0, Scene_E[i, j, t, 0] == 0)
                m.addGenConstrIndicator(ee[i, j], 1, Scene_E[i, j, t, 1] == Scene_V[i, t, 1])
                m.addGenConstrIndicator(ee[i, j], 0, Scene_E[i, j, t, 1] == 0)
                #
                # m.addConstr(F[i, j, t] <= ff[i, j] * V_max)
                # m.addConstr(F[i, j, t] >= -ff[i, j] * V_max)
                # m.addConstr(F[i, j, t] - V__svc[i, j, t] <= (1 - ff[i, j]) * V_max)
                # m.addConstr(F[i, j, t] - V__svc[i, j, t] >= (ff[i, j] - 1) * V_max)
                # m.addConstr(F[i, j, t] <= ff[i, j] * V_max)
                # m.addConstr(F[i, j, t] >= ff[i, j] * 0)
                # m.addConstr(F[i, j, t] <= V__svc[i, j, t] - (1 - ff[i, j]) * 0)
                # m.addConstr(F[i, j, t] >= V__svc[i, j, t] - (1 - ff[i, j]) * V_max)
                m.addGenConstrIndicator(ff[i, j], 1, F[i, j, t] == V__svc[i, j, t])
                m.addGenConstrIndicator(ff[i, j], 0, F[i, j, t] == 0)
                m.addGenConstrIndicator(ff[i, j], 1, Scene_F[i, j, t, 0] == Scene_V__svc[i, j, t, 0])
                m.addGenConstrIndicator(ff[i, j], 0, Scene_F[i, j, t, 0] == 0)
                m.addGenConstrIndicator(ff[i, j], 1, Scene_F[i, j, t, 1] == Scene_V__svc[i, j, t, 1])
                m.addGenConstrIndicator(ff[i, j], 0, Scene_F[i, j, t, 1] == 0)
                #
                # m.addConstr(G[i, j, t] <= gg[i, j] * V_max)
                # m.addConstr(G[i, j, t] >= -gg[i, j] * V_max)
                # m.addConstr(G[i, j, t] - V__svc[i, j, t] <= (1 - gg[i, j]) * V_max)
                # m.addConstr(G[i, j, t] - V__svc[i, j, t] >= (gg[i, j] - 1) * V_max)
                # m.addConstr(G[i, j, t] <= gg[i, j] * V_max)
                # m.addConstr(G[i, j, t] >= gg[i, j] * 0)
                # m.addConstr(G[i, j, t] <= V__svc[i, j, t] - (1 - gg[i, j]) * 0)
                # m.addConstr(G[i, j, t] >= V__svc[i, j, t] - (1 - gg[i, j]) * V_max)
                m.addGenConstrIndicator(gg[i, j], 1, G[i, j, t] == V__svc[i, j, t])
                m.addGenConstrIndicator(gg[i, j], 0, G[i, j, t] == 0)
                m.addGenConstrIndicator(gg[i, j], 1, Scene_G[i, j, t, 0] == Scene_V__svc[i, j, t, 0])
                m.addGenConstrIndicator(gg[i, j], 0, Scene_G[i, j, t, 0] == 0)
                m.addGenConstrIndicator(gg[i, j], 1, Scene_G[i, j, t, 1] == Scene_V__svc[i, j, t, 1])
                m.addGenConstrIndicator(gg[i, j], 0, Scene_G[i, j, t, 1] == 0)
                #
                # m.addConstr(H[i, j, t] <= hh[i, j] * V_max)
                # m.addConstr(H[i, j, t] >= -hh[i, j] * V_max)
                # m.addConstr(H[i, j, t] - V[i, t] <= (1 - hh[i, j]) * V_max)
                # m.addConstr(H[i, j, t] - V[i, t] >= (hh[i, j] - 1) * V_max)
                # m.addConstr(H[i, j, t] <= hh[i, j] * V_max)
                # m.addConstr(H[i, j, t] >= hh[i, j] * V_min)
                # m.addConstr(H[i, j, t] <= V[j, t] - (1 - hh[i, j]) * V_min)
                # m.addConstr(H[i, j, t] >= V[j, t] - (1 - hh[i, j]) * V_max)
                m.addGenConstrIndicator(hh[i, j], 1, H[i, j, t] == V[j, t])
                m.addGenConstrIndicator(hh[i, j], 0, H[i, j, t] == 0)
                m.addGenConstrIndicator(hh[i, j], 1, Scene_H[i, j, t, 0] == Scene_V[j, t, 0])
                m.addGenConstrIndicator(hh[i, j], 0, Scene_H[i, j, t, 0] == 0)
                m.addGenConstrIndicator(hh[i, j], 1, Scene_H[i, j, t, 1] == Scene_V[j, t, 1])
                m.addGenConstrIndicator(hh[i, j], 0, Scene_H[i, j, t, 1] == 0)


                #
                m.addConstr(
                    E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t] - r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] *
                    Q_tran[i, j, t] <= M * (1 - L[i, j]))
                m.addConstr(
                    E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t] - r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] *
                    Q_tran[i, j, t] >= M * (L[i, j] - 1))
                m.addConstr(
                    E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t] - r__[i][j] * P_tran[i, j, t] - x__[i][j] *
                    Q_tran[i, j, t] <= M * L[i, j])
                m.addConstr(
                    E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t] - r__[i][j] * P_tran[i, j, t] - x__[i][j] *
                    Q_tran[i, j, t] >= -1 * M * L[i, j])
                #
                m.addConstr(
                    Scene_E[i, j, t, 0] + Scene_F[i, j, t, 0] - Scene_G[i, j, t, 0] - Scene_H[i, j, t, 0] - r__vsc[i][j] *
                    Scene_P_tran[i, j, t, 0] - x__vsc[i][j] *
                    Scene_Q_tran[i, j, t, 0] <= M * (1 - L[i, j]))
                m.addConstr(
                    Scene_E[i, j, t, 0] + Scene_F[i, j, t, 0] - Scene_G[i, j, t, 0] - Scene_H[i, j, t, 0] - r__vsc[i][j] *
                    Scene_P_tran[i, j, t, 0] - x__vsc[i][j] *
                    Scene_Q_tran[i, j, t, 0] >= M * (L[i, j] - 1))
                m.addConstr(
                    Scene_E[i, j, t, 0] + Scene_F[i, j, t, 0] - Scene_G[i, j, t, 0] - Scene_H[i, j, t, 0] - r__[i][j] *
                    Scene_P_tran[i, j, t, 0] - x__[i][j] *
                    Scene_Q_tran[i, j, t, 0] <= M * L[i, j])
                m.addConstr(
                    Scene_E[i, j, t, 0] + Scene_F[i, j, t, 0] - Scene_G[i, j, t, 0] - Scene_H[i, j, t, 0] - r__[i][j] *
                    Scene_P_tran[i, j, t, 0] - x__[i][j] *
                    Scene_Q_tran[i, j, t, 0] >= -1 * M * L[i, j])
                m.addConstr(
                    Scene_E[i, j, t, 1] + Scene_F[i, j, t, 1] - Scene_G[i, j, t, 1] - Scene_H[i, j, t, 1] - r__vsc[i][j] * Scene_P_tran[i, j, t, 1] - x__vsc[i][j] *
                    Scene_Q_tran[i, j, t, 1] <= M * (1 - L[i, j]))
                m.addConstr(
                    Scene_E[i, j, t, 1] + Scene_F[i, j, t, 1] - Scene_G[i, j, t, 1] - Scene_H[i, j, t, 1] - r__vsc[i][j] * Scene_P_tran[i, j, t, 1] - x__vsc[i][j] *
                    Scene_Q_tran[i, j, t, 1] >= M * (L[i, j] - 1))
                m.addConstr(
                    Scene_E[i, j, t, 1] + Scene_F[i, j, t, 1] - Scene_G[i, j, t, 1] - Scene_H[i, j, t, 1] - r__[i][j] * Scene_P_tran[i, j, t, 1] - x__[i][j] *
                    Scene_Q_tran[i, j, t, 1] <= M * L[i, j])
                m.addConstr(
                    Scene_E[i, j, t, 1] + Scene_F[i, j, t, 1] - Scene_G[i, j, t, 1] - Scene_H[i, j, t, 1] - r__[i][j] * Scene_P_tran[i, j, t, 1] - x__[i][j] *
                    Scene_Q_tran[i, j, t, 1] >= -1 * M * L[i, j])

                # m.addGenConstrIndicator(L[i,j], 0,
                #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__[i][j] * P_tran[i, j, t] - x__[i][j] * Q_tran[i, j, t],
                #                         gb.GRB.EQUAL, 0)
                # m.addGenConstrIndicator(L[i, j], 1,
                #                         E[i, j, t] + F[i, j, t] - G[i, j, t] - H[i, j, t]-r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t],
                #                         gb.GRB.EQUAL, 0)

                #
                m.addConstr(Q_tran[i, j, t] <= L[i, j] * (Q_vsc_max - M) + M)
                m.addConstr(Q_tran[i, j, t] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))
                m.addConstr(Scene_Q_tran[i, j, t, 0] <= L[i, j] * (Q_vsc_max - M) + M)
                m.addConstr(Scene_Q_tran[i, j, t, 0] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))
                m.addConstr(Scene_Q_tran[i, j, t, 1] <= L[i, j] * (Q_vsc_max - M) + M)
                m.addConstr(Scene_Q_tran[i, j, t, 1] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))

                #
                m.addConstr(P_tran[i, j, t]*S_base <=  gama* S_line)
                m.addConstr(P_tran[i, j, t]*S_base >= -gama * S_line)
                m.addConstr(Scene_P_tran[i, j, t, 0] * S_base <= gama * S_line)
                m.addConstr(Scene_P_tran[i, j, t, 0] * S_base >= -gama * S_line)
                m.addConstr(Scene_P_tran[i, j, t, 1] * S_base <= gama * S_line)
                m.addConstr(Scene_P_tran[i, j, t, 1] * S_base >= -gama * S_line)

                m.addConstr(Q_tran[i, j, t] <= gama * S_line/S_base)
                m.addConstr(Q_tran[i, j, t] >= -gama * S_line/S_base)
                m.addConstr(Scene_Q_tran[i, j, t, 0] <= gama * S_line / S_base)
                m.addConstr(Scene_Q_tran[i, j, t, 0] >= -gama * S_line / S_base)
                m.addConstr(Scene_Q_tran[i, j, t, 1] <= gama * S_line / S_base)
                m.addConstr(Scene_Q_tran[i, j, t, 1] >= -gama * S_line / S_base)

                m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] <= 1.41 * gama * S_line/S_base)
                m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] >= -1.41 * gama * S_line/S_base)
                m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 0] + Scene_Q_tran[i, j, t, 0] <= 1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 0] + Scene_Q_tran[i, j, t, 0] >= -1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 0] - Scene_Q_tran[i, j, t, 0] <= 1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 0] - Scene_Q_tran[i, j, t, 0] >= -1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 1] + Scene_Q_tran[i, j, t, 1] <= 1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 1] + Scene_Q_tran[i, j, t, 1] >= -1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 1] - Scene_Q_tran[i, j, t, 1] <= 1.41 * gama * S_line / S_base)
                m.addConstr(Scene_P_tran[i, j, t, 1] - Scene_Q_tran[i, j, t, 1] >= -1.41 * gama * S_line / S_base)

# m.setParam("Threads", 8)
f1=C_invest + C_operation
f2=1-delta/0.4
# m.setObjective(f1, gb.GRB.MINIMIZE)
m.setObjectiveN(f1,index=0,
                    priority=2,
                    weight=1.0,
                    name="f1")
m.setObjectiveN(f2,index=1,
                    priority=3,
                    weight=1.0,
                    name="f2")

m.optimize()
Result = []
for v in m.getVars():
    Result.append([v.VarName, v.X])
    if v.varName.split('[')[0] in ['W', 'U','x','P_sub','P_ess_ch','P_ess_dis']:
        print(v.VarName, v.X)

for i in range(m.NumObj):
    print(f"Objective {i} value =", m.getObjective(i).getValue())
# obj0_val = m.ObjN[0].getValue()
# obj1_val = m.ObjN[1].getValue()
# # obj2_val = m.ObjNVal[2]
# # print('Obj:', m.objVal)
# print('Obj:', obj0_val)
# print('Obj:', obj1_val)
# print('Obj:', obj2_val)
# m.computeIIS()
# m.write("model.ilp")
with open('Result.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    for row in Result:
        writer.writerow(row)
