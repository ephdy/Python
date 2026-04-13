from pyomo.environ import *

from _13_nodes_distribution_network import *
import pandas as pd
import time

import os

def PYOMO_Solve(S, Edges,mu,epsi, Default=None):
    data = get_data(S, Edges)
    model = ConcreteModel()

    # ========= 集合 =========
    model.N = Set(initialize=nodes)
    model.t = Set(initialize=times)

    model.AC = Set(initialize=[i for i in nodes if S[i] == 0])
    model.DC = Set(initialize=[i for i in nodes if S[i] == 1])

    model.E = Set(dimen=2, initialize=Edges)

    # VSC
    model.VSC = Set(initialize=data['VSC']['list'])

    # ========= 参数 =========

    model.G = Param(model.N, model.N, initialize=data['G'], default=0)
    model.B = Param(model.N, model.N, initialize=data['B'], default=0)
    model.R = Param(model.N, model.N, initialize=data['R'], default=0)

    model.Pd = Param(model.N, model.t, initialize=data['load_P'], default=0)
    model.Qd = Param(model.N, model.t, initialize=data['load_Q'], default=0)

    model.Pmax_Buy = Param(model.N, model.t, initialize=data['buy_P'], default=0)

    model.Pmax_DG0 = Param(model.N, model.t, initialize=data['DG_P'], default=0)
    model.Pmax_DG = Param(model.N, model.t,mutable=True, initialize=data['DG_P'], default=0)

    model.Pmax_Ess = Param(model.N, model.t, initialize=data['ess_P'], default=0)

    # model.SOC_init = Param(model.N, initialize={5: 0.5}, default=0)

    # 映射
    model.map_ac = Param(model.VSC, model.N, initialize=data['VSC']['ac'], default=0)
    model.map_dc = Param(model.VSC, model.N, initialize=data['VSC']['dc'], default=0)

    # ========= 变量 =========
    model.V = Var(model.N, model.t, bounds=(0.9, 1.1),initialize=1)
    model.theta = Var(model.N, model.t, bounds=(-3.14, 3.14),initialize=0)
    model.Vdc = Var(model.DC, model.t, bounds=(0.9, 1.1),initialize=1)

    model.P = Var(model.AC, model.AC, model.t, bounds=(-0.25, 0.25))
    model.Q = Var(model.AC, model.AC, model.t, bounds=(-0.25, 0.25))

    model.P_DG = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_DG[i,t]))
    model.Q_DG = Var(model.N, model.t, bounds=(0, 0.3),initialize=0)

    model.P_buy = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Buy[i,t]))
    model.Q_buy = Var(model.N, model.t, bounds=lambda m,i,t: (-m.Pmax_Buy[i,t], m.Pmax_Buy[i,t]))

    model.P_ess_ch = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Ess[i,t]),initialize=0)
    model.P_ess_dis = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Ess[i,t]),initialize=0)

    model.SOC = Var(model.N, model.t, bounds=(0.1, 0.9),initialize=0.5)

    model.P_in = Var(model.N, model.t, bounds=(-0.7, 0.7))
    model.Q_in = Var(model.N, model.t, bounds=(-0.7, 0.7))

    model.P_vsc_ac = Var(model.VSC, model.t, bounds=(-0.5, 0.5))
    model.P_vsc_dc = Var(model.VSC, model.t, bounds=(-0.5, 0.5))
    model.Q_vsc = Var(model.VSC, model.t, bounds=(-0.5, 0.5))

    model.P_vsc_loss = Var(model.VSC, model.t, bounds=(0, None))

    # ========= 约束 =========

    # slack
    def slack_rule(m, t):
        return m.theta[0, t] == 0
    model.slack = Constraint(model.t, rule=slack_rule)

    # P_in
    def Pin_rule(m, i, t):
        return m.P_in[i, t] == (
            m.P_buy[i, t] + m.P_DG[i, t]
            + m.P_ess_dis[i, t] - m.P_ess_ch[i, t]
            - m.Pd[i, t]
        )
    model.Pin = Constraint(model.N, model.t, rule=Pin_rule)

    # Q_in
    def Qin_rule(m, i, t):
        return m.Q_in[i, t] == (
            m.Q_buy[i, t] + m.Q_DG[i, t]
            - m.Qd[i, t]
            - sum(m.map_ac[v, i] * m.Q_vsc[v, t] for v in m.VSC)
        )
    model.Qin = Constraint(model.N, model.t, rule=Qin_rule)

    # AC P 平衡
    def ac_p_rule(m, i, t):
        return m.P_in[i, t] - sum(m.map_ac[v, i] * m.P_vsc_ac[v, t] for v in m.VSC) == \
               sum(
                   m.V[i,t]*m.V[j,t]*(
                       m.G[i,j]*cos(m.theta[i,t]-m.theta[j,t])
                       + m.B[i,j]*sin(m.theta[i,t]-m.theta[j,t])
                   )
                   for j in m.AC
               )
    model.AC_P = Constraint(model.AC, model.t, rule=ac_p_rule)

    def ac_q_rule(m, i, t):
        return m.Q_in[i, t]  == \
               sum(
                   m.V[i,t]*m.V[j,t]*(
                       m.G[i,j]*sin(m.theta[i,t]-m.theta[j,t])
                       - m.B[i,j]*cos(m.theta[i,t]-m.theta[j,t])
                   )
                   for j in m.AC
               )
    model.AC_Q = Constraint(model.AC, model.t, rule=ac_q_rule)

    # DC 平衡
    def dc_rule(m, i, t):
        return m.P_in[i, t] - sum(m.map_dc[v,i]*m.P_vsc_dc[v,t] for v in m.VSC) == \
               sum(m.Vdc[i,t]*(m.Vdc[i,t]-m.Vdc[j,t])*m.R[i,j] for j in m.DC)
    model.DC_balance = Constraint(model.DC, model.t, rule=dc_rule)

    # VSC 功率平衡
    def vsc_balance_rule(m, v, t):
        return m.P_vsc_ac[v,t] + m.P_vsc_dc[v,t] == m.P_vsc_loss[v,t]
    model.VSC_balance = Constraint(model.VSC, model.t, rule=vsc_balance_rule)

    # 损耗
    def vsc_loss_rule(m, v, t):
        return m.P_vsc_loss[v,t]**2 == 1e-4 * (
            m.P_vsc_ac[v,t]**2 + m.Q_vsc[v,t]**2
        )
    model.VSC_loss = Constraint(model.VSC, model.t, rule=vsc_loss_rule)

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
                    0.25 * 0.25 * 0.8 * 0.8)  # = 0.04
        else:
            return Constraint.Skip
    def line_DC_limit_rule(m, x, y, t):
        if (x, y) in model.E:
            return (m.Vdc[x, t] * (m.Vdc[x, t] - m.Vdc[y, t]) * m.R[x, y])**2 <= 0.25 * 0.25 * 0.8 * 0.8
        else:
            return Constraint.Skip
    def line_VSC_limit_rule(m, v, t):
        return (m.P_vsc_ac[v, t]**2+m.Q_vsc[v, t]**2) <= 0.25 * 0.25 * 0.8 * 0.8
    # # 在模型中添加约束
    model.line_P = Constraint(model.AC,model.AC, model.t, rule=line_power_rule)
    model.line_Q = Constraint(model.AC,model.AC, model.t, rule=line_reactive_rule)
    model.line_AC_limit = Constraint(model.AC,model.AC, model.t, rule=line_AC_limit_rule)
    model.line_DC_limit = Constraint(model.DC, model.DC, model.t, rule=line_DC_limit_rule)
    model.line_VSC_limit = Constraint(model.VSC, model.t, rule=line_VSC_limit_rule)


    # ========= 目标函数 =========
    def obj_rule(m):
        return sum(
            c_s * sum(m.P_buy[i,t] for i in m.N)
            + c_e * sum(m.P_ess_ch[i,t] + m.P_ess_dis[i,t] for i in m.N)
            + c_d * sum(m.Pmax_DG[i,t] - m.P_DG[i,t] for i in m.N)
            for t in m.t
        ) * S_base

    model.obj = Objective(rule=obj_rule, sense=minimize)

    # ========= 求解 =========
    solver = SolverFactory('ipopt')
    # solver.options['linear_solver'] = 'MA27'

    # solver.options['linear_solver'] = 'pardiso'MA27
    # result = solver.solve(model, tee=False)

    sens=[1+mu, (1+mu)*(1-epsi), (1+mu)*(1+epsi)]
    print(sens)
    res=[]
    for sen in sens:
        for t in model.t:
            model.Pmax_DG[7, t].set_value(model.Pmax_DG0[7, t]*sen)
            model.Pmax_DG[8, t].set_value(model.Pmax_DG0[8, t]*sen)
            model.Pmax_DG[10, t].set_value(model.Pmax_DG0[10, t]*sen)
            model.Pmax_DG[12, t].set_value(model.Pmax_DG0[12, t]*sen)

        result =solver.solve(model, tee=False)
        res+=[str(result.solver.termination_condition)]
        res+=[value(model.obj)]

    # # 手动计算各部分
    # # 计算购电成本
    # buy_cost = 0
    # for t in model.t:
    #     for i in model.N:
    #         buy_cost += c_s * model.P_buy[i, t].value
    # buy_cost *= S_base
    #
    # # 计算储能成本
    # ess_cost = 0
    # for t in model.t:
    #     for i in model.N:
    #         ess_cost += c_e * (model.P_ess_ch[i, t].value + model.P_ess_dis[i, t].value)
    # ess_cost *= S_base
    #
    # # 计算弃光/弃风惩罚
    # dg_curtailment = 0
    # for t in model.t:
    #     for i in model.N:
    #         dg_curtailment += c_d * (model.Pmax_DG[i, t] - model.P_DG[i, t].value)
    # dg_curtailment *= S_base
    #
    # # 打印结果
    # print(f"购电成本: {buy_cost:.2f}")
    # print(f"储能成本: {ess_cost:.2f}")
    # print(f"弃光/弃风惩罚: {dg_curtailment:.2f}")
    # print(f"总成本: {buy_cost + ess_cost + dg_curtailment:.2f}")

    return res


def get_data(S,Edges):
    data={}

    # ---------- 1. 线路导纳 ----------
    G = {}
    B = {}
    for i, j in Edges:
        if S[i] == 0 and S[j] == 0:
            R, X = r_line[i][j][0], x_line[i][j][0]
            denom = R ** 2 + X ** 2
            G[(i, j)] = -R / denom
            B[(i, j)] = X / denom


    # ---------- 2. 节点自导纳 ----------
    for node in nodes:
        Ri = Xi = 0
        for i, j in Edges:
            if i == node and S[i] == 0 and S[j] == 0:
                R, X = r_line[i][j][0], x_line[i][j][0]
                denom = R**2 + X**2
                Ri += R / denom
                Xi += -X / denom

        G[(node, node)] = Ri
        B[(node, node)] = Xi

    data['G'], data['B'] = G, B

    # ---------- 3. 电阻矩阵 ----------
    data['R'] = {
        (i, j): (1 / (r_line[i][j][0]))
        for i, j in Edges
        if S[i] == 1 and S[j] == 1
    }

    # ---------- 4. 负荷 ----------
    data['load_P'] = {
        (i, t): n_Load[i] * P_load[t] / S_base
        for i in nodes for t in times
    }
    data['load_Q'] = {
        (i, t): n_Load[i] * Q_load[t] / S_base
        for i in nodes for t in times
    }

    # ---------- 5. DG ----------
    DG_P, DG_Q = {}, {}
    for i in nodes:
        if n_DG[i] == 0:
            continue

        # 系数 p
        if i in [7, 12]:
            p = 2 / 9
        elif i in [8, 10]:
            p = 2.5 / 9
        else:
            p = 0

        for t in times:
            a = min(n_DG[i] * DG_curve[t] * p , 3)
            b = (9 - a ** 2) ** 0.5  # 3^2 = 9

            DG_P[(i, t)] = a / S_base
            DG_Q[(i, t)] = b / S_base

    data['DG_P'], data['DG_Q'] = DG_P, DG_Q

    # ---------- 6. 外部购电 ----------
    data['buy_P'] = {(0, t): 1 for t in times}

    # ---------- 7. 储能 ----------
    data['ess_P'] = {(5, t): 0.25 for t in times}

    # ---------- 8. VSC ----------
    L = []
    VSC = {'ac': {}, 'dc': {}}
    visited = set()
    k = 0

    for i, j in Edges:
        if S[i] != S[j] and (j, i) not in visited:
            visited.add((i, j))
            L.append((i, j))

            if S[i] == 0:
                VSC['ac'][(k, i)] = 1
                VSC['dc'][(k, j)] = 1
            else:
                VSC['ac'][(k, j)] = 1
                VSC['dc'][(k, i)] = 1

            k += 1

    VSC['list'] = list(range(k))

    data['VSC'], data['L'] = VSC, L
    return data


def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')

def fun3(path):
    base, ext = path.rsplit('.', 1)
    new_path = base + '结果' + '.' + ext
    data1 = pd.read_csv(path)
    X = data1.iloc[:, :13].values
    Y = data1.iloc[:, 13:33 + 13].values
    Z = data1.iloc[:, -2].values
    W = data1.iloc[:, -1].values
    print(X.shape, Y.shape, Z.shape)
    if os.path.exists(new_path):
        data2 = pd.read_csv(new_path)
        R = data2.iloc[:, :2].values
        ex = len(R) + 1
    else:
        ex = 0
    start = time.time()
    for d in range(1111):
        S = X[d]
        U = Y[d]
        mu = Z[d]
        epsi= W[d]
        Edges = []

        for k in range(len(Branch)):
            if U[k] == 1:
                i, j = Branch[k]
                Edges.append((i, j))
                Edges.append((j, i))


        try:
            res = PYOMO_Solve(S, Edges,mu,epsi)
        except Exception as e:
            print(f"IPOPT求解出错: {e}")
            res  = ['None']  # 或设置默认值
        data = list(S) + list(U) + [mu,epsi] + res
        print(data)
        # Draw_Grid(U, S)
        save_csv(data, new_path)
        print('求解耗时', time.time() - start)
        start = time.time()

if __name__ == '__main__':

    fun3('./snap/新样本_1.csv')
    # fun3('./snap/50万样本_2.csv')
    # fun3('./snap/50万样本_3.csv')
    # fun3('./snap/50万样本_4.csv')
    # fun3('./snap/50万样本_5.csv')
    # fun3('./snap/50万样本_6.csv')



