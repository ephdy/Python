import gurobipy as gb

# 定义系统参数
n = 13  # 节点数
kk = 2  # 线路选型种类
N_d, T_line, T_cvt, T_p, T = 365, 40, 45, 40, 24
beta_line, beta_cvt = 0.05, 0.05  # 线路、换流器年维护费用系数
r = 0.075  # 贴现率
c_v, c_c, c_s, c_d, c_e = 1154.13e3, 1018.35e3, 400, 400, 10
L_min, L_max = 1, 2
M = 100
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
r__ = [[0 for _ in range(n)] for _ in range(n)]
x__ = [[0 for _ in range(n)] for _ in range(n)]
r__vsc = [[0 for _ in range(n)] for _ in range(n)]
x__vsc = [[0 for _ in range(n)] for _ in range(n)]
for i in range(n):
    for j in range(n):
        r__[i][j] = Length[i][j] * 0.0598
        r__vsc[i][j] = r__[i][j] + 0.2889
        x__[i][j] = Length[i][j] * 0.0979
        x__vsc[i][j] = x__[i][j] + 0.7548
c_l = [147648, 295296]
S_line_k = [2.5, 5]
n__ac = [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1]
n__dc = [0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0]
n__wind = [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0]
n__pv = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
n__ess = [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
P_load = [6.40, 6.20, 6.00, 5.90, 5.80, 5.60, 5.50, 5.60, 5.90, 6.40, 6.80, 7.00, 7.20, 7.30, 7.00, 6.60, 6.80, 7.50,
          7.90, 7.80, 7.60, 7.20, 6.90, 6.60]
Q_load = []
for i in range(len(P_load)):
    P_load[i] = P_load[i] / (sum(n__ac) + sum(n__dc))
    Q_load.append(P_load[i] * 0.619)
# DG容量配置情况
P_DG_max = [[0 for _ in range(T)] for _ in range(n)]
for i in [[8, 2.0], [9, 2.5], [11, 2.5], [13, 2.0]]:
    for t in range(T):
        P_DG_max[i[0] - 1][t] += i[1]

# print(P_DG_max)
m = gb.Model("mip1")
# 定义节点类型变量
W = m.addVars(n, vtype=gb.GRB.BINARY, name="W")
m.addConstr(W[0] == 0)
# 定义节点连接变量
U = m.addVars(n, n, vtype=gb.GRB.BINARY, name="U")
for i in range(n):
    m.addConstr(U[i, i] == 0)
for i in range(n):
    for j in range(i + 1, n):
        m.addConstr(U[i, j] == U[j, i])
# 定义线路类型变量
x = m.addVars(n, n, kk, vtype=gb.GRB.BINARY, name="x")

# 线路选型约束
for i in range(n):
    for j in range(n):
        m.addConstr(x.sum(i, j, '*') == 1)
#         (gb.quicksum(x[i, j, kk] for kk in range(k)) == 1)
for i in range(n):
    for j in range(i + 1, n):
        for k in range(kk):
            m.addConstr(x[i, j, k] == x[j, i, k])

# 定义各节点电压
V = m.addVars(n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
V__svc = m.addVars(n, n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V__svc")
for i in range(n):
    for j in range(i + 1, n):
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
            m.addConstr(P_tran[i, j, t] == -P_tran[j, i, t])
            m.addConstr(Q_tran[i, j, t] == -Q_tran[j, i, t])

# 目标函数

# 线路建设成本
C_line = 0
X = m.addVars(n, n, kk, vtype=gb.GRB.BINARY, name="X")  # 线性化引入辅助变量X=x*u
for i in range(n):
    for j in range(n):
        for k in range(kk):
            m.addConstr(X[i, j, k] <= x[i, j, k])
            m.addConstr(X[i, j, k] <= U[i, j])
            m.addConstr(X[i, j, k] >= x[i, j, k] + U[i, j] - 1)
for i in range(n):
    for j in range(n):
        for k in range(kk):
            # C_line += c_l[k] * L[i][j] * x[i, j, k] * U[i, j]#未线性化
            C_line += 0.5 * c_l[k] * Length[i][j] * X[i, j, k]
# 线路建设成本
# 定义换流支路
L = m.addVars(n, n, vtype=gb.GRB.BINARY, name="L")
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
uL = m.addVars(n, n, vtype=gb.GRB.BINARY, name="uL")  # u_ij*L_ij线性化
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
P_sub = m.addVars(24, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_sub")
Q_sub = m.addVars(24, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_sub")
P_ess_ch = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
P_ess_dis = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
P_DG_813 = m.addVars(2, 24, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
P_DG_911 = m.addVars(2, 24, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
Q_DG_813 = m.addVars(2, 24, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Q_DG_813")
Q_DG_911 = m.addVars(2, 24, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Q_DG_911")
C_operation = 0
f_op = 0

for t in range(T):
    f_op += c_s * P_sub[t]
    f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
    f_op += c_d * (2 - P_DG_813[0, t])
    f_op += c_d * (2.5 - P_DG_911[0, t])
    f_op += c_d * (2.5 - P_DG_911[1, t])
    f_op += c_d * (2 - P_DG_813[1, t])

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
        SS = 0
        for j in range(n):
            if i != j:
                SS += P_tran[i, j, t] * S_base
        if i == 0:
            m.addConstr(SS == P_sub[t])
            # m.addConstr(P_sub[t] - P_load[t] - SS <= e)
            # m.addConstr(P_sub[t] - P_load[t] - SS >= 0)
        elif i == 5:
            m.addConstr(
                SS == 0 - P_load[t] * (n__ac[i] + n__dc[i]) + P_ess_dis[t] - P_ess_ch[t])
            # m.addConstr(
            #     0 - P_load[t] + P_ess_dis[t] - P_ess_ch[t] - SS <= e)
            # m.addConstr(
            #     0 - P_load[t] + P_ess_dis[t] - P_ess_ch[t] - SS >= 0)
        elif i == 7:
            m.addConstr(SS == P_DG_813[0, t] - P_load[t] * (n__ac[i] + n__dc[i]))
        elif i == 8:
            m.addConstr(SS == P_DG_911[0, t] - P_load[t] * (n__ac[i] + n__dc[i]))
        elif i == 10:
            m.addConstr(SS == P_DG_911[1, t] - P_load[t] * (n__ac[i] + n__dc[i]))
        elif i == 12:
            m.addConstr(SS == P_DG_813[1, t] - P_load[t] * (n__ac[i] + n__dc[i]))
        else:
            m.addConstr(SS == 0 - P_load[t] * (n__ac[i] + n__dc[i]))
        # m.addConstr(P_sub[t] * (i == 1) + P_DG[i, t] * n__wind[i] + P_DG[i, t] * n__pv[i] - P_load[t] + (P_ess_dis[t] - P_ess_ch[t]) * n__ess[i] - SS == 0)

# 无功功率平衡方程
for i in range(n):
    for t in range(T):
        SS = 0
        for j in range(n):
            if i != j:
                SS += Q_tran[i, j, t] * S_base
        if i == 0:
            m.addConstr(Q_sub[t] - SS == 0)
        elif i == 7:
            m.addConstr(Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS <= M * W[i])
            m.addConstr(Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS >= -M * W[i])
        elif i == 8:
            m.addConstr(Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS <= M * W[i])
            m.addConstr(Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS >= -M * W[i])
        elif i == 10:
            m.addConstr(Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS <= M * W[i])
            m.addConstr(Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS >= -M * W[i])
        elif i == 12:
            m.addConstr(Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS <= M * W[i])
            m.addConstr(Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - SS >= -M * W[i])
        else:
            m.addConstr(0 - Q_load[t] * (n__ac[i] + n__dc[i]) - SS <= M * W[i])
            m.addConstr(0 - Q_load[t] * (n__ac[i] + n__dc[i]) - SS >= -M * W[i])

ww = m.addVars(n, n, vtype=gb.GRB.BINARY, name="ww")  # u_ij*L_ij线性化
for i in range(n):
    for j in range(n):
        m.addConstr(ww[i, j] <= W[i])
        m.addConstr(ww[i, j] <= W[j])
        m.addConstr(ww[i, j] >= W[i] + W[j] - 1)

for i in range(n):
    for j in range(i + 1, n):
        for t in range(T):
            m.addConstr(P_tran[i, j, t] <= M * U[i, j])
            m.addConstr(P_tran[i, j, t] >= -M * U[i, j])
            m.addConstr(Q_tran[i, j, t] <= M * U[i, j])
            m.addConstr(Q_tran[i, j, t] >= -M * U[i, j])
            m.addConstr(Q_tran[i, j, t] <= M * ww[i, j])
            m.addConstr(Q_tran[i, j, t] >= -M * ww[i, j])

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
for i in range(n):
    m.addConstr(wV[i, t] <= W[i] * V_max)
    m.addConstr(wV[i, t] >= -W[i] * V_max)
    m.addConstr(wV[i, t] - wV[i, t] <= (1 - W[i]) * V_max)
    m.addConstr(wV[i, t] - wV[i, t] >= (W[i] - 1) * V_max)
    for j in range(n):
        if i != j:
            m.addConstr(f[i, j] <= L[i, j])
            m.addConstr(f[i, j] <= W[i])
            m.addConstr(f[i, j] >= L[i, j] + W[i] - 1)
            m.addConstr(g[i, j] <= L[i, j])
            m.addConstr(g[i, j] <= W[j])
            m.addConstr(g[i, j] >= L[i, j] + W[j] - 1)
            m.addConstr(f[i, j] <= L[i, j])
            m.addConstr(e[i, j] + f[i, j] == 1)
            m.addConstr(g[i, j] + h[i, j] == 1)

            m.addConstr(ee[i, j] <= e[i, j])
            m.addConstr(ee[i, j] <= U[i, j])
            m.addConstr(ee[i, j] >= e[i, j] + U[i, j] - 1)
            m.addConstr(ff[i, j] <= f[i, j])
            m.addConstr(ff[i, j] <= U[i, j])
            m.addConstr(ff[i, j] >= f[i, j] + U[i, j] - 1)
            m.addConstr(gg[i, j] <= g[i, j])
            m.addConstr(gg[i, j] <= U[i, j])
            m.addConstr(gg[i, j] >= g[i, j] + U[i, j] - 1)
            m.addConstr(hh[i, j] <= h[i, j])
            m.addConstr(hh[i, j] <= U[i, j])
            m.addConstr(hh[i, j] >= h[i, j] + U[i, j] - 1)
            #
            S_line = 0
            for k in range(kk):
                S_line += x[i, j, k] * S_line_k[k]
            m.addConstr(S_line <= S_vsc_ij)
            for t in range(T):
                #
                m.addConstr(E[i, j, t] <= ee[i, j] * V_max)
                m.addConstr(E[i, j, t] >= -ee[i, j] * V_max)
                m.addConstr(E[i, j, t] - V[i, t] <= (1 - ee[i, j]) * V_max)
                m.addConstr(E[i, j, t] - V[i, t] >= (ee[i, j] - 1) * V_max)
                #
                m.addConstr(F[i, j, t] <= ff[i, j] * V_max)
                m.addConstr(F[i, j, t] >= -ff[i, j] * V_max)
                m.addConstr(F[i, j, t] - V__svc[i, j, t] <= (1 - ff[i, j]) * V_max)
                m.addConstr(F[i, j, t] - V__svc[i, j, t] >= (ff[i, j] - 1) * V_max)
                #
                m.addConstr(G[i, j, t] <= gg[i, j] * V_max)
                m.addConstr(G[i, j, t] >= -gg[i, j] * V_max)
                m.addConstr(G[i, j, t] - V__svc[i, j, t] <= (1 - gg[i, j]) * V_max)
                m.addConstr(G[i, j, t] - V__svc[i, j, t] >= (gg[i, j] - 1) * V_max)
                #
                m.addConstr(H[i, j, t] <= hh[i, j] * V_max)
                m.addConstr(H[i, j, t] >= -hh[i, j] * V_max)
                m.addConstr(H[i, j, t] - V[i, t] <= (1 - hh[i, j]) * V_max)
                m.addConstr(H[i, j, t] - V[i, t] >= (hh[i, j] - 1) * V_max)
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
                    Q_tran[i, j, t] >= -M * L[i, j])
                #
                m.addConstr(V__svc[i, j, t] >= L[i, j] * V_min)
                m.addConstr(V__svc[i, j, t] <= wV[i, t] + wV[j, t])
                #
                m.addConstr(Q_tran[i, j, t] <= L[i, j] * (Q_vsc_max - M) + M)
                m.addConstr(Q_tran[i, j, t] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))
                #
                m.addConstr(P_tran[i, j, t] <= gama * S_line / S_base)
                m.addConstr(P_tran[i, j, t] >= -gama * S_line / S_base)
                m.addConstr(Q_tran[i, j, t] <= gama * S_line / S_base)
                m.addConstr(Q_tran[i, j, t] >= -gama * S_line / S_base)
                m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
# 储能约束
alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS)
m.addConstr(E_k[0] == 5)
ess_dis, ess_ch = 0, 0
for t in range(T):
    m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
    m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
    m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
    if t != 0:
        m.addConstr(E_k[t] == E_k[t - 1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    ess_ch += P_ess_ch[t] * 0.9
    ess_dis += P_ess_dis[t] / 0.9
m.addConstr(ess_dis == ess_ch)

m.setObjective(C_invest + C_operation, gb.GRB.MINIMIZE)
# m.setObjective(gb.quicksum(x), gb.GRB.MAXIMIZE)
m.optimize()
for v in m.getVars():
    if v.varName.split('[')[0] in ['W', 'U', 'P_sub', 'P_tran', 'Q_tran']:
        print(v.VarName, v.X)
print('Obj:', m.objVal)
