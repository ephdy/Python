import xgboost as xgb
import numpy as np
import gurobipy as gb
import json
import copy
import _13_nodes_distribution_network as H
import time
from collections import defaultdict



def extract_leaves_from_tree_array(tree, n_features):
    """
    适用于 split_indices 格式
    """

    split_indices = tree["split_indices"]
    split_conditions = tree["split_conditions"]
    left_children = tree["left_children"]
    right_children = tree["right_children"]
    base_weights = tree["base_weights"]  # 叶子值

    leaves = []

    def dfs(nid, ff):
        # ========= 判断叶子 =========
        if left_children[nid] == -1:
            value = base_weights[nid]
            leaves.append((copy.deepcopy(ff), value))
            return

        # ========= 取 split =========
        f = split_indices[nid]

        thresh = split_conditions[nid]

        # ========= 左子树（≤）=========
        new_ff = copy.deepcopy(ff)
        new_ff[0].append(f)
        new_ff[1].append(0)
        dfs(left_children[nid], new_ff)

        # ========= 右子树（>）=========
        new_ff = copy.deepcopy(ff)
        new_ff[0].append(f)
        new_ff[1].append(1)
        dfs(right_children[nid], new_ff)

    # 初始特征
    features0 = np.full(n_features, -1.0)
    ff0=[[],[]]


    dfs(0, ff0)  # 根节点通常是0

    return leaves

def load_xgb_json(model_path):
    with open(model_path, "r") as f:
        model = json.load(f)
    return model

def extract_all_trees(model_json, n_features):
    trees = []

    for tree in model_json["learner"]["gradient_booster"]["model"]["trees"]:

        leaves = extract_leaves_from_tree_array(tree, n_features)
        trees.append(leaves)
    base_score=float(model_json["learner"]["learner_model_param"]["base_score"][1:-1])
    return trees,base_score

m=gb.Model('Grid_planning')
S={}
for i in range(H.n):
    S[i]=m.addVar(vtype=gb.GRB.BINARY, name=f"S_{i}")
m.addConstr(S[0]==0)
# 定义支路投建变量
U = {}
for i, j in H.Branch:
    U[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"U_{i}_{j}")
mu=m.addVar(vtype=gb.GRB.BINARY, name="mu")
eps=m.addVar(vtype=gb.GRB.BINARY, name="eps")


# 枚举四种组合的指示变量
z00 = m.addVar(vtype=gb.GRB.BINARY, name="z00")  # mu0=0, eps0=0
z01 = m.addVar(vtype=gb.GRB.BINARY, name="z01")  # mu0=0, eps0=1
z10 = m.addVar(vtype=gb.GRB.BINARY, name="z10")  # mu0=1, eps0=0
z11 = m.addVar(vtype=gb.GRB.BINARY, name="z11")  # mu0=1, eps0=1
z00.BranchPriority = 100
z01.BranchPriority = 100
z10.BranchPriority = 100
z11.BranchPriority = 100
# 只有一个组合被选中
m.addConstr(z00 + z01 + z10 + z11 == 1,name="z00")

# 关联原始二元变量
m.addConstr(mu == z10 + z11)
m.addConstr(eps == z01 + z11)
Q = m.addVar(vtype=gb.GRB.CONTINUOUS, name="Q")
m.addConstr(Q == 0 * z00 + 0.4762 * z01 + 0.4762 * z10 + 1 * z11)# 1.11 1.21 1.21 1.32 ///0 0 0.01 0.02

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
    L[(i, j)].BranchPriority = 100
    m.addConstr(L[(i, j)] >= (S[i] - S[j]),name=f"L1_{i}_{j}")
    m.addConstr(L[(i, j)] >= (S[j] - S[i]), name=f"L2_{i}_{j}")
    m.addConstr(L[(i, j)] <= (S[i] + S[j]),name=f"L3_{i}_{j}")
    m.addConstr(L[(i, j)] <= (2 - S[i] - S[j]),name=f"L4_{i}_{j}")
    # m.addConstr(L[(i, j)] <= U[(i, j)])

input_vars = []
for i in H.nodes:
    input_vars.append(S[i])
for i, j in H.Branch:
    input_vars.append(U[(i, j)])
input_vars.append(mu)
input_vars.append(eps)
# for i in range(len(input_vars)):
#     m.addConstr(input_vars[i]==d[i])

# fop=m.addVar(lb=-gb.GRB.INFINITY,name="fop")
# Loss=m.addVar(lb=-gb.GRB.INFINITY,name="Loss")
# fop=m.addVar(name="fop")
# Loss=m.addVar(name="Loss")
V4=m.addVar(name="V4")

def load_allone(m,V4):
    start_time = time.time()
    model_json1 = load_xgb_json("m_fop.json")
    model_json2 = load_xgb_json("m_Loss.json")

    n_features = 48

    trees1, base_score1 = extract_all_trees(model_json1, n_features)
    trees2, base_score2 = extract_all_trees(model_json2, n_features)
    y_trees1 = []
    y_trees2 = []


    # z = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    # ================== 🔥 合并树 ==================
    trees_all = []
    weight_all = []

    # 模型1
    for t in trees1:
        trees_all.append(t)
        weight_all.append(1//(43720-4122))

    # 模型2
    for t in trees2:
        trees_all.append(t)
        weight_all.append(1)

    base_total = (base_score1-4122)/(43720-4122) + base_score2

    # ================== z变量 ==================
    z = {}

    V4_expr = 0

    for t, leaves in enumerate(trees_all):

        Len = len(leaves)

        z[t] = {}

        # 创建 z
        for l in range(Len):
            z[t][l] = m.addVar(lb=0, ub=1, vtype=gb.GRB.BINARY,
                               name=f"z_{t}_{l}")

        # 每棵树选一个叶子
        m.addConstr(gb.quicksum(z[t].values()) == 1,
                    name=f"sum_tree_{t}")

        # 输出直接累计（🔥 没有 y 变量）
        for l in range(Len):
            leaf_val = leaves[l][-1]
            V4_expr += weight_all[t] * leaf_val * z[t][l]

    # ================== 统一目标 ==================
    m.addConstr(V4 == V4_expr + base_total)
    # ================路径约束==================================
    FC= {i: {0: [], 1: []} for i in range(48)}

    for t, leaves in enumerate(trees_all):
        for l in range(len(leaves)):
            path_features = leaves[l][0][0]
            path_values = leaves[l][0][1]

            for k in range(len(path_features)):
                f = path_features[k]
                v = path_values[k]
                FC[f][v].append(z[t][l])



    for f in range(len(FC.keys())):
        if f==0:
            continue
        m.addGenConstrIndicator(input_vars[f], 0, gb.quicksum(FC[f][1]), gb.GRB.EQUAL, 0, name=f"indicator{f}_0")
        m.addGenConstrIndicator(input_vars[f], 1, gb.quicksum(FC[f][0]), gb.GRB.EQUAL, 0, name=f"indicator{f}_1")


    # ================路径约束==================================
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"嵌入1耗时: {elapsed:.2f} 秒")
    return V4

load_allone(m,V4)





m.update()
print(f"变量数: {m.numVars}")
print(f"约束数: {m.numConstrs}")
print(f"非零元素: {m.numNZs}")



LU={}
for i, j in H.Branch:
    LU[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"LU_{i}_{j}")
    LU[(i, j)].BranchPriority = 100
    m.addConstr(LU[(i, j)] <= L[(i, j)],name=f"LU1_{i}_{j}")
    m.addConstr(LU[(i, j)] <= U[(i, j)],name=f"LU2_{i}_{j}")
    m.addConstr(LU[(i, j)] >= L[(i, j)] + U[(i, j)] - 1 ,name=f"LU3_{i}_{j}")

# 线路建设成本
# 换流器安装成本
C_line = 0
S_vsc=0
S_c = 0

for i, j in H.Branch:
    C_line += H.c_l[0] * H.Length[i][j] * U[(i, j)]
    S_vsc += H.S_vsc_ij*LU[(i, j)]

for i in H.nodes:
    S_c = S_c + H.S_c_load * (H.n__ac[i] * S[i] + H.n__dc[i] * (1 - S[i]))
    S_c = S_c + H.S_c_wind * (S[i] + 2 * (1 - S[i])) * H.n__wind[i]
    S_c = S_c + H.S_c_pv * H.n__pv[i]

C_cvt = H.c_c * S_c + H.c_v * S_vsc

C_invest0 = C_line * (H.r * (pow(1+H.r,H.T_line)/(pow(1+H.r,H.T_line)-1)) +H.beta_line)+ C_cvt * (H.r *(pow(1+H.r,H.T_cvt)/(pow(1+H.r,H.T_cvt)-1)) + H.beta_cvt)
C_invest=(C_invest0-5485588)/(20991965-5485588)
# C_operation = fop * H.N_d



m.setObjective(C_invest-Q+V4+1, gb.GRB.MINIMIZE)
start_time = time.time()

# warms=[0.0, -0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0]
# for i in range(48):
#     input_vars[i].Start=warms[i]

# 设置调优参数
# m.setParam('TimeLimit', 600)        # 单次求解时间限制
# m.setParam('TuneTimeLimit', 3600)   # 调优总时间限制
# m.setParam('TuneCriterion', 3)      # 调优准则：最大化下界
#
# # 运行调优
# m.tune()
#
# # 获取最优参数并应用到模型
# for i in range(m.getParamInfo('TuneResults')[2]):
#     m.getTuneResult(i)
#     # 使用调优后的参数重新求解
#     m.optimize()
m.write("V4_model.mps")
for i in range(len(input_vars)):
    input_vars[i].BranchPriority = 10000000000
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
print(V4.X)
# print(pred_sales1.X)
print(m.ObjVal)
res=[]
for i in range(len(input_vars)):
    res.append(input_vars[i].X)
print(res)
if m.Status == gb.GRB.OPTIMAL:
    for i, var in enumerate(input_vars):
        print(f"input_vars[{i}] = {var.X}")