import xgboost as xgb
import numpy as np
import gurobipy as gb
import json
import copy
import _13_nodes_distribution_network as H
import time
from collections import defaultdict



m=gb.Model('Grid_planning')
S={}
for i in range(H.n):
    S[i]=m.addVar(vtype=gb.GRB.BINARY, name=f"S_{i}")
m.addConstr(S[0]==0)
# 定义支路投建变量
U = {}
for i, j in H.Branch:
    U[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"U_{i}_{j}")




#===============================规划约束=================================================
for node in range(H.n):
        m.addConstr(
            sum(U[(i, j)] for i, j in H.Branch if i == node or j == node) <= H.L_max,
            name=f"degree_less_{node}")
        m.addConstr(
            sum(U[(i, j)] for i, j in H.Branch if i == node or j == node) >= H.L_min,
            name=f"degree_more_{node}"
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
# m.addConstr(
#     sum(U[(i, j)] for i, j in H.Branch) == H.n - 1,
#     name="edges_count"
# )
L={}
for i, j in H.Branch:
    L[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"L_{i}_{j}")
    m.addConstr(L[(i, j)] >= (S[i] - S[j]),name=f"L1_{i}_{j}")
    m.addConstr(L[(i, j)] >= (S[j] - S[i]), name=f"L2_{i}_{j}")
    m.addConstr(L[(i, j)] <= (S[i] + S[j]),name=f"L3_{i}_{j}")
    m.addConstr(L[(i, j)] <= (2 - S[i] - S[j]),name=f"L4_{i}_{j}")

input_vars = []
for i in H.nodes:
    input_vars.append(S[i])
for i, j in H.Branch:
    input_vars.append(U[(i, j)])
# for i in range(len(input_vars)):
#     m.addConstr(input_vars[i]==d[i])


m.update()
print(f"变量数: {m.numVars}")
print(f"约束数: {m.numConstrs}")
print(f"非零元素: {m.numNZs}")



LU={}
for i, j in H.Branch:
    LU[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"LU_{i}_{j}")
    m.addConstr(LU[(i, j)] <= L[(i, j)],name=f"LU1_{i}_{j}")
    m.addConstr(LU[(i, j)] <= U[(i, j)],name=f"LU2_{i}_{j}")
    m.addConstr(LU[(i, j)] >= L[(i, j)] + U[(i, j)] - 1 ,name=f"LU3_{i}_{j}")

# 线路建设成本
# 换流器安装成本
C_line = 0
S_vsc=0
S_c = 0

for i, j in H.Branch:
    C_line += H.c_l[1] * H.Length[i][j] * U[(i, j)]
    S_vsc += H.S_vsc_ij*LU[(i, j)]

for i in H.nodes:
    S_c = S_c + H.S_c_load * (H.n__ac[i] * S[i] + H.n__dc[i] * (1 - S[i]))
    S_c = S_c + H.S_c_wind * (S[i] + 2 * (1 - S[i])) * H.n__wind[i]
    S_c = S_c + H.S_c_pv * H.n__pv[i]

C_cvt = H.c_c * S_c + H.c_v * S_vsc

C_invest = C_line * (H.r * (pow(1+H.r,H.T_line)/(pow(1+H.r,H.T_line)-1)) +H.beta_line)+ C_cvt * (H.r *(pow(1+H.r,H.T_cvt)/(pow(1+H.r,H.T_cvt)-1)) + H.beta_cvt)

m.setObjective(C_invest, gb.GRB.MAXIMIZE)
start_time = time.time()

for i in range(len(input_vars)):
    input_vars[i].BranchPriority = 100000000
# m.setParam("Threads", 4)
m.setParam("Threads", 0)
m.optimize()

if m.Status == gb.GRB.INFEASIBLE:
    print("模型不可行，正在计算IIS...")

    # 1. 计算IIS
    m.computeIIS()
    m.write("model_iis.ilp")

if m.status != gb.GRB.OPTIMAL:
    print(m.status)
elapsed = time.time() - start_time
print(f"求解耗时: {elapsed:.2f} 秒")
# print(fop.X)
# print(Loss.X)
# print(pred_sales1.X)
print(m.ObjVal)
res=[]
for i in range(len(input_vars)):
    res.append(round(input_vars[i].Xn))
print(res)
# if m.Status == gb.GRB.OPTIMAL:
#     for i, var in enumerate(input_vars):
#         print(f"input_vars[{i}] = {var.X}")