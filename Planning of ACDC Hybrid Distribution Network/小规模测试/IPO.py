from pyomo.environ import *
import numpy as np
import _13_nodes_distribution_network as H
import pandas as pd
import time
import matplotlib.pyplot as plt
import math
import os


# 候选线路（固定顺序）
Branch = [
    (0,1),(0,2),(0,4),
    (1,2),(1,3),(1,4),(1,6),
    (2,4),(2,5),
    (3,4),(3,6),
    (4,5),(4,6)
]
nodes=7

def PYOMO_Solve(Edges, Gain_DG, D=0,Default=None):
    data = get_data(Edges, Gain_DG)
    model = ConcreteModel()
    S_line = 0.25+0.25*D
    Adj = {i: [] for i in range(nodes)}

    for i, j in Edges:
        Adj[i].append(j)
    # ========= 集合 =========
    model.N = Set(initialize=range(nodes))
    model.t = Set(initialize=range(H.T))

    model.E = Set(dimen=2, initialize=Edges)

    # ========= 参数 =========

    model.G = Param(model.N, model.N, initialize=data['G'], default=0)
    model.B = Param(model.N, model.N, initialize=data['B'], default=0)


    model.Pd = Param(model.N, model.t, initialize=data['load_P'], default=0)
    model.Qd = Param(model.N, model.t, initialize=data['load_Q'], default=0)

    model.Pmax_Buy = Param(model.N, model.t, initialize=data['buy_P'], default=0)
    model.Default = Param(model.N, model.t, initialize=data['Default'], default=0)

    model.Pmax_DG = Param(model.N, model.t, initialize=data['DG_P'], default=0)
    model.Qmax_DG = Param(model.N, model.t, initialize=data['DG_Q'], default=0)

    model.Pmax_Ess = Param(model.N, model.t, initialize=data['ess_P'], default=0)

    # model.SOC_init = Param(model.N, initialize={5: 0.5}, default=0)


    # ========= 变量 =========
    model.V = Var(model.N, model.t, bounds=(0.9, 1.1),initialize=1)
    model.theta = Var(model.N, model.t, bounds=(-0.5,0.5),initialize=0)


    model.P = Var(model.E, model.t, bounds=(-0.25, 0.25))
    model.Q = Var(model.E, model.t, bounds=(-0.25, 0.25))

    model.P_DG = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_DG[i,t]),initialize=lambda m,i,t: m.Default[i,t]*0.99)
    model.Q_DG = Var(model.N, model.t, bounds=(0,0.3),initialize=0)

    model.P_buy = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Buy[i,t]))
    model.Q_buy = Var(model.N, model.t, bounds=lambda m,i,t: (-m.Pmax_Buy[i,t], m.Pmax_Buy[i,t]))

    model.P_ess_ch = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Ess[i,t]),initialize=0)
    model.P_ess_dis = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Ess[i,t]),initialize=0)

    model.SOC = Var(model.N, model.t, bounds=(0.1, 0.9),initialize=0.5)

    model.P_in = Var(model.N, model.t, bounds=(-0.7, 0.7))
    model.Q_in = Var(model.N, model.t, bounds=(-0.7, 0.7))


    # ========= 约束 =========

    # slack
    def slack_rule(m, t):
        return m.theta[0, t] == 0
    model.slack = Constraint(model.t, rule=slack_rule)



    # AC P 平衡
    # def ac_p_rule(m, i, t):
    #     return m.P_buy[i, t] + m.P_DG[i, t] + m.P_ess_dis[i, t] - m.P_ess_ch[i, t] - m.Pd[i, t] == \
    #            sum(
    #                m.V[i,t]*m.V[j,t]*(
    #                    m.G[i,j]*cos(m.theta[i,t]-m.theta[j,t])
    #                    + m.B[i,j]*sin(m.theta[i,t]-m.theta[j,t])
    #                )
    #                for j in m.N
    #            )

    def ac_p_rule(m, i, t):
        return (
                m.P_buy[i, t]
                + m.P_DG[i, t]
                + m.P_ess_dis[i, t]
                - m.P_ess_ch[i, t]
                - m.Pd[i, t]
        ) == sum(
            m.V[i, t] * m.V[j, t] * (
                    m.G[i, j] * cos(m.theta[i, t] - m.theta[j, t])
                    + m.B[i, j] * sin(m.theta[i, t] - m.theta[j, t])
            )
            for j in Adj[i]
        ) + m.V[i, t] ** 2 * m.G[i, i]

    model.AC_P = Constraint(model.N, model.t, rule=ac_p_rule)



    # def ac_q_rule(m, i, t):
    #     return m.Q_buy[i, t] + m.Q_DG[i, t] - m.Qd[i, t]  == \
    #            sum(
    #                m.V[i,t]*m.V[j,t]*(
    #                    m.G[i,j]*sin(m.theta[i,t]-m.theta[j,t])
    #                    - m.B[i,j]*cos(m.theta[i,t]-m.theta[j,t])
    #                )
    #                for j in m.N
    #            )
    def ac_q_rule(m, i, t):
        return (
                m.Q_buy[i, t]
                + m.Q_DG[i, t]
                - m.Qd[i, t]
        ) == sum(
            m.V[i, t] * m.V[j, t] * (
                    m.G[i, j] * sin(m.theta[i, t] - m.theta[j, t])
                    - m.B[i, j] * cos(m.theta[i, t] - m.theta[j, t])
            )
            for j in Adj[i]
        ) - m.V[i, t] ** 2 * m.B[i, i]
    model.AC_Q = Constraint(model.N, model.t, rule=ac_q_rule)


    # Ess
    def soc_rule(m, i, t):
        if i == 5:
            if t == 0:
                return m.SOC[i,t] == 0.5 + 0.9 * m.P_ess_ch[i, t] - (1 / 0.9) * m.P_ess_dis[i, t]
            else:
                return m.SOC[i,t] == m.SOC[i,t-1] + 0.9 * m.P_ess_ch[i, t] - (1 / 0.9) * m.P_ess_dis[i, t]
        else:
            return Constraint.Skip
    model.Ess_I_init = Constraint(model.N, model.t, rule=soc_rule)
    def soc_per_rule(m, i):
        if i==5:
            return m.SOC[i, 23] == 0.5
        else:
            return Constraint.Skip
    model.soc_final = Constraint(model.N, rule=soc_per_rule)
    # def ess_rule(m, t):
    #         return m.P_ess_ch[5, t]*m.P_ess_dis[5, t]==0
    # model.Ess_chdis = Constraint(model.N, rule=ess_rule)

    # 定义系统安全运行方程
    def line_power_rule(m, x, y, t):
        if (x, y) in m.E:  # 仅当线路存在时定义约束
            return (m.P[x, y, t] ==
                    m.V[x, t] ** 2 * m.G[x, y] -
                    m.V[x, t] * m.V[y, t] * (
                            m.G[x, y] * cos(m.theta[x, t] - m.theta[y, t]) +
                            m.B[x, y] * sin(m.theta[x, t] - m.theta[y, t])
                    ))
        else:
            return Constraint.Skip

    def line_reactive_rule(m, x, y, t):
        if (x, y) in m.E:
            return (m.Q[x, y, t] ==
                    -m.V[x, t] ** 2 * m.B[x, y] -
                    m.V[x, t] * m.V[y, t] * (
                            m.G[x, y] * sin(m.theta[x, t] - m.theta[y, t]) -
                            m.B[x, y] * cos(m.theta[x, t] - m.theta[y, t])
                    ))
        else:
            return Constraint.Skip

    def line_AC_limit_rule(m, x, y, t):
        if (x, y) in model.E:
            return (m.P[x, y, t] ** 2 + m.Q[x, y, t] ** 2 <=
                    S_line * S_line * 0.8 * 0.8)  # = 0.04
        else:
            return Constraint.Skip
    # # 在模型中添加约束
    model.line_P = Constraint(model.E, model.t, rule=line_power_rule)
    model.line_Q = Constraint(model.E, model.t, rule=line_reactive_rule)
    model.line_AC_limit = Constraint(model.E, model.t, rule=line_AC_limit_rule)


    # ========= 目标函数 =========
    def obj_rule(m):
        return sum(
            H.c_s * sum(m.P_buy[i,t] for i in m.N)
            + H.c_e * sum(m.P_ess_ch[i,t] + m.P_ess_dis[i,t] for i in m.N)
            + H.c_d * sum(m.Pmax_DG[i,t] - m.P_DG[i,t] for i in m.N)
            for t in m.t
        ) * H.S_base

    model.obj = Objective(rule=obj_rule, sense=minimize)

    # ========= 求解 =========
    solver = SolverFactory('ipopt')
    # solver.options['linear_solver'] = 'MA27'
    # solver.threads = 2
    # solver.options['linear_solver'] = 'pardiso'MA27
    solver.options['print_level'] = 5
    solver.options['halt_on_ampl_error'] = 'yes'

    # solver.options['tol'] = 1e-6
    # solver.options['acceptable_tol'] = 1e-4
    # solver.options['acceptable_iter'] = 5
    #
    # solver.options['mu_strategy'] = 'adaptive'
    # solver.options['linear_solver'] = 'mumps'
    # solver.options['bound_push'] = 1e-6
    # solver.options['bound_frac'] = 1e-6
    result = solver.solve(model, tee=0)

    return str(result.solver.termination_condition),value(model.obj)


def get_data(Edges,Gain_DG):
    data={}

    # ---------- 1. 线路导纳 ----------
    G = {}
    B = {}
    for i, j in Edges:
        R, X = H.r_line[i][j][0], H.x_line[i][j][0]
        denom = R ** 2 + X ** 2
        G[(i, j)] = -R / denom
        B[(i, j)] = X / denom


    # ---------- 2. 节点自导纳 ----------
    for node in range(nodes):
        Ri = Xi = 0
        for i, j in Edges:
            if i == node:
                R, X = H.r_line[i][j][0], H.x_line[i][j][0]
                denom = R**2 + X**2
                Ri += R / denom
                Xi += -X / denom

        G[(node, node)] = Ri
        B[(node, node)] = Xi

    data['G'], data['B'] = G, B

    # ---------- 4. 负荷 ----------
    data['load_P'] = {
        (i, t): H.n_Load[i] * H.P_load[t]
        for i in range(nodes) for t in range(H.T)
    }
    data['load_Q'] = {
        (i, t): H.n_Load[i] * H.Q_load[t]
        for i in range(nodes) for t in range(H.T)
    }

    # ---------- 5. DG ----------
    DG_P, DG_Q = {}, {}
    Default={}
    for i in range(nodes):
        if i not in [3, 5]:
            continue

        # 系数 p
        if i ==3 :
            p = 4 / 15
        elif i ==5:
            p = 5 / 15
        else:
            p = 0

        for t in range(H.T):
            a = min(H.DG_curve[t] * p * Gain_DG, 0.3)
            b = (0.09 - a ** 2) ** 0.5  # 3^2 = 9

            c=min(min(H.DG_curve[t]* Gain_DG,H.P_load[t]) *p,0.3)
            DG_P[(i, t)] = a
            DG_Q[(i, t)] = b
            Default[(i, t)] = c


    data['DG_P'], data['DG_Q'] = DG_P, DG_Q

    data['Default']=Default

    # ---------- 6. 外部购电 ----------
    data['buy_P'] = {(0, t): 1 for t in range(H.T)}

    # ---------- 7. 储能 ----------
    data['ess_P'] = {(5, t): 0.25 for t in range(H.T)}

    return data


def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')


def fun3(path):
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
                status, obj = PYOMO_Solve(Edges, Gain)
            except Exception as e:
                print(f"IPOPT求解出错: {e}")
                obj, status = 'None', 'None'  # 或设置默认值
            res+=[status, obj]
        dt = list(X) + res
        print(dt)

        save_csv(dt, new_path)
        print('求解耗时', time.time() - start)
        start = time.time()

if __name__ == '__main__':

    fun3('trees_7nodes_expand.csv')


