import gurobipy as gb
import _13_nodes_distribution_network as H
import pandas as pd
from collections import defaultdict



def fop_solving(S,U0,D,mu,epsilon,Gain=1,n=13,T=24):
    U={}
    for ind in range(len(U0)):
        if U0[ind]==1:
            U[H.Branch[ind]] = 1

    VSC_DC=[]
    m=gb.Model('m1')
    L = defaultdict(int)
    for key in U.keys():
        if abs(S[key[0]]-S[key[1]]):
            L[key]=int(abs(S[key[0]]-S[key[1]]))
            if S[key[0]]==1:
                VSC_DC.append(key[0])
            else:
                VSC_DC.append(key[1])

    V={}
    # 定义各节点电压
    for i in range(n):
        for t in range(T):
            V[(i,t)]=m.addVar(lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name=f"V_{i}_{t}")
    loss_svc={}
    for key in L.keys():
        for t in range(T):
            loss_svc[(key[0], key[1], t)]=m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"loss_vsc_{key}_{t}")
    P_tr = defaultdict(int)
    Q_tr = defaultdict(int)
    for key in U.keys():
        for t in range(T):
            # V_svc[(key[0], key[1],t)]=m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"V_svc_{key}_{t}")
            P_tr[(key[0], key[1], t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"P_tr_{key}_{t}")
            Q_tr[(key[0], key[1], t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"Q_tr_{key}_{t}")
    P_buy = defaultdict(int)
    Q_buy = defaultdict(int)
    Ess={'ch':defaultdict(int),'dis':defaultdict(int),'flag_dis':defaultdict(int),'flag_ch':defaultdict(int),'Ek':defaultdict(int)}
    for t in range(T):
        P_buy[(0,t)] = m.addVar(ub=1, vtype=gb.GRB.CONTINUOUS, name=f"P_buy_{t}")
        Q_buy[(0,t)] = m.addVar(lb=-0.48, ub=0.48, vtype=gb.GRB.CONTINUOUS, name=f"Q_buy_{t}")

        Ess['ch'][(5,t)] = m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"P_ess_ch_{t}")
        Ess['dis'][(5,t)] = m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"P_ess_dis_{t}")
        Ess['flag_ch'][(5,t)] = m.addVar(vtype=gb.GRB.BINARY,name=f"flag_ch_{t}")
        Ess['flag_dis'][(5,t)] = m.addVar(vtype=gb.GRB.BINARY,name=f"flag_dis_{t}")
        Ess['Ek'][(5,t)] = m.addVar(lb=0.1 * H.S_ess / H.S_base, ub=0.9 * H.S_ess / H.S_base, vtype=gb.GRB.CONTINUOUS,name=f"E_k_{t}")
    # 储能约束
    m.addConstr(Ess['Ek'][(5,0)] == 0.5)
    for t in range(T):
        m.addConstr(Ess['flag_ch'][(5,t)] + Ess['flag_dis'][(5,t)] <= 1)
        m.addConstr(Ess['dis'][(5,t)] <= Ess['flag_dis'][(5,t)] * H.P_ess_max)
        m.addConstr(Ess['ch'][(5,t)] <= Ess['flag_ch'][(5,t)] * H.P_ess_max)
        if t != 0:
            m.addConstr(Ess['Ek'][(5,t)] == Ess['Ek'][(5,t-1)] + Ess['ch'][(5,t)] * 0.9 - Ess['dis'][(5,t)] / 0.9)
    ch_total=gb.quicksum(Ess['ch'][(5,t)] for t in range(T))* 0.9
    dis_total=gb.quicksum(Ess['dis'][(5,t)] for t in range(T))/ 0.9
    m.addConstr(ch_total == dis_total)

    DG={'P':defaultdict(int),'Q':defaultdict(int)}
    for t in range(T):
        DG['P'][(7, t)] = m.addVar(ub=H.DG_curve[t] * Gain * 2.0 / 9 / H.S_base * 1, vtype=gb.GRB.CONTINUOUS, name=f"P_DG7_{t}")
        DG['P'][(8, t)] = m.addVar(ub=H.DG_curve[t] * Gain * 2.5 / 9 / H.S_base * 1, vtype=gb.GRB.CONTINUOUS, name=f"P_DG8_{t}")
        DG['P'][(10, t)] = m.addVar(ub=H.DG_curve[t] * Gain * 2.5 / 9 / H.S_base * 1, vtype=gb.GRB.CONTINUOUS, name=f"P_DG10_{t}")
        DG['P'][(12, t)] = m.addVar(ub=H.DG_curve[t] * Gain * 2.0 / 9 / H.S_base * 1, vtype=gb.GRB.CONTINUOUS, name=f"P_DG12_{t}")
        DG['Q'][(7, t)] = m.addVar(ub=0.3, vtype=gb.GRB.CONTINUOUS, name=f"Q_DG7_{t}")
        DG['Q'][(8, t)] = m.addVar(ub=0.3, vtype=gb.GRB.CONTINUOUS, name=f"Q_DG8_{t}")
        DG['Q'][(10, t)] = m.addVar(ub=0.3, vtype=gb.GRB.CONTINUOUS, name=f"Q_DG10_{t}")
        DG['Q'][(12, t)] = m.addVar(ub=0.3, vtype=gb.GRB.CONTINUOUS, name=f"Q_DG12_{t}")

    #目标函数

    f_op=0
    for t in range(T):
        f_op += H.c_s * P_buy[(0,t)]
        f_op += H.c_e * (Ess['ch'][(5,t)]+ Ess['dis'][(5,t)])
        f_op += H.c_d * (H.DG_curve[t] * Gain * 2.0 / 9 / H.S_base - DG['P'][(7, t)])
        f_op += H.c_d * (H.DG_curve[t] * Gain * 2.5 / 9 / H.S_base - DG['P'][(8, t)])
        f_op += H.c_d * (H.DG_curve[t] * Gain * 2.5 / 9 / H.S_base - DG['P'][(10, t)])
        f_op += H.c_d * (H.DG_curve[t] * Gain * 2.0 / 9 / H.S_base - DG['P'][(12, t)])

    load={'P': {},'Q':{}}
    for i in range (n):
        for t in range(T):
            load['P'][(i,t)] = H.n_Load[i] * H.P_load[t]
            load['Q'][(i,t)] = H.n_Load[i] * H.Q_load[t]


    # 有功功率平衡方程
    for i in range(n):
        for t in range(T):
            if i in VSC_DC:
                loss=0
            else:
                loss=0
            tr_total=0
            for key in U.keys():
                if key[0]==i:
                    tr_total -= P_tr[(key[0], key[1], t)]
                elif key[1]==i:
                    tr_total += P_tr[(key[0], key[1], t)]
            m.addConstr(P_buy[(i,t)] + Ess['dis'][(i,t)] + Ess['ch'][(i,t)] + DG['P'][(i,t)]
                        -load['P'][(i, t)]==tr_total,name=f"P_{i}_{t}")

    # 无功功率平衡方程
    for i in range(n):
        for t in range(T):
            tr_total=0
            for key in U.keys():
                if key[0]==i:
                    tr_total -= Q_tr[(key[0], key[1],t)]
                elif key[1]==i:
                    tr_total += Q_tr[(key[0], key[1], t)]
            m.addConstr(Q_buy[(i,t)] -load['Q'][(i, t)] + DG['Q'][(i,t)] == tr_total )


    # # 电压方程
    for (i,j) in U.keys():
        for t in range(T):
            m.addConstr(V[(i,t)] - V[(j,t)] == (H.r_line[i][j][0] * P_tr[(i,j,t)] + H.x_line[i][j][0] * Q_tr[(i,j,t)]))
            S=0.25
            # 传输容量约束
            m.addConstr(P_tr[(i,j,t)] <= 0.8 * S, name='传输容量约束1')
            m.addConstr(P_tr[(i,j,t)] >= -0.8 * S, name='传输容量约束2')

            m.addConstr(Q_tr[(i,j,t)] <= 0.8 * S, name='传输容量约束3')
            m.addConstr(Q_tr[(i,j,t)] >= -0.8 * S, name='传输容量约束4')

            m.addConstr(P_tr[(i,j,t)] + Q_tr[(i,j,t)] <= 1.41 * 0.8 * S, name='传输容量约束5')
            m.addConstr(P_tr[(i,j,t)] + Q_tr[(i,j,t)] >= -1.41 * 0.8 * S, name='传输容量约束6')
            m.addConstr(P_tr[(i,j,t)] - Q_tr[(i,j,t)] <= 1.41 * 0.8 * S, name='传输容量约束7')
            m.addConstr(P_tr[(i,j,t)] - Q_tr[(i,j,t)] >= -1.41 * 0.8 * S, name='传输容量约束8')






    m.setObjective(f_op*10, gb.GRB.MINIMIZE)
    m.setParam('LogToConsole', 1)
    m.setParam('OutputFlag', 0)
    m.optimize()
    # 打印目标值
    if m.Status == gb.GRB.OPTIMAL:
        print(f"最优目标值: {m.objVal}")
    else:
        print("未找到最优解")
    if m.Status == gb.GRB.INFEASIBLE:
        print("模型不可行，正在计算 IIS...")

        # 计算不可行子系统
        m.computeIIS()

        # 将 IIS 写入文件查看
        m.write("m..ilp")

        # 打印参与 IIS 的约束
        print("\n参与不可行子系统的约束:")
        for c in m.getConstrs():
            if c.IISConstr:
                print(f"  {c.ConstrName}")

        for v in m.getVars():
            if v.IISLB:  # 下界导致不可行
                print(f"  变量 {v.VarName} 的下界 {v.LB}")
            if v.IISUB:  # 上界导致不可行
                print(f"  变量 {v.VarName} 的上界 {v.UB}")


if __name__ == "__main__":
    Data = pd.read_csv("./原本/新样本_1.csv")
    data= Data.iloc[:, :].values

    for i in range(len(data)):
        S = data[i][:13]
        U = data[i][13:13 + 33]
        mu = data[i][-2]
        epsilon = data[i][-1]
        Gain=(1+mu)
        fop_solving(S, U, 1, mu, epsilon,Gain)
