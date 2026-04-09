# 定义系统参数
n = 13  # 节点数
kk = 2  # 线路选型种类
N_d, T_line, T_cvt, T_p, T = 365, 40, 45, 40, 24
beta_line, beta_cvt = 0.05, 0.05  # 线路、换流器年维护费用系数
r = 0.075  # 贴现率
c_v, c_c, c_s, c_d, c_e = 1154.13e3, 1018.35e3, 400, 400, 10
L_min, L_max = 1, 3
M = 1000
S_vsc_ij = 5
S_c_load, S_c_wind, S_c_pv = 3, 3, 3
P_ess_max = 2.5
Q_vsc_max = 1
S_base = 10
V_min, V_max = 0.95, 1.05
gama = 0.8
S_ess = 10
Length = [
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
]

# 线路阻抗
r__ = [[0 for _ in range(n)] for _ in range(n)]
x__ = [[0 for _ in range(n)] for _ in range(n)]
r__vsc = [[0 for _ in range(n)] for _ in range(n)]
x__vsc = [[0 for _ in range(n)] for _ in range(n)]
for i in range(n):
    for j in range(n):
        if j != i:
            r__[i][j] = Length[i][j] * 0.0598
            r__vsc[i][j] = r__[i][j]+0.2889
            x__[i][j] = Length[i][j] * 0.0979
            x__vsc[i][j] = x__[i][j]+0.7548

# 线路选材成本和容量
c_l = [147.648e3, 295.296e3]
S_line_k = [2.5, 5]

# 节点资源情况
n__ac =   [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1]
n__dc =   [0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0]
n__wind = [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0]
n__pv =   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
n__ess =  [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
#          1  2  3  4  5  6  7  8  9 10 11 12 13

# 24小时P、Q,DG最大出力
P_load = [6.40,6.20,6.00,5.90,5.80,5.60,5.50,5.60,5.90,6.40,6.80,7.00,7.20,7.30,7.00,6.60,6.80,7.50,7.90,7.80,7.60,7.20,6.90,6.60]
DG_total=[6.20,6.00,5.80,5.60,5.50,5.40,5.50,5.20,4.80,4.60,4.50,4.70,5.00,5.50,6.20,6.80,7.00,6.30,6.50,6.40,6.10,6.00,6.20,6.50]
#           0    1    2    3    4    5    6    7    8    9    10   11   12   13   14   15   16   17   18   19   20   21   22   23
Q_load = [0 for _ in range(T)]
for i in range(T):
    P_load[i] = P_load[i] / (sum(n__ac) + sum(n__dc))
    Q_load[i] = P_load[i] * 0.619*0.8




import numpy as np
import random
import gurobipy as gb
import time









def Lower_layer_model_solving(W,U,x,L):

    m=gb.Model('m1')
    # 定义各节点电压
    V = m.addVars(n, T, lb=0.95, ub=1.05, vtype=gb.GRB.CONTINUOUS, name="V")
    V__svc = m.addVars(n, n, T, vtype=gb.GRB.CONTINUOUS, name="V__svc")
    for i in range(n):
        for j in range(i + 1, n):
            for t in range(T):
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])
                m.addConstr(V__svc[i, j, t] == V__svc[j, i, t])

    # 定义线路潮流
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
    for i in range(n):
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
    # 电压方程
    for i in range(n):
        for j in range(n):
            if i != j:
                #
                S_line = S_line_k[x[i][j]]
                for t in range(T):
                    m.addConstr(U[i][j]*((1-L[i][j]*W[i])*V[i,t]+(L[i][j]*W[i]-L[i][j]*W[j])*V__svc[i,j,t]-(1-L[i][j]*W[j])*V[j,t])==
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
# ---------------------------
# Helper: encode/decode chromosome
# ---------------------------
def upper_tri_indices(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]

def chromosome_length(n):
    m = len(upper_tri_indices(n))
    return n + 2 * m

def pack_chromosome(W, U, X):
    n = len(W)
    idxs = upper_tri_indices(n)
    chrom = []
    chrom.extend(W.tolist())
    for (i, j) in idxs:
        chrom.append(int(U[i, j]))
    for (i, j) in idxs:
        chrom.append(int(X[i, j]))
    return np.array(chrom, dtype=np.int8)

def unpack_chromosome(chrom, n):
    idxs = upper_tri_indices(n)
    m = len(idxs)
    W = chrom[:n].astype(int)
    U_flat = chrom[n:n + m].astype(int)
    X_flat = chrom[n + m:n + 2 * m].astype(int)
    U = np.zeros((n, n), dtype=int)
    X = np.zeros((n, n), dtype=int)
    for k, (i, j) in enumerate(idxs):
        U[i, j] = U_flat[k]
        U[j, i] = U_flat[k]
        X[i, j] = X_flat[k]
        X[j, i] = X_flat[k]
    return W, U, X

# ---------------------------
# 修复算子（Repair Operator）
# ---------------------------
def repair_U(U):
    """强制修复 U 使其满足 1 ≤ 行和 ≤ 3"""
    n = U.shape[0]
    for i in range(n):
        row_sum = U[i].sum()
        # 若行和 < 1，随机添加连接
        if row_sum < 1:
            zeros = [j for j in range(n) if j != i and U[i, j] == 0]
            if zeros:
                j = random.choice(zeros)
                U[i, j] = U[j, i] = 1
        # 若行和 > 3，随机删除多余连接
        elif row_sum > 3:
            ones = [j for j in range(n) if j != i and U[i, j] == 1]
            random.shuffle(ones)
            while U[i].sum() > 3 and ones:
                j = ones.pop()
                U[i, j] = U[j, i] = 0
    return U

# ---------------------------
# Problem-specific fitness
# ---------------------------
def compute_cost(W, U, X):
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
    f_op = Lower_layer_model_solving(W, U, X, L)


    # C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
    for d in range(T_p):
        C_operation += N_d * f_op / pow(1 + r, d + 1)
    for d in range(T_line):
        C_operation += beta_line * C_line / pow(1 + r, d + 1)
    for d in range(T_cvt):
        C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
    z = C_invest + C_operation
    return float(z)

def fitness_of_chromosome(chrom, n, cost_w, cost_u, cost_x):
    W, U, X = unpack_chromosome(chrom, n)
    U = repair_U(U)  # 修复可行性
    return compute_cost(W, U, X), W, U, X

# ---------------------------
# GA operators
# ---------------------------
def initial_population(pop_size, n):
    L = chromosome_length(n)
    pop = np.random.randint(0, 2, size=(pop_size, L), dtype=np.int8)
    return pop

def tournament_selection(pop, fitnesses, k=3):
    idxs = np.random.choice(len(pop), size=k, replace=False)
    return idxs[np.argmin(fitnesses[idxs])]

def uniform_crossover(parent1, parent2):
    mask = np.random.rand(parent1.size) < 0.5
    return np.where(mask, parent1, parent2).astype(np.int8)

def bitflip_mutation(chrom, mut_prob):
    mask = np.random.rand(chrom.size) < mut_prob
    chrom2 = chrom.copy()
    chrom2[mask] = 1 - chrom2[mask]
    return chrom2

# ---------------------------
# Main GA solver
# ---------------------------
def ga_solve(
    n,
    cost_w=None,
    cost_u=1.0,
    cost_x=1.0,
    pop_size=100,
    generations=50,
    mut_prob=0.01,
    early_stop_tol=1e-4,
    early_stop_patience=5,
    verbose=True,
    seed=None,
):
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)


    pop = initial_population(pop_size, n)

    best_fitness = float("inf")
    best_chrom = None
    no_improve = 0
    best_hist = []

    for gen in range(1, generations + 1):
        fitnesses = np.zeros(pop_size)
        for i in range(pop_size):
            z, W, U, X = fitness_of_chromosome(pop[i], n, cost_w, cost_u, cost_x)
            fitnesses[i] = z
            pop[i] = pack_chromosome(W, U, X)  # 重新打包修复后的可行个体

        cur_best_idx = np.argmin(fitnesses)
        cur_best_fit = fitnesses[cur_best_idx]

        if cur_best_fit < best_fitness - 1e-12:
            best_fitness = cur_best_fit
            best_chrom = pop[cur_best_idx].copy()
            best_z = cur_best_fit
            best_W, best_U, best_X = unpack_chromosome(best_chrom, n)
            no_improve = 0
        else:
            no_improve += 1

        best_hist.append(best_fitness)
        if verbose:
            print(f"Gen {gen:>3}  best_z={best_z:.6f}")

        if len(best_hist) > 1:
            if abs(best_hist[-1] - best_hist[-2]) < early_stop_tol:
                no_improve += 1
        if no_improve >= early_stop_patience:
            if verbose:
                print(f"Stopping early at generation {gen}.")
            break

        # reproduction
        new_pop = np.empty_like(pop)
        new_pop[0] = best_chrom.copy()  # elitism

        for k in range(1, pop_size):
            p1 = pop[tournament_selection(pop, fitnesses, k=3)]
            p2 = pop[tournament_selection(pop, fitnesses, k=3)]
            child = uniform_crossover(p1, p2)
            child = bitflip_mutation(child, mut_prob)
            # 修复子代可行性
            W, U, X = unpack_chromosome(child, n)
            U = repair_U(U)
            new_pop[k] = pack_chromosome(W, U, X)

        pop = new_pop

    result = {
        "W": best_W,
        "U": best_U,
        "X": best_X,
        "z": best_z,
        "generations_run": gen,
    }
    return result

# ---------------------------
# Example usage
# ---------------------------
if __name__ == "__main__":
    start_time = time.time()
    n = 13
    sol = ga_solve(
        n,
        pop_size=100,
        generations=50,
        mut_prob=0.02,
        seed=42,
        verbose=True,
    )
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"程序运行时间: {elapsed_time:.4f} 秒")
    print("\n=== 最终可行解 ===")
    print("W:", sol["W"])
    print("U:\n", sol["U"])
    print("行和:", sol["U"].sum(axis=1))
    print("X:\n", sol["X"])
    print(f"目标值 z = {sol['z']:.4f}")
