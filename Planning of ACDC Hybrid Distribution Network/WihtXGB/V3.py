import xgboost as xgb
import numpy as np
import gurobipy as gb
import json

import _13_nodes_distribution_network as H
import time


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

    def dfs(nid, lower, upper):
        # ========= 判断叶子 =========
        if left_children[nid] == -1:
            value = base_weights[nid]
            leaves.append((lower.copy(), upper.copy(), value))
            return

        # ========= 取 split =========
        f = split_indices[nid]
        thresh = split_conditions[nid]

        # ========= 左子树（≤）=========
        new_upper = upper.copy()
        new_upper[f] = min(new_upper[f], thresh-0.005)
        dfs(left_children[nid], lower, new_upper)

        # ========= 右子树（>）=========
        new_lower = lower.copy()
        new_lower[f] = max(new_lower[f], thresh)
        dfs(right_children[nid], new_lower, upper)

    # 初始区间
    lower0 = np.full(n_features, 0.0)
    upper0 = np.full(n_features,  2.0)

    dfs(0, lower0, upper0)  # 根节点通常是0

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
    print(base_score)
    return trees,base_score


# 2. 准备输入数据
# 输入格式可以是: numpy数组、列表、pandas DataFrame
# 注意: 特征数量必须与训练时一致，且顺序相同
dd=[[0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,1,1,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,1,0,1,1,0,0,0,0.2,18991.45572],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,1,1,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,1,0,1,1,0,0,0,0.1,14566.06733],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,1,1,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,1,0,1,1,0,0,0.1,0.2,17380.53408],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,1,1,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,1,0,1,1,0,0,0.1,0.1,13026.53298],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,1,0,0,0,1,0,0,1,1,1,0,0,1,0,0,0,0,1,0,0,1,1,0,0,0,0,1,0,1,0,0.2,23909.87817],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,1,0,0,0,1,0,0,1,1,1,0,0,1,0,0,0,0,1,0,0,1,1,0,0,0,0,1,0,1,0,0.1,23878.16072],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,1,0,0,0,1,0,0,1,1,1,0,0,1,0,0,0,0,1,0,0,1,1,0,0,0,0,1,0,1,0.1,0.2,24914.70745],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,1,0,0,0,1,0,0,1,1,1,0,0,1,0,0,0,0,1,0,0,1,1,0,0,0,0,1,0,1,0.1,0.1,25463.91952],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,0,1,0,1,1,1,1,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,1,0,1,0,0.2,26017.45459],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,0,1,0,1,1,1,1,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,1,0,1,0,0.1,26701.34001],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,0,1,0,1,1,1,1,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,1,0,1,0.1,0.2,28811.68836],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,0,1,0,1,1,1,1,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,1,0,1,0.1,0.1,30693.7746],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,0,0,1,0,1,0,0,0,1,0,1,0,0,1,0,0,0,0,1,0,1,1,1,1,1,0,0,0,1,0,0.2,15645.74726],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,0,0,1,0,1,0,0,0,1,0,1,0,0,1,0,0,0,0,1,0,1,1,1,1,1,0,0,0,1,0,0.1,12278.39373],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,0,0,1,0,1,0,0,0,1,0,1,0,0,1,0,0,0,0,1,0,1,1,1,1,1,0,0,0,1,0.1,0.2,12128.06269],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,0,0,0,1,1,0,1,1,1,1,1,1,0,0,0,0,0,0,1,0,0,0,1,0,0,1,0,0,1,1,1,0,0.1,12780.18951],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,0,0,0,1,1,0,1,1,1,1,1,1,0,0,0,0,0,0,1,0,0,0,1,0,0,1,0,0,1,1,1,0.1,0.2,12561.27643],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,0,0,0,1,1,0,1,1,1,1,1,1,0,0,0,0,0,0,1,0,0,0,1,0,0,1,0,0,1,1,1,0.1,0.1,7715.064653],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,0,0,1,1,0,0,1,1,0,1,1,1,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0.1,12511.94398],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,0,0,1,1,0,0,1,1,0,1,1,1,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,0.1,0.2,12266.88701],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,0,0,1,1,0,0,1,1,0,1,1,1,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,0.1,0.1,7464.98374],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,0,0,1,0,0,1,1,1,1,0,1,0,0,0,0,1,0,1,1,1,0,1,1,0,0.1,12937.54082],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,0,0,1,0,0,1,1,1,1,0,1,0,0,0,0,1,0,1,1,1,0,1,1,0.1,0.2,12714.8584],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,0,0,1,0,0,1,1,1,1,0,1,0,0,0,0,1,0,1,1,1,0,1,1,0.1,0.1,5871.2967],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,0,1,0,1,1,0,1,1,1,0,0,0,0,0,0,1,0,1,0,0,1,1,0,0,0,0,1,1,1,1,0,0.1,12231.15918],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,0,1,0,1,1,0,1,1,1,0,0,0,0,0,0,1,0,1,0,0,1,1,0,0,0,0,1,1,1,1,0.1,0.2,12347.07511],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,0,1,0,1,1,0,1,1,1,0,0,0,0,0,0,1,0,1,0,0,1,1,0,0,0,0,1,1,1,1,0.1,0.1,7820.852054],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,0,0,1,0,0,0,1,0,0,1,1,1,0,1,1,0,1,0,0,0,1,1,0,1,0,1,0,0,1,0,1,0,0.2,15788.94184],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,0,0,1,0,0,0,1,0,0,1,1,1,0,1,1,0,1,0,0,0,1,1,0,1,0,1,0,0,1,0,1,0,0.1,12364.7178],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,0,0,1,0,0,0,1,0,0,1,1,1,0,1,1,0,1,0,0,0,1,1,0,1,0,1,0,0,1,0,1,0.1,0.2,12147.57713],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,0,0,1,0,0,0,1,0,0,1,1,1,0,1,1,0,1,0,0,0,1,1,0,1,0,1,0,0,1,0,1,0.1,0.1,7624.041636],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,0,0,1,0,0,0,1,0,0,1,0,0,0,0,1,1,1,0,0,0,0,1,0,1,1,1,0,1,1,0,0.2,15742.87458],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,0,0,1,0,0,0,1,0,0,1,0,0,0,0,1,1,1,0,0,0,0,1,0,1,1,1,0,1,1,0.1,0.2,12167.81441],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,1,0,0,1,0,0,0,1,0,0,1,0,0,0,0,1,1,1,0,0,0,0,1,0,1,1,1,0,1,1,0.1,0.1,7730.954524],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,0,1,0,1,0,0,0,0,0,1,1,0,1,1,0,1,0,0,1,1,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0.1,13078.20754],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,0,1,0,1,0,0,0,0,0,1,1,0,1,1,0,1,0,0,1,1,0,1,1,0,0,0,0,0,0,1,1,0,0,0.1,0.2,12991.55629],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,0,1,0,1,0,0,0,0,0,1,1,0,1,1,0,1,0,0,1,1,0,1,1,0,0,0,0,0,0,1,1,0,0,0.1,0.1,8116.525215],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,0,1,0,1,0,1,0,1,0,0,1,0,0,0,0,1,1,1,0,0,1,0,1,0,1,1,0,0,0,1,0,0.2,15580.21478],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,0,1,0,1,0,1,0,1,0,0,1,0,0,0,0,1,1,1,0,0,1,0,1,0,1,1,0,0,0,1,0,0.1,12236.40576],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,1,1,1,0,1,0,1,0,1,0,1,0,0,1,0,0,0,0,1,1,1,0,0,1,0,1,0,1,1,0,0,0,1,0.1,0.2,12008.28778],
    [0,0,0,1,0,0,1,1,0,1,0,0,1,0,0,1,1,0,1,0,0,0,0,0,0,1,0,1,0,0,1,1,1,0,0,0,1,0,0,0,1,0,1,0,1,1,0,0.1,13434.52274]]

d=[row[:-1] for row in dd][0]
m=gb.Model('Grid_planning')
S={}
for i in range(H.n):
    S[i]=m.addVar(vtype=gb.GRB.BINARY, name=f"S_{i}")
m.addConstr(S[0]==0)
# 定义支路投建变量
U = {}
for i, j in H.Branch:
    U[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"U_{i}_{j}")
mu0=m.addVar(vtype=gb.GRB.BINARY, name="mu0")
eps0=m.addVar(vtype=gb.GRB.BINARY, name="eps0")
mu=m.addVar(vtype=gb.GRB.CONTINUOUS, name="mu")
eps=m.addVar(vtype=gb.GRB.CONTINUOUS, name="eps")
m.addConstr(mu==0.1*mu0)
m.addConstr(eps==eps0*0.1+0.1)

#===============================规划约束=================================================
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
# m.addConstr(
#     sum(U[(i, j)] for i, j in H.Branch) == H.n - 1,
#     name="edges_count"
# )
L={}
for i, j in H.Branch:
    L[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"L_{i}_{j}")
    m.addConstr(L[(i, j)] >= (S[i] - S[j]))
    m.addConstr(L[(i, j)] >= (S[j] - S[i]))
    m.addConstr(L[(i, j)] <= (S[i] + S[j]))
    m.addConstr(L[(i, j)] <= (2 - S[i] - S[j]))
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

fop=m.addVar()


def load_biggs(m,fop):
    start_time = time.time()
    model_json1 = load_xgb_json("../XGBoost_main/model1.json")
    # model_json2 = load_xgb_json("model2.json")

    n_features = 48

    trees1, base_score = extract_all_trees(model_json1, n_features)
    # trees2 = extract_all_trees(model_json1, n_features)
    # y_total1 = m.addVar(lb=-gb.GRB.INFINITY, name="y1")
    # y_total2 = m.addVar(lb=-gb.GRB.INFINITY, name="y2")
    y_trees1 = []
    # y_trees2 = []

    # ========= 每棵树 =========
    for t, leaves in enumerate(trees1):

        Len = len(leaves)

        # z变量
        z = m.addVars(Len, vtype=gb.GRB.BINARY, name=f"z_{t}")
        z.BranchPriority = 20

        # 输出
        y = m.addVar(lb=-gb.GRB.INFINITY, name=f"y_{t}")
        y_trees1.append(y)

        # ========= 1. 选择一个叶子 =========
        m.addConstr(z.sum() == 1)

        # ========= 2. 区间约束（核心tight约束）=========
        for i in range(n_features):
            m.addConstr(
                sum((leaves[l][1][i]) * z[l] for l in range(Len)) >= input_vars[i]
            )

            m.addConstr(
                sum(leaves[l][0][i] * z[l] for l in range(Len)) <= input_vars[i]
            )

        # ========= 3. 输出 =========
        m.addConstr(
            y == sum(leaves[l][2] * z[l] for l in range(Len))
        )

    # ========= 4. 汇总 =========
    m.addConstr(fop == gb.quicksum(y_trees1) + base_score)

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"嵌入1耗时: {elapsed:.2f} 秒")
    return fop

load_biggs(m,fop)
m.update()
print(f"变量数: {m.numVars}")
print(f"约束数: {m.numConstrs}")
print(f"非零元素: {m.numNZs}")


LU={}
for i, j in H.Branch:
    LU[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"LU_{i}_{j}")
    m.addConstr(LU[(i, j)] <= L[(i, j)])
    m.addConstr(LU[(i, j)] <= U[(i, j)])
    m.addConstr(LU[(i, j)] <= L[(i, j)] + U[(i, j)] - 1 )


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

C_invest = C_line * (H.r * (pow(1+H.r,H.T_line)/(pow(1+H.r,H.T_line)-1)) +H.beta_line)+ C_cvt * (H.r *(pow(1+H.r,H.T_cvt)/(pow(1+H.r,H.T_cvt)-1)) + H.beta_cvt)
C_operation = fop * H.N_d

for i in range(len(input_vars)):
    input_vars[i].BranchPriority = 100




m.setObjective(C_operation+C_invest, gb.GRB.MINIMIZE)
start_time = time.time()

# # 设置调优参数
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

m.optimize()










if m.status != gb.GRB.OPTIMAL:
    print(m.status)
elapsed = time.time() - start_time
print(f"求解耗时: {elapsed:.2f} 秒")
print(fop.X)
print(m.ObjVal)
res=[]
for i in range(len(input_vars)):
    res.append(input_vars[i].X)
print(res)
if m.Status == gb.GRB.OPTIMAL:
    for i, var in enumerate(input_vars):
        print(f"input_vars[{i}] = {var.X}")