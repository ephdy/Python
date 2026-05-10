from gurobipy import *
import math
import pandas as pd
import os,time
# =========================
# SOCP DistFlow OPF
# radial distribution network
# =========================

def solve_socp_opf(
        nodes,
        edges,
        T,
        r,
        x,
        Pd,
        Qd,
        DG_max,
        Buy_max,
        ESS_max,
        c_s,
        c_e,
        c_d,
        S_base=1.0
):

    """
    nodes : list of nodes
    edges : directed radial edges [(i,j),...]

    r[(i,j)]
    x[(i,j)]

    Pd[(i,t)]
    Qd[(i,t)]

    DG_max[(i,t)]
    Buy_max[(i,t)]
    ESS_max[(i,t)]
    """

    # ============================================
    # children / parent
    # ============================================

    children = {i: [] for i in nodes}
    parent = {}

    for i, j in edges:
        children[i].append(j)
        parent[j] = i

    # ============================================
    # model
    # ============================================

    m = Model("DistFlow_SOCP")

    # ============================================
    # variables
    # ============================================

    # voltage squared
    v = m.addVars(nodes, range(T),
                  lb=0.9**2,
                  ub=1.1**2,
                  name="v")

    # branch active power
    P = m.addVars(edges, range(T),
                  lb=-0.5,
                  ub=0.5,
                  name="P")

    # branch reactive power
    Q = m.addVars(edges, range(T),
                  lb=-0.5,
                  ub=0.5,
                  name="Q")

    # current squared
    l = m.addVars(edges, range(T),
                  lb=0,
                  name="l")

    # DG
    P_DG = m.addVars(nodes, range(T),
                     lb=0,
                     name="P_DG")

    Q_DG = m.addVars(nodes, range(T),
                     lb=-1,
                     ub=1,
                     name="Q_DG")

    # buy
    P_buy = m.addVars(nodes, range(T),
                      lb=0,
                      name="P_buy")

    Q_buy = m.addVars(nodes, range(T),
                      lb=-1,
                      ub=1,
                      name="Q_buy")

    # ESS
    P_ch = m.addVars(nodes, range(T),
                     lb=0,
                     name="P_ch")

    P_dis = m.addVars(nodes, range(T),
                      lb=0,
                      name="P_dis")

    SOC = m.addVars(nodes, range(T),
                    lb=0.1,
                    ub=0.9,
                    name="SOC")

    # ============================================
    # bounds
    # ============================================

    for i in nodes:
        for t in range(T):

            dgmax = DG_max.get((i,t), 0)
            buymax = Buy_max.get((i,t), 0)
            essmax = ESS_max.get((i,t), 0)

            P_DG[i,t].ub = dgmax

            P_buy[i,t].ub = buymax

            P_ch[i,t].ub = essmax
            P_dis[i,t].ub = essmax

    # ============================================
    # slack bus
    # ============================================

    for t in range(T):
        m.addConstr(v[0,t] == 1.0)

    # ============================================
    # nodal power balance
    # ============================================

    for t in range(T):

        for i in nodes:

            # incoming branch
            Pin = 0
            Qin = 0

            if i in parent:

                k = parent[i]

                Pin += (
                        P[k,i,t]
                        - r[k,i] * l[k,i,t]
                )

                Qin += (
                        Q[k,i,t]
                        - x[k,i] * l[k,i,t]
                )

            # outgoing branches
            Pout = quicksum(
                P[i,j,t]
                for j in children[i]
            )

            Qout = quicksum(
                Q[i,j,t]
                for j in children[i]
            )

            # active power balance
            m.addConstr(

                Pin
                + P_DG[i,t]
                + P_buy[i,t]
                + P_dis[i,t]
                - P_ch[i,t]
                - Pd.get((i,t),0)

                ==

                Pout

            )

            # reactive power balance
            m.addConstr(

                Qin
                + Q_DG[i,t]
                + Q_buy[i,t]
                - Qd.get((i,t),0)

                ==

                Qout

            )

    # ============================================
    # voltage drop
    # ============================================

    for t in range(T):

        for i,j in edges:

            m.addConstr(

                v[j,t]

                ==

                v[i,t]
                - 2 * (
                        r[i,j] * P[i,j,t]
                        + x[i,j] * Q[i,j,t]
                )
                + (r[i,j]**2 + x[i,j]**2)
                * l[i,j,t]

            )

    # ============================================
    # SOCP constraints
    # ============================================

    for t in range(T):

        for i,j in edges:

            # P^2 + Q^2 <= v * l

            m.addQConstr(

                P[i,j,t] * P[i,j,t]
                +
                Q[i,j,t] * Q[i,j,t]

                <=

                v[i,t] * l[i,j,t]

            )

    # ============================================
    # line capacity
    # ============================================

    Smax = 0.25 * 0.8

    for t in range(T):

        for i,j in edges:

            m.addQConstr(

                P[i,j,t] * P[i,j,t]
                +
                Q[i,j,t] * Q[i,j,t]

                <=

                Smax * Smax

            )

    # ============================================
    # ESS dynamics
    # ============================================

    for t in range(T):

        if t == 0:

            m.addConstr(

                SOC[5,0]

                ==

                0.5
                + 0.9 * P_ch[5,0]
                - (1/0.9) * P_dis[5,0]

            )

        else:

            m.addConstr(

                SOC[5,t]

                ==

                SOC[5,t-1]
                + 0.9 * P_ch[5,t]
                - (1/0.9) * P_dis[5,t]

            )

    m.addConstr(SOC[5,T-1] == 0.5)

    # ============================================
    # objective
    # ============================================

    obj = quicksum(

        c_s * quicksum(P_buy[i,t] for i in nodes)

        +

        c_e * quicksum(
            P_ch[i,t] + P_dis[i,t]
            for i in nodes
        )

        +

        c_d * quicksum(
            DG_max.get((i,t),0) - P_DG[i,t]
            for i in nodes
        )

        for t in range(T)

    ) * S_base

    m.setObjective(obj, GRB.MINIMIZE)

    # ============================================
    # gurobi settings
    # ============================================

    m.Params.NonConvex = 0

    m.Params.MIPGap = 1e-4

    m.Params.NumericFocus = 2

    m.Params.BarConvTol = 1e-8

    m.optimize()

    # ============================================
    # results
    # ============================================

    if m.status == GRB.OPTIMAL:

        print("Optimal objective:", m.objVal)

    else:

        print("status =", m.status)

    return m


def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')

def fun(path):
    base, ext = path.rsplit('.', 1)
    new_path = base + '结果' + '.' + ext
    df = pd.read_csv(path)
    data1 = df.iloc[:, :].values
    if os.path.exists(new_path):
        data2 = pd.read_csv(new_path,header=None)
        R = data2.iloc[:, :2].values
        ex = len(R)
    else:
        ex = 0
    start = time.time()
    for k in range(ex, len(data1)):
        X = data1[k]
        U = X[:13]
        mu = X[-2]*0.1
        epsi = X[-1]*0.1+0.1
        Edges = []

        for k in range(len(Branch)):
            if U[k] == 1:
                i, j = Branch[k]
                Edges.append((i, j))
                Edges.append((j, i))
        sens=[1+mu,(1+mu)*(1-epsi),(1+mu)*(1+epsi)]
        res=[]
        for Gain in sens:
            try:
                status, obj = solve_socp_opf(range(7),Edges,24,r,x,Pd,Qd,DG_max,Buy_max,ESS_max,c_s,c_e,c_d,S_base=10)
            except Exception as e:
                print(f"IPOPT求解出错: {e}")
                obj, status = 'None', 'None'  # 或设置默认值
            res+=[status, obj]
        dt = list(X) + res
        print(dt)

        save_csv(dt, new_path)
        print('求解耗时', time.time() - start)
        start = time.time()

Branch = [
    (0,1),(0,2),(0,4),
    (1,2),(1,3),(1,4),(1,6),
    (2,4),(2,5),
    (3,4),(3,6),
    (4,5),(4,6)
]
nodes=7

if __name__ == '__main__':

    fun('trees_7nodes_expand.csv')