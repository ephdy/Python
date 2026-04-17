import xgboost as xgb
import numpy as np
import gurobipy as gb
from gurobi_ml import add_predictor_constr
import _13_nodes_distribution_network as H
import time
# 1. 加载已训练好的模型
# 支持 .json, .ubj, .bst 等格式 [citation:2][citation:9]
model1 = xgb.Booster()
model1.load_model('../XGBoost_main/model1_m.json')  # 替换成你的模型路径
model2 = xgb.Booster()
model2.load_model('../XGBoost_main/model2_m.json')  # 替换成你的模型路径
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
input_data = np.array([[row[:-1] for row in dd][0]])
print(input_data)# 示例: 一行5个特征

# 3. 执行预测
# 对于回归任务: 直接输出预测值
# 对于二分类任务: 默认输出概率值 (0到1之间) [citation:6]
prediction = model1.predict(xgb.DMatrix(input_data))

# 4. 打印输出
print(f"预测结果: {prediction}")

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
m.addConstr(mu==0.1*mu0,name="mu021")
m.addConstr(eps==eps0*0.1+0.1,name="eps021")

# 枚举四种组合的指示变量
z00 = m.addVar(vtype=gb.GRB.BINARY, name="z00")  # mu0=0, eps0=0
z01 = m.addVar(vtype=gb.GRB.BINARY, name="z01")  # mu0=0, eps0=1
z10 = m.addVar(vtype=gb.GRB.BINARY, name="z10")  # mu0=1, eps0=0
z11 = m.addVar(vtype=gb.GRB.BINARY, name="z11")  # mu0=1, eps0=1

# 只有一个组合被选中
m.addConstr(z00 + z01 + z10 + z11 == 1,name="z00")

# 关联原始二元变量
m.addConstr(mu0 == z10 + z11)
m.addConstr(eps0 == z01 + z11)
Gain = m.addVar(vtype=gb.GRB.CONTINUOUS, name="Gain")
m.addConstr(Gain == 0.9 * z00 + 0.8 * z01 + 0.99 * z10 + 0.88 * z11)

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
m.addConstr(
    sum(U[(i, j)] for i, j in H.Branch) == H.n - 1,
    name="edges_count"
)
L={}
for i, j in H.Branch:
    L[(i, j)] = m.addVar(vtype=gb.GRB.BINARY, name=f"L_{i}_{j}")
    m.addConstr(L[(i, j)] >= (S[i] - S[j]),name=f"L1_{i}_{j}")
    m.addConstr(L[(i, j)] >= (S[j] - S[i]), name=f"L2_{i}_{j}")
    m.addConstr(L[(i, j)] <= (S[i] + S[j]),name=f"L3_{i}_{j}")
    m.addConstr(L[(i, j)] <= (2 - S[i] - S[j]),name=f"L4_{i}_{j}")
    # m.addConstr(L[(i, j)] <= U[(i, j)])

input_vars = []
input_vars2 = []
for i in H.nodes:
    input_vars.append(S[i])
    input_vars2.append(S[i])
for i, j in H.Branch:
    input_vars.append(U[(i, j)])
    input_vars2.append(U[(i, j)])
input_vars.append(mu)
input_vars.append(eps)
input_vars2.append(Gain)
# for i in range(len(input_vars)):
#     m.addConstr(input_vars[i]==d[i])

fop=m.addVar()
Loss=m.addVar()
start_time = time.time()
pred_constr1 = add_predictor_constr(m, model1, input_vars)
pred_sales1 = pred_constr1.output
pred_constr2 = add_predictor_constr(m, model2, input_vars2)
pred_sales2 = pred_constr2.output
elapsed = time.time() - start_time
print(f"嵌入耗时: {elapsed:.2f} 秒")
m.update()
print(f"变量数: {m.numVars}")
print(f"约束数: {m.numConstrs}")
print(f"非零元素: {m.numNZs}")
m.addConstr(pred_sales1==fop)
m.addConstr(pred_sales2==Loss)


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
    C_line += H.c_l[0] * H.Length[i][j] * U[(i, j)]
    S_vsc += H.S_vsc_ij*LU[(i, j)]

for i in H.nodes:
    S_c = S_c + H.S_c_load * (H.n__ac[i] * S[i] + H.n__dc[i] * (1 - S[i]))
    S_c = S_c + H.S_c_wind * (S[i] + 2 * (1 - S[i])) * H.n__wind[i]
    S_c = S_c + H.S_c_pv * H.n__pv[i]

C_cvt = H.c_c * S_c + H.c_v * S_vsc

C_invest = C_line * (H.r * (pow(1+H.r,H.T_line)/(pow(1+H.r,H.T_line)-1)) +H.beta_line)+ C_cvt * (H.r *(pow(1+H.r,H.T_cvt)/(pow(1+H.r,H.T_cvt)-1)) + H.beta_cvt)
C_operation = fop * H.N_d



m.setObjective(C_operation+C_invest+Loss*1e6, gb.GRB.MINIMIZE)
start_time = time.time()


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
m.write("my_model.mps")
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
print(fop.X)
# print(pred_sales1.X)
print(m.ObjVal)
res=[]
for i in range(len(input_vars)):
    res.append(input_vars[i].X)