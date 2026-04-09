# ga_network_mst.py
import random
import numpy as np
from collections import deque
import multiprocessing
from deap import base, creator, tools, algorithms
from _13_nodes_distribution_network import *
import gurobipy as gb
# ---------------------------
# Problem settings
# ---------------------------
N_NODES = n          # 节点数（可改）
MIN_ROW = 1
MAX_ROW = 3
N=n

POP_SIZE = 200
GENERATIONS = 10
SEED = 42
N_JOBS = max(1, multiprocessing.cpu_count() - 1)

random.seed(SEED)
np.random.seed(SEED)

# ---------------------------
def Lower_layer_solving(W,U,x,L):

    m=gb.Model('m1')
    #
    # 定义各节点电压
    V = m.addVars(N, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
    V__svc = m.addVars(N, N, T, vtype=gb.GRB.CONTINUOUS, name="V__svc")
    for i in range(N):
        for j in range(i + 1, N):
            for t in range(T):
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
    # 定义线路潮流
    P_tran = m.addVars(N, N, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="P_tran")
    Q_tran = m.addVars(N, N, T, lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name="Q_tran")
    for t in range(T):
        for i in range(N):
            m.addConstr(P_tran[i, i, t] == 0)
            m.addConstr(Q_tran[i, i, t] == 0)
            for j in range(i + 1, N):
                if i != j:
                    m.addConstr(P_tran[i, j, t] == -P_tran[j, i, t])
                    m.addConstr(Q_tran[i, j, t] == -Q_tran[j, i, t])
    # 购电功率
    P_sub = m.addVars(24, ub=10, vtype=gb.GRB.CONTINUOUS, name="P_sub")
    Q_sub = m.addVars(24, lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name="Q_sub")
    # 储能充放电功率
    P_ess_ch = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
    P_ess_dis = m.addVars(24, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
    # 储能约束
    alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
    alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
    E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS)
    m.addConstr(E_k[0] == 5)
    for t in range(T):
        m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
        m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
        m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
        if t != 0:
            m.addConstr(E_k[t] == E_k[t - 1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
    # DG出力
    P_DG_813 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_813")
    P_DG_911 = m.addVars(2, 24, vtype=gb.GRB.CONTINUOUS, name="P_DG_911")
    Q_DG_813 = m.addVars(2, 24, ub=2.0, vtype=gb.GRB.CONTINUOUS, name="Q_DG_813")
    Q_DG_911 = m.addVars(2, 24, ub=2.5, vtype=gb.GRB.CONTINUOUS, name="Q_DG_911")

    for t in range(T):
        m.addConstr(P_DG_813[0, t] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG_813[1, t] <= DG_total[t] * 2 / 9)
        m.addConstr(P_DG_911[0, t] <= DG_total[t] * 2.5 / 9)
        m.addConstr(P_DG_911[1, t] <= DG_total[t] * 2.5 / 9)

    #目标函数
    f_op = 0

    for t in range(T):
        f_op += c_s * P_sub[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
        f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[0, t])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[0, t])
        f_op += c_d * (DG_total[t] * 2.5 / 9 - P_DG_911[1, t])
        f_op += c_d * (DG_total[t] * 2 / 9 - P_DG_813[1, t])
    # 有功功率平衡方程
    for i in range(N):
        for t in range(T):
            if i == 0:
                m.addConstr(P_sub[t] - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 5:
                m.addConstr(
                    0 - P_load[t] * (n__ac[i] + n__dc[i]) + P_ess_dis[t] - P_ess_ch[t] - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 7:
                m.addConstr(
                    P_DG_813[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 8:
                m.addConstr(
                    P_DG_911[0, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 10:
                m.addConstr(
                    P_DG_911[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            elif i == 12:
                m.addConstr(
                    P_DG_813[1, t] - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)
            else:
                m.addConstr(0 - P_load[t] * (n__ac[i] + n__dc[i]) - P_tran.sum(i, '*', t) * S_base == 0)

    # 无功功率平衡方程
    for i in range(N):
        for t in range(T):
            if i == 0:
                m.addConstr(Q_sub[t] - Q_tran.sum(i, '*', t) * S_base == 0)
            elif i == 7:
                m.addConstr((Q_DG_813[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            elif i == 8:
                m.addConstr((Q_DG_911[0, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            elif i == 10:
                m.addConstr((Q_DG_911[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            elif i == 12:
                m.addConstr((Q_DG_813[1, t] - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*',t) * S_base)*(1-W[i])==0)
            else:
                m.addConstr((0 - Q_load[t] * (n__ac[i] + n__dc[i]) - Q_tran.sum(i, '*', t) * S_base)*(1-W[i])==0)
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(P_tran[i, j, t] <= M * U[i][j])
                m.addConstr(P_tran[i, j, t] >= -M * U[i][j])
                m.addConstr(Q_tran[i, j, t] <= M * U[i][j])
                m.addConstr(Q_tran[i, j, t] >= -M * U[i][j])
                m.addConstr(Q_tran[i, j, t] <= M * (1 - W[i]*W[j]))
                m.addConstr(Q_tran[i, j, t] >= -M * (1 - W[i]*W[j]))
    # 电压方程
    for i in range(N):
        for j in range(N):
            if i != j:
                #
                S_line = S_line_k[x[i][j]]
                for t in range(T):
                    m.addConstr(U[i][j]*((1-L[i][j]*W[i])*V[i,t]+(L[i][j]*W[i]-L[i][j]*W[j])*V__svc[i,j,t]-(1-L[i][j]*W[j])*V[i,t])==
                                (1-L[i][j])*(r__[i][j] * P_tran[i, j, t] + x__[i][j] * Q_tran[i, j, t])+
                                L[i][j]*(r__vsc[i][j] * P_tran[i, j, t] - x__vsc[i][j] * Q_tran[i, j, t]))
                    #
                    m.addConstr(Q_tran[i, j, t] <= L[i][j] * (Q_vsc_max - M) + M)
                    m.addConstr(Q_tran[i, j, t] >= -1 * (L[i][j] * (Q_vsc_max - M) + M))
                    #
                    m.addConstr(P_tran[i, j, t] <= gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] >= -gama * S_line / S_base)

                    m.addConstr(Q_tran[i, j, t] <= gama * S_line / S_base)
                    m.addConstr(Q_tran[i, j, t] >= -gama * S_line / S_base)

                    m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] + Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] <= 1.41 * gama * S_line / S_base)
                    m.addConstr(P_tran[i, j, t] - Q_tran[i, j, t] >= -1.41 * gama * S_line / S_base)


    m.setObjective(f_op, gb.GRB.MINIMIZE)

    m.setParam('LogToConsole', 0)
    m.optimize()
    # for v in m.getVars():
    #     if v.varName.split('[')[0] in ['W', 'U', 'x', 'P_sub','P_ess_ch','P_ess_dis']:
    #         print(v.VarName, v.X)
    if m.status == gb.GRB.OPTIMAL:
        return m.objVal
    else:
        return 9e13
# Encoding/Decoding helpers
# Individual representation:
# [ W(0..N-1) , U_flat (N*N entries row-major), X_flat (N*N) ]
# For simplicity X is included but not used in evaluate; adjust as needed.
# ---------------------------
def encode(W, U, X):
    """把 W,U,X 转为个体列表"""
    return list(W.flatten()) + list(U.flatten()) + list(X.flatten())

def decode(ind):
    """把个体列表解码为 W,U,X"""
    idx = 0
    W = np.array(ind[idx: idx + N_NODES], dtype=int)
    idx += N_NODES
    U_flat = np.array(ind[idx: idx + N_NODES * N_NODES], dtype=int)
    U = U_flat.reshape((N_NODES, N_NODES))
    idx += N_NODES * N_NODES
    X_flat = np.array(ind[idx: idx + N_NODES * N_NODES], dtype=int)
    X = X_flat.reshape((N_NODES, N_NODES))
    return W, U, X

def make_random_individual():
    W = np.random.randint(0, 2, size=(N_NODES,))
    U = np.random.randint(0, 2, size=(N_NODES, N_NODES))
    U = np.triu(U, 1)
    U = U + U.T
    np.fill_diagonal(U, 0)
    X = np.random.randint(0, 2, size=(N_NODES, N_NODES))
    X = np.triu(X, 1)
    X = X + X.T
    np.fill_diagonal(X, 0)
    return encode(W, U, X)

# ---------------------------
# MST + 修复 算子
# ---------------------------
BASE_LENGTH = np.array(Length)
def build_cost_matrix_from_X(base_length, X):
    """
    base_length: n x n numpy array (对称，0对角)
    X: n x n matrix with values 0 or 1 (edge type)
    返回： n x n 对称成本矩阵 cost[i,j] = base_length[i,j] * k(X[i,j])
    """
    n = base_length.shape[0]
    cost = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i+1, n):
            # 如果 X 的编码是对称并且对角为0，这里只读上三角
            if X[i, j] == 0:
                k = 147.648
            else:
                k = 295.296
            cost[i, j] = base_length[i, j] * k
            cost[j, i] = cost[i, j]
    np.fill_diagonal(cost, 0.0)
    return cost
def mst_repair_with_cost(U, cost_matrix, extra_edges=2):
    """
    使用 cost_matrix 作为边权求 MST，然后加入少量随机边。
    U 参数仅用于确定 n 的大小（或可传 n）。
    """
    n = cost_matrix.shape[0]
    # 构造边列表 (weight, i, j)
    edges = []
    for i in range(n):
        for j in range(i+1, n):
            edges.append((cost_matrix[i, j], i, j))
    # Kruskal
    edges.sort(key=lambda x: x[0])
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    newU = np.zeros((n, n), dtype=int)
    for w, i, j in edges:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
            newU[i, j] = 1
            newU[j, i] = 1
    # 轻量补边：优先选取成本较小的未被选中边（可改为随机）
    remaining = [(cost_matrix[i,j], i, j) for i in range(n) for j in range(i+1, n) if newU[i,j] == 0]
    remaining.sort(key=lambda x: x[0])  # 按成本从小到大
    k = min(extra_edges, len(remaining))
    for idx in range(k):
        _, i, j = remaining[idx]
        newU[i, j] = 1
        newU[j, i] = 1
    return newU
# def mst_repair_full(U, extra_edges=2):
#     """
#     以所有节点为对象，构造 MST，然后加少量随机边
#     U: n x n (ignored except size), 返回 newU (symmetric, zero diagonal)
#     """
#     n = U.shape[0]
#     # 构造完全图权重全部为1（如果有实际权重可替换）
#     edges = [(1, i, j) for i in range(n) for j in range(i+1, n)]
#
#     parent = list(range(n))
#     def find(x):
#         while parent[x] != x:
#             parent[x] = parent[parent[x]]
#             x = parent[x]
#         return x
#
#     mst_edges = []
#     for w, i, j in edges:
#         ri, rj = find(i), find(j)
#         if ri != rj:
#             parent[ri] = rj
#             mst_edges.append((i, j))
#
#     newU = np.zeros((n, n), dtype=int)
#     for i, j in mst_edges:
#         newU[i, j] = 1
#         newU[j, i] = 1
#
#     # 轻量补边，随机选择一些未加入的边
#     remaining = [(i, j) for i in range(n) for j in range(i+1, n) if newU[i, j] == 0]
#     random.shuffle(remaining)
#     for k in range(min(extra_edges, len(remaining))):
#         i, j = remaining[k]
#         newU[i, j] = 1
#         newU[j, i] = 1
#
#     return newU

def enforce_row_bounds(U, min_row=MIN_ROW, max_row=MAX_ROW):
    """确保每行的度在[min_row, max_row]范围内（对称矩阵）"""
    n = U.shape[0]
    # 修剪过多的边
    for i in range(n):
        while U[i].sum() > max_row:
            ones = [j for j in range(n) if j != i and U[i, j] == 1]
            if not ones:
                break
            j = random.choice(ones)
            U[i, j] = U[j, i] = 0
    # 补足较少的边
    for i in range(n):
        while U[i].sum() < min_row:
            zeros = [j for j in range(n) if j != i and U[i, j] == 0]
            if not zeros:
                break
            j = random.choice(zeros)
            U[i, j] = U[j, i] = 1
    return U

def repair_individual(ind, min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=2):
    W, U, X = decode(ind)
    W[0]=0
    # 保证对称与对角
    U = np.triu(U, 1); U = U + U.T; np.fill_diagonal(U, 0)
    X = np.triu(X, 1); X = X + X.T; np.fill_diagonal(X, 0)

    # 先做行和约束（避免孤立）
    U = enforce_row_bounds(U, min_row=min_row, max_row=max_row)

    # 用 X 构造成本矩阵
    cost_matrix = build_cost_matrix_from_X(BASE_LENGTH, X)

    # 使用 cost-based MST 修复
    U = mst_repair_with_cost(U, cost_matrix, extra_edges=extra_edges)

    # 再次保证行和范围
    U = enforce_row_bounds(U, min_row=min_row, max_row=max_row)

    # 编码并返回
    new_ind = encode(W, U, X)
    ind[:] = new_ind
    return ind

# ---------------------------
# 评价函数（示例）
# ---------------------------
def evaluate(ind):
    """
    示例目标（需要最小化）：
      cost = edge_cost + dc_node_cost
    edge_cost: 每条边计 1（注意 U 是对称的，计一次）
    dc_node_cost: W[i]==1 时计 0.5
    你应将此函数替换为真实的投资/运行成本计算（含 X）
    """
    W, U, X = decode(ind)
    L = [[0 for _ in range(N)] for _ in range(N)]
    C_line = 0
    S_vsc = 0
    S_c = 0
    for i in range(N):
        S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
        S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
        S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
        for j in range(N):
            L[i][j] = abs(W[i] - W[j])
            S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
            for k in range(kk):
                C_line += 0.5 * c_l[X[i][j]] * Length[i][j] * U[i][j]
    C_cvt = c_c * S_c + c_v * S_vsc
    C_invest = C_line + C_cvt
    C_operation = 0
    f_op = Lower_layer_solving(W, U, X,L)

    # C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
    for d in range(T_p):
        C_operation += N_d * f_op / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
    f1 = C_invest + C_operation
    # f2 = Lower_layer_model_solving(W, U, X, L,1)
    z = f1
    return (z,)

# ---------------------------
# DEAP setup
# ---------------------------
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()
# gene generators
toolbox.register("individual", tools.initIterate, creator.Individual, make_random_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# operators
toolbox.register("mate", tools.cxTwoPoint)
# mutation: flip each bit with indpb probability
def bitflip_mutation(individual, indpb=0.02):
    for i in range(len(individual)):
        if random.random() < indpb:
            individual[i] = 1 - int(individual[i])
    return (individual,)

toolbox.register("mutate", bitflip_mutation)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("evaluate", evaluate)

# We'll decorate mutate to include repair (so mutate returns repaired individual)
def mutate_and_repair(ind):
    ind, = toolbox.mutate(ind)
    repair_individual(ind, min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=2)
    # invalidate fitness so it'll be re-evaluated
    del ind.fitness.values
    return (ind,)

toolbox.register("mutate_and_repair", mutate_and_repair)

# We'll also create a helper to repair offspring after crossover
def cx_and_repair(child1, child2):
    tools.cxTwoPoint(child1, child2)
    repair_individual(child1, min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=2)
    repair_individual(child2, min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=2)
    try:
        del child1.fitness.values
    except AttributeError:
        pass
    try:
        del child2.fitness.values
    except AttributeError:
        pass
    return child1, child2

# ---------------------------
# Main GA loop with early stopping
# ---------------------------
def main(seed=SEED, pop_size=POP_SIZE, generations=GENERATIONS, n_jobs=N_JOBS):
    random.seed(seed)
    np.random.seed(seed)

    pool = multiprocessing.Pool(processes=n_jobs)
    toolbox.register("map", pool.map)

    pop = toolbox.population(n=pop_size)

    # initial repair to ensure feasibility
    for ind in pop:
        repair_individual(ind, min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=2)

    # initial evaluation
    fitnesses = list(toolbox.map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    hof = tools.HallOfFame(1)
    hof.update(pop)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: float(np.mean([a[0] for a in x])))
    stats.register("min", lambda x: float(np.min([a[0] for a in x])))

    logbook = tools.Logbook()
    logbook.header = ["gen", "avg", "min"]

    best_prev = hof[0].fitness.values[0]

    CX_PB = 0.5
    MUT_PB = 0.35   # 提高突变概率
    THRESHOLD = 1e-4
    FORCE_STOP_GEN = 50

    for gen in range(generations):
        # selection
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))

        # crossover (pairwise)
        for i in range(1, len(offspring), 2):
            if random.random() < CX_PB:
                offspring[i-1], offspring[i] = cx_and_repair(offspring[i-1], offspring[i])

        # mutation (use our mutate_and_repair with probability)
        for i in range(len(offspring)):
            if random.random() < MUT_PB:
                offspring[i], = mutate_and_repair(offspring[i])

        # evaluate invalid individuals
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid)
        for ind, fit in zip(invalid, fitnesses):
            ind.fitness.values = fit

        pop[:] = offspring
        hof.update(pop)

        record = stats.compile(pop)
        record_dict = {"gen": gen, "avg": record["avg"], "min": record["min"]}
        logbook.record(**record_dict)
        print(logbook.stream)

        best_now = hof[0].fitness.values[0]
        diff = abs(best_prev - best_now)
        # if gen < FORCE_STOP_GEN and diff < THRESHOLD:
        #     print(f"\nEarly stop at gen {gen}: best change {diff:.4e} < {THRESHOLD}")
        #     break
        best_prev = best_now

    pool.close()
    pool.join()

    best = hof[0]
    W_best, U_best, X_best = decode(best)
    print("\n=== Best Solution ===")
    print("W (AC=0 / DC=1):", W_best)
    print("U adjacency (rowsum):\n", U_best)
    print("rowsum:", U_best.sum(axis=1))
    print("X (example):\n", X_best)
    print(f"Objective (cost) = {best.fitness.values[0]:.6f}")

    return pop, logbook, hof

if __name__ == "__main__":
    pop, log, hof = main(pop_size=200, generations=10)
