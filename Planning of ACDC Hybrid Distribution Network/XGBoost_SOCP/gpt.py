import gurobipy as gp
from gurobipy import GRB
from _13_nodes_distribution_network import *
def build_model():

    m = gp.Model("Hybrid_ACDC_planning")

    # -----------------------------
    # 集合
    # -----------------------------
    N = range(n)
    Tset = range(T)

    # 只定义 i<j 的线路
    E = [(i,j) for i in N for j in N if i<j]

    # -----------------------------
    # 变量
    # -----------------------------

    # 节点类型
    W = m.addVars(N, vtype=GRB.BINARY,name="W")

    # 是否建线
    U = m.addVars(E,vtype=GRB.BINARY,name="U")

    # 线路型号
    x = m.addVars(E,vtype=GRB.BINARY,name="x")

    # VSC线路判断
    L = m.addVars(E,vtype=GRB.BINARY,name="L")

    # 电压平方
    V2 = m.addVars(N,Tset,lb=V_min**2,ub=V_max**2,name="V2")

    # 潮流
    P = m.addVars(N,N,Tset,lb=-1,ub=1,name="P")
    Q = m.addVars(N,N,Tset,lb=-1,ub=1,name="Q")
    I2 = m.addVars(N,N,Tset,lb=0,name="I2")

    # 购电
    P_buy = m.addVars(Tset,lb=0,ub=10,name="P_buy")
    Q_buy = m.addVars(Tset,lb=-4.8,ub=4.8,name="Q_buy")

    # DG
    P_DG = m.addVars(N,Tset,lb=0,name="P_DG")
    Q_DG = m.addVars(N,Tset,name="Q_DG")

    # 储能
    P_ch = m.addVars(Tset,lb=0,name="P_ch")
    P_dis = m.addVars(Tset,lb=0,name="P_dis")
    E = m.addVars(Tset,lb=0.1 * S_ess, ub=0.9 * S_ess,name="E")

    alpha_ch = m.addVars(Tset,vtype=GRB.BINARY)
    alpha_dis = m.addVars(Tset,vtype=GRB.BINARY)

    # -----------------------------
    # 网络结构约束
    # -----------------------------

    # 节点类型
    m.addConstr(W[0]==1)

    # 线路型号必须建线
    for (i,j) in E:
        m.addConstr(x[i,j] <= U[i,j])

    # VSC判断
    for (i,j) in E:

        m.addConstr(L[i,j] >= W[i] - W[j])
        m.addConstr(L[i,j] >= W[j] - W[i])
        m.addConstr(L[i,j] <= W[i] + W[j])
        m.addConstr(L[i,j] <= 2 - W[i] - W[j])

    # -----------------------------
    # 连通性 (virtual flow)
    # -----------------------------

    F = m.addVars(N,N,lb=-(n-1),ub=n-1,name="F")

    for i in N:
        for j in N:
            if i!=j:

                if (min(i,j),max(i,j)) in E:

                    m.addConstr(F[i,j] <= (n-1)*U[min(i,j),max(i,j)])
                    m.addConstr(F[i,j] >= -(n-1)*U[min(i,j),max(i,j)])

                else:

                    m.addConstr(F[i,j]==0)

    m.addConstr(gp.quicksum(F[0,j] for j in N if j!=0)==n-1)

    for i in N:
        if i!=0:
            m.addConstr(
                gp.quicksum(F[j,i] for j in N if j!=i) -
                gp.quicksum(F[i,j] for j in N if j!=i)
                ==1
            )

    # -----------------------------
    # 潮流绑定线路
    # -----------------------------

    for (i,j) in E:
        for t in Tset:

            m.addConstr(P[i,j,t] <= M*U[i,j])
            m.addConstr(P[i,j,t] >= -M*U[i,j])

            m.addConstr(Q[i,j,t] <= M*U[i,j])
            m.addConstr(Q[i,j,t] >= -M*U[i,j])

            m.addConstr(I2[i,j,t] <= M*U[i,j])

    # -----------------------------
    # 参数插值
    # -----------------------------

    r = {}
    xline = {}

    for (i,j) in E:

        r[i,j] = r_ac[i][j] + (r_vsc[i][j]-r_ac[i][j]) * L[i,j]
        xline[i,j] = x_ac[i][j] + (x_vsc[i][j]-x_ac[i][j]) * L[i,j]

    # -----------------------------
    # DistFlow
    # -----------------------------

    for (i,j) in E:
        for t in Tset:

            m.addConstr(
                P[i,j,t] + P[j,i,t] ==
                r[i,j]*I2[i,j,t]
            )

            m.addConstr(
                Q[i,j,t] + Q[j,i,t] ==
                xline[i,j]*I2[i,j,t]
            )

    # -----------------------------
    # 电压方程
    # -----------------------------

    for (i,j) in E:
        for t in Tset:

            m.addConstr(
                V2[j,t] ==
                V2[i,t]
                -2*r[i,j]*P[i,j,t]
                -2*xline[i,j]*Q[i,j,t]
            )

    # -----------------------------
    # SOC潮流
    # -----------------------------

    for (i,j) in E:
        for t in Tset:

            m.addQConstr(
                P[i,j,t]*P[i,j,t] +
                Q[i,j,t]*Q[i,j,t]
                <= V2[i,t]*I2[i,j,t]
            )

    # -----------------------------
    # 功率平衡
    # -----------------------------

    for i in N:
        for t in Tset:

            Pin = gp.quicksum(P[j,i,t] for j in N if j!=i)
            Pout = gp.quicksum(P[i,j,t] for j in N if j!=i)

            m.addConstr(
                Pin - Pout
                + P_DG[i,t]
                + P_dis[t]*ess_bus[i]
                - P_ch[t]*ess_bus[i]
                + P_buy[t]*grid_bus[i]
                ==
                P_load[i][t]
            )

    # -----------------------------
    # DC节点无功
    # -----------------------------

    for i in N:
        for j in N:
            for t in Tset:

                m.addConstr(Q[i,j,t] <= M*W[i])
                m.addConstr(Q[i,j,t] >= -M*W[i])

    # -----------------------------
    # 储能
    # -----------------------------

    m.addConstr(E[0]==E_init)

    for t in Tset:

        m.addConstr(alpha_ch[t] + alpha_dis[t] <=1)

        m.addConstr(P_ch[t] <= alpha_ch[t]*Pmax_ess)
        m.addConstr(P_dis[t] <= alpha_dis[t]*Pmax_ess)

        if t>0:

            m.addConstr(
                E[t]==E[t-1]
                + eta_ch*P_ch[t]
                - P_dis[t]/eta_dis
            )

    m.addConstr(E[T-1]==E[0])

    # -----------------------------
    # 线路容量
    # -----------------------------

    for (i,j) in E:

        S = S0 + (S1-S0)*x[i,j]

        for t in Tset:

            m.addConstr(P[i,j,t] <= gamma*S)
            m.addConstr(P[i,j,t] >= -gamma*S)

            m.addConstr(Q[i,j,t] <= gamma*S)
            m.addConstr(Q[i,j,t] >= -gamma*S)

    # -----------------------------
    # 目标函数
    # -----------------------------

    C_line = gp.quicksum(
        length[i][j]*(c0 + (c1-c0)*x[i,j]) * U[i,j]
        for (i,j) in E
    )

    C_op = gp.quicksum(
        c_e * P_buy[t]
        for t in Tset
    )

    m.setObjective(C_line + C_op,GRB.MINIMIZE)

    return m

build_model()