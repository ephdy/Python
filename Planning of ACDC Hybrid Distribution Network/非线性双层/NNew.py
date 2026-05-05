# ga_network_stable.py
import random
import numpy as np
from collections import deque
import multiprocessing
from deap import base, creator, tools
import copy
import time
from Gurobi_solving import *
from _13_nodes_distribution_network import *
import gurobipy as gb
import os
import csv
import datetime
# -------------------------
# Problem data (BASE_LENGTH)
# -------------------------
BASE_LENGTH = np.array([
    [0.00, 1.61, 1.61, 3.22, 2.25, 3.22, 3.86, 3.86, 5.47, 4.51, 5.47, 6.11, 6.11],
    [1.61, 0.00, 2.25, 1.61, 1.61, 3.86, 2.25, 3.22, 3.86, 3.86, 4.83, 4.51, 5.47],
    [1.61, 2.25, 0.00, 3.86, 1.61, 1.61, 3.22, 2.25, 4.83, 3.86, 3.86, 5.47, 4.51],
    [3.22, 1.61, 3.86, 0.00, 2.25, 4.51, 1.61, 4.51, 2.25, 3.22, 5.47, 3.86, 4.83],
    [2.25, 1.61, 1.61, 2.25, 0.00, 2.25, 1.61, 1.61, 3.22, 2.25, 3.22, 3.86, 3.86],
    [3.22, 3.86, 1.61, 4.51, 2.25, 0.00, 3.86, 1.61, 5.47, 3.22, 2.25, 4.83, 3.86],
    [3.86, 2.25, 3.22, 1.61, 1.61, 3.86, 0.00, 2.25, 1.61, 1.61, 3.86, 2.25, 3.22],
    [3.86, 3.22, 2.25, 3.86, 1.61, 1.61, 2.25, 0.00, 3.86, 1.61, 1.61, 3.22, 2.25],
    [5.47, 3.86, 4.83, 2.25, 3.22, 5.47, 1.61, 3.86, 0.00, 2.25, 4.51, 1.61, 3.86],
    [4.51, 3.86, 3.86, 3.22, 2.25, 3.22, 1.61, 1.61, 2.25, 0.00, 2.25, 1.61, 1.61],
    [5.47, 4.83, 3.86, 5.47, 3.22, 2.25, 3.86, 1.61, 4.51, 2.25, 0.00, 3.86, 1.61],
    [6.11, 4.51, 5.47, 3.86, 3.86, 4.83, 2.25, 3.22, 1.61, 1.61, 3.86, 0.00, 2.25],
    [6.11, 5.47, 4.51, 4.83, 3.86, 3.86, 3.22, 2.25, 3.86, 1.61, 1.61, 2.25, 0.00]
])
# BASE_LENGTH = np.array([[1 for _ in range(n)]for _ in range(n)])
MIN_ROW = 1
MAX_ROW = 3
POP_SIZE = 200
GENERATIONS = 100
SEED = 42
N_JOBS = max(1, multiprocessing.cpu_count() - 1)
ELITE_SIZE = 2            # number of elites to preserve each generation
CX_PB = 0.5
MUTPB = 0.15
THRESHOLD = 1e-4
FORCE_STOP_GEN = 50
random.seed(SEED)
np.random.seed(SEED)
CC=0
def find_upper_right_ones_python(arr):
    n = len(arr)
    result = []
    for i in range(n):
        for j in range(i+1, n):
            if arr[i][j] == 1:
                result.append((i, j))
    return result

# -------------------------
def encode(W, U, X):
    return list(W.flatten()) + list(U.flatten()) + list(X.flatten())

def decode(ind):
    idx = 0
    W = np.array(ind[idx: idx + n], dtype=int)
    idx += n
    U_flat = np.array(ind[idx: idx + n * n], dtype=int)
    U = U_flat.reshape((n, n))
    idx += n * n
    X_flat = np.array(ind[idx: idx + n * n], dtype=int)
    X = X_flat.reshape((n, n))
    return W, U, X

def make_random_individual():
    W = np.random.randint(0, 2, size=(n,))
    U = np.random.randint(0, 2, size=(n, n))
    U = np.triu(U, 1)
    U = U + U.T
    np.fill_diagonal(U, 0)
    X = np.random.randint(0, 2, size=(n, n))
    X = np.triu(X, 1)
    X = X + X.T
    np.fill_diagonal(X, 0)
    return encode(W, U, X)

# -------------------------
# utility: BFS connected components
# -------------------------
def connected_components(U):
    n = U.shape[0]
    visited = [False] * n
    comps = []
    for i in range(n):
        if not visited[i]:
            q = deque([i])
            visited[i] = True
            comp = [i]
            while q:
                u = q.popleft()
                for v in range(n):
                    if U[u, v] == 1 and not visited[v]:
                        visited[v] = True
                        q.append(v)
                        comp.append(v)
            comps.append(comp)
    return comps

# -------------------------
# build cost matrix from X and BASE_LENGTH
# -------------------------
def build_cost_matrix_from_X(base_length, X):
    n = base_length.shape[0]
    cost = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i+1, n):
            k = 1.1 if X[i, j] == 0 else 1.9
            cost[i, j] = base_length[i, j] * k
            cost[j, i] = cost[i, j]
    np.fill_diagonal(cost, 0.0)
    return cost




# -------------------------
# evaluation: cost-based, uses BASE_LENGTH & X scaling
# -------------------------
def evaluate(ind):
    W, U, X = decode(ind)
    # ensure symmetric for evaluation
    U = np.triu(U, 1); U = U + U.T
    X = np.triu(X, 1); X = X + X.T

    L = [[0 for _ in range(n)] for _ in range(n)]
    C_line = 0
    S_vsc = 0
    S_c = 0
    for i in range(n):
        S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
        S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
        S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])
            S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
            for k in range(kk):
                C_line += 0.5 * c_l[X[i][j]] * Length[i][j] * U[i][j]
    C_cvt = c_c * S_c + c_v * S_vsc
    C_invest = C_line + C_cvt
    C_operation = 0
    # f_op = Lower_layer_solving_1(W,U,X)

    w1,w2,w3=8,50,10
    # f1=Lower_layer_solving_2(W,U,X)
    # U_1_index = find_upper_right_ones(U)
    # k_U_lack = len(U_1_index)
    # U_lack_1 = []
    # for i in U_1_index:
    #     U_new = copy.deepcopy(U)
    #     U_new[i[0]][i[1]] = 0
    #     U_new[i[1]][i[0]] = 0
    #     U_lack_1.append(U_new)
    # obj,f_op, delta, mu = Lower_layer_solving_1(W, U, X,w1,w2)
    # for d in range(T_p):
    #     C_operation += N_d * f_op / pow(1 + r, d + 1)
    # for d in range(T_line):
    #     C_operation += beta_line * C_line / pow(1 + r, d + 1)
    # for d in range(T_cvt):
    #     C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
    # # f1 = (C_invest + C_operation-1.037e8)/5e7
    # f1 = (C_invest + C_operation-1.037e8)/5e7
    # f2= 1-delta/0.4
    # Loss_count=0
    # for i in range(k_U_lack):
    #     Loss_count+=Lower_layer_solving_3(W0, U_lack_1[i], X, delta, mu)
    # f3=Loss_count/k_U_lack/(sum(n__ac)+sum(n__dc))
    # f4=mu
    # z=w1*f1+w2*f2+w3*f3
    obj, f_op, delta, mu,loss = Lower_layer_solving_2(W, U, X)
    for d in range(T_p):
        C_operation += N_d * f_op / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
    f1=(C_invest + C_operation - 1.037e8) / 3e7
    f2=1-delta/0.4
    f3=loss
    global CC
    CC+=1
    print(CC)

    #return (z, 0, 0, 0)
    # return obj, f_op, delta, mu,loss
    return f1,f2,f3

def repair_minimal(ind, min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=0, rng=None):
    """
    构造性修复（从成本矩阵出发重建 U）：
    - 最终严格满足 min_row <= degree <= max_row
    - 最终连通
    - 优先低成本边（MST + 最低成本补边）
    - 若约束在数学上不可行，会抛出 ValueError（提示不可能）
    """

    W, U, X=decode(ind)
    W[0] = 0
    if rng is None:
        rng = random

    n = U.shape[0]
    if n <= 1:
        return np.zeros((n, n), dtype=int)

    # 先做基本检查：若总体度数上下界不可能，则报错
    # 最大允许的边数 (simple graph)：
    max_total_edges = n * max_row // 2
    # 为了连通至少需要 n-1 条边
    if max_total_edges < n - 1:
        raise ValueError(f"在 n={n}, max_row={max_row} 下无法构造连通图 (需要至少 {n-1} 条边, 但上界只允许 {max_total_edges}).")

    # 最小需要的总度数
    min_total_degree = n * min_row
    # 最大允许的总度数
    max_total_degree = n * max_row
    if min_total_degree > max_total_degree:
        raise ValueError("min_row 与 max_row 不兼容（总体度数下界 > 上界）")

    # 构建成本矩阵（用于贪心）
    cost_matrix = build_cost_matrix_from_X(BASE_LENGTH, X)

    # 结果矩阵（从零开始构建），保证对角 0 和对称
    U_new = np.zeros((n, n), dtype=int)

    # 边列表 (i,j,cost) for all i<j, 升序按成本
    edges = [(i, j, float(cost_matrix[i, j])) for i in range(n) for j in range(i+1, n)]
    edges.sort(key=lambda x: x[2])

    # ---------- 1) 用 Kruskal-like 方法在不超过 max_row 的前提下构造连通骨架（优先低成本） ----------
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
            return True
        return False

    degree = [0] * n
    edges_used = []

    # 先尝试选边连接不同连通分量（保证最终连通）, 但选边时不能使任一端度超过 max_row
    for i, j, c in edges:
        if find(i) != find(j) and degree[i] < max_row and degree[j] < max_row:
            union(i, j)
            U_new[i, j] = U_new[j, i] = 1
            degree[i] += 1
            degree[j] += 1
            edges_used.append((i, j, c))
        # 若已连通（single component），可以提前停止（保留可选）
        roots = set(find(x) for x in range(n))
        if len(roots) == 1:
            break

    # 如果仍未连通，说明在 max_row 限制下不能用这些边连接，各种尝试失败 -> 抛错
    roots = set(find(x) for x in range(n))
    if len(roots) > 1:
        # 尝试放宽策略：在仍然未连通时，搜索任意能连接两个分量的边（即使暂时把某些度推到 max_row）
        # 如果都不行，则一定不可行（已在前面有数学判断，但这里再确认）
        connected_now = False
        for i, j, c in edges:
            if find(i) != find(j) and degree[i] < max_row and degree[j] < max_row:
                union(i, j)
                U_new[i, j] = U_new[j, i] = 1
                degree[i] += 1
                degree[j] += 1
        roots = set(find(x) for x in range(n))
        if len(roots) > 1:
            raise ValueError("无法在严格 max_row 限制下构造连通骨架 —— 请检查 max_row 是否过小。")

    # ---------- 2) 确保每个节点至少达到 min_row：选择最便宜的可用边 ----------
    # 持续添加最小成本的边，要求新边不使任何端点超过 max_row
    # 优先从当前 degree 较小的节点开始
    # 构建候选边优先队列（按成本）
    import heapq
    heap = []
    for i, j, c in edges:
        if U_new[i, j] == 0:
            heapq.heappush(heap, (c, i, j))

    # 迭代直到所有节点 degree >= min_row 或 没有合适边
    while True:
        deficit_nodes = [idx for idx in range(n) if degree[idx] < min_row]
        if not deficit_nodes:
            break
        # 找一条可行的最便宜边，使其至少帮助一个欠度节点
        found = False
        new_heap = []
        while heap:
            c, a, b = heapq.heappop(heap)
            # 如果任一端在欠度节点并且添加后两端都不超 max_row，则选它
            if (degree[a] < min_row or degree[b] < min_row) and degree[a] < max_row and degree[b] < max_row:
                U_new[a, b] = U_new[b, a] = 1
                degree[a] += 1
                degree[b] += 1
                found = True
                break
            else:
                # 暂存继续
                new_heap.append((c, a, b))
        # 把暂存的放回 heap
        for item in new_heap:
            heapq.heappush(heap, item)
        if not found:
            # 没有任何单条边可以满足（说明受 max_row 限制），此时尝试更复杂策略：
            # - 在两条边上同时操作（swap 风格）通常很复杂；但若找不到直接单边补充，说明不可行
            raise ValueError("无法在 max_row 限制下把所有节点的 degree 提升到 min_row —— 请检查 max_row 是否过小。")

    # ---------- 3) 如果需要可选地添加 extra_edges（全局最便宜的若不超 max_row） ----------
    if extra_edges and extra_edges > 0:
        # 继续使用 heap，添加额外最便宜边
        added = 0
        while heap and added < extra_edges:
            c, a, b = heapq.heappop(heap)
            if U_new[a, b] == 0 and degree[a] < max_row and degree[b] < max_row:
                U_new[a, b] = U_new[b, a] = 1
                degree[a] += 1
                degree[b] += 1
                added += 1

    # ---------- 4) 最终验证：所有节点度数在区间内且连通 ----------
    if not all(min_row <= degree[i] <= max_row for i in range(n)):
        # 万一有不满足（一般不会），抛错以便上层处理
        raise ValueError(f"最终度数未满足约束。degree={degree}")
    # 连通性校验
    if len(connected_components(U_new)) != 1:
        raise ValueError("构建后图仍不连通（理论上不应发生）")

    return encode(W,U_new,X)
# -------------------------
# DEAP setup
# -------------------------
creator.create("FitnessMin", base.Fitness, weights=(-1.0,-1.0,-999999.0))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()
toolbox.register("individual", tools.initIterate, creator.Individual, make_random_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("mate", tools.cxTwoPoint)

# bitflip mutation with probability per gene
def bitflip_mutation(individual, indpb=0.02):
    for i in range(len(individual)):
        if random.random() < indpb:
            individual[i] = 1 - int(individual[i])
    return (individual,)

toolbox.register("mutate", bitflip_mutation)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("evaluate", evaluate)

# -------------------------
# multiprocessing worker initializer (seed RNGs)
# -------------------------
def _init_worker(seed):
    random.seed(seed + int(time.time() * 1000) % 100000)
    np.random.seed(seed + int(time.time() * 1000) % 100000)

# -------------------------
# GA main loop with elitism & minimal-disturbance repair
# -------------------------
def main(seed=SEED, pop_size=POP_SIZE, generations=GENERATIONS, n_jobs=N_JOBS):
    random.seed(seed)
    np.random.seed(seed)
    # pool = multiprocessing.Pool(processes=n_jobs)
    toolbox.register("map", map)


    pop = toolbox.population(n=pop_size)

    # initial repair (deterministic/minimal)
    for ind in pop:
        ind[:]=repair_minimal(ind, min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=0, rng=random)

    # initial evaluation
    fitnesses = list(toolbox.map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    # HallOfFame and stats
    hof = tools.HallOfFame(ELITE_SIZE)
    hof.update(pop)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: float(np.mean([a[0] for a in x])))
    stats.register("min", lambda x: float(np.min([a[0] for a in x])))
    stats.register("avg1", lambda x: float(np.mean([a[1] for a in x])))
    stats.register("min1", lambda x: float(np.min([a[1] for a in x])))
    stats.register("avg2", lambda x: float(np.mean([a[2] for a in x])))
    stats.register("min2", lambda x: float(np.min([a[2] for a in x])))
    # stats.register("avg3", lambda x: float(np.mean([a[3] for a in x])))
    # stats.register("min3", lambda x: float(np.min([a[3] for a in x])))
    # stats.register("avg4", lambda x: float(np.mean([a[4] for a in x])))
    # stats.register("min4", lambda x: float(np.min([a[4] for a in x])))

    best_prev = hof[0].fitness.values[0]

    log = []
    trigger=0
    for gen in range(generations):
        global CC
        CC =0
        # Elitism: keep ELITE_SIZE best
        elites = tools.selBest(pop, ELITE_SIZE)
        # selection
        offspring = toolbox.select(pop, len(pop) - ELITE_SIZE)
        offspring = list(map(toolbox.clone, offspring))

        # Crossover
        for i in range(1, len(offspring), 2):
            if random.random() < CX_PB:
                toolbox.mate(offspring[i-1], offspring[i])
                # mark fitness invalid
                try:
                    del offspring[i-1].fitness.values
                except AttributeError:
                    pass
                try:
                    del offspring[i].fitness.values
                except AttributeError:
                    pass

        # Mutation
        for i in range(len(offspring)):
            if random.random() < MUTPB:
                offspring[i], = toolbox.mutate(offspring[i])
                try:
                    del offspring[i].fitness.values
                except AttributeError:
                    pass

        # Repair offspring deterministically with cost-driven rules
        for i in range(len(offspring)):
            offspring[i][:]=repair_minimal(offspring[i], min_row=MIN_ROW, max_row=MAX_ROW, extra_edges=0, rng=random)

        # reassemble population with elites
        pop = elites + offspring
        # evaluate invalid individuals
        invalid = [ind for ind in pop if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid)
        for ind, fit in zip(invalid, fitnesses):
            ind.fitness.values = fit

        hof.update(pop)
        rec = stats.compile(pop)
        log.append((gen, rec["avg1"], rec["min1"]))
        print(
            f"Gen {gen}: avg={rec['avg']:.6f}, min={rec['min']:.6f},"
            f"avg1={rec['avg1']:.6f}, min1={rec['min1']:.6f},"
            f" avg2={rec['avg2']:.6f}, min2={rec['min2']:.6f}, ")
        # print(f"Gen {gen}: avg={rec['avg']:.6f}, min={rec['min']:.6f},avg1={rec['avg1']:.6f}, min1={rec['min1']:.6f}, avg2={rec['avg2']:.6f}, min2={rec['min2']:.6f}, avg3={rec['avg3']:.6f}, min3={rec['min3']:.6f}")
        print(f"程序运行时间: {time.time() - start_time:.4f} 秒")

        # early stopping
        best_now = hof[0].fitness.values[0]
        diff = abs(best_prev - best_now)
        if gen < FORCE_STOP_GEN and diff < THRESHOLD:
            trigger+=1
        #     print(f"Early stop at gen {gen}: best change {diff:.4e} < {THRESHOLD}")
        #     break
        best_prev = best_now


    best = hof[0]
    W_best, U_best, X_best = decode(best)
    print("\n=== Best Solution ===")
    print("W (AC=0 / DC=1):", W_best)
    print("U adjacency (rowsum):\n", U_best)
    print("rowsum:", U_best.sum(axis=1))
    print(f"Objective (cost) = {best.fitness.values[0]:.6f}")
    # pool.close()
    # pool.join()
    return pop, log, hof


if __name__ == '__main__':
    start_time = time.time()

    pop, log, hof = main(seed=SEED,pop_size=200, generations=50)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"程序运行时间: {elapsed_time:.4f} 秒")

