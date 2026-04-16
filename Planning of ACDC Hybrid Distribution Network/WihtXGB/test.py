import time
from traceback import format_exc

import gurobipy as gb
import xgboost as xgb
import _13_nodes_distribution_network as H
from gurobi_ml import add_predictor_constr

# dd=[0,0,1,0,0,0,0,0,0,1,1,0,1,0,1,0,1,1,0,1,1,0,0,0,0,0,1,1,0,0,0,1,0,0,0,1,1,0,1,1,1,1,0,0,0,0,1.08]
dd=[0,0,0,1,0,0,1,1,0,1,0,0,1,1,0,1,1,1,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,1,0,1,1,0,0,0,0.2]
print(len(dd))
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
    mu=m.addVar(vtype=gb.GRB.CONTINUOUS, name="mu")
    eps=m.addVar(vtype=gb.GRB.CONTINUOUS, name="eps")

    # m.addConstr(Gain==1, name="Gain")
    fop =m.addVar(vtype=gb.GRB.CONTINUOUS, name="fop")
    Loss =m.addVar(vtype=gb.GRB.CONTINUOUS, name="Loss")
    # for node in range(H.n):
    #     m.addConstr(
    #         sum(U[(i, j)] for i, j in H.Branch if i == node or j == node) <= H.L_max,
    #         name=f"degree_{node}")
    #     m.addConstr(
    #         sum(U[(i, j)] for i, j in H.Branch if i == node or j == node) >= H.L_min,
    #         name=f"degree_{node}"
    #     )
    # F = {}
    # for i, j in H.Branch:
    #     F[(i, j)] = m.addVar(lb=-len(H.nodes) + 1, ub=len(H.nodes) - 1, vtype=gb.GRB.CONTINUOUS, name=f"F_{i}_{j}")
    # for node in H.nodes:
    #     if node == 0:
    #         m.addConstr(
    #             sum(F[(node, j)] for i, j in H.Branch if i == node) == len(H.nodes) - 1,
    #             name=f"flow_balance_{node}"
    #         )
    #     else:
    #         m.addConstr(
    #             sum(F[(i, node)] for i, j in H.Branch if j == node) - sum(
    #                 F[(node, j)] for i, j in H.Branch if i == node) == 1,
    #             name=f"flow_balance_{node}"
    #         )
    #
    # for i, j in H.Branch:
    #     m.addConstr(F[(i, j)] <= len(H.nodes) * U[(i, j)], name=f"flow_+cap_{i}_{j}")
    #     m.addConstr(F[(i, j)] >= -len(H.nodes) * U[(i, j)], name=f"flow_-cap_{i}_{j}")
    # m.addConstr(
    #     sum(U[(i, j)] for i, j in H.Branch) == H.n - 1,
    #     name="edges_count"
    # )

    # L={}
    # for i, j in H.Branch:
    #     L[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"L_{i}_{j}")
    #     m.addConstr(L[(i, j)] >= (W[i] - W[j]))
    #     m.addConstr(L[(i, j)] >= (W[j] - W[i]))
    #     m.addConstr(L[(i, j)] <= (W[i] + W[j]))
    #     m.addConstr(L[(i, j)] <= (2 - W[i] - W[j]))
    #     m.addConstr(L[(i, j)] <= U[(i, j)])

    input_vars = []
    for i in H.nodes:
        input_vars.append(W[i])
    for i, j in H.Branch:
        input_vars.append(U[(i, j)])
    input_vars.append(mu)
    input_vars.append(eps)
    for i in range(len(input_vars)):
        m.addConstr(input_vars[i]==dd[i])
    # =================================================================
    print('Add constraints')
    start_time = time.time()
    pred_constr1 = add_predictor_constr(m, XGB_model1, input_vars)
    pred_sales1 = pred_constr1.output

    # m.addGenConstrExp(pred_sales1, fop, name="exp_constr1")
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"嵌入1耗时: {elapsed:.2f} 秒")
    # m.update()
    # print(f"变量数: {m.numVars}")
    # print(f"约束数: {m.numConstrs}")
    # print(f"非零元素: {m.numNZs}")
    # start_time = time.time()
    # pred_constr2 = add_predictor_constr(m, XGB_model1, input_vars)
    # pred_sales2 = pred_constr2.output
    # m.addGenConstrExp(pred_sales2, Loss, name="exp_constr2")
    # end_time = time.time()
    # elapsed = end_time - start_time
    # print(f"嵌入2耗时: {elapsed:.2f} 秒")
    # print('Added successfully')
    # m.update()
    # print(f"变量数: {m.numVars}")
    # print(f"约束数: {m.numConstrs}")
    # print(f"非零元素: {m.numNZs}")
    # =================================================================
    # start_time = time.time()
    # model_json1 = load_xgb_json("model1.json")
    # model_json2 = load_xgb_json("model2.json")
    #
    # n_features = 13 + 33 + 1
    #
    # trees1 = extract_all_trees(model_json1, n_features)
    # trees2 = extract_all_trees(model_json1, n_features)
    # y_total1 = m.addVar(lb=-gb.GRB.INFINITY, name="y1")
    # y_total2 = m.addVar(lb=-gb.GRB.INFINITY, name="y2")
    # y_trees1 = []
    # y_trees2 = []
    # # ========= 每棵树 =========
    # for t, leaves in enumerate(trees1):
    #
    #     Len = len(leaves)
    #
    #     # z变量
    #     z = m.addVars(Len, vtype=gb.GRB.BINARY, name=f"z_{t}")
    #
    #     # 输出
    #     y_t = m.addVar(lb=-gb.GRB.INFINITY, name=f"y_{t}")
    #     y_trees1.append(y_t)
    #
    #     # ========= 1. 选择一个叶子 =========
    #     m.addConstr(z.sum() == 1)
    #
    #     # ========= 2. 区间约束（核心tight约束）=========
    #     for i in range(n_features):
    #         m.addConstr(
    #             sum(leaves[l][1][i] * z[l] for l in range(Len))-1e-4 >= input_vars[i]
    #         )
    #
    #         m.addConstr(
    #             sum(leaves[l][0][i] * z[l] for l in range(Len)) <= input_vars[i]
    #         )
    #
    #     # ========= 3. 输出 =========
    #     m.addConstr(
    #         y_t == sum(leaves[l][2] * z[l] for l in range(Len))
    #     )
    #
    # # ========= 4. 汇总 =========
    # m.addConstr(y_total1 == sum(y_trees1))
    # m.addGenConstrExp(y_total1, fop, name="exp_constr1")
    # end_time = time.time()
    # elapsed = end_time - start_time
    # print(f"嵌入1耗时: {elapsed:.2f} 秒")
    #
    # m.update()
    # print(f"变量数: {m.numVars}")
    # print(f"约束数: {m.numConstrs}")
    # print(f"非零元素: {m.numNZs}")
    #
    # # ========= 每棵树 =========
    # for t, leaves in enumerate(trees2):
    #
    #     Len = len(leaves)
    #
    #     # z变量
    #     z = m.addVars(Len, vtype=gb.GRB.BINARY, name=f"z2_{t}")
    #
    #     # 输出
    #     y_t = m.addVar(lb=-gb.GRB.INFINITY, name=f"y2_{t}")
    #     y_trees2.append(y_t)
    #
    #     # ========= 1. 选择一个叶子 =========
    #     m.addConstr(z.sum() == 1)
    #
    #     # ========= 2. 区间约束（核心tight约束）=========
    #     for i in range(n_features):
    #         m.addConstr(
    #             sum(leaves[l][1][i] * z[l] for l in range(Len)) - 1e-4 >= input_vars[i]
    #         )
    #
    #         m.addConstr(
    #             sum(leaves[l][0][i] * z[l] for l in range(Len)) <= input_vars[i]
    #         )
    #
    #     # ========= 3. 输出 =========
    #     m.addConstr(
    #         y_t == sum(leaves[l][2] * z[l] for l in range(Len))
    #     )
    #
    # # ========= 4. 汇总 =========
    # m.addConstr(y_total2 == sum(y_trees2))
    # m.addGenConstrExp(y_total2, Loss, name="exp_constr2")
    # end_time = time.time()
    # elapsed = end_time - start_time
    # print(f"嵌入2耗时: {elapsed:.2f} 秒")
    # #
    # #
    # #
    # #
    # #
    # #
    # #
    # #
    # #
    # #
    # m.update()
    # print(f"变量数: {m.numVars}")
    # print(f"约束数: {m.numConstrs}")
    # print(f"非零元素: {m.numNZs}")









    # 线路建设成本
    # 换流器安装成本
    # C_line = 0
    # S_vsc=0
    # S_c = 0
    #
    # for i, j in H.Branch:
    #     C_line += H.c_l[0] * H.Length[i][j] * U[(i, j)]
    #     S_vsc += H.S_vsc_ij*L[(i, j)]
    #
    # for i in H.nodes:
    #     S_c = S_c + H.S_c_load * (H.n__ac[i] * W[i] + H.n__dc[i] * (1 - W[i]))
    #     S_c = S_c + H.S_c_wind * (W[i] + 2 * (1 - W[i])) * H.n__wind[i]
    #     S_c = S_c + H.S_c_pv * H.n__pv[i]
    #
    # C_cvt = H.c_c * S_c + H.c_v * S_vsc
    #
    # C_invest = C_line * (pow(1+H.r,H.T_line)/(pow(1+H.r,H.T_line)-1)) + C_cvt * (pow(1+H.r,H.T_cvt)/(pow(1+H.r,H.T_line)-1))
    # C_operation = fop * H.N_d

    # m.setParam('OutputFlag', 0)
    m.setParam("Threads", 0)
    m.setObjective(2, gb.GRB.MINIMIZE)
    # m.setObjective(C_invest + C_operation + Loss * 1e8, gb.GRB.MINIMIZE)
    print('start optimization')
    start_time = time.time()
    m.optimize()
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"求解耗时: {elapsed:.2f} 秒")

    if m.status != gb.GRB.OPTIMAL:
        return m.status
    print(fop.X)
    print(pred_sales1.X)
    return m.ObjVal
if __name__ == "__main__":
    a=Grid_planning('../XGBoost_main/model3.json','../XGBoost_main/model2.json')
    print(a)