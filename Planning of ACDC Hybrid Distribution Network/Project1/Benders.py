{"id": "78640", "variant": "standard", "title": "Parallel Batch Logic-based Benders with 0-1 Tight Cuts"}
< content >
from gurobipy import Model, GRB
from concurrent.futures import ThreadPoolExecutor

# ============================
# 用户输入区域
# ============================

n_x = 5
x_ub = [1] * n_x
x_lb = [0] * n_x

n_y_int = 3
y_int_ub = [1] * n_y_int
y_int_lb = [0] * n_y_int

n_y_cont = 2
y_cont_ub = [10] * n_y_cont
y_cont_lb = [0] * n_y_cont


# 上层目标函数
def upper_level_obj(x_vals, theta_val):
    return theta_val + sum(x_vals)


# 下层目标函数
def subproblem_obj(y_int_vals, y_cont_vals, x_vals):
    return sum(y_cont_vals) + sum(y_int_vals) + sum(x_vals)


# 下层约束
def add_subproblem_constraints(SP, y_int_vars, y_cont_vars, x_vals):
    SP.addConstr(sum(y_cont_vars) >= sum(y_int_vars) - sum(x_vals))
    return SP


# ============================
# 主问题初始化
# ============================
MP = Model("master_problem")
x = MP.addVars(n_x, lb=x_lb, ub=x_ub, vtype=GRB.BINARY, name='x')
theta = MP.addVar(lb=-GRB.INFINITY, name='theta')
MP.setObjective(theta, GRB.MINIMIZE)

history_x = []
history_v = []

converged = False
iteration = 0


# ============================
# 子问题求解函数
# ============================
def solve_subproblem(x_val):
    SP = Model()
    SP.Params.OutputFlag = 0
    y_int = SP.addVars(n_y_int, lb=y_int_lb, ub=y_int_ub, vtype=GRB.INTEGER)
    y_cont = SP.addVars(n_y_cont, lb=y_cont_lb, ub=y_cont_ub, vtype=GRB.CONTINUOUS)
    SP = add_subproblem_constraints(SP, y_int, y_cont, x_val)
    SP.setObjective(sum(y_cont[i] for i in range(n_y_cont]) + sum(
        y_int[i].X if y_int[i].X else 0 for i in range(n_y_int]), GRB.MINIMIZE)
    SP.optimize()
    if SP.status == GRB.INFEASIBLE:
        return None, None, None
    y_int_val = [y_int[i].X for i in range(n_y_int)]
    y_cont_val = [y_cont[i].X for i in range(n_y_cont)]
    v_star = subproblem_obj(y_int_val, y_cont_val, x_val)
    return x_val, v_star, (y_int_val, y_cont_val)


# ============================
# 生成候选上层解（可根据策略生成多个）
# ============================
def generate_candidate_x(n_candidates=3):
    # 简单示例：在 x 范围内随机生成 n_candidates 个解
    # 可替换为启发式、剪枝或离散搜索策略
    from random import randint
    candidates = []
    for _ in range(n_candidates):
        candidates.append([randint(0, 1) for _ in range(n_x)])
    return candidates


# ============================
# 迭代循环
# ============================
while not converged:
    iteration += 1
    print(f"Iteration {iteration}: Solving Master Problem")
    MP.optimize()

    # 批量生成候选 x
    candidates = generate_candidate_x(n_candidates=5)

    # 并行求解子问题
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(solve_subproblem, c) for c in candidates]
        for f in futures:
            results.append(f.result())

    converged = True  # 默认收敛，若有 θ < v* 则翻转

    for x_val, v_star, y_solution in results:
        if x_val is None:
            continue
        if theta.X < v_star - 1e-6:
            converged = False
            # 添加 0-1 tight cut
            z = MP.addVar(vtype=GRB.BINARY, name="z_curr")
            for i in range(n_x):
                if x_val[i] > 0.5:
                    MP.addConstr(x[i] - z <= 0)
                else:
                    MP.addConstr(z - x[i] <= 0)
            MP.addConstr(theta >= v_star * z)
            history_x.append(x_val.copy())
            history_v.append(v_star)

    # 可行性切割（子问题 infeasible 时）
    for x_val, v_star, _ in results:
        if x_val is None:
            expr = sum((1 - x[i]) if x_val[i] > 0.5 else x[i] for i in range(n_x))
            MP.addConstr(expr >= 1)

print("Converged solution:")
print("x =", [x[i].X for i in range(n_x)])
print("theta =", theta.X)
