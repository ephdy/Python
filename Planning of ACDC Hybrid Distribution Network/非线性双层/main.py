from pyomo.environ import *
import random
import numpy as np
from collections import deque
import multiprocessing
from deap import base, creator, tools
import copy
import time
import networkx as nx
import _13_nodes_distribution_network as H

import os
import csv
import datetime

MIN_ROW = 1
MAX_ROW = 3
POP_SIZE = 200
GENERATIONS = 100
SEED = 42
N_JOBS = max(1, multiprocessing.cpu_count() - 1)
ELITE_SIZE = 2            # number of elites to preserve each generation
CX_PB = 0.5
MUTPB = 0.15
THRESHOLD = 1e-4
FORCE_STOP_GEN = 50
random.seed(SEED)
np.random.seed(SEED)
CC=0
def get_data(S,Edges,Gain_DG):
    data={}

    # ---------- 1. 线路导纳 ----------
    G = {}
    B = {}
    for i, j in Edges:
        if S[i] == 0 and S[j] == 0:
            R, X = H.r_line[i][j][0], H.x_line[i][j][0]
            denom = R ** 2 + X ** 2
            G[(i, j)] = -R / denom
            B[(i, j)] = X / denom


    # ---------- 2. 节点自导纳 ----------
    for node in H.nodes:
        Ri = Xi = 0
        for i, j in Edges:
            if i == node and S[i] == 0 and S[j] == 0:
                R, X = H.r_line[i][j][0], H.x_line[i][j][0]
                denom = R**2 + X**2
                Ri += R / denom
                Xi += -X / denom

        G[(node, node)] = Ri
        B[(node, node)] = Xi

    data['G'], data['B'] = G, B

    # ---------- 3. 电阻矩阵 ----------
    data['R'] = {
        (i, j): (1 / (H.r_line[i][j][0]))
        for i, j in Edges
        if S[i] == 1 and S[j] == 1
    }

    # ---------- 4. 负荷 ----------
    data['load_P'] = {
        (i, t): H.n_Load[i] * H.P_load[t] / H.S_base
        for i in H.nodes for t in H.times
    }
    data['load_Q'] = {
        (i, t): H.n_Load[i] * H.Q_load[t] / H.S_base
        for i in H.nodes for t in H.times
    }

    # ---------- 5. DG ----------
    DG_P, DG_Q = {}, {}
    Default={}
    for i in H.nodes:
        if H.n_DG[i] == 0:
            continue

        # 系数 p
        if i in [7, 12]:
            p = 2 / 9
        elif i in [8, 10]:
            p = 2.5 / 9
        else:
            p = 0

        for t in H.times:
            a = min(H.n_DG[i] * H.DG_curve[t] * p * Gain_DG, 3)
            b = (9 - a ** 2) ** 0.5  # 3^2 = 9
            c=min(min(H.DG_curve[t]* Gain_DG,H.P_load[t])*H.n_DG[i] *p,3)
            DG_P[(i, t)] = a / H.S_base
            DG_Q[(i, t)] = b / H.S_base
            Default[(i, t)] = c / H.S_base



    data['DG_P'], data['DG_Q'] = DG_P, DG_Q

    data['Default']=Default

    # ---------- 6. 外部购电 ----------
    data['buy_P'] = {(0, t): 1 for t in H.times}

    # ---------- 7. 储能 ----------
    data['ess_P'] = {(5, t): 0.25 for t in H.times}

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

def fop_Solve(S, Edges, D,Gain_DG, Default=None):
    data = get_data(S, Edges, Gain_DG)
    S_line=(0.25+0.25*D)
    model = ConcreteModel()

    # ========= 集合 =========
    model.N = Set(initialize=H.nodes)
    model.t = Set(initialize=H.times)

    model.AC = Set(initialize=[i for i in H.nodes if S[i] == 0])
    model.DC = Set(initialize=[i for i in H.nodes if S[i] == 1])

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
    model.Default = Param(model.N, model.t, initialize=data['Default'], default=0)

    model.Pmax_DG = Param(model.N, model.t, initialize=data['DG_P'], default=0)

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

    model.P_DG = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_DG[i,t]),initialize=lambda m,i,t: m.Default[i,t])
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
                    S_line * S_line * 0.8 * 0.8)  # = 0.04
        else:
            return Constraint.Skip
    def line_DC_limit_rule(m, x, y, t):
        if (x, y) in model.E:
            return (m.Vdc[x, t] * (m.Vdc[x, t] - m.Vdc[y, t]) * m.R[x, y])**2 <= S_line * S_line * 0.8 * 0.8
        else:
            return Constraint.Skip
    def line_VSC_limit_rule(m, v, t):
        return (m.P_vsc_ac[v, t]**2+m.Q_vsc[v, t]**2) <= S_line * S_line * 0.8 * 0.8
    # # 在模型中添加约束
    model.line_P = Constraint(model.AC,model.AC, model.t, rule=line_power_rule)
    model.line_Q = Constraint(model.AC,model.AC, model.t, rule=line_reactive_rule)
    model.line_AC_limit = Constraint(model.AC,model.AC, model.t, rule=line_AC_limit_rule)
    model.line_DC_limit = Constraint(model.DC, model.DC, model.t, rule=line_DC_limit_rule)
    model.line_VSC_limit = Constraint(model.VSC, model.t, rule=line_VSC_limit_rule)


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
    result = solver.solve(model, tee=False)

    # 检查求解状态
    if result.solver.status != SolverStatus.ok:
        print(f"Solver status: {result.solver.status}")
        print(f"Termination condition: {result.solver.termination_condition}")
        return 'error', 5e5

    if result.solver.termination_condition == TerminationCondition.optimal:
        obj = value(model.obj)
        return 'optimal', obj
    else:
        return result.solver.termination_condition, 5e5

    return str(result.solver.termination_condition),value(model.obj)

def Loss_Solve(S, Edges,D,Gain_DG, Default=None):
    data=get_data(S,Edges,Gain_DG)
    S_line = (0.25 + 0.25 * D)
    model = ConcreteModel()

    # ========= 集合 =========
    model.N = Set(initialize=H.nodes)
    model.t = Set(initialize=H.times)

    model.AC = Set(initialize=[i for i in H.nodes if S[i] == 0])
    model.DC = Set(initialize=[i for i in H.nodes if S[i] == 1])

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

    model.Pmax_DG = Param(model.N, model.t, initialize=data['DG_P'], default=0)

    model.Pmax_Ess = Param(model.N, model.t, initialize=data['ess_P'], default=0)

    # model.SOC_init = Param(model.N, initialize={5: 0.5}, default=0)

    # 映射
    model.map_ac = Param(model.VSC, model.N, initialize=data['VSC']['ac'], default=0)
    model.map_dc = Param(model.VSC, model.N, initialize=data['VSC']['dc'], default=0)

    # ========= 变量 =========
    model.V = Var(model.N, model.t, bounds=(0.9, 1.1), initialize=1)
    model.theta = Var(model.N, model.t, bounds=(-3.14, 3.14), initialize=0)
    model.Vdc = Var(model.DC, model.t, bounds=(0.9, 1.1), initialize=1)

    model.P = Var(model.AC, model.AC, model.t, bounds=(-0.25, 0.25))
    model.Q = Var(model.AC, model.AC, model.t, bounds=(-0.25, 0.25))

    model.P_DG = Var(model.N, model.t, bounds=lambda m, i, t: (0, m.Pmax_DG[i, t]),
                     initialize=lambda m, i, t: m.Pmax_DG[i, t] * 0.9)
    model.Q_DG = Var(model.N, model.t, bounds=(0, 0.3), initialize=0)

    model.P_buy = Var(model.N, model.t, bounds=lambda m, i, t: (0, m.Pmax_Buy[i, t]))
    model.Q_buy = Var(model.N, model.t, bounds=lambda m, i, t: (-m.Pmax_Buy[i, t], m.Pmax_Buy[i, t]))

    model.P_ess_ch = Var(model.N, model.t, bounds=lambda m, i, t: (0, m.Pmax_Ess[i, t]), initialize=0)
    model.P_ess_dis = Var(model.N, model.t, bounds=lambda m, i, t: (0, m.Pmax_Ess[i, t]), initialize=0)

    model.SOC = Var(model.N, model.t, bounds=(0.1, 0.9), initialize=0.5)

    model.P_in = Var(model.N, model.t, bounds=(-0.7, 0.7))
    model.Q_in = Var(model.N, model.t, bounds=(-0.7, 0.7))

    model.P_vsc_ac = Var(model.VSC, model.t, bounds=(-0.5, 0.5))
    model.P_vsc_dc = Var(model.VSC, model.t, bounds=(-0.5, 0.5))
    model.Q_vsc = Var(model.VSC, model.t, bounds=(-0.5, 0.5))

    model.P_vsc_loss = Var(model.VSC, model.t, bounds=(0, None))

    model.P_load = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pd[i,t]), initialize=lambda m,i,t: m.Pd[i,t]*0.9)
    model.Q_load = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Qd[i,t]), initialize=lambda m,i,t: m.Qd[i,t]*0.9)

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
            - m.P_load[i, t]
        )
    model.Pin = Constraint(model.N, model.t, rule=Pin_rule)

    # Q_in
    def Qin_rule(m, i, t):
        return m.Q_in[i, t] == (
            m.Q_buy[i, t] + m.Q_DG[i, t]
            - m.Q_load[i, t]
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
                    S_line * S_line )  # = 0.04
        else:
            return Constraint.Skip


    def line_DC_limit_rule(m, x, y, t):
        if (x, y) in model.E:
            return (m.Vdc[x, t] * (m.Vdc[x, t] - m.Vdc[y, t]) * m.R[x, y])**2 <= S_line * S_line
        else:
            return Constraint.Skip


    def line_VSC_limit_rule(m, v, t):
        return (m.P_vsc_ac[v, t]**2+m.Q_vsc[v, t]**2) <= S_line * S_line
    # # 在模型中添加约束
    model.line_P = Constraint(model.AC,model.AC, model.t, rule=line_power_rule)
    model.line_Q = Constraint(model.AC,model.AC, model.t, rule=line_reactive_rule)
    model.line_AC_limit = Constraint(model.AC,model.AC, model.t, rule=line_AC_limit_rule)
    model.line_DC_limit = Constraint(model.DC, model.DC, model.t, rule=line_DC_limit_rule)
    model.line_VSC_limit = Constraint(model.VSC, model.t, rule=line_VSC_limit_rule)
    # ========= 目标函数 =========
    def obj_rule(m):
        return sum(m.Pd[i,t] - m.P_load[i,t] for i in m.N for t in m.t)
    # sum(m.Pd[i,t]-m.P_load[i,t] for i in m.N for t in m.t)
    # sum( sum(m.Pd[i,t]-m.P_load[i,t] for i in m.N) for t in m.t )/sum(m.Pd[i,t] for i in m.N for t in m.t)


    model.obj = Objective(rule=obj_rule, sense=minimize)

    # ========= 求解 =========
    solver = SolverFactory('ipopt')
    result = solver.solve(model, tee=False)

    # 检查求解状态
    if result.solver.status != SolverStatus.ok:
        print(f"Solver status: {result.solver.status}")
        print(f"Termination condition: {result.solver.termination_condition}")
        return 'error', 0.5

    if result.solver.termination_condition == TerminationCondition.optimal:
        obj = value(model.obj)
        return 'optimal', obj
    else:
        return result.solver.termination_condition, 0.5

    return str(result.solver.termination_condition),value(model.obj)

# -------------------------
def generate_connected_network_with_degree_constraint(candidate_branches, min_degree=1, max_degree=3, seed=None):
    """
    从候选支路中随机选择支路组成全连通网络，且每个节点度数满足约束

    参数:
    candidate_branches: 候选支路列表，每个元素为(node1, node2)
    min_degree: 最小度数，默认为1
    max_degree: 最大度数，默认为3
    seed: 随机种子，用于结果可重现

    返回:
    selected_indices: 被选择的支路对应的0/1列表，1表示选择，0表示不选择
    selected_branches: 被选择的支路列表
    G: 生成的网络图
    """
    if seed is not None:
        random.seed(seed)

    # 获取所有节点
    all_nodes = set()
    for branch in candidate_branches:
        all_nodes.add(branch[0])
        all_nodes.add(branch[1])
    n_nodes = len(all_nodes)

    # 验证最小度数约束的可行性：对于n个节点的连通图，至少需要n-1条边
    # 如果每个节点度数至少为min_degree，则总边数至少为 ceil(n * min_degree / 2)
    min_edges_needed = max(n_nodes - 1, (n_nodes * min_degree + 1) // 2)
    if min_edges_needed > len(candidate_branches):
        raise ValueError(f"候选支路数量不足以满足最小度数约束！需要至少{min_edges_needed}条边")

    max_attempts = 1000  # 最大尝试次数
    for attempt in range(max_attempts):
        # 初始化
        G = nx.Graph()
        G.add_nodes_from(all_nodes)
        selected_indices = [0] * len(candidate_branches)
        selected_branches = []

        # 计算每个节点的当前度数
        degree_count = {node: 0 for node in all_nodes}

        # 创建边索引列表并随机打乱
        edge_indices = list(range(len(candidate_branches)))
        random.shuffle(edge_indices)

        # 第一步：使用改进的Kruskal算法确保连通性，同时考虑度数约束
        parent = {node: node for node in all_nodes}

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            root_x = find(x)
            root_y = find(y)
            if root_x != root_y:
                parent[root_x] = root_y
                return True
            return False

        # 选择边确保连通性，同时遵守度数约束
        for idx in edge_indices:
            u, v = candidate_branches[idx]

            # 检查度数约束
            if degree_count[u] >= max_degree or degree_count[v] >= max_degree:
                continue

            # 如果这条边能连接两个不同的连通分量，且满足度数约束
            if find(u) != find(v):
                if union(u, v):
                    selected_indices[idx] = 1
                    selected_branches.append((u, v))
                    G.add_edge(u, v)
                    degree_count[u] += 1
                    degree_count[v] += 1

        # 检查是否所有节点都已连通
        components = list(nx.connected_components(G))

        # 如果还有多个连通分量，尝试用剩余的边连接它们
        if len(components) > 1:
            for idx in edge_indices:
                if selected_indices[idx] == 1:
                    continue

                u, v = candidate_branches[idx]

                # 检查度数约束
                if degree_count[u] >= max_degree or degree_count[v] >= max_degree:
                    continue

                # 如果这条边连接不同的连通分量
                if find(u) != find(v):
                    if union(u, v):
                        selected_indices[idx] = 1
                        selected_branches.append((u, v))
                        G.add_edge(u, v)
                        degree_count[u] += 1
                        degree_count[v] += 1

                        # 重新检查连通分量
                        components = list(nx.connected_components(G))
                        if len(components) == 1:
                            break

        # 第二步：确保所有节点满足最小度数约束
        if len(components) == 1:  # 图是连通的
            nodes_need_edges = [node for node in all_nodes if degree_count[node] < min_degree]

            # 尝试为度数不足的节点添加边
            success = True
            for node in nodes_need_edges:
                edges_added = 0
                # 找到所有包含该节点且未被选择的候选边
                candidate_edges_for_node = [
                    (idx, u, v) for idx, (u, v) in enumerate(candidate_branches)
                    if (u == node or v == node) and selected_indices[idx] == 0
                       and degree_count[u] < max_degree and degree_count[v] < max_degree
                ]

                random.shuffle(candidate_edges_for_node)

                for idx, u, v in candidate_edges_for_node:
                    if degree_count[node] >= min_degree:
                        break

                    other_node = v if u == node else u
                    if degree_count[other_node] < max_degree:
                        selected_indices[idx] = 1
                        selected_branches.append((u, v))
                        G.add_edge(u, v)
                        degree_count[u] += 1
                        degree_count[v] += 1
                        union(u, v)
                        edges_added += 1

                # 检查是否满足最小度数
                if degree_count[node] < min_degree:
                    success = False
                    break

            # 第三步：验证所有节点的度数约束并可选添加额外边
            if success:
                # 验证度数约束
                degree_check = all(min_degree <= degree_count[node] <= max_degree
                                   for node in all_nodes)

                if degree_check:
                    # 可选的第四步：随机添加一些额外边（仍遵守度数约束）
                    remaining_edges = [(idx, u, v) for idx, (u, v) in enumerate(candidate_branches)
                                       if selected_indices[idx] == 0
                                       and degree_count[u] < max_degree
                                       and degree_count[v] < max_degree]

                    random.shuffle(remaining_edges)

                    # 随机添加额外边，概率可调整
                    for idx, u, v in remaining_edges:
                        if random.random() < 0.2:  # 20%概率添加额外边
                            selected_indices[idx] = 1
                            selected_branches.append((u, v))
                            G.add_edge(u, v)
                            degree_count[u] += 1
                            degree_count[v] += 1
                        if random.random() < 0.1:  # 20%概率添加额外边
                            selected_indices[idx] = 1
                            selected_branches.append((u, v))
                            G.add_edge(u, v)
                            degree_count[u] += 1
                            degree_count[v] += 1

                    # 最终验证
                    final_degree_check = all(min_degree <= degree_count[node] <= max_degree
                                             for node in all_nodes)

                    if final_degree_check and nx.is_connected(G):
                        return selected_indices, selected_branches, G, degree_count

        # 如果这次尝试失败，继续下一次尝试
        if attempt == max_attempts - 1:
            print(f"警告：经过{max_attempts}次尝试后仍未找到可行解")

    return None, None, None, None

def make_random_individual():
    S=np.random.randint(0, 2, size=(13,))
    selected_indices, selected_branches, G, degree_count = generate_connected_network_with_degree_constraint(
        H.Branch, min_degree=1, max_degree=3, seed=None
    )
    D=np.random.randint(0, 2, size=(3,))
    return [int(x) for x in np.concatenate([S, selected_indices, D])]
# -------------------------
def repair_individual(ind, branch_list, min_degree=1, max_degree=3):
    """
    修复个体使其满足连通性和节点度数约束

    参数:
    individual: 当前个体（0/1列表）
    branch_list: 候选支路列表
    min_degree: 最小度数
    max_degree: 最大度数

    返回:
    repaired_individual: 修复后的个体
    """
    # 获取所有节点
    all_nodes = set()
    for u, v in branch_list:
        all_nodes.add(u)
        all_nodes.add(v)

    # 创建当前图
    G = nx.Graph()
    G.add_nodes_from(all_nodes)
    individual=ind[13:13+33]
    selected_edges = []
    for i, (u, v) in enumerate(branch_list):
        if individual[i] == 1:
            G.add_edge(u, v)
            selected_edges.append(i)

    # 计算当前度数
    degree_count = {node: G.degree(node) for node in all_nodes}

    # 第一步：删除违反最大度数约束的边
    repaired = individual.copy()

    # 找到度数超限的节点
    over_degree_nodes = [node for node in all_nodes if degree_count[node] > max_degree]

    while over_degree_nodes:
        node = random.choice(over_degree_nodes)
        # 找到该节点连接的边
        connected_edges = []
        for i, (u, v) in enumerate(branch_list):
            if repaired[i] == 1 and (u == node or v == node):
                connected_edges.append((i, u, v))

        if connected_edges:
            # 随机删除一条边（优先删除对连通性影响小的边）
            # 检查删除每条边后是否仍连通
            for i, u, v in connected_edges:
                test_G = G.copy()
                test_G.remove_edge(u, v)
                if nx.is_connected(test_G) and degree_count[u] > min_degree and degree_count[v] > min_degree:
                    # 可以安全删除
                    repaired[i] = 0
                    G.remove_edge(u, v)
                    degree_count[u] -= 1
                    degree_count[v] -= 1
                    break
            else:
                # 如果没有安全删除的边，强制删除一条
                i, u, v = connected_edges[0]
                repaired[i] = 0
                G.remove_edge(u, v)
                degree_count[u] -= 1
                degree_count[v] -= 1

        over_degree_nodes = [node for node in all_nodes if degree_count[node] > max_degree]

    # 第二步：修复连通性
    if not nx.is_connected(G):
        # 找到所有连通分量
        components = list(nx.connected_components(G))

        # 为每个节点标记分量
        node_to_component = {}
        for comp_id, comp in enumerate(components):
            for node in comp:
                node_to_component[node] = comp_id

        # 找到可以连接不同分量的边
        while len(components) > 1:
            candidate_edges = []
            for i, (u, v) in enumerate(branch_list):
                if repaired[i] == 0:  # 未选择的边
                    if node_to_component[u] != node_to_component[v]:  # 连接不同分量
                        if degree_count[u] < max_degree and degree_count[v] < max_degree:
                            candidate_edges.append((i, u, v))

            if not candidate_edges:
                # 没有合适的边，需要先调整
                break

            # 随机选择一条边添加
            i, u, v = random.choice(candidate_edges)
            repaired[i] = 1
            G.add_edge(u, v)
            degree_count[u] += 1
            degree_count[v] += 1

            # 重新计算连通分量
            components = list(nx.connected_components(G))
            node_to_component = {}
            for comp_id, comp in enumerate(components):
                for node in comp:
                    node_to_component[node] = comp_id

    # 第三步：修复最小度数约束
    under_degree_nodes = [node for node in all_nodes if degree_count[node] < min_degree]

    for node in under_degree_nodes:
        while degree_count[node] < min_degree:
            # 找到包含该节点的候选边
            candidate_edges = []
            for i, (u, v) in enumerate(branch_list):
                if repaired[i] == 0 and (u == node or v == node):
                    other = v if u == node else u
                    if degree_count[other] < max_degree:
                        candidate_edges.append((i, u, v))

            if not candidate_edges:
                # 无法添加边，需要更复杂的修复
                break

            # 随机选择一条边
            i, u, v = random.choice(candidate_edges)
            repaired[i] = 1
            G.add_edge(u, v)
            degree_count[u] += 1
            degree_count[v] += 1

    # 第四步：可选优化，减少冗余边
    # 尝试删除不影响约束的边
    for i, (u, v) in enumerate(branch_list):
        if repaired[i] == 1:
            if degree_count[u] > min_degree and degree_count[v] > min_degree:
                test_G = G.copy()
                test_G.remove_edge(u, v)
                if nx.is_connected(test_G):
                    repaired[i] = 0
                    G.remove_edge(u, v)
                    degree_count[u] -= 1
                    degree_count[v] -= 1

    return ind[:13]+repaired+ind[13+33:]
# -------------------------
def evaluate(ind):
    S=ind[:13]
    U=ind[13:13+33]
    D=ind[13+33]
    mu=ind[13+33+1]
    epsilon=ind[13+33+2]

    C_line = 0
    S_vsc = 0
    S_c = 0
    for i in range(H.n):
        S_c = S_c + H.S_c_load * (H.n__ac[i] * S[i] + H.n__dc[i] * (1 - S[i]))
        S_c = S_c + H.S_c_wind * (S[i] + 2 * (1 - S[i])) * H.n__wind[i]
        S_c = S_c + H.S_c_pv * (1 - S[i]) * H.n__pv[i]
    for u in U:
        (i, j) = H.Branch[u]
        S_vsc += 0.5 * H.S_vsc_ij * u * abs(S[i] - S[j])
        C_line += 0.5 * H.c_l[D] * H.Length[i][j] * u


    C_cvt = H.c_c * S_c + H.c_v * S_vsc
    C_invest0 = C_line * (H.r * (pow(1 + H.r, H.T_line) / (pow(1 + H.r, H.T_line) - 1)) + H.beta_line) + C_cvt * (
                H.r * (pow(1 + H.r, H.T_cvt) / (pow(1 + H.r, H.T_cvt) - 1)) + H.beta_cvt)
    C_invest = (C_invest0 - 5485588) / (20991965 - 5485588)

    Edges = []
    for k in range(len(H.Branch)):
        if U[k] == 1:
            i, j = H.Branch[k]
            Edges.append((i, j))
            Edges.append((j, i))
    sens = [1 + mu, (1 + mu * 0.1) * (1 - (0.1+epsilon*0.1)), (1 + mu * 0.1) * (1 + (0.1+epsilon*0.1))]
    sens = [round(s, 2) for s in sens]
    fop=[]
    loss=[]
    for sen in sens:
        try:
            status,obj=fop_Solve(S, Edges,D,sen)
        except Exception as e:
            print(f"IPOPT求解出错: {e}")
            obj, status = 'None', 'None'  # 或设置默认值
        if status=='optimal':
            fop.append(obj)
        else:
            fop.append(50000)
    C_operation=(0.8*fop[0]+0.8*fop[1]+0.8*fop[2]-4122)/(43720-4122)
    res=0
    conut=0
    for k in range(len(H.Branch)):
        if U[k] == 1:
            conut += 1
            U_new = U.copy()
            U_new[k] = 0
            Edges = []
            for kk in range(len(H.Branch)):
                if U_new[kk] == 1:
                    i, j = H.Branch[kk]
                    Edges.append((i, j))
                    Edges.append((j, i))
            try:
                status, obj = Loss_Solve(S, Edges, D, sens[1])
            except Exception as e:
                obj, status = 'err', 'None'  # 或设置默认值
            try:
                res += 0 if abs(obj) < 1e-5 else obj
            except TypeError:
                res += 0.5
    Loss=res/conut

    Q = 0.4762 * (mu + epsilon - 2*mu*epsilon) + 1 * mu*epsilon
    return C_invest,-Q,C_operation,Loss

# -------------------------
# DEAP setup
# -------------------------
creator.create("FitnessMin", base.Fitness, weights=(-1.0,-1.0,-1.0,-1.0))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()
toolbox.register("individual", tools.initIterate, creator.Individual, make_random_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("mate", tools.cxTwoPoint)

# bitflip mutation with probability per gene
def bitflip_mutation(individual, indpb=0.02):
    for i in range(len(individual)):
        if random.random() < indpb:
            individual[i] = 1 - int(individual[i])
    return (individual,)

toolbox.register("mutate", bitflip_mutation)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("evaluate", evaluate)

# -------------------------
# multiprocessing worker initializer (seed RNGs)
# -------------------------
def _init_worker(seed):
    random.seed(seed + int(time.time() * 1000) % 100000)
    np.random.seed(seed + int(time.time() * 1000) % 100000)

# -------------------------
# GA main loop with elitism & minimal-disturbance repair
# -------------------------
def main(seed=SEED, pop_size=POP_SIZE, generations=GENERATIONS, n_jobs=N_JOBS):
    random.seed(seed)
    np.random.seed(seed)
    # pool = multiprocessing.Pool(processes=n_jobs)
    toolbox.register("map", map)


    pop = toolbox.population(n=pop_size)


    # initial evaluation
    fitnesses = list(toolbox.map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    # HallOfFame and stats
    hof = tools.HallOfFame(ELITE_SIZE)
    hof.update(pop)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: float(np.mean([a[0] for a in x])))
    stats.register("min", lambda x: float(np.min([a[0] for a in x])))
    stats.register("avg1", lambda x: float(np.mean([a[1] for a in x])))
    stats.register("min1", lambda x: float(np.min([a[1] for a in x])))
    stats.register("avg2", lambda x: float(np.mean([a[2] for a in x])))
    stats.register("min2", lambda x: float(np.min([a[2] for a in x])))
    # stats.register("avg3", lambda x: float(np.mean([a[3] for a in x])))
    # stats.register("min3", lambda x: float(np.min([a[3] for a in x])))
    # stats.register("avg4", lambda x: float(np.mean([a[4] for a in x])))
    # stats.register("min4", lambda x: float(np.min([a[4] for a in x])))

    best_prev = hof[0].fitness.values[0]

    log = []
    trigger=0
    for gen in range(generations):
        global CC
        CC =0
        # Elitism: keep ELITE_SIZE best
        elites = tools.selBest(pop, ELITE_SIZE)
        # selection
        offspring = toolbox.select(pop, len(pop) - ELITE_SIZE)
        offspring = list(map(toolbox.clone, offspring))

        # Crossover
        for i in range(1, len(offspring), 2):
            if random.random() < CX_PB:
                toolbox.mate(offspring[i-1], offspring[i])
                # mark fitness invalid
                try:
                    del offspring[i-1].fitness.values
                except AttributeError:
                    pass
                try:
                    del offspring[i].fitness.values
                except AttributeError:
                    pass

        # Mutation
        for i in range(len(offspring)):
            if random.random() < MUTPB:
                offspring[i], = toolbox.mutate(offspring[i])
                try:
                    del offspring[i].fitness.values
                except AttributeError:
                    pass

        # Repair offspring deterministically with cost-driven rules
        for i in range(len(offspring)):
            offspring[i][:]=repair_individual(offspring[i],H.Branch,1,3)

        # reassemble population with elites
        pop = elites + offspring
        # evaluate invalid individuals
        invalid = [ind for ind in pop if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid)
        for ind, fit in zip(invalid, fitnesses):
            ind.fitness.values = fit

        hof.update(pop)
        rec = stats.compile(pop)
        log.append((gen, rec["avg1"], rec["min1"]))
        print(
            f"Gen {gen}: avg={rec['avg']:.6f}, min={rec['min']:.6f},"
            f"avg1={rec['avg1']:.6f}, min1={rec['min1']:.6f},"
            f" avg2={rec['avg2']:.6f}, min2={rec['min2']:.6f}, ")
        # print(f"Gen {gen}: avg={rec['avg']:.6f}, min={rec['min']:.6f},avg1={rec['avg1']:.6f}, min1={rec['min1']:.6f}, avg2={rec['avg2']:.6f}, min2={rec['min2']:.6f}, avg3={rec['avg3']:.6f}, min3={rec['min3']:.6f}")
        print(f"程序运行时间: {time.time() - start_time:.4f} 秒")

        # early stopping
        best_now = hof[0].fitness.values[0]
        diff = abs(best_prev - best_now)
        if gen < FORCE_STOP_GEN and diff < THRESHOLD:
            trigger+=1
        #     print(f"Early stop at gen {gen}: best change {diff:.4e} < {THRESHOLD}")
        #     break
        best_prev = best_now


    best = hof[0]

    print("\n=== Best Solution ===")
    print(best)
    print(f"Objective (cost) = {best.fitness.values[0]:.6f}")
    # pool.close()
    # pool.join()
    return pop, log, hof


if __name__ == '__main__':
    start_time = time.time()

    pop, log, hof = main(seed=SEED,pop_size=200, generations=50)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"程序运行时间: {elapsed_time:.4f} 秒")

