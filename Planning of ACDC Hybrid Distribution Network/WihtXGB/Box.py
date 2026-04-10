import sys
import os
import json
# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(project_root)
sys.path.insert(0, project_root)

import _13_nodes_distribution_network as H
import xgboost as xgb
from gurobi_ml import add_predictor_constr
import gurobipy as gb
import time

def Grid_planning(path_XGB1,path_XGB2):
    print("Grid Planning")
    XGB_model1 = xgb.Booster()
    XGB_model1.load_model(path_XGB1)
    XGB_model2 = xgb.Booster()
    XGB_model2.load_model(path_XGB2)
    print("Loaded!")
    m=gb.Model('Grid_planning')
    # 定义节点类型变量
    W={}
    for i in range(H.n):
        W[i]=m.addVar(vtype=gb.GRB.BINARY, name=f"W_{i}")
    # 定义支路投建变量
    U = {}
    for i, j in H.Branch:
        U[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"U_{i}_{j}")
    Gain = m.addVar(vtype=gb.GRB.CONTINUOUS, name="Gain")
    m.addConstr(Gain==1, name="Gain")
    fop =m.addVar(vtype=gb.GRB.CONTINUOUS, name="fop")
    Loss =m.addVar(vtype=gb.GRB.CONTINUOUS, name="Loss")
    for node in range(H.n):
        m.addConstr(
            sum(U[(i, j)] for i, j in H.Branch if i == node or j == node) <= H.L_max,
            name=f"degree_{node}")
        m.addConstr(
            sum(U[(i, j)] for i, j in H.Branch if i == node or j == node) >= H.L_min,
            name=f"degree_{node}"
        )
    F = {}
    for i, j in H.Branch:
        F[(i, j)] = m.addVar(lb=-len(H.nodes) + 1, ub=len(H.nodes) - 1, vtype=gb.GRB.CONTINUOUS, name=f"F_{i}_{j}")
    for node in H.nodes:
        if node == 0:
            m.addConstr(
                sum(F[(node, j)] for i, j in H.Branch if i == node) == len(H.nodes) - 1,
                name=f"flow_balance_{node}"
            )
        else:
            m.addConstr(
                sum(F[(i, node)] for i, j in H.Branch if j == node) - sum(
                    F[(node, j)] for i, j in H.Branch if i == node) == 1,
                name=f"flow_balance_{node}"
            )

    for i, j in H.Branch:
        m.addConstr(F[(i, j)] <= len(H.nodes) * U[(i, j)], name=f"flow_+cap_{i}_{j}")
        m.addConstr(F[(i, j)] >= -len(H.nodes) * U[(i, j)], name=f"flow_-cap_{i}_{j}")
    m.addConstr(
        sum(U[(i, j)] for i, j in H.Branch) == H.n - 1,
        name="edges_count"
    )

    L={}
    for i, j in H.Branch:
        L[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"L_{i}_{j}")
        m.addConstr(L[(i, j)] >= (W[i] - W[j]))
        m.addConstr(L[(i, j)] >= (W[j] - W[i]))
        m.addConstr(L[(i, j)] <= (W[i] + W[j]))
        m.addConstr(L[(i, j)] <= (2 - W[i] - W[j]))
        m.addConstr(L[(i, j)] <= U[(i, j)])

    input_vars = []
    for i in H.nodes:
        input_vars.append(W[i])
    for i, j in H.Branch:
        input_vars.append(U[(i, j)])
    input_vars.append(Gain)
    print('Add constraints')
    start_time = time.time()
    pred_constr1 = add_predictor_constr(m, XGB_model1, input_vars)
    pred_sales1 = pred_constr1.output
    m.addGenConstrExp(pred_sales1, fop, name="exp_constr1")
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"嵌入1耗时: {elapsed:.2f} 秒")
    start_time = time.time()
    pred_constr2 = add_predictor_constr(m, XGB_model1, input_vars)
    pred_sales2 = pred_constr2.output
    m.addGenConstrExp(pred_sales2, Loss, name="exp_constr2")
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"嵌入2耗时: {elapsed:.2f} 秒")
    print('Added successfully')

    # 线路建设成本
    # 换流器安装成本
    C_line = 0
    S_vsc=0
    S_c = 0

    for i, j in H.Branch:
        C_line += H.c_l[0] * H.Length[i][j] * U[(i, j)]
        S_vsc += H.S_vsc_ij*L[(i, j)]

    for i in H.nodes:
        S_c = S_c + H.S_c_load * (H.n__ac[i] * W[i] + H.n__dc[i] * (1 - W[i]))
        S_c = S_c + H.S_c_wind * (W[i] + 2 * (1 - W[i])) * H.n__wind[i]
        S_c = S_c + H.S_c_pv * H.n__pv[i]

    C_cvt = H.c_c * S_c + H.c_v * S_vsc

    C_invest = C_line * (pow(1+H.r,H.T_line)/(pow(1+H.r,H.T_line)-1)) + C_cvt * (pow(1+H.r,H.T_cvt)/(pow(1+H.r,H.T_line)-1))
    C_operation = fop * H.N_d

    m.setParam('OutputFlag', 0)
    m.setParam("Threads", 0)
    m.setObjective(C_invest + C_operation+Loss, gb.GRB.MINIMIZE)
    print('start optimization')
    start_time = time.time()
    m.optimize()
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"求解耗时: {elapsed:.2f} 秒")
    if m.status != gb.GRB.OPTIMAL:
        return m.status
    return m.ObjVal