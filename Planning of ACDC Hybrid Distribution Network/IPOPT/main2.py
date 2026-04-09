from pyomo.environ import *
from _13_nodes_distribution_network import *
import pandas as pd
import time
import os
import argparse



def PYOMO_Solve(S, Edges, Gain_DG, Default=None):

    model = ConcreteModel()

    # ========= 集合 =========
    model.N = Set(initialize=nodes)
    model.t = Set(initialize=times)

    model.AC = Set(initialize=[i for i in nodes if S[i] == 0])
    model.DC = Set(initialize=[i for i in nodes if S[i] == 1])

    model.E = Set(dimen=2, initialize=Edges)

    # VSC
    link_L, list_L = get_L(S, Edges)
    model.VSC = Set(initialize=list_L)

    # ========= 参数 =========
    G_matrix, B_matrix = get_Y(S, Edges)

    model.G = Param(model.N, model.N, initialize=G_matrix, default=0)
    model.B = Param(model.N, model.N, initialize=B_matrix, default=0)
    model.R = Param(model.N, model.N, initialize=get_R1(S, Edges), default=0)



    load_P, load_Q = get_Load()
    model.Pd = Param(model.N, model.t, initialize=load_P, default=0)
    model.Qd = Param(model.N, model.t, initialize=load_Q, default=0)

    model.Pmax_Buy = Param(model.N, model.t, initialize=get_Buy(), default=0)

    model.Pmax_DG = Param(model.N, model.t, initialize=get_DG(Gain_DG)[0], default=0)

    model.Pmax_Ess = Param(model.N, model.t, initialize=get_Ess(), default=0)

    # model.SOC_init = Param(model.N, initialize={5: 0.5}, default=0)

    # 映射
    model.map_ac = Param(model.VSC, model.N, initialize=link_L[0], default=0)
    model.map_dc = Param(model.VSC, model.N, initialize=link_L[1], default=0)

    # ========= 变量 =========
    model.V = Var(model.N, model.t, bounds=(0.9, 1.1))
    model.theta = Var(model.N, model.t, bounds=(-3.14, 3.14))
    model.Vdc = Var(model.DC, model.t, bounds=(0.9, 1.1))

    model.P = Var(model.AC, model.AC, model.t, bounds=(-0.25, 0.25))
    model.Q = Var(model.AC, model.AC, model.t, bounds=(-0.25, 0.25))

    model.P_DG = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_DG[i,t]))
    model.Q_DG = Var(model.N, model.t, bounds=(0, 0.3))

    model.P_buy = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Buy[i,t]))
    model.Q_buy = Var(model.N, model.t, bounds=lambda m,i,t: (-m.Pmax_Buy[i,t], m.Pmax_Buy[i,t]))

    model.P_ess_ch = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Ess[i,t]))
    model.P_ess_dis = Var(model.N, model.t, bounds=lambda m,i,t: (0, m.Pmax_Ess[i,t]))

    model.SOC = Var(model.N, model.t, bounds=(0.1, 0.9))

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
    result = solver.solve(model, tee=False)

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

    return str(result.solver.termination_condition),value(model.obj)

def get_Y(S,Edges):
    G_matrix={}
    B_matrix={}
    for i,j in Edges:
        R = r_line[i][j][0]
        X = x_line[i][j][0]
        G_matrix[(i,j)]=-R / (R ** 2 + X ** 2)
        B_matrix[(i,j)]=X / (R ** 2 + X ** 2)
    for node in nodes:
        Ri=0
        Xi=0
        for i,j in Edges:
            if i==node :
                R = r_line[i][j][0]
                X = x_line[i][j][0]
                if S[i] ==0 and S[j]==0:
                    Ri+=R / (R ** 2 + X ** 2)
                    Xi+=-X / (R ** 2 + X ** 2)
        G_matrix[(node, node)] = Ri
        B_matrix[(node, node)] = Xi
    return G_matrix, B_matrix

def get_R1(S,Edges):
    R_matrix= {}
    for i,j in Edges:
        if S[i] != S[j]:
            R=r_line[i][j][1]
        else:
            R = r_line[i][j][0]

        R_matrix[(i,j)]=1/R
    return R_matrix

def get_Load():
    load_P= {}
    load_Q={}
    for i in nodes:
        for t in times:
            load_P[(i, t)]=n_Load[i]*P_load[t]/S_base
            load_Q[(i, t)]=n_Load[i]*Q_load[t]/S_base
    return load_P, load_Q

def get_DG(Gain_DG):
    max_DG = []
    max_DG.append({})  # 添加第一个空子列表
    max_DG.append({})
    for i in nodes:
        if i in [7,12]:
            p=2 / 9
        elif i in [8,10]:
            p=2.5 / 9
        else:
            p=0
        if n_DG[i]!=0:
            for t in times:
                a0=n_DG[i] * DG_curve[t] * p * Gain_DG
                if a0>=3:
                    a=3
                else:
                    a=a0

                b=(3**2-a**2)** 0.5
                max_DG[0][(i,t)]=a/S_base
                max_DG[1][(i,t)]=b/S_base
    return max_DG

def get_Buy():
    Pmax_buy={}
    for t in times:
        Pmax_buy[(0,t)]=1
    return Pmax_buy

def get_Ess():
    max_ess={}
    for t in times:
        max_ess[(5,t)]=0.25
    return max_ess

def get_L(S,Edges):
    L=[]
    link=[]
    link.append({})
    link.append({})
    k=0
    visted=[]
    for i,j in Edges:
        if S[i] != S[j] and (j,i) not in visted:
            visted.append((i,j))
            L.append((i,j))
            if S[i] ==0:
                link[0][(k,i)]=1
                link[1][(k,j)]=1
            else:
                link[0][(k,j)]=1
                link[1][(k,i)]=1
            k=k+1

    return link,list(range(int(len(L))))
def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')

def fun3(path):
    base, ext = path.rsplit('.', 1)
    new_path = base + '结果' + '.' + ext
    data1 = pd.read_csv(path)
    X = data1.iloc[:, :13].values
    Y = data1.iloc[:, 13:33 + 13].values
    Z = data1.iloc[:, 33 + 13:].values
    print(X.shape, Y.shape, Z.shape)
    if os.path.exists(new_path):
        data2 = pd.read_csv(new_path)
        R = data2.iloc[:, :2].values
        ex = len(R) + 1
    else:
        ex = 0
    start = time.time()
    for d in range(ex, len(Z)):
        S = X[d]
        U = Y[d]
        Gain = Z[d][0]
        Edges = []

        for k in range(len(Branch)):
            if U[k] == 1:
                i, j = Branch[k]
                Edges.append((i, j))
                Edges.append((j, i))

        try:
            status,obj = PYOMO_Solve(S, Edges, Gain)
        except Exception as e:
            print(f"GAMS求解出错: {e}")
            obj, status = 'None', 'None'  # 或设置默认值
        data = list(S) + list(U) + [Gain] + [status,obj]
        save_csv(data, new_path)
        print('求解耗时', time.time() - start)
        start = time.time()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='这是一个示例程序')

    # 添加位置参数（必须提供）
    parser.add_argument('input', help='输入文件路径')
    #
    # # 添加可选参数
    # parser.add_argument('--output', '-o', help='输出文件路径')
    # parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    # parser.add_argument('--count', '-c', type=int, default=1, help='重复次数（默认1）')

    # 解析参数
    args = parser.parse_args()

    # print(f"输入文件: {args.input}")
    # if args.output:
    #     print(f"输出文件: {args.output}")
    # if args.verbose:
    #     print("详细模式开启")
    # print(f"重复次数: {args.count}")

    fun3(args.input)
    # fun3('./snap/50万样本_198.csv')



