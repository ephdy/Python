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

# 线路阻抗
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

# 线路选材成本和容量
c_l = [147648, 295296]
S_line_k = [2.5, 5]

# 节点资源情况
n__ac = [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1]
n__dc = [0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0]
n__wind = [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0]
n__pv = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
n__ess = [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]

# 24小时P、Q
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
V__vsc = m.addVars(n, n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V__svc")
for i in range(n):
    for j in range(i + 1, n):
        m.addConstr(V__vsc[i, j, t] == V__vsc[j, i, t])
        m.addConstr(V__vsc[i, j, t] == V__vsc[j, i, t])

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
# 购电功率
P_sub = m.addVars(24, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_sub")
Q_sub = m.addVars(24, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_sub")
# 储能充放电功率
P_ess_ch = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
P_ess_dis = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
# DG出力
P_DG_813 = m.addVars(2, 24, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
P_DG_911 = m.addVars(2, 24, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
Q_DG_813 = m.addVars(2, 24, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Q_DG_813")
Q_DG_911 = m.addVars(2, 24, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Q_DG_911")

# 中间变量
X = m.addVars(n, n, kk, vtype=gb.GRB.BINARY, name="X")  # 线性化引入辅助变量X=x*u
L = m.addVars(n, n, vtype=gb.GRB.BINARY, name="L")  # L=|w_i-w_j|
uL = m.addVars(n, n, vtype=gb.GRB.BINARY, name="uL")  # u_ij*L_ij线性化
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
    f_op += c_d * (2 - P_DG_813[0, t])
    f_op += c_d * (2.5 - P_DG_911[0, t])
    f_op += c_d * (2.5 - P_DG_911[1, t])
    f_op += c_d * (2 - P_DG_813[1, t])

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
        elif i == 5:
            m.addConstr(
                0 - P_load[t] * (n__ac[i] + n__dc[i]) + P_ess_dis[t] - P_ess_ch[t] - P_tran.sum(i, '*', t) * S_base == 0)
        elif i == 7:
            m.addConstr(P_DG_813[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
        elif i == 8:
            m.addConstr(P_DG_911[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
        elif i == 10:
            m.addConstr(P_DG_911[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
        elif i == 12:
            m.addConstr(P_DG_813[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
        else:
            m.addConstr( 0 - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)

# 无功功率平衡方程
for i in range(n):
    for t in range(T):
        if i == 0:
            m.addConstr(Q_sub[t] - Q_tran.sum(i, '*', t) * S_base == 0)
        elif i == 7:
            m.addConstr((1-W[i])*(Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) ==0)
        elif i == 8:
            m.addConstr((1-W[i])*(Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) == 0)
        elif i == 10:
            m.addConstr((1-W[i])*(Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) == 0)
        elif i == 12:
            m.addConstr((1-W[i])*(Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) == 0)
        else:
            m.addConstr((1-W[i])*(0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) == 0)


for i in range(n):
    for j in range(i+1,n):
        for t in range(T):
            m.addConstr(P_tran[i, j, t] <= M * U[i, j])
            m.addConstr(P_tran[i, j, t] >= -M * U[i, j])
            m.addConstr(Q_tran[i, j, t] <= M * U[i, j])
            m.addConstr(Q_tran[i, j, t] >= -M * U[i, j])
            m.addConstr(Q_tran[i, j, t] <= M * (1-W[i]*W[j]))
            m.addConstr(Q_tran[i, j, t] >= -M * (1-W[i]*W[j]))

for i in range(n):
    for j in range(n):
        if i != j:
            m.addConstr(U[i,j]*((1-L[i,j]*W[i])*V[i,t]+(L[i,j]*W[i]-L[i,j]*W[j])*V__vsc[i,j,t]-(1-L[i,j]*W[j])*U[j,t])==
                        (1-L[i,j]*(r__[i,j]*P_tran[i,j]+x__*Q_tran[i,j]))+L[i,j]*(r__vsc[i,j]*P_tran[i,j]+x__vsc*Q_tran[i,j]))
            m.addConstr(V__vsc[i,j,t]>=V_min*L[i,j])
            m.addConstr(V__vsc[i, j, t] <= (W[i]*V[i,t]+W[j]*V[j,t]))
            m.addConstr(Q_tran[i, j, t] <= L[i, j] * (Q_vsc_max - M) + M)
            m.addConstr(Q_tran[i, j, t] >= -1 * (L[i, j] * (Q_vsc_max - M) + M))
            S_line = 0
            for k in range(kk):
                S_line += x[i, j, k] * S_line_k[k]
            m.addConstr(S_line <= S_vsc_ij)
            m.addConstr(P_tran[i, j, t]*P_tran[i, j, t]+Q_tran[i, j, t]*Q_tran[i, j, t] <= pow(gama*S_line,2))

#储能约束
alpha__dis=m.addVars(T,vtype=gb.GRB.BINARY)
alpha__ch=m.addVars(T,vtype=gb.GRB.BINARY)
E_k=m.addVars(T,lb=0.1*S_ess,ub=0.9*S_ess,vtype=gb.GRB.CONTINUOUS)
m.addConstr(E_k[0]==5)
for t in range(T):
    m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
    m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
    m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
    if t !=0:
        m.addConstr(E_k[t]==E_k[t-1]+P_ess_ch[t]*0.9-P_ess_dis[t]/0.9)
m.addConstr(gb.quicksum(P_ess_ch)*0.9 == gb.quicksum(P_ess_dis)/0.9)



m.setObjective(C_invest + C_operation, gb.GRB.MINIMIZE)
# m.setObjective(gb.quicksum(x), gb.GRB.MAXIMIZE)
m.optimize()
for v in m.getVars():
    if v.varName.split('[')[0] in ['W', 'U', 'P_sub', 'P_tran', 'Q_tran']:
        print(v.VarName, v.X)
print('Obj:', m.objVal)
