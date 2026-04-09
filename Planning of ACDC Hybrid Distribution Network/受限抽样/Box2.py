from _13_nodes_distribution_network import *
import gurobipy as gb
import csv
import itertools
import matplotlib.pyplot as plt
import numpy as np
import math
from datetime import datetime
import pandas as pd


def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')
def Loading_constraints(model,path,all_vars,num_vars):
    data=[]
    try:
        with open(path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)

            # 跳过第一行标题
            next(csv_reader, None)

            # 读取剩余的所有行
            for row in csv_reader:
                data.append(row)

    except FileNotFoundError:
        print(f"错误：文件 '{path}' 未找到")
    except Exception as e:
        print(f"读取文件时出错：{e}")
    for dt in data:
        model.addConstr(gb.quicksum((1 - all_vars[i]) if dt[i] == 1 else all_vars[i] for i in range(num_vars)) >= 1)
    print('Loaded!')
    return model

def get_X(model,Q,h,all_vars,num_vars):
    f=gb.quicksum(h[i] * all_vars[i] for i in range(n) if h[i] != 0)+gb.quicksum(
        Q[i][j] * all_vars[i] * all_vars[j]
        for i in range(n)
        for j in range(n)
        if Q[i][j] != 0
    )
    model.setObjective(f ,gb.GRB.MINIMIZE)
    model.optimize()
    if model.status != gb.GRB.OPTIMAL:
        return None
    return [1 if var.X > 0.5 else 0 for var in all_vars]

def save_csv(data,path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(path, mode='a', header=False, index=False, encoding='utf-8')

def Planning_sampling(N):

    master = gb.Model("UP_layer")
    # 定义规划变量
    # 定义节点类型变量
    # W = master.addVars(n, vtype=gb.GRB.BINARY, name="W")
    # master.addConstr(W[0] == 0)  # 根节点为交流
    # 定义节点连接变量
    U = {}
    for i,j in Branch:
        U[(i, j)] = master.addVar(vtype=gb.GRB.BINARY, name=f"U_{i}_{j}")

    for node in range(n):
        master.addConstr(
            sum(U[(i, j)] for i, j in Branch if i == node or j == node) <= L_max,
            name=f"degree_{node}"
        )
        master.addConstr(
            sum(U[(i, j)] for i, j in Branch if i == node or j == node) >= L_min,
            name=f"degree_{node}"
        )
    # master.addConstr(U[(0,1)]==0)
    F = {}
    for i, j in Branch:
        F[(i, j)] = master.addVar(lb=-len(nodes)+1, ub=len(nodes)-1, vtype=gb.GRB.CONTINUOUS, name=f"F_{i}_{j}")
    for node in nodes:
        if node == 0:
            # 根节点：流出 - 流入 = 总节点数-1
            master.addConstr(
                sum(F[(node, j)] for i, j in Branch if i == node) == len(nodes) - 1,
                name=f"flow_balance_{node}"
            )
        else:
            # 其他节点：流出 - 流入 = -1
            master.addConstr(
                sum(F[(i, node)] for i, j in Branch if j == node)-sum(F[(node, j)] for i, j in Branch if i == node)== 1,
                name=f"flow_balance_{node}"
            )

    # 流量与边选择的关系：如果边被选中，才能有流量
    for i, j in Branch:
        master.addConstr(F[(i, j)] <= len(nodes) * U[(i, j)], name=f"flow_+cap_{i}_{j}")
        master.addConstr(F[(i, j)] >= -len(nodes) * U[(i, j)], name=f"flow_-cap_{i}_{j}")
    master.addConstr(
        sum(U[(i, j)] for i, j in Branch) == n - 1,
        name="edges_count"
    )


    master.setParam('OutputFlag', 0)
    all_vars = []
    for i, j in Branch:
        all_vars.append(U[(i, j)])

    num_vars=len(all_vars)
    samples = 0
    master.setParam("Threads", 0)
    master=Loading_constraints(master, '受限邻接矩阵.CSV', all_vars,num_vars)
    # k=0
    while samples < N:
        # if k>7:
        #     k=0
        #     print(datetime.now())
        # else:
        #     k+=1
        h = np.random.uniform(-1, 1, num_vars)
        A = np.random.rand(num_vars, 13) * 2 - 1
        Temp = A.T @ A
        Q = Temp / np.max(np.abs(Temp))
        X = get_X(master, Q, h, all_vars, num_vars)
        master.reset(clearall=1)
        if X==None:
            print('X=None')
        else:
            save_csv(X, '受限邻接矩阵NEW.CSV')
            master.addConstr(gb.quicksum((1 - all_vars[i]) if X[i] == 1 else all_vars[i] for i in range(num_vars)) >= 1)
            samples +=1
        if samples >= N:
            break

def get_W():
    # 后11列的所有可能组合
    remaining_cols = 11

    all_combinations = []
    for bits in itertools.product([0, 1], repeat=remaining_cols):
        # 每行格式：[0, 0] + 当前组合
        S = 0
        print(bits)
        for i in range(2, n):
            S += 3 * ((n__ac[i - 2] * bits[i - 2]) + n__ac[i] * (1 - bits[i - 2]))
            S += 3 * (2 - bits[i - 2])
        row = [0, 0] + list(bits) + [S]
        all_combinations.append(row)

    print(f"总共生成了 {len(all_combinations)} 种组合")

    # 保存到CSV文件
    csv_filename = "all_combinations_13cols.csv"
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)

        # 写入表头
        headers = [f"列{i + 1}" for i in range(13)]
        writer.writerow(headers)

        # 写入所有组合
        writer.writerows(all_combinations)

    print(f"数据已保存到 {csv_filename}")

    # 显示前10行作为示例
    print("\n前10行示例：")
    for i, row in enumerate(all_combinations[:10]):
        print(f"行{i + 1}: {row}")

    return all_combinations

def Draw_Grid(U=None,W=None):
    if W is None:
        W = [0] * len(coordinate)
    elif len(W) != len(coordinate):
        W = [0] * len(coordinate)
    # 根据W值设置颜色
    colors = ['blue' if w == 0 else 'red' for w in W]

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

    # 分离坐标
    x = [p[0] for p in coordinate]
    y = [p[1] for p in coordinate]

    # 分别绘制圆点和三角形，以便添加图例
    circle_x = [x[i] for i in range(len(x)) if n__wind[i] == 0 and n__pv[i]==0]
    circle_y = [y[i] for i in range(len(y)) if n__wind[i] == 0 and n__pv[i]==0]
    triangle_x = [x[i] for i in range(len(x)) if n__wind[i] == 1 or n__pv[i]==1]
    triangle_y = [y[i] for i in range(len(y)) if n__wind[i] == 1 or n__pv[i]==1]


    # 设置颜色
    colors = ['blue' if w == 0 else 'red' for w in W]
    colors_circle=[colors[i] for i in range(len(colors)) if n__wind[i] == 0 and n__pv[i]==0]
    colors_triangle =[colors[i] for i in range(len(colors)) if n__wind[i] == 1 or n__pv[i]==1]

    # 绘图
    fig, ax = plt.subplots(figsize=(12, 10))

    edges=[]
    if U is not None:
        for i in range(len(U)):
            if U[i] == 1:
                edges.append(Branch[i])
    print(edges)
    # 绘制边
    if edges is not None:
        for edge in edges:
            if isinstance(edge, (tuple, list)) and len(edge) == 2:
                i, j = edge
                # i,j直接从0开始，不需要减1
                xi, yi = coordinate[i]
                xj, yj = coordinate[j]

                # 计算两点之间的距离
                dist = math.sqrt((xj - xi) ** 2 + (yj - yi) ** 2)

                # 如果两点距离较远，使用弯曲曲线
                if dist > q * 1.5:
                    # 计算中点
                    mx = (xi + xj) / 2
                    my = (yi + yj) / 2

                    # 计算垂直方向偏移
                    dx = xj - xi
                    dy = yj - yi
                    perp_x = -dy
                    perp_y = dx
                    length = math.sqrt(perp_x ** 2 + perp_y ** 2)
                    if length > 0:
                        perp_x /= length
                        perp_y /= length

                    # 弯曲程度
                    curvature = dist * 0.3
                    offset_x = perp_x * curvature
                    offset_y = perp_y * curvature

                    # 贝塞尔曲线控制点
                    ctrl1_x = mx - offset_x * 0.5
                    ctrl1_y = my - offset_y * 0.5
                    ctrl2_x = mx + offset_x * 0.5
                    ctrl2_y = my + offset_y * 0.5

                    # 绘制贝塞尔曲线
                    from matplotlib.path import Path
                    import matplotlib.patches as patches

                    verts = [(xi, yi), (ctrl1_x, ctrl1_y), (ctrl2_x, ctrl2_y), (xj, yj)]
                    codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
                    path = Path(verts, codes)
                    patch = patches.PathPatch(path, facecolor='none', edgecolor='gray',
                                              linewidth=1.5, alpha=0.6)
                    ax.add_patch(patch)
                else:
                    # 距离较近，画直线
                    ax.plot([xi, xj], [yi, yj], 'gray', linewidth=1.5, alpha=0.6)

    # # 绘制点
    # ax.scatter(x, y, c=colors, s=200, edgecolors='black', linewidth=1.5, zorder=5)

    # 绘制圆点
    if circle_x:
        ax.scatter(circle_x, circle_y, marker='o', c=colors_circle, s=150,
                    edgecolors='black', linewidth=1.5, zorder=5, label='n[i]=0 (圆点)')

        # 绘制三角形
    if triangle_x:
        ax.scatter(triangle_x, triangle_y, marker='^', c=colors_triangle, s=150,
                    edgecolors='black', linewidth=1.5, zorder=5, label='n[i]=1 (三角形)')

    # 添加标签（节点编号从0开始）
    for i, (xi, yi) in enumerate(coordinate):
        ax.annotate(str(i), (xi, yi), xytext=(8, 8), textcoords='offset points',
                    fontsize=12, fontweight='bold')

    # 设置图形
    ax.grid(True, alpha=0.3)
    margin = q * 0.5
    ax.set_xlim(-margin, max(x) + margin)
    ax.set_ylim(-margin, max(y) + margin)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(f'13 Points (Nodes 0-12, q={q})', fontsize=14)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')

    plt.tight_layout()
    plt.show()
    pass


def Operation(U_limited,f_DG):#潮流
    W=[0,0,0,0,0,0,0,0,0,0,0,0,0]
    C=[[1 for _ in range(n)] for _ in range(n)]
    U = [[0 for _ in range(n)] for _ in range(n)]
    for edge in range(len(U_limited)):
        if U_limited[edge] ==1:
            (i,j)=Branch[edge]
            U[i][j] = 1
            U[j][i] = 1

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
        m.addConstr(Q_DG[9,t] <= 2.0)
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
    f_op = 0
    for t in range(T):
        f_op += c_s * P_buy[t]
        f_op += c_e * (P_ess_ch[t] + P_ess_dis[t])
        f_op += c_d * (DG_total[t] * 2.0 / 9 *f_DG - P_DG[(7, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 *f_DG - P_DG[(8, t)])
        f_op += c_d * (DG_total[t] * 2.5 / 9 *f_DG - P_DG[(10, t)])
        f_op += c_d * (DG_total[t] * 2.0 / 9 *f_DG - P_DG[(12, t)])

    m.setParam("OutputFlag", 0)

    m.setParam("Threads", 0)
    m.setObjective(f_op, gb.GRB.MINIMIZE)

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
        return [m.objVal,C_buy,C_DG,C_ess]
    else:
        return [m.status]
