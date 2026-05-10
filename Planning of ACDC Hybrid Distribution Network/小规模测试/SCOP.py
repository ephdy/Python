def Operation3(X,f_DG):#潮流
    W,U,C= encode(X, n)


    m = gb.Model("mip1")

    # 定义换流支路
    L = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            L[i][j] = abs(W[i] - W[j])
    L = [[abs(W[i] - W[j]) for j in range(n)] for i in range(n)]

    # 构建支路列表
    root=0
    branches = []
    for i in range(n):
        for j in range(i + 1, n):
            if U[i][j] == 1:
                branches.append((i, j))
    # 构建网络的树形结构（从根节点开始BFS）
    parent = {}
    children = {i: [] for i in range(n)}
    visited = [False] * n
    queue = [root]
    visited[root] = True

    while queue:
        node = queue.pop(0)
        for i in range(n):
            if U[node][i] == 1 and not visited[i]:
                parent[i] = node
                children[node].append(i)
                visited[i] = True
                queue.append(i)

    # 定义各节点电压
    V = {}
    for t in range(T):
        for i in range(n):
            V[(i, t)] = m.addVar(lb=0.95**2, ub=1.05**2, vtype=gb.GRB.CONTINUOUS, name=f"V_{i}_{t}")

    # 定义线路潮流
    # 支路有功功率 P[i,j,t]
    P = {}
    # 支路无功功率 Q[i,j,t]
    Q = {}
    # 支路电流平方 I[i,j,t]
    I = {}
    # 换流电压 V_svc[i,j,t]
    V_svc = {}

    for i, j in branches:
        for t in range(T):
            P[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"P_{i}_{j}_{t}")
            Q[(i, j, t)] = m.addVar(lb=-1, ub=1, vtype=gb.GRB.CONTINUOUS, name=f"Q_{i}_{j}_{t}")
            I[(i, j, t)] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"I_{i}_{j}_{t}")
            V_svc[(i, j, t)] = m.addVar(lb=0, vtype=gb.GRB.CONTINUOUS, name=f"V_svc_{i}_{j}_{t}")
    m.update()
    # 购电功率
    P_buy={}
    Q_buy={}
    for t in range(T):
        P_buy[t] = m.addVar(lb=0, ub=10, vtype=gb.GRB.CONTINUOUS, name=f"P_buy_{t}")
        Q_buy[t] = m.addVar(lb=-4.8, ub=4.8, vtype=gb.GRB.CONTINUOUS, name=f"Q_buy_{t}")
    # 储能充放电功率
    P_ess_ch = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_ch")
    P_ess_dis = m.addVars(24, lb=0, vtype=gb.GRB.CONTINUOUS, name="P_ess_dis")
    alpha__dis = m.addVars(T, vtype=gb.GRB.BINARY)
    alpha__ch = m.addVars(T, vtype=gb.GRB.BINARY)
    E_k = m.addVars(T, lb=0.1 * S_ess, ub=0.9 * S_ess, vtype=gb.GRB.CONTINUOUS, name="E_k")
    # DG出力
    P_DG={}
    Q_DG={}
    for i in range(n):
        for t in range(T):
            if i in [7,12,8,10]:
                P_DG[(i,t)]=m.addVar(vtype=gb.GRB.CONTINUOUS,name=f"P_DG_{i}_{t}" )
                Q_DG[(i, t)] = m.addVar(vtype=gb.GRB.CONTINUOUS, name=f"Q_DG_{i}_{t}")
            else:
                P_DG[(i, t)] = 0
                Q_DG[(i, t)]=0
    for t in range(T):
        m.addConstr(P_DG[(7, t)] <= DG_total[t] * 2 / 9 *f_DG)
        m.addConstr(P_DG[(12, t)] <= DG_total[t] * 2 / 9 *f_DG)
        m.addConstr(P_DG[(8, t)] <= DG_total[t] * 2.5 / 9 *f_DG)
        m.addConstr(P_DG[(10, t)] <= DG_total[t] * 2.5 / 9 *f_DG)
        m.addConstr(Q_DG[(7,t)] <= 2.0)
        m.addConstr(Q_DG[(12, t)] <= 2.0)
        m.addConstr(Q_DG[(8, t)] <= 2.5)
        m.addConstr(Q_DG[(10, t)] <= 2.5)

    # 模型约束
    #1 节点功率平衡方程
    for k in range(n):
        for t in range(T):
            if k == root:
                # 根节点
                P_out = 0
                Q_out = 0

                for child in children[k]:
                    if (k, child) in [(a, b) for a, b in branches]:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in [(a, b) for a, b in branches]:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]

                m.addConstr(P_buy[t] == P_out * S_base, f"P_{k}_{t}")
                m.addConstr(Q_buy[t] == Q_out * S_base, f"Q_{k}_{t}")

            else:
                # 非根节点
                try:
                    parent_node = parent[k]
                except:
                    return None

                # 从父节点流入的功率
                if (parent_node, k) in [(a, b) for a, b in branches]:
                    P_in = P[(parent_node, k, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                    Q_in = Q[(parent_node, k, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(parent_node, k, t)]
                elif (k, parent_node) in [(a, b) for a, b in branches]:
                    P_in = -P[(k, parent_node, t)] - r_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                    Q_in = -Q[(k, parent_node, t)] - x_line[parent_node][k][L[parent_node][k]] * I[(k, parent_node, t)]
                else:
                    continue

                # 流出到子节点的功率
                P_out = 0
                Q_out = 0
                for child in children[k]:
                    if (k, child) in [(a, b) for a, b in branches]:
                        P_out += P[(k, child, t)]
                        Q_out += Q[(k, child, t)]
                    elif (child, k) in [(a, b) for a, b in branches]:
                        P_out -= P[(child, k, t)]
                        Q_out -= Q[(child, k, t)]

                P_total=P_DG[(k, t)] + (P_ess_dis[t] - P_ess_ch[t])*n__ess[k] -P_load[t] * (n__ac[k] + n__dc[k])
                Q_total=Q_DG[k, t] -Q_load[t] * (n__ac[k] + n__dc[k])
                m.addConstr(P_in * S_base + P_total == P_out * S_base , f"P_{k}_{t}")
                m.addConstr(Q_in * S_base + Q_total == Q_out * S_base, f"Q_{k}_{t}")

    #
    #2 电压方程

    for i, j in branches:
        for t in range(T):
            m.addConstr(V_svc[i, j, t] >= V_min ** 2 * L[i][j])
            m.addConstr(V_svc[i, j, t] <= W[i]*V[i,t] + W[j]*V[j,t])

            R=r_line[i][j][L[i][j]]
            X=x_line[i][j][L[i][j]]

            f = L[i][j] * W[i]
            e=1-f
            g = L[i][j] * W[j]
            h=1-g
            if j in parent and parent[j] == i:
                # i是父节点，j是子节点
                m.addConstr(
                    2 * (R * P[(i, j, t)] + X * Q[(i, j, t)])-(R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e*V[(i, t)] + (f-g) * V_svc[(i,j,t)] - h*V[(j, t)],
                    f"Vc_{i}_{j}_{t}"
                )
            elif i in parent and parent[i] == j:
                # j是父节点，i是子节点
                m.addConstr(
                    - 2 * (R * P[(i, j, t)] + X * Q[(i, j, t)]) - (R ** 2 + X ** 2) * I[(i, j, t)] ==
                    e*V[(j, t)] + (f-g) * V_svc[(i,j,t)]- h*V[(i, t)],
                    f"Vc_{i}_{j}_{t}"
                )
    #2 二阶锥约束
    for i, j in branches:
        for t in range(T):
            # 确定父节点
            if j in parent and parent[j] == i:
                parent_node = i
            elif i in parent and parent[i] == j:
                parent_node = j
            else:
                parent_node = i

            # 旋转锥约束
            m.addQConstr(
                I[(i, j, t)] * V[(parent_node, t)] >=
                P[(i, j, t)] * P[(i, j, t)] + Q[(i, j, t)] * Q[(i, j, t)],
                f"soc_{i}_{j}_{t}"
            )

    #3 VSC无功补偿能力约束
    for i, j in branches:
        for t in range(T):
            m.addConstr(Q[(i, j, t)] <= L[i][j] * (Q_vsc_max-M) + M)

    # 4 系统安全运行约束
    for i, j in branches:
        S_line = 2.5 + 2.5 * C[i][j]
        for t in range(T):
            m.addConstr(P[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(P[(i, j, t)] * S_base >= -gama * S_line)

            m.addConstr(Q[(i, j, t)] * S_base <= gama * S_line)
            m.addConstr(Q[(i, j, t)] * S_base >= -gama * S_line)

            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] + Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] <= 1.41 * gama * S_line / S_base)
            m.addConstr(P[(i, j, t)] - Q[(i, j, t)] >= -1.41 * gama * S_line / S_base)

    # 5 储能约束
    m.addConstr(E_k[0] == 5)
    m.addConstr(P_ess_ch[0] == 0)
    m.addConstr(P_ess_dis[0] == 0)
    for t in range(T):
        m.addConstr(alpha__ch[t] + alpha__dis[t] <= 1)
        m.addConstr(P_ess_dis[t] <= alpha__dis[t] * P_ess_max)
        m.addConstr(P_ess_ch[t] <= alpha__ch[t] * P_ess_max)
        if t != 0:
            m.addConstr(E_k[t] == E_k[t-1] + P_ess_ch[t] * 0.9 - P_ess_dis[t] / 0.9)
    m.addConstr(gb.quicksum(P_ess_ch) * 0.9 == gb.quicksum(P_ess_dis) / 0.9)
    #m.addConstr(E_k[0] == E_k[T - 1])

    # 目标函数

    # 投资成本
    # C_line = 0
    # S_vsc = 0
    # S_c = 0
    # for i in range(n):
    #     S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
    #     S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
    #     S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
    #     for j in range(n):
    #         S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
    #         C_line += 0.5 * c_l[C[i][j]] * Length[i][j] * U[i][j]
    # C_cvt = c_c * S_c + c_v * S_vsc
    # C_invest = C_line + C_cvt


    # 运行成本
    # C_operation = 0
    f_op = 0


    for t in range(T):
        f_op += c_s * P_buy[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
        f_op += c_d * (DG_total[t] * 2.0 / 9 *f_DG - P_DG[(7, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 *f_DG - P_DG[(8, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 *f_DG - P_DG[(10, t)])
        f_op += c_d * (DG_total[t] * 2.0 / 9 *f_DG - P_DG[(12, t)])

    # for d in range(T_p):
    #     C_operation += N_d * f_op / pow(1 + r, d + 1)
    # for d in range(T_line):
    #     C_operation += beta_line * C_line / pow(1 + r, d + 1)
    # for d in range(T_cvt):
    #     C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
    m.setParam("OutputFlag", 0)

    m.setParam("Threads", 0)
    m.setObjective(f_op, gb.GRB.MINIMIZE)
    # 检查问题规模
    # print(f"变量数: {m.numVars}")
    # print(f"约束数: {m.numConstrs}")
    # print(f"非零元素: {m.numNZs}")
    # m.Params.Threads = 0  # 0表示自动选择最优线程数
    # 针对不同问题类型优化参数
    # m.Params.Method = 2        # 内点法对于大规模问题可能更好
    # m.Params.Crossover = 0     # 禁用交叉，对于纯线性问题
    # m.Params.Presolve = 2      # 积极的预处理
    # m.Params.MIPFocus = 1      # 侧重找到更好可行解
    # m.computeIIS()
    # m.write("model.ilp")
    m.optimize()
    if m.status == gb.GRB.INFEASIBLE:
        print("模型不可行，正在计算 IIS...")
        m.computeIIS()  # 计算不可约不一致子系统
        m.write("model_iis.ilp")  # 导出为 ILP 文件
        print("IIS 已导出至 'model_iis.ilp'")
    if m.status == gb.GRB.OPTIMAL:
        C_buy = 0
        C_ess = 0
        C_DG = 0

        # 提取变量值并计算成本
        for t in range(T):
            # 获取购电变量值
            P_buy_t = P_buy[t].X if hasattr(P_buy[t], 'X') else P_buy[t]
            C_buy += c_s * P_buy_t

            # 获取储能充放电变量值
            P_ess_ch_t = P_ess_ch[t].X if hasattr(P_ess_ch[t], 'X') else P_ess_ch[t]
            P_ess_dis_t = P_ess_dis[t].X if hasattr(P_ess_dis[t], 'X') else P_ess_dis[t]
            C_ess += c_e * (P_ess_ch_t + P_ess_dis_t)

            # 计算 DG 成本（注意：这里的逻辑可能需要根据实际情况调整）
            # 假设 DG_total[t] 是已知参数，f_DG 是已知参数
            term1 = DG_total[t] * 2.0 / 9 * f_DG - P_DG[(7, t)].X
            term2 = DG_total[t] * 2.5 / 9 * f_DG - P_DG[(8, t)].X
            term3 = DG_total[t] * 2.5 / 9 * f_DG - P_DG[(10, t)].X
            term4 = DG_total[t] * 2.0 / 9 * f_DG - P_DG[(12, t)].X

            C_DG += c_d * (term1 + term2 + term3 + term4)
        return [m.objVal,C_buy,C_ess,C_DG]
    else:
        return None
