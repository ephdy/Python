import json
import numpy as np

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
        new_upper[f] = min(new_upper[f], thresh)
        dfs(left_children[nid], lower, new_upper)

        # ========= 右子树（>）=========
        new_lower = lower.copy()
        new_lower[f] = max(new_lower[f], thresh)
        dfs(right_children[nid], new_lower, upper)

    # 初始区间
    lower0 = np.full(n_features, 0)
    upper0 = np.full(n_features,  2)

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

    return trees

from gurobipy import Model, GRB

def build_gurobi_model(trees, n_features):
    model = Model()

    # ========= 决策变量 =========
    w = model.addVars(n_features, lb=-GRB.INFINITY, name="w")

    y_total = model.addVar(lb=-GRB.INFINITY, name="y")

    y_trees = []

    # ========= 每棵树 =========
    for t, leaves in enumerate(trees):

        L = len(leaves)

        # z变量
        z = model.addVars(L, vtype=GRB.BINARY, name=f"z_{t}")

        # 输出
        y_t = model.addVar(lb=-GRB.INFINITY, name=f"y_{t}")
        y_trees.append(y_t)

        # ========= 1. 选择一个叶子 =========
        model.addConstr(z.sum() == 1)

        # ========= 2. 区间约束（核心tight约束）=========
        for i in range(n_features):

            model.addConstr(
                sum(leaves[l][1][i] * z[l] for l in range(L)) >= w[i]
            )

            model.addConstr(
                sum(leaves[l][0][i] * z[l] for l in range(L)) <= w[i]
            )

        # ========= 3. 输出 =========
        model.addConstr(
            y_t == sum(leaves[l][2] * z[l] for l in range(L))
        )

    # ========= 4. 汇总 =========
    model.addConstr(y_total == sum(y_trees))

    return model, w, y_total


model_json = load_xgb_json("model3.json")

n_features = 13+33+1

trees = extract_all_trees(model_json, n_features)
print(trees)
model, w, y_total = build_gurobi_model(trees, n_features)
model, w, y = build_gurobi_model(trees, n_features)

# 示例目标
# model.setObjective(y, GRB.MAXIMIZE)
#
# model.optimize()