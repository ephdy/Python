import gurobipy as gb
from _13_nodes_distribution_network import *
import copy
def find_upper_right_ones(arr):
    n = len(arr)
    result = []
    for i in range(n):
        for j in range(i+1, n):
            if arr[i][j] == 1:
                result.append((i, j))
    return result

def Lower_layer_solving(W,U,x,n=13,T=24,mode=0):
    m=gb.Model('m1')
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])
    # 新能源消纳指标
    if mode==1:
        epsilon = m.addVar(lb=1, ub=2, vtype=gb.GRB.CONTINUOUS, name="epsilon")
        mu = m.addVar(lb=1, ub=2, vtype=gb.GRB.CONTINUOUS, name="mu")
        delta = m.addVar(ub=0.4, vtype=gb.GRB.CONTINUOUS, name="delta")
        m.addConstr(delta <= mu * 0.2)
        f2=-delta
    # 失负荷指标
    if mode==2:
        Load_loss=m.addVars(n, 2,vtype=gb.GRB.BINARY,name="Load_loss")
        for i in range(n):
            if n__ac[i]==0:
                m.addConstr(Load_loss[i, 0] == 0)
            if n__dc[i]==0:
                m.addConstr(Load_loss[i, 1] == 0)
        f3=sum(n__ac)+sum(n__dc)-Load_loss.sum()

    # 定义各节点电压
    if mode == 1:
        Scene_V = m.addVars(n, T, 2, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
        Scene_V__svc = m.addVars(n, n, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
        for scene in range(scenes):
            for i in range(n):
                for j in range(i + 1, n):
                    for t in range(T):
                        m.addConstr(Scene_V[i, j, t, scene] == Scene_V[j, i, t, scene])
                        m.addConstr(Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene])
    else:
        V = m.addVars(n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
        V__svc = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="V__svc")
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
                    m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])

    # 定义线路潮流
    if mode == 1:
        Scene_P_tran = m.addVars(n, n, T, 2,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
        Scene_Q_tran = m.addVars(n, n, T, 2,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
        for scene in range(scenes):
            for t in range(T):
                for i in range(n):
                    m.addConstr(Scene_P_tran[i, i, t, scene] == 0)
                    m.addConstr(Scene_Q_tran[i, i, t, scene] == 0)
                    for j in range(i + 1, n):
                        if i != j:
                            m.addConstr(Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene])
                            m.addConstr(Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene])
    else:
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
    # 购电功率
    if mode == 1:
        Scene_P_sub = m.addVars(T, 2, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
        Scene_Q_sub = m.addVars(T, 2, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")
    else:
        P_sub = m.addVars(T, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_sub")
        Q_sub = m.addVars(T, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_sub")

    # 储能充放电功率
    # 储能约束
    if mode == 1:
        Scene_P_ess_ch = m.addVars(T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
        Scene_P_ess_dis = m.addVars(T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
        Scene_alpha__dis = m.addVars(T, 2, vtype=gb.GRB.BINARY)
        Scene_alpha__ch = m.addVars(T, 2, vtype=gb.GRB.BINARY)
        Scene_E_k = m.addVars(T, 2, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS)
        for scene in range(scenes):
            m.addConstr(Scene_E_k[0, scene] == 5)
            for t in range(T):
                m.addConstr(Scene_alpha__ch[t,scene] + Scene_alpha__dis[t,scene] <= 1)
                m.addConstr(Scene_P_ess_dis[t,scene] <= Scene_alpha__dis[t,scene] * P_ess_max)
                m.addConstr(Scene_P_ess_ch[t,scene] <= Scene_alpha__ch[t,scene] * P_ess_max)
                if t != 0:
                    m.addConstr(Scene_E_k[t,scene] == Scene_E_k[t - 1,scene] + Scene_P_ess_ch[t,scene] * 0.9 - Scene_P_ess_dis[t,scene] / 0.9)
            m.addConstr(Scene_P_ess_ch.sum('*', scene) * 0.9 == Scene_P_ess_dis.sum('*', scene) / 0.9)
    else:
        P_ess_ch = m.addVars(T, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
        P_ess_dis = m.addVars(T, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
        alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY,name="alpha__dis")
        alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY,name="alpha__ch")
        E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS,name="E_k")
        m.addConstr(E_k[0] == 5)
        for t in range(T):
            m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
            m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
            m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
            if t != 0:
                m.addConstr(E_k[t] == E_k[t - 1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
        m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
    # DG出力
    if mode == 1:
        Scene_P_DG_813 = m.addVars(2, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_813")
        Scene_P_DG_911 = m.addVars(2, T, 2, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_911")
        Scene_Q_DG_813 = m.addVars(2, T, 2, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
        Scene_Q_DG_911 = m.addVars(2, T, 2, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")

        for t in range(T):
            m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2.0 / 9*(mu-delta))
            m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2.0 / 9*(mu-delta))
            m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9*(mu-delta))
            m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9*(mu-delta))
            m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2.0 / 9*(mu+delta))
            m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2.0 / 9*(mu+delta))
            m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9*(mu+delta))
            m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9*(mu+delta))
    else:
        P_DG_813 = m.addVars(2, T, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
        P_DG_911 = m.addVars(2, T, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
        Q_DG_813 = m.addVars(2, T, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Q_DG_813")
        Q_DG_911 = m.addVars(2, T, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Q_DG_911")

        for t in range(T):
            m.addConstr(P_DG_813[0, t] <= DG_total[t] * 2 / 9)
            m.addConstr(P_DG_813[1, t] <= DG_total[t] * 2 / 9)
            m.addConstr(P_DG_911[0, t] <= DG_total[t] * 2.5 / 9)
            m.addConstr(P_DG_911[1, t] <= DG_total[t] * 2.5 / 9)

    #目标函数
    if mode==0:
        f_op = 0
        for t in range(T):
            f_op += c_s * P_sub[t]
            f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
            f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[0, t])
            f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[0, t])
            f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[1, t])
            f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[1, t])
    # 有功功率平衡方程
    for i in range(n):
        for t in range(T):
            if i == 0:
                if mode == 1:
                    m.addConstr(Scene_P_sub[t, 0] - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
                    m.addConstr(Scene_P_sub[t, 1] - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
                else:
                    m.addConstr(P_sub[t] - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 5:
                if mode == 1:
                    m.addConstr(
                        0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, 0] - Scene_P_ess_ch[
                            t, 0] - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
                    m.addConstr(
                        0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, 1] - Scene_P_ess_ch[
                            t, 1] - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
                elif mode == 2:
                    m.addConstr(
                        0 - P_load[t] * (Load_loss[i,0] + Load_loss[i,1]) + P_ess_dis[t] - P_ess_ch[t] - P_tran.sum(i, '*',
                                                                                                        t) * S_base == 0)
                else:
                    m.addConstr(
                        0 - P_load[t] * (n__ac[i] + n__dc[i]) + P_ess_dis[t] - P_ess_ch[t] - P_tran.sum(i, '*',
                                                                                                        t) * S_base == 0)
            elif i == 7:
                if mode == 1:
                    m.addConstr(
                        Scene_P_DG_813[0, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       0) * S_base == 0)
                    m.addConstr(
                        Scene_P_DG_813[0, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       1) * S_base == 0)
                elif mode == 2:
                    m.addConstr(
                        P_DG_813[0, t] - P_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - P_tran.sum(i, '*', t) * S_base == 0)
                else:
                    m.addConstr(
                        P_DG_813[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 8:
                if mode == 1:
                    m.addConstr(
                        Scene_P_DG_911[0, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       0) * S_base == 0)
                    m.addConstr(
                        Scene_P_DG_911[0, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       1) * S_base == 0)
                elif mode == 2:
                    m.addConstr(
                        P_DG_911[0, t] - P_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - P_tran.sum(i, '*', t) * S_base == 0)
                else:
                    m.addConstr(
                        P_DG_911[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 10:
                if mode == 1:
                    m.addConstr(
                        Scene_P_DG_911[1, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       0) * S_base == 0)
                    m.addConstr(
                        Scene_P_DG_911[1, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       1) * S_base == 0)
                elif mode == 2:
                    m.addConstr(
                        P_DG_911[1, t] - P_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - P_tran.sum(i, '*', t) * S_base == 0)
                else:
                    m.addConstr(
                        P_DG_911[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 12:
                if mode == 1:
                    m.addConstr(
                        Scene_P_DG_813[1, t, 0] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       0) * S_base == 0)
                    m.addConstr(
                        Scene_P_DG_813[1, t, 1] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       1) * S_base == 0)
                elif mode == 2:
                    m.addConstr(
                        P_DG_813[1, t] - P_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - P_tran.sum(i, '*', t) * S_base == 0)
                else:
                    m.addConstr(
                        P_DG_813[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            else:
                if mode == 1:
                    m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 0) * S_base == 0)
                    m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, 1) * S_base == 0)
                elif mode == 2:
                    m.addConstr(0 - P_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - P_tran.sum(i, '*', t) * S_base == 0)
                else:
                    m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)

    # 无功功率平衡方程
    for i in range(n):
        for t in range(T):
            if i == 0:
                if mode == 1:
                    m.addConstr(Scene_Q_sub[t, 0] - Scene_Q_tran.sum(i, '*', t, 0) * S_base == 0)
                    m.addConstr(Scene_Q_sub[t, 1] - Scene_Q_tran.sum(i, '*', t, 1) * S_base == 0)
                else:
                    m.addConstr(Q_sub[t] - Q_tran.sum(i, '*', t) * S_base == 0)
            elif i == 7:
                if mode == 1:
                    m.addConstr(
                        (Scene_Q_DG_813[0, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
                    m.addConstr(
                        (Scene_Q_DG_813[0, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
                elif mode == 2:
                    m.addConstr(
                        (Q_DG_813[0, t] - Q_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - Q_tran.sum(i, '*', t) * S_base) * (
                                1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) * (
                                    1 - W[i]) == 0)
            elif i == 8:
                if mode == 1:
                    m.addConstr(
                        (Scene_Q_DG_911[0, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
                    m.addConstr(
                        (Scene_Q_DG_911[0, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
                elif mode == 2:
                    m.addConstr(
                        (Q_DG_911[0, t] - Q_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - Q_tran.sum(i, '*', t) * S_base) * (
                                1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) * (
                                    1 - W[i]) == 0)
            elif i == 10:
                if mode == 1:
                    m.addConstr(
                        (Scene_Q_DG_911[1, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
                    m.addConstr(
                        (Scene_Q_DG_911[1, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
                elif mode == 2:
                    m.addConstr(
                        (Q_DG_911[1, t] - Q_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - Q_tran.sum(i, '*', t) * S_base) * (
                                1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) * (
                                    1 - W[i]) == 0)
            elif i == 12:
                if mode == 1:
                    m.addConstr(
                        (Scene_Q_DG_813[1, t, 0] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
                    m.addConstr(
                        (Scene_Q_DG_813[1, t, 1] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
                elif mode == 2:
                    m.addConstr(
                        (Q_DG_813[1, t] - Q_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - Q_tran.sum(i, '*', t) * S_base) * (
                                1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) * (
                                    1 - W[i]) == 0)
            else:
                if mode == 1:
                    m.addConstr(
                        (0 - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 0) * S_base) * (1 - W[i]) == 0)
                    m.addConstr(
                        (0 - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, 1) * S_base) * (1 - W[i]) == 0)
                elif mode == 2:
                    m.addConstr(
                        (0 - Q_load[t] * (Load_loss[i,0] + Load_loss[i,1]) - Q_tran.sum(i, '*', t) * S_base) * (1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base) * (1 - W[i]) == 0)
    #
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                # m.addConstr(P_tran[i, j, t] <= M * U[i][j])
                # m.addConstr(P_tran[i, j, t] >= -M * U[i][j])
                # m.addConstr(Q_tran[i, j, t] <= M * U[i][j])
                # m.addConstr(Q_tran[i, j, t] >= -M * U[i][j])
                # m.addConstr(Q_tran[i, j, t] <= M * (1 - W[i]*W[j]))
                # m.addConstr(Q_tran[i, j, t] >= -M * (1 - W[i]*W[j]))
                if mode == 1:
                    if U[i][j] == 0:
                        m.addConstr(Scene_P_tran[i, j, t, 0] == 0, name='联通潮流约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, 0] == 0, name='联通潮流约束2')
                        m.addConstr(Scene_P_tran[i, j, t, 1] == 0, name='联通潮流约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, 1] == 0, name='联通潮流约束2')
                    if W[i] * W[j] == 1:
                        m.addConstr(Scene_Q_tran[i, j, t, 0] == 0, name='换流无功约束')
                        m.addConstr(Scene_Q_tran[i, j, t, 1] == 0, name='换流无功约束')
                else:
                    if U[i][j] == 0:
                        m.addConstr(P_tran[i, j, t] == 0, name='联通潮流约束1')
                        m.addConstr(Q_tran[i, j, t] == 0, name='联通潮流约束2')
                    if W[i] * W[j] == 1:
                        m.addConstr(Q_tran[i, j, t] == 0, name='换流无功约束')


    # # 电压方程
    for i in range(n):
        for j in range(n):
            if i != j:
                #
                S_line = S_line_k[x[i][j]]
                for t in range(T):
                    if mode == 1:
                        for scene in range(scenes):
                            m.addConstr(U[i][j] * (
                                    (1 - L[i][j] * W[i]) * Scene_V[i, t, scene]
                                    + (L[i][j] * W[i] - L[i][j] * W[j]) * Scene_V__svc[i, j, t, scene]
                                    - (1 - L[i][j] * W[j]) * Scene_V[j, t, scene]) ==
                                    (1 - L[i][j]) * (r__[i][j] * Scene_P_tran[i, j, t, scene] + x__[i][j] * Scene_Q_tran[i, j, t, scene])
                                    +L[i][j] * (r__vsc[i][j] * Scene_P_tran[i, j, t, scene] - x__vsc[i][j] * Scene_Q_tran[i, j, t, scene]),name='电压方程')
                            # VSC约束
                            m.addConstr(Scene_Q_tran[i, j, t, scene] <= L[i][j] * (Q_vsc_max - M) + M,name='VSC无功约束1')
                            m.addConstr(Scene_Q_tran[i, j, t, scene] >= -1 * (L[i][j] * (Q_vsc_max - M) + M),name='VSC无功约束2')
                            # 传输容量约束
                            m.addConstr(Scene_P_tran[i, j, t, scene] <= gama * S_line / S_base,name='传输容量约束1')
                            m.addConstr(Scene_P_tran[i, j, t, scene] >= -gama * S_line / S_base,name='传输容量约束2')

                            m.addConstr(Scene_Q_tran[i, j, t, scene] <= gama * S_line / S_base,name='传输容量约束3')
                            m.addConstr(Scene_Q_tran[i, j, t, scene] >= -gama * S_line / S_base,name='传输容量约束4')

                            m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[i, j, t, scene] <= 1.41 * gama * S_line / S_base,name='传输容量约束5')
                            m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[i, j, t, scene] >= -1.41 * gama * S_line / S_base,name='传输容量约束6')
                            m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[i, j, t, scene] <= 1.41 * gama * S_line / S_base,name='传输容量约束7')
                            m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[i, j, t, scene] >= -1.41 * gama * S_line / S_base,name='传输容量约束8')
                    else:
                        m.addConstr(U[i][j] * ((1 - L[i][j] * W[i]) * V[i, t] + (L[i][j] * W[i] - L[i][j] * W[j]) * V__svc[i, j, t] - (1 - L[i][j] * W[j]) * V[j, t])
                                    ==(1 - L[i][j]) * (r__[i][j] * P_tran[i, j, t] + x__[i][j] * Q_tran[i, j, t]) +L[i][j] * (r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t]),name='电压方程')
                        # VSC约束
                        m.addConstr(Q_tran[i, j, t] <= L[i][j] * (Q_vsc_max - M) + M,name='VSC无功约束1')
                        m.addConstr(Q_tran[i, j, t] >= -1 * (L[i][j] * (Q_vsc_max - M) + M),name='VSC无功约束2')
                        # 传输容量约束
                        m.addConstr(P_tran[i, j, t] <= gama * S_line / S_base,name='传输容量约束1')
                        m.addConstr(P_tran[i, j, t] >= -gama * S_line / S_base,name='传输容量约束2')
                        #
                        m.addConstr(Q_tran[i, j, t] <= gama * S_line / S_base,name='传输容量约束3')
                        m.addConstr(Q_tran[i, j, t] >= -gama * S_line / S_base,name='传输容量约束4')
                        #
                        m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base,name='传输容量约束5')
                        m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base,name='传输容量约束6')
                        m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base,name='传输容量约束7')
                        m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base,name='传输容量约束8')
    if  mode==0:
        m.setObjective(f_op, gb.GRB.MINIMIZE)
    elif mode==1:
        m.setObjective(f2, gb.GRB.MINIMIZE)
    elif mode==2:
        m.setObjective(f3, gb.GRB.MINIMIZE)
    m.setParam('LogToConsole', 0)
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    # Result = []
    # for v in m.getVars():
    #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
    #         print(v.VarName, v.X)
    if m.status == gb.GRB.OPTIMAL:
        return m.objVal
    else:
        return 9e12



def Lower_layer_solving_1(W,U,x,w1=1,w2=1,n=13,T=24):
    m=gb.Model('m1')
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])
    # epsilon = m.addVar(lb=1, ub=2, vtype=gb.GRB.CONTINUOUS, name="epsilon")
    mu = m.addVar(lb=1, ub=2, vtype=gb.GRB.CONTINUOUS, name="mu")
    delta = m.addVar(ub=0.4, vtype=gb.GRB.CONTINUOUS, name="delta")
    m.addConstr(delta <= mu * 0.2)
    f2=-delta

    # 定义各节点电压
    Scene_V = m.addVars(n, T, scenes, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
    Scene_V__svc = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    m.addConstr(Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene])

    # 定义线路潮流
    Scene_P_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
    Scene_Q_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
    for scene in range(scenes):
        for t in range(T):
            for i in range(n):
                m.addConstr(Scene_P_tran[i, i, t, scene] == 0)
                m.addConstr(Scene_Q_tran[i, i, t, scene] == 0)
                for j in range(i + 1, n):
                    if i != j:
                        m.addConstr(Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene])
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene])
    # 购电功率
    Scene_P_sub = m.addVars(T, scenes, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
    Scene_Q_sub = m.addVars(T, scenes, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")

    # 储能充放电功率
    # 储能约束
    Scene_P_ess_ch = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
    Scene_P_ess_dis = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
    Scene_alpha__dis = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__dis")
    Scene_alpha__ch = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__ch")
    Scene_E_k = m.addVars(T, scenes, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS,name="Scene_E_k")
    for scene in range(scenes):
        m.addConstr(Scene_E_k[0, scene] == 5)
        for t in range(T):
            m.addConstr(Scene_alpha__ch[t,scene] + Scene_alpha__dis[t,scene] <= 1)
            m.addConstr(Scene_P_ess_dis[t,scene] <= Scene_alpha__dis[t,scene] * P_ess_max)
            m.addConstr(Scene_P_ess_ch[t,scene] <= Scene_alpha__ch[t,scene] * P_ess_max)
            if t != 0:
                m.addConstr(Scene_E_k[t,scene] == Scene_E_k[t - 1,scene] + Scene_P_ess_ch[t,scene] * 0.9 - Scene_P_ess_dis[t,scene] / 0.9)
        m.addConstr(Scene_P_ess_ch.sum('*', scene) * 0.9 == Scene_P_ess_dis.sum('*', scene) / 0.9)
    # DG出力
    Scene_P_DG_813 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_813")
    Scene_P_DG_911 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_911")
    Scene_Q_DG_813 = m.addVars(2, T, scenes, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
    Scene_Q_DG_911 = m.addVars(2, T, scenes, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")

    for t in range(T):
        m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[0, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_813[1, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[0, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[1, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))

    #目标函数

    f_op=[0,0,0]
    for scene in range(scenes):
        if scene == 0:
            coef=1
        elif scene == 1:
            coef=(mu - delta)
        elif scene == 2:
            coef=(mu + delta)
        for t in range(T):
            f_op[scene] += c_s * Scene_P_sub[t, scene]
            f_op[scene] += c_e * (Scene_P_ess_ch[t, scene] + Scene_P_ess_dis[t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[1, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[1, t, scene])
    # 有功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_P_sub[t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 5:
                    m.addConstr(
                        0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, scene] - Scene_P_ess_ch[
                            t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        Scene_P_DG_813[0, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 8:
                    m.addConstr(
                        Scene_P_DG_911[0, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 10:
                    m.addConstr(
                        Scene_P_DG_911[1, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 12:
                    m.addConstr(
                        Scene_P_DG_813[1, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                else:
                    m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)

    # 无功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_Q_sub[t, scene] - Scene_Q_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        (Scene_Q_DG_813[0, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 8:
                    m.addConstr(
                        (Scene_Q_DG_911[0, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 10:
                    m.addConstr(
                        (Scene_Q_DG_911[1, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 12:
                    m.addConstr(
                        (Scene_Q_DG_813[1, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (0 - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
    #
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    if U[i][j] == 0:
                        m.addConstr(Scene_P_tran[i, j, t, scene] == 0, name='联通潮流约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='联通潮流约束2')
                    if W[i] * W[j] == 1:
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='换流无功约束')


    # # 电压方程
    for scene in range(scenes):
        for i in range(n):
            for j in range(n):
                if i != j:
                    S_line = S_line_k[x[i][j]]
                    for t in range(T):
                        m.addConstr(U[i][j] * (
                                (1 - L[i][j] * W[i]) * Scene_V[i, t, scene]
                                + (L[i][j] * W[i] - L[i][j] * W[j]) * Scene_V__svc[i, j, t, scene]
                                - (1 - L[i][j] * W[j]) * Scene_V[j, t, scene]) ==
                                    (1 - L[i][j]) * (
                                                r__[i][j] * Scene_P_tran[i, j, t, scene] + x__[i][j] * Scene_Q_tran[
                                            i, j, t, scene])
                                    + L[i][j] * (r__vsc[i][j] * Scene_P_tran[i, j, t, scene] - x__vsc[i][j] *
                                                 Scene_Q_tran[i, j, t, scene]), name='电压方程')
                        # VSC约束
                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= L[i][j] * (Q_vsc_max - M) + M, name='VSC无功约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -1 * (L[i][j] * (Q_vsc_max - M) + M),
                                    name='VSC无功约束2')
                        # 传输容量约束
                        m.addConstr(Scene_P_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束1')
                        m.addConstr(Scene_P_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束2')

                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束3')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束4')

                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束5')
                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束6')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束7')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束8')
    f1=(0.8*f_op[0]+0.1*f_op[1]+0.1*f_op[2]-5e3)/4e3
    f2=1-delta/0.4
    m.setObjective(w1*f1+w2*f2, gb.GRB.MINIMIZE)
    m.setParam('LogToConsole', 0)
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    # Result = []
    # for v in m.getVars():
    #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
    #         print(v.VarName, v.X)


    # 重新计算 f_op（3 个场景）
    # f_op = [0.0, 0.0, 0.0]
    #
    # mu_val = mu.X
    # delta_val = delta.X
    #
    # for scene in range(scenes):
    #     if scene == 0:
    #         coef = 1
    #     elif scene == 1:
    #         coef = (mu_val - delta_val)
    #     elif scene == 2:
    #         coef = (mu_val + delta_val)
    #
    #     for t in range(T):
    #         f_op[scene] += c_s * Scene_P_sub[t, scene].X
    #         f_op[scene] += c_e * (Scene_P_ess_ch[t, scene].X + Scene_P_ess_dis[t, scene].X)
    #
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[0, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[0, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[1, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[1, t, scene].X)
    #
    # print("三个场景运行成本：")
    # print(f_op)
    # print(delta.X)
    # print(mu.X)


    if m.status == gb.GRB.OPTIMAL:
        f_op_val = [0, 0, 0]

        for scene in range(scenes):
            if scene == 0:
                coef = 1
            elif scene == 1:
                coef = (mu.X - delta.X)
            elif scene == 2:
                coef = (mu.X + delta.X)

            for t in range(T):
                f_op_val[scene] += c_s * Scene_P_sub[t, scene].X
                f_op_val[scene] += c_e * (Scene_P_ess_ch[t, scene].X + Scene_P_ess_dis[t, scene].X)
                f_op_val[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[0, t, scene].X)
                f_op_val[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[0, t, scene].X)
                f_op_val[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[1, t, scene].X)
                f_op_val[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[1, t, scene].X)

        f1_val = 0.8 * f_op_val[0] + 0.1 * f_op_val[1] + 0.1 * f_op_val[2]
        return m.objVal,f1_val,delta.X,mu.X
    else:
        return 9e12,1e4,0,1


def Lower_layer_solving_2(W,U,x,n=13,T=24):
    m=gb.Model('m1')
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])
    # epsilon = m.addVar(lb=1, ub=2, vtype=gb.GRB.CONTINUOUS, name="epsilon")
    mu = m.addVar(lb=1, ub=2, vtype=gb.GRB.CONTINUOUS, name="mu")
    delta = m.addVar(ub=0.4, vtype=gb.GRB.CONTINUOUS, name="delta")
    m.addConstr(delta <= mu * 0.2)
    f2=-delta

    # 定义各节点电压
    Scene_V = m.addVars(n, T, scenes, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
    Scene_V__svc = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    m.addConstr(Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene])
                    m.addConstr(Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene])

    # 定义线路潮流
    Scene_P_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
    Scene_Q_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
    for scene in range(scenes):
        for t in range(T):
            for i in range(n):
                m.addConstr(Scene_P_tran[i, i, t, scene] == 0)
                m.addConstr(Scene_Q_tran[i, i, t, scene] == 0)
                for j in range(i + 1, n):
                    if i != j:
                        m.addConstr(Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene])
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene])
    # 购电功率
    Scene_P_sub = m.addVars(T, scenes, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
    Scene_Q_sub = m.addVars(T, scenes, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")

    # 储能充放电功率
    # 储能约束
    Scene_P_ess_ch = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
    Scene_P_ess_dis = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
    Scene_alpha__dis = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__dis")
    Scene_alpha__ch = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__ch")
    Scene_E_k = m.addVars(T, scenes, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS,name="Scene_E_k")
    for scene in range(scenes):
        m.addConstr(Scene_E_k[0, scene] == 5)
        for t in range(T):
            m.addConstr(Scene_alpha__ch[t,scene] + Scene_alpha__dis[t,scene] <= 1)
            m.addConstr(Scene_P_ess_dis[t,scene] <= Scene_alpha__dis[t,scene] * P_ess_max)
            m.addConstr(Scene_P_ess_ch[t,scene] <= Scene_alpha__ch[t,scene] * P_ess_max)
            if t != 0:
                m.addConstr(Scene_E_k[t,scene] == Scene_E_k[t - 1,scene] + Scene_P_ess_ch[t,scene] * 0.9 - Scene_P_ess_dis[t,scene] / 0.9)
        m.addConstr(Scene_P_ess_ch.sum('*', scene) * 0.9 == Scene_P_ess_dis.sum('*', scene) / 0.9)
    # DG出力
    Scene_P_DG_813 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_813")
    Scene_P_DG_911 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_911")
    Scene_Q_DG_813 = m.addVars(2, T, scenes, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
    Scene_Q_DG_911 = m.addVars(2, T, scenes, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")

    for t in range(T):
        m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[0, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_813[1, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[0, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[1, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
    #目标函数

    f_op=[0,0,0]
    for scene in range(scenes):
        if scene == 0:
            coef=1
        elif scene == 1:
            coef=(mu - delta)
        elif scene == 2:
            coef=(mu + delta)
        for t in range(T):
            f_op[scene] += c_s * Scene_P_sub[t, scene]
            f_op[scene] += c_e * (Scene_P_ess_ch[t, scene] + Scene_P_ess_dis[t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[1, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[1, t, scene])
    # 有功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_P_sub[t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 5:
                    m.addConstr(
                        0 - P_load[t] * (n__ac[i] + n__dc[i]) + Scene_P_ess_dis[t, scene] - Scene_P_ess_ch[
                            t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        Scene_P_DG_813[0, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 8:
                    m.addConstr(
                        Scene_P_DG_911[0, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 10:
                    m.addConstr(
                        Scene_P_DG_911[1, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 12:
                    m.addConstr(
                        Scene_P_DG_813[1, t, scene] - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                else:
                    m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)

    # 无功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_Q_sub[t, scene] - Scene_Q_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        (Scene_Q_DG_813[0, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 8:
                    m.addConstr(
                        (Scene_Q_DG_911[0, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 10:
                    m.addConstr(
                        (Scene_Q_DG_911[1, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 12:
                    m.addConstr(
                        (Scene_Q_DG_813[1, t, scene] - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (0 - Q_load[t] * (n__ac[i] + n__dc[i]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
    #
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    if U[i][j] == 0:
                        m.addConstr(Scene_P_tran[i, j, t, scene] == 0, name='联通潮流约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='联通潮流约束2')
                    if W[i] * W[j] == 1:
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='换流无功约束')


    # # 电压方程
    for scene in range(scenes):
        for i in range(n):
            for j in range(n):
                if i != j:
                    S_line = S_line_k[x[i][j]]
                    for t in range(T):
                        m.addConstr(U[i][j] * (
                                (1 - L[i][j] * W[i]) * Scene_V[i, t, scene]
                                + (L[i][j] * W[i] - L[i][j] * W[j]) * Scene_V__svc[i, j, t, scene]
                                - (1 - L[i][j] * W[j]) * Scene_V[j, t, scene]) ==
                                    (1 - L[i][j]) * (
                                                r__[i][j] * Scene_P_tran[i, j, t, scene] + x__[i][j] * Scene_Q_tran[
                                            i, j, t, scene])
                                    + L[i][j] * (r__vsc[i][j] * Scene_P_tran[i, j, t, scene] - x__vsc[i][j] *
                                                 Scene_Q_tran[i, j, t, scene]), name='电压方程')
                        # VSC约束
                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= L[i][j] * (Q_vsc_max - M) + M, name='VSC无功约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -1 * (L[i][j] * (Q_vsc_max - M) + M),
                                    name='VSC无功约束2')
                        # 传输容量约束
                        m.addConstr(Scene_P_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束1')
                        m.addConstr(Scene_P_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束2')

                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束3')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束4')

                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束5')
                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束6')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束7')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束8')













    U_1_index=find_upper_right_ones(U)
    k_U_lack=len(U_1_index)
    U_lack_1=[]
    for i in U_1_index:
        U_new = copy.deepcopy(U)
        U_new[i[0]][i[1]]=0
        U_new[i[1]][i[0]] = 0
        U_lack_1.append(U_new)
    Loss_load=m.addVars(n,2,k_U_lack,vtype=gb.GRB.BINARY,name='Loss_load')
    for k in range(k_U_lack):
        for i in range(n):
            if n__ac[i] == 0:
                m.addConstr(Loss_load[i, 0,k] == 0)
            if n__dc[i] == 0:
                m.addConstr(Loss_load[i, 1,k] == 0)
    # 定义各节点电压
    Lack_V = m.addVars(n, T, scenes,k_U_lack, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Lack_V")
    Lack_V__svc = m.addVars(n, n, T, scenes,k_U_lack, vtype=gb.GRB.CONTINUOUS, name="Lack_V__svc")
    for k in range(k_U_lack):
        for scene in range(scenes):
            for i in range(n):
                for j in range(i + 1, n):
                    for t in range(T):
                        m.addConstr(Lack_V__svc[i, j, t, scene,k] == Lack_V__svc[j, i, t, scene,k])
                        m.addConstr(Lack_V__svc[i, j, t, scene,k] == Lack_V__svc[j, i, t, scene,k])

    # 定义线路潮流
    Lack_P_tran = m.addVars(n, n, T, scenes,k_U_lack, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Lack_P_tran")
    Lack_Q_tran = m.addVars(n, n, T, scenes,k_U_lack, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Lack_Q_tran")
    for k in range(k_U_lack):
        for scene in range(scenes):
            for t in range(T):
                for i in range(n):
                    m.addConstr(Lack_P_tran[i, i, t, scene, k] == 0)
                    m.addConstr(Lack_Q_tran[i, i, t, scene, k] == 0)
                    for j in range(i + 1, n):
                        if i != j:
                            m.addConstr(Lack_P_tran[i, j, t, scene, k] == -Lack_P_tran[j, i, t, scene, k])
                            m.addConstr(Lack_Q_tran[i, j, t, scene, k] == -Lack_Q_tran[j, i, t, scene, k])
    # 购电功率
    Lack_P_sub = m.addVars(T, scenes,k_U_lack, ub=10, vtype=gb.GRB.CONTINUOUS, name="Lack_P_sub")
    Lack_Q_sub = m.addVars(T, scenes,k_U_lack, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Lack_Q_sub")

    # 储能充放电功率
    # 储能约束
    Lack_P_ess_ch = m.addVars(T, scenes,k_U_lack, vtype=gb.GRB.CONTINUOUS, name="Lack_P_ess_ch")
    Lack_P_ess_dis = m.addVars(T, scenes,k_U_lack, vtype=gb.GRB.CONTINUOUS, name="Lack_P_ess_dis")
    Lack_alpha__dis = m.addVars(T, scenes,k_U_lack, vtype=gb.GRB.BINARY, name="Lack_alpha__dis")
    Lack_alpha__ch = m.addVars(T, scenes,k_U_lack, vtype=gb.GRB.BINARY, name="Lack_alpha__ch")
    Lack_E_k = m.addVars(T, scenes,k_U_lack, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS, name="Lack_E_k")
    for k in range(k_U_lack):
        for scene in range(scenes):
            m.addConstr(Lack_E_k[0, scene,k] == 5)
            for t in range(T):
                m.addConstr(Lack_alpha__ch[t, scene, k] + Lack_alpha__dis[t, scene, k] <= 1)
                m.addConstr(Lack_P_ess_dis[t, scene, k] <= Lack_alpha__dis[t, scene, k] * P_ess_max)
                m.addConstr(Lack_P_ess_ch[t, scene, k] <= Lack_alpha__ch[t, scene, k] * P_ess_max)
                if t != 0:
                    m.addConstr(Lack_E_k[t, scene, k] == Lack_E_k[t - 1, scene, k] + Lack_P_ess_ch[
                        t, scene, k] * 0.9 -Lack_P_ess_dis[t, scene, k] / 0.9)
            m.addConstr(Lack_P_ess_ch.sum('*', scene, k) * 0.9 == Lack_P_ess_dis.sum('*', scene, k) / 0.9)
    # DG出力
    Lack_P_DG_813 = m.addVars(2, T, scenes,k_U_lack, vtype=gb.GRB.CONTINUOUS, name="Lack_P_DG_813")
    Lack_P_DG_911 = m.addVars(2, T, scenes,k_U_lack, vtype=gb.GRB.CONTINUOUS, name="Lack_P_DG_911")
    Lack_Q_DG_813 = m.addVars(2, T, scenes,k_U_lack, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Lack_Q_DG_813")
    Lack_Q_DG_911 = m.addVars(2, T, scenes,k_U_lack, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Lack_Q_DG_911")

    for k in range(k_U_lack):
        for t in range(T):
            m.addConstr(Lack_P_DG_813[0, t, 0, k] <= DG_total[t] * 2.0 / 9 * 1)
            m.addConstr(Lack_P_DG_813[1, t, 0, k] <= DG_total[t] * 2.0 / 9 * 1)
            m.addConstr(Lack_P_DG_911[0, t, 0, k] <= DG_total[t] * 2.5 / 9 * 1)
            m.addConstr(Lack_P_DG_911[1, t, 0, k] <= DG_total[t] * 2.5 / 9 * 1)
            m.addConstr(Lack_P_DG_813[0, t, 1, k] <= DG_total[t] * 2.0 / 9 * (mu - delta))
            m.addConstr(Lack_P_DG_813[1, t, 1, k] <= DG_total[t] * 2.0 / 9 * (mu - delta))
            m.addConstr(Lack_P_DG_911[0, t, 1, k] <= DG_total[t] * 2.5 / 9 * (mu - delta))
            m.addConstr(Lack_P_DG_911[1, t, 1, k] <= DG_total[t] * 2.5 / 9 * (mu - delta))
            m.addConstr(Lack_P_DG_813[0, t, 2, k] <= DG_total[t] * 2.0 / 9 * (mu + delta))
            m.addConstr(Lack_P_DG_813[1, t, 2, k] <= DG_total[t] * 2.0 / 9 * (mu + delta))
            m.addConstr(Lack_P_DG_911[0, t, 2, k] <= DG_total[t] * 2.5 / 9 * (mu + delta))
            m.addConstr(Lack_P_DG_911[1, t, 2, k] <= DG_total[t] * 2.5 / 9 * (mu + delta))
    # 目标函数

    # f_op = [0, 0, 0]
    # for scene in range(scenes):
    #     if scene == 0:
    #         coef = 1
    #     elif scene == 1:
    #         coef = (mu - delta)
    #     elif scene == 2:
    #         coef = (mu + delta)
    #     for t in range(T):
    #         f_op[scene] += c_s * Scene_P_sub[t, scene]
    #         f_op[scene] += c_e * (Scene_P_ess_ch[t, scene] + Scene_P_ess_dis[t, scene])
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[0, t, scene])
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[0, t, scene])
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[1, t, scene])
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[1, t, scene])
    # 有功功率平衡方程
    for k in range(k_U_lack):
        for scene in range(scenes):
            for i in range(n):
                for t in range(T):
                    if i == 0:
                        m.addConstr(Lack_P_sub[t, scene, k] - Lack_P_tran.sum(i, '*', t, scene, k) * S_base == 0)
                    elif i == 5:
                        m.addConstr(
                            0 - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) + Lack_P_ess_dis[t, scene, k] - Lack_P_ess_ch[
                                t, scene, k] - Lack_P_tran.sum(i, '*', t, scene, k) * S_base == 0)
                    elif i == 7:
                        m.addConstr(
                            Lack_P_DG_813[0, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Lack_P_tran.sum(i, '*',
                                                                                                               t,
                                                                                                               scene, k) * S_base == 0)
                    elif i == 8:
                        m.addConstr(
                            Lack_P_DG_911[0, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Lack_P_tran.sum(i, '*',
                                                                                                               t,
                                                                                                               scene, k) * S_base == 0)
                    elif i == 10:
                        m.addConstr(
                            Lack_P_DG_911[1, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Lack_P_tran.sum(i, '*',
                                                                                                               t,
                                                                                                               scene, k) * S_base == 0)
                    elif i == 12:
                        m.addConstr(
                            Lack_P_DG_813[1, t, scene, k] - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Lack_P_tran.sum(i, '*',
                                                                                                               t,
                                                                                                               scene, k) * S_base == 0)
                    else:
                        m.addConstr(
                            0 - P_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) - Lack_P_tran.sum(i, '*', t, scene, k) * S_base == 0)

    # 无功功率平衡方程
    for k in range(k_U_lack):
        for scene in range(scenes):
            for i in range(n):
                for t in range(T):
                    if i == 0:
                        m.addConstr(Lack_Q_sub[t, scene, k] - Lack_Q_tran.sum(i, '*', t, scene, k) * S_base == 0)
                    elif i == 7:
                        m.addConstr(
                            (Lack_Q_DG_813[0, t, scene, k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) -
                             Lack_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W[i]) == 0)
                    elif i == 8:
                        m.addConstr(
                            (Lack_Q_DG_911[0, t, scene, k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) -
                             Lack_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W[i]) == 0)
                    elif i == 10:
                        m.addConstr(
                            (Lack_Q_DG_911[1, t, scene, k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) -
                             Lack_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W[i]) == 0)
                    elif i == 12:
                        m.addConstr(
                            (Lack_Q_DG_813[1, t, scene, k] - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) -
                             Lack_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W[i]) == 0)
                    else:
                        m.addConstr(
                            (0 - Q_load[t] * (Loss_load[i,0,k]+Loss_load[i,1,k]) -
                             Lack_Q_tran.sum(i, '*', t, scene, k) * S_base) * (1 - W[i]) == 0)
    #
    for k in range(k_U_lack):
        for scene in range(scenes):
            for i in range(n):
                for j in range(i + 1, n):
                    for t in range(T):
                        if U_lack_1[k][i][j] == 0:
                            m.addConstr(Lack_P_tran[i, j, t, scene, k] == 0, name='联通潮流约束1')
                            m.addConstr(Lack_Q_tran[i, j, t, scene, k] == 0, name='联通潮流约束2')
                        if W[i] * W[j] == 1:
                            m.addConstr(Lack_Q_tran[i, j, t, scene, k] == 0, name='换流无功约束')

    # # 电压方程
    for k in range(k_U_lack):
        for scene in range(scenes):
            for i in range(n):
                for j in range(n):
                    if i != j:
                        S_line = S_line_k[x[i][j]]
                        for t in range(T):
                            m.addConstr(U_lack_1[k][i][j] * (
                                    (1 - L[i][j] * W[i]) * Lack_V[i, t, scene, k]
                                    + (L[i][j] * W[i] - L[i][j] * W[j]) * Lack_V__svc[i, j, t, scene, k]
                                    - (1 - L[i][j] * W[j]) * Lack_V[j, t, scene, k]) ==
                                        (1 - L[i][j]) * (r__[i][j] * Lack_P_tran[i, j, t, scene, k] + x__[i][j] * Lack_Q_tran[i, j, t, scene, k])
                                        + L[i][j] * (r__vsc[i][j] * Lack_P_tran[i, j, t, scene, k] - x__vsc[i][j] *Lack_Q_tran[i, j, t, scene, k]), name='电压方程')
                            # VSC约束
                            m.addConstr(Lack_Q_tran[i, j, t, scene, k] <= L[i][j] * (Q_vsc_max - M) + M,
                                        name='VSC无功约束1')
                            m.addConstr(Lack_Q_tran[i, j, t, scene, k] >= -1 * (L[i][j] * (Q_vsc_max - M) + M),
                                        name='VSC无功约束2')
                            # 传输容量约束
                            m.addConstr(Lack_P_tran[i, j, t, scene, k] <= gama * S_line / S_base, name='传输容量约束1')
                            m.addConstr(Lack_P_tran[i, j, t, scene, k] >= -gama * S_line / S_base, name='传输容量约束2')

                            m.addConstr(Lack_Q_tran[i, j, t, scene, k] <= gama * S_line / S_base, name='传输容量约束3')
                            m.addConstr(Lack_Q_tran[i, j, t, scene, k] >= -gama * S_line / S_base, name='传输容量约束4')

                            m.addConstr(Lack_P_tran[i, j, t, scene, k] + Lack_Q_tran[
                                i, j, t, scene, k] <= 1.41 * gama * S_line / S_base, name='传输容量约束5')
                            m.addConstr(Lack_P_tran[i, j, t, scene, k] + Lack_Q_tran[
                                i, j, t, scene, k] >= -1.41 * gama * S_line / S_base, name='传输容量约束6')
                            m.addConstr(Lack_P_tran[i, j, t, scene, k] - Lack_Q_tran[
                                i, j, t, scene, k] <= 1.41 * gama * S_line / S_base, name='传输容量约束7')
                            m.addConstr(Lack_P_tran[i, j, t, scene, k] - Lack_Q_tran[
                                i, j, t, scene, k] >= -1.41 * gama * S_line / S_base, name='传输容量约束8')






    f1=(0.8*f_op[0]+0.1*f_op[1]+0.1*f_op[2]-5e3)/4e3
    f2=1-delta/0.4
    f3=((sum(n__ac)+sum(n__dc))*k_U_lack-Loss_load.sum())/(sum(n__ac)+sum(n__dc))
    m.setObjective(f1+f2+10*f3, gb.GRB.MINIMIZE)
    m.setParam('LogToConsole', 1)
    # m.setParam('MemLimit', 24000)
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    # Result = []
    # for v in m.getVars():
    #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
    # print(v.VarName, v.X)


    # print("三个场景运行成本：")
    # print(f_op)
    # print(delta.X)
    # print(mu.X)
    # print(Loss_load[0,0,0].X)
    # R_LOSS=[]
    # for k in range(k_U_lack):
    #     a=[]
    #     for j in range(2):
    #         b=[]
    #         for i in range(n):
    #             b.append(Loss_load[i,j,k].X)
    #         a.append(b)
    #     R_LOSS.append(a)
    # print(R_LOSS)
    # print
    # Ss=[]
    # for k in range(k_U_lack):
    #     a=[]
    #     a.append(sum(n__ac) - sum(R_LOSS[k][0]))
    #     a.append(sum(n__dc) - sum(R_LOSS[k][1]))
    #     Ss.append(a)
    # print(Ss)



    if m.status == gb.GRB.OPTIMAL:
        # 重新计算 f_op（3 个场景）
        f_op = [0.0, 0.0, 0.0]
        mu_val = mu.X
        delta_val = delta.X
        for scene in range(scenes):
            if scene == 0:
                coef = 1
            elif scene == 1:
                coef = (mu_val - delta_val)
            elif scene == 2:
                coef = (mu_val + delta_val)

            for t in range(T):
                f_op[scene] += c_s * Scene_P_sub[t, scene].X
                f_op[scene] += c_e * (Scene_P_ess_ch[t, scene].X + Scene_P_ess_dis[t, scene].X)

                f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[0, t, scene].X)
                f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[0, t, scene].X)
                f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[1, t, scene].X)
                f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[1, t, scene].X)
        R_LOSS = []
        for k in range(k_U_lack):
            a=[]
            for j in range(2):
                b=[]
                for i in range(n):
                    b.append(Loss_load[i,j,k].X)
                a.append(b)
            R_LOSS.append(a)
        Ss=[]
        for k in range(k_U_lack):
            a=[]
            a.append(sum(n__ac) - sum(R_LOSS[k][0]))
            a.append(sum(n__dc) - sum(R_LOSS[k][1]))
            Ss.append(a)
        f3=sum(element for row in Ss for element in row)/(sum(n__ac)+sum(n__dc))
        return m.objVal,0.8*f_op[0]+0.1*f_op[1]+0.1*f_op[2],delta.X,mu.X,f3
    else:
        return 9e12,1e4,0,1,1


def Lower_layer_solving_3(W,U,x,delta,mu,n=13,T=24):
    m=gb.Model('m1')
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])

    Loss_load = m.addVars(n, 2, vtype=gb.GRB.BINARY, name='Loss_load')
    for i in range(n):
        if n__ac[i] == 0:
            m.addConstr(Loss_load[i, 0] == 0)
        if n__dc[i] == 0:
            m.addConstr(Loss_load[i, 1] == 0)

    # 定义各节点电压
    Scene_V = m.addVars(n, T, scenes, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
    Scene_V__svc = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    m.addConstr(Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene])
    # 定义线路潮流
    Scene_P_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
    Scene_Q_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
    for scene in range(scenes):
        for t in range(T):
            for i in range(n):
                m.addConstr(Scene_P_tran[i, i, t, scene] == 0)
                m.addConstr(Scene_Q_tran[i, i, t, scene] == 0)
                for j in range(i + 1, n):
                    if i != j:
                        m.addConstr(Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene])
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene])
    # 购电功率
    Scene_P_sub = m.addVars(T, scenes, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
    Scene_Q_sub = m.addVars(T, scenes, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")

    # 储能充放电功率
    # 储能约束
    Scene_P_ess_ch = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
    Scene_P_ess_dis = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
    Scene_alpha__dis = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__dis")
    Scene_alpha__ch = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__ch")
    Scene_E_k = m.addVars(T, scenes, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS,name="Scene_E_k")
    for scene in range(scenes):
        m.addConstr(Scene_E_k[0, scene] == 5)
        for t in range(T):
            m.addConstr(Scene_alpha__ch[t,scene] + Scene_alpha__dis[t,scene] <= 1)
            m.addConstr(Scene_P_ess_dis[t,scene] <= Scene_alpha__dis[t,scene] * P_ess_max)
            m.addConstr(Scene_P_ess_ch[t,scene] <= Scene_alpha__ch[t,scene] * P_ess_max)
            if t != 0:
                m.addConstr(Scene_E_k[t,scene] == Scene_E_k[t - 1,scene] + Scene_P_ess_ch[t,scene] * 0.9 - Scene_P_ess_dis[t,scene] / 0.9)
        m.addConstr(Scene_P_ess_ch.sum('*', scene) * 0.9 == Scene_P_ess_dis.sum('*', scene) / 0.9)
    # DG出力
    Scene_P_DG_813 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_813")
    Scene_P_DG_911 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_911")
    Scene_Q_DG_813 = m.addVars(2, T, scenes, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
    Scene_Q_DG_911 = m.addVars(2, T, scenes, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")

    for t in range(T):
        m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[0, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_813[1, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[0, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[1, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
    #目标函数

    f_op=[0,0,0]
    for scene in range(scenes):
        if scene == 0:
            coef=1
        elif scene == 1:
            coef=(mu - delta)
        elif scene == 2:
            coef=(mu + delta)
        for t in range(T):
            f_op[scene] += c_s * Scene_P_sub[t, scene]
            f_op[scene] += c_e * (Scene_P_ess_ch[t, scene] + Scene_P_ess_dis[t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[1, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[1, t, scene])
    # 有功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_P_sub[t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 5:
                    m.addConstr(
                        0 - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) + Scene_P_ess_dis[t, scene] - Scene_P_ess_ch[
                            t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        Scene_P_DG_813[0, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 8:
                    m.addConstr(
                        Scene_P_DG_911[0, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 10:
                    m.addConstr(
                        Scene_P_DG_911[1, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 12:
                    m.addConstr(
                        Scene_P_DG_813[1, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                else:
                    m.addConstr(0 - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)

    # 无功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_Q_sub[t, scene] - Scene_Q_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        (Scene_Q_DG_813[0, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 8:
                    m.addConstr(
                        (Scene_Q_DG_911[0, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 10:
                    m.addConstr(
                        (Scene_Q_DG_911[1, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 12:
                    m.addConstr(
                        (Scene_Q_DG_813[1, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (0 - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
    #
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    if U[i][j] == 0:
                        m.addConstr(Scene_P_tran[i, j, t, scene] == 0, name='联通潮流约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='联通潮流约束2')
                    if W[i] * W[j] == 1:
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='换流无功约束')


    # # 电压方程
    for scene in range(scenes):
        for i in range(n):
            for j in range(n):
                if i != j:
                    S_line = S_line_k[x[i][j]]
                    for t in range(T):
                        m.addConstr(U[i][j] * (
                                (1 - L[i][j] * W[i]) * Scene_V[i, t, scene]
                                + (L[i][j] * W[i] - L[i][j] * W[j]) * Scene_V__svc[i, j, t, scene]
                                - (1 - L[i][j] * W[j]) * Scene_V[j, t, scene]) ==
                                    (1 - L[i][j]) * (
                                                r__[i][j] * Scene_P_tran[i, j, t, scene] + x__[i][j] * Scene_Q_tran[
                                            i, j, t, scene])
                                    + L[i][j] * (r__vsc[i][j] * Scene_P_tran[i, j, t, scene] - x__vsc[i][j] *
                                                 Scene_Q_tran[i, j, t, scene]), name='电压方程')
                        # VSC约束
                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= L[i][j] * (Q_vsc_max - M) + M, name='VSC无功约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -1 * (L[i][j] * (Q_vsc_max - M) + M),
                                    name='VSC无功约束2')
                        # 传输容量约束
                        m.addConstr(Scene_P_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束1')
                        m.addConstr(Scene_P_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束2')

                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束3')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束4')

                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束5')
                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束6')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束7')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束8')








    f1=(0.8*f_op[0]+0.1*f_op[1]+0.1*f_op[2]-5e3)/4e3
    f2=1-delta/0.4
    f3=sum(n__ac)+sum(n__dc)-Loss_load.sum()
    m.setObjective(f3, gb.GRB.MINIMIZE)
    m.setParam('LogToConsole', 0)
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    # Result = []
    # for v in m.getVars():
    #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
    #         print(v.VarName, v.X)


    # # 重新计算 f_op（3 个场景）
    # f_op = [0.0, 0.0, 0.0]
    #
    # mu_val = mu.X
    # delta_val = delta.X
    #
    # for scene in range(scenes):
    #     if scene == 0:
    #         coef = 1
    #     elif scene == 1:
    #         coef = (mu_val - delta_val)
    #     elif scene == 2:
    #         coef = (mu_val + delta_val)
    #
    #     for t in range(T):
    #         f_op[scene] += c_s * Scene_P_sub[t, scene].X
    #         f_op[scene] += c_e * (Scene_P_ess_ch[t, scene].X + Scene_P_ess_dis[t, scene].X)
    #
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[0, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[0, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[1, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[1, t, scene].X)

    # print("三个场景运行成本：")
    # print(f_op)
    # print(delta.X)
    # print(mu.X)
    # print(Loss_load[0,0,0].X)
    # R_LOSS=[]
    # for k in range(k_U_lack):
    #     a=[]
    #     for j in range(2):
    #         b=[]
    #         for i in range(n):
    #             b.append(Loss_load[i,j,k].X)
    #         a.append(b)
    #     R_LOSS.append(a)
    # print(R_LOSS)
    # print
    # Ss=[]
    # for k in range(k_U_lack):
    #     a=[]
    #     a.append(sum(n__ac) - sum(R_LOSS[k][0]))
    #     a.append(sum(n__dc) - sum(R_LOSS[k][1]))
    #     Ss.append(a)
    # print(Ss)



    if m.status == gb.GRB.OPTIMAL:
        return m.objVal
    else:
        return 9e12

# 性能更好的Lower_layer_solving_3
def Lower_layer_solving_31(W,U,x,delta,mu,n=13,T=24):
    m=gb.Model('m1')
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])

    Loss_load = m.addVars(n, 2, vtype=gb.GRB.BINARY, name='Loss_load')
    m.addConstrs(
        (Loss_load[i, 0] == 0 for i in range(n) if n__ac[i] == 0),
        name="Loss_load_AC_zero"
    )
    m.addConstrs(
        (Loss_load[i, 1] == 0 for i in range(n) if n__dc[i] == 0),
        name="Loss_load_DC_zero"
    )

    # 定义各节点电压
    Scene_V = m.addVars(n, T, scenes, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="Scene_V")
    Scene_V__svc = m.addVars(n, n, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_V__svc")
    m.addConstrs(
        (Scene_V__svc[i, j, t, scene] == Scene_V__svc[j, i, t, scene]
         for scene in range(scenes)
         for i in range(n)
         for j in range(i + 1, n)
         for t in range(T)),
        name="Scene_V_svc_symmetry"
    )
    # 定义线路潮流
    Scene_P_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_P_tran")
    Scene_Q_tran = m.addVars(n, n, T, scenes,lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_tran")
    m.addConstrs(
        (Scene_P_tran[i, i, t, scene] == 0
         for scene in range(scenes)
         for t in range(T)
         for i in range(n)),
        name="Scene_P_tran_diag_zero"
    )
    m.addConstrs(
        (Scene_Q_tran[i, i, t, scene] == 0
         for scene in range(scenes)
         for t in range(T)
         for i in range(n)),
        name="Scene_Q_tran_diag_zero"
    )
    m.addConstrs(
        (Scene_P_tran[i, j, t, scene] == -Scene_P_tran[j, i, t, scene]
         for scene in range(scenes)
         for t in range(T)
         for i in range(n)
         for j in range(i + 1, n)),
        name="Scene_P_tran_antisym"
    )
    m.addConstrs(
        (Scene_Q_tran[i, j, t, scene] == -Scene_Q_tran[j, i, t, scene]
         for scene in range(scenes)
         for t in range(T)
         for i in range(n)
         for j in range(i + 1, n)),
        name="Scene_Q_tran_antisym"
    )
    # 购电功率
    Scene_P_sub = m.addVars(T, scenes, ub=10, vtype=gb.GRB.CONTINUOUS, name="Scene_P_sub")
    Scene_Q_sub = m.addVars(T, scenes, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_sub")

    # 储能充放电功率
    # 储能约束
    Scene_P_ess_ch = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_ch")
    Scene_P_ess_dis = m.addVars(T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_ess_dis")
    Scene_alpha__dis = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__dis")
    Scene_alpha__ch = m.addVars(T, scenes, vtype=gb.GRB.BINARY,name="Scene_alpha__ch")
    Scene_E_k = m.addVars(T, scenes, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS,name="Scene_E_k")

    m.addConstrs((Scene_E_k[0, s] == 5 for s in range(scenes)), name="ESS_init")
    m.addConstrs(
        (Scene_alpha__ch[t, s] + Scene_alpha__dis[t, s] <= 1 for s in range(scenes) for t in range(T)),
        name="ESS_ch_dis_mutual"
    )
    m.addConstrs(
        (Scene_P_ess_ch[t, s] <= Scene_alpha__ch[t, s] * P_ess_max for s in range(scenes) for t in range(T)),
        name="ESS_ch_power"
    )
    m.addConstrs(
        (Scene_P_ess_dis[t, s] <= Scene_alpha__dis[t, s] * P_ess_max for s in range(scenes) for t in range(T)),
        name="ESS_dis_power"
    )
    m.addConstrs(
        (Scene_E_k[t, s] == Scene_E_k[t - 1, s] + Scene_P_ess_ch[t, s] * 0.9 - Scene_P_ess_dis[t, s] / 0.9
         for s in range(scenes) for t in range(1, T)),
        name="ESS_energy_status"
    )
    m.addConstrs(
        (Scene_P_ess_ch.sum('*', s) * 0.9 == Scene_P_ess_dis.sum('*', s) / 0.9 for s in range(scenes)),
        name="ESS_energy_balance"
    )
    # DG出力
    Scene_P_DG_813 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_813")
    Scene_P_DG_911 = m.addVars(2, T, scenes, vtype=gb.GRB.CONTINUOUS, name="Scene_P_DG_911")
    Scene_Q_DG_813 = m.addVars(2, T, scenes, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_813")
    Scene_Q_DG_911 = m.addVars(2, T, scenes, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Scene_Q_DG_911")

    for t in range(T):
        m.addConstr(Scene_P_DG_813[0, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_813[1, t, 0] <= DG_total[t] * 2.0 / 9 * 1)
        m.addConstr(Scene_P_DG_911[0, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_911[1, t, 0] <= DG_total[t] * 2.5 / 9 * 1)
        m.addConstr(Scene_P_DG_813[0, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[1, t, 1] <= DG_total[t] * 2.0 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[0, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_911[1, t, 1] <= DG_total[t] * 2.5 / 9 * (mu - delta))
        m.addConstr(Scene_P_DG_813[0, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_813[1, t, 2] <= DG_total[t] * 2.0 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[0, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
        m.addConstr(Scene_P_DG_911[1, t, 2] <= DG_total[t] * 2.5 / 9 * (mu + delta))
    #目标函数

    f_op=[0,0,0]
    for scene in range(scenes):
        if scene == 0:
            coef=1
        elif scene == 1:
            coef=(mu - delta)
        elif scene == 2:
            coef=(mu + delta)
        for t in range(T):
            f_op[scene] += c_s * Scene_P_sub[t, scene]
            f_op[scene] += c_e * (Scene_P_ess_ch[t, scene] + Scene_P_ess_dis[t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[0, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 *coef - Scene_P_DG_911[1, t, scene])
            f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 *coef - Scene_P_DG_813[1, t, scene])
    # 有功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_P_sub[t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 5:
                    m.addConstr(
                        0 - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) + Scene_P_ess_dis[t, scene] - Scene_P_ess_ch[
                            t, scene] - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        Scene_P_DG_813[0, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 8:
                    m.addConstr(
                        Scene_P_DG_911[0, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 10:
                    m.addConstr(
                        Scene_P_DG_911[1, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                elif i == 12:
                    m.addConstr(
                        Scene_P_DG_813[1, t, scene] - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t,
                                                                                                       scene) * S_base == 0)
                else:
                    m.addConstr(0 - P_load[t] * (Loss_load[i,0] + Loss_load[i,1]) - Scene_P_tran.sum(i, '*', t, scene) * S_base == 0)

    # 无功功率平衡方程
    for scene in range(scenes):
        for i in range(n):
            for t in range(T):
                if i == 0:
                    m.addConstr(Scene_Q_sub[t, scene] - Scene_Q_tran.sum(i, '*', t, scene) * S_base == 0)
                elif i == 7:
                    m.addConstr(
                        (Scene_Q_DG_813[0, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 8:
                    m.addConstr(
                        (Scene_Q_DG_911[0, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 10:
                    m.addConstr(
                        (Scene_Q_DG_911[1, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                elif i == 12:
                    m.addConstr(
                        (Scene_Q_DG_813[1, t, scene] - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
                else:
                    m.addConstr(
                        (0 - Q_load[t] * (Loss_load[i,0] + Loss_load[i,1]) -
                         Scene_Q_tran.sum(i, '*', t, scene) * S_base) * (1 - W[i]) == 0)
    #潮流约束
    # m.addConstrs(
    #     (Scene_P_tran[i, j, t, scene] == 0
    #      for scene in range(scenes)
    #      for t in range(T)
    #      for i in range(n)
    #      for j in range(i + 1, n)
    #      if U[i][j] == 0),
    #     name="联通潮流约束1"
    # )
    # m.addConstrs(
    #     (Scene_Q_tran[i, j, t, scene] == 0
    #      for scene in range(scenes)
    #      for t in range(T)
    #      for i in range(n)
    #      for j in range(i + 1, n)
    #      if U[i][j] == 0),
    #     name="联通潮流约束2"
    # )
    # m.addConstrs(
    #     (Scene_Q_tran[i, j, t, scene] == 0
    #      for scene in range(scenes)
    #      for t in range(T)
    #      for i in range(n)
    #      for j in range(i + 1, n)
    #      if W[i] * W[j] == 1),
    #     name="换流无功约束"
    # )
    for scene in range(scenes):
        for i in range(n):
            for j in range(i + 1, n):
                for t in range(T):
                    if U[i][j] == 0:
                        m.addConstr(Scene_P_tran[i, j, t, scene] == 0, name='联通潮流约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='联通潮流约束2')
                    if W[i] * W[j] == 1:
                        m.addConstr(Scene_Q_tran[i, j, t, scene] == 0, name='换流无功约束')

    # # 电压方程
    for scene in range(scenes):
        for i in range(n):
            for j in range(n):
                if i != j:
                    S_line = S_line_k[x[i][j]]
                    for t in range(T):
                        m.addConstr(U[i][j] * (
                                (1 - L[i][j] * W[i]) * Scene_V[i, t, scene]
                                + (L[i][j] * W[i] - L[i][j] * W[j]) * Scene_V__svc[i, j, t, scene]
                                - (1 - L[i][j] * W[j]) * Scene_V[j, t, scene]) ==
                                    (1 - L[i][j]) * (
                                                r__[i][j] * Scene_P_tran[i, j, t, scene] + x__[i][j] * Scene_Q_tran[
                                            i, j, t, scene])
                                    + L[i][j] * (r__vsc[i][j] * Scene_P_tran[i, j, t, scene] - x__vsc[i][j] *
                                                 Scene_Q_tran[i, j, t, scene]), name='电压方程')
                        # VSC约束
                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= L[i][j] * (Q_vsc_max - M) + M, name='VSC无功约束1')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -1 * (L[i][j] * (Q_vsc_max - M) + M),
                                    name='VSC无功约束2')
                        # 传输容量约束
                        m.addConstr(Scene_P_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束1')
                        m.addConstr(Scene_P_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束2')

                        m.addConstr(Scene_Q_tran[i, j, t, scene] <= gama * S_line / S_base, name='传输容量约束3')
                        m.addConstr(Scene_Q_tran[i, j, t, scene] >= -gama * S_line / S_base, name='传输容量约束4')

                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束5')
                        m.addConstr(Scene_P_tran[i, j, t, scene] + Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束6')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] <= 1.41 * gama * S_line / S_base, name='传输容量约束7')
                        m.addConstr(Scene_P_tran[i, j, t, scene] - Scene_Q_tran[
                            i, j, t, scene] >= -1.41 * gama * S_line / S_base, name='传输容量约束8')








    f1=(0.8*f_op[0]+0.1*f_op[1]+0.1*f_op[2]-5e3)/4e3
    f2=1-delta/0.4
    f3=sum(n__ac)+sum(n__dc)-Loss_load.sum()
    m.setObjective(f3, gb.GRB.MINIMIZE)
    m.setParam('LogToConsole', 0)
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    # Result = []
    # for v in m.getVars():
    #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
    #         print(v.VarName, v.X)


    # # 重新计算 f_op（3 个场景）
    # f_op = [0.0, 0.0, 0.0]
    #
    # mu_val = mu.X
    # delta_val = delta.X
    #
    # for scene in range(scenes):
    #     if scene == 0:
    #         coef = 1
    #     elif scene == 1:
    #         coef = (mu_val - delta_val)
    #     elif scene == 2:
    #         coef = (mu_val + delta_val)
    #
    #     for t in range(T):
    #         f_op[scene] += c_s * Scene_P_sub[t, scene].X
    #         f_op[scene] += c_e * (Scene_P_ess_ch[t, scene].X + Scene_P_ess_dis[t, scene].X)
    #
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[0, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[0, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.5 / 9 * coef - Scene_P_DG_911[1, t, scene].X)
    #         f_op[scene] += c_d * (DG_total[t] * 2.0 / 9 * coef - Scene_P_DG_813[1, t, scene].X)

    # print("三个场景运行成本：")
    # print(f_op)
    # print(delta.X)
    # print(mu.X)
    # print(Loss_load[0,0,0].X)
    # R_LOSS=[]
    # for k in range(k_U_lack):
    #     a=[]
    #     for j in range(2):
    #         b=[]
    #         for i in range(n):
    #             b.append(Loss_load[i,j,k].X)
    #         a.append(b)
    #     R_LOSS.append(a)
    # print(R_LOSS)
    # print
    # Ss=[]
    # for k in range(k_U_lack):
    #     a=[]
    #     a.append(sum(n__ac) - sum(R_LOSS[k][0]))
    #     a.append(sum(n__dc) - sum(R_LOSS[k][1]))
    #     Ss.append(a)
    # print(Ss)



    if m.status == gb.GRB.OPTIMAL:
        return m.objVal
    else:
        return 9e12