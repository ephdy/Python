import random
import networkx as nx
from itertools import combinations
from collections import Counter
import numpy as np
def generate_connected_network_with_degree_constraint(candidate_branches, min_degree=1, max_degree=3, seed=None):
    """
    从候选支路中随机选择支路组成全连通网络，且每个节点度数满足约束

    参数:
    candidate_branches: 候选支路列表，每个元素为(node1, node2)
    min_degree: 最小度数，默认为1
    max_degree: 最大度数，默认为3
    seed: 随机种子，用于结果可重现

    返回:
    selected_indices: 被选择的支路对应的0/1列表，1表示选择，0表示不选择
    selected_branches: 被选择的支路列表
    G: 生成的网络图
    """
    if seed is not None:
        random.seed(seed)

    # 获取所有节点
    all_nodes = set()
    for branch in candidate_branches:
        all_nodes.add(branch[0])
        all_nodes.add(branch[1])
    n_nodes = len(all_nodes)

    # 验证最小度数约束的可行性：对于n个节点的连通图，至少需要n-1条边
    # 如果每个节点度数至少为min_degree，则总边数至少为 ceil(n * min_degree / 2)
    min_edges_needed = max(n_nodes - 1, (n_nodes * min_degree + 1) // 2)
    if min_edges_needed > len(candidate_branches):
        raise ValueError(f"候选支路数量不足以满足最小度数约束！需要至少{min_edges_needed}条边")

    max_attempts = 1000  # 最大尝试次数
    for attempt in range(max_attempts):
        # 初始化
        G = nx.Graph()
        G.add_nodes_from(all_nodes)
        selected_indices = [0] * len(candidate_branches)
        selected_branches = []

        # 计算每个节点的当前度数
        degree_count = {node: 0 for node in all_nodes}

        # 创建边索引列表并随机打乱
        edge_indices = list(range(len(candidate_branches)))
        random.shuffle(edge_indices)

        # 第一步：使用改进的Kruskal算法确保连通性，同时考虑度数约束
        parent = {node: node for node in all_nodes}

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            root_x = find(x)
            root_y = find(y)
            if root_x != root_y:
                parent[root_x] = root_y
                return True
            return False

        # 选择边确保连通性，同时遵守度数约束
        for idx in edge_indices:
            u, v = candidate_branches[idx]

            # 检查度数约束
            if degree_count[u] >= max_degree or degree_count[v] >= max_degree:
                continue

            # 如果这条边能连接两个不同的连通分量，且满足度数约束
            if find(u) != find(v):
                if union(u, v):
                    selected_indices[idx] = 1
                    selected_branches.append((u, v))
                    G.add_edge(u, v)
                    degree_count[u] += 1
                    degree_count[v] += 1

        # 检查是否所有节点都已连通
        components = list(nx.connected_components(G))

        # 如果还有多个连通分量，尝试用剩余的边连接它们
        if len(components) > 1:
            for idx in edge_indices:
                if selected_indices[idx] == 1:
                    continue

                u, v = candidate_branches[idx]

                # 检查度数约束
                if degree_count[u] >= max_degree or degree_count[v] >= max_degree:
                    continue

                # 如果这条边连接不同的连通分量
                if find(u) != find(v):
                    if union(u, v):
                        selected_indices[idx] = 1
                        selected_branches.append((u, v))
                        G.add_edge(u, v)
                        degree_count[u] += 1
                        degree_count[v] += 1

                        # 重新检查连通分量
                        components = list(nx.connected_components(G))
                        if len(components) == 1:
                            break

        # 第二步：确保所有节点满足最小度数约束
        if len(components) == 1:  # 图是连通的
            nodes_need_edges = [node for node in all_nodes if degree_count[node] < min_degree]

            # 尝试为度数不足的节点添加边
            success = True
            for node in nodes_need_edges:
                edges_added = 0
                # 找到所有包含该节点且未被选择的候选边
                candidate_edges_for_node = [
                    (idx, u, v) for idx, (u, v) in enumerate(candidate_branches)
                    if (u == node or v == node) and selected_indices[idx] == 0
                       and degree_count[u] < max_degree and degree_count[v] < max_degree
                ]

                random.shuffle(candidate_edges_for_node)

                for idx, u, v in candidate_edges_for_node:
                    if degree_count[node] >= min_degree:
                        break

                    other_node = v if u == node else u
                    if degree_count[other_node] < max_degree:
                        selected_indices[idx] = 1
                        selected_branches.append((u, v))
                        G.add_edge(u, v)
                        degree_count[u] += 1
                        degree_count[v] += 1
                        union(u, v)
                        edges_added += 1

                # 检查是否满足最小度数
                if degree_count[node] < min_degree:
                    success = False
                    break

            # 第三步：验证所有节点的度数约束并可选添加额外边
            if success:
                # 验证度数约束
                degree_check = all(min_degree <= degree_count[node] <= max_degree
                                   for node in all_nodes)

                if degree_check:
                    # 可选的第四步：随机添加一些额外边（仍遵守度数约束）
                    remaining_edges = [(idx, u, v) for idx, (u, v) in enumerate(candidate_branches)
                                       if selected_indices[idx] == 0
                                       and degree_count[u] < max_degree
                                       and degree_count[v] < max_degree]

                    random.shuffle(remaining_edges)

                    # 随机添加额外边，概率可调整
                    for idx, u, v in remaining_edges:
                        if random.random() < 0.2:  # 20%概率添加额外边
                            selected_indices[idx] = 1
                            selected_branches.append((u, v))
                            G.add_edge(u, v)
                            degree_count[u] += 1
                            degree_count[v] += 1
                        if random.random() < 0.1:  # 20%概率添加额外边
                            selected_indices[idx] = 1
                            selected_branches.append((u, v))
                            G.add_edge(u, v)
                            degree_count[u] += 1
                            degree_count[v] += 1

                    # 最终验证
                    final_degree_check = all(min_degree <= degree_count[node] <= max_degree
                                             for node in all_nodes)

                    if final_degree_check and nx.is_connected(G):
                        return selected_indices, selected_branches, G, degree_count

        # 如果这次尝试失败，继续下一次尝试
        if attempt == max_attempts - 1:
            print(f"警告：经过{max_attempts}次尝试后仍未找到可行解")

    return None, None, None, None


# 原始候选支路数据
Branch = [(0, 1), (0, 2), (0, 4),
          (1, 2), (1, 3), (1, 4), (1, 6),
          (2, 4), (2, 5), (2, 7),
          (3, 4), (3, 6), (3, 8),
          (4, 5), (4, 6), (4, 7), (4, 9),
          (5, 7), (5, 10),
          (6, 7), (6, 8), (6, 9), (6, 11),
          (7, 9), (7, 10), (7, 12),
          (8, 9), (8, 11),
          (9, 10), (9, 11), (9, 12),
          (10, 12),
          (11, 12)]

# 生成满足度数约束的随机全连通网络
print("正在生成满足度数约束的网络...")
selected_indices, selected_branches, G, degree_count = generate_connected_network_with_degree_constraint(
    Branch, min_degree=1, max_degree=3, seed=None
)

# 运行1000次统计边数分布
edge_counts = []
success_count = 0
fail_count = 0

# for i in range(1000):
#     selected_indices, selected_branches, G, degree_count = generate_connected_network_with_degree_constraint(
#         Branch, min_degree=1, max_degree=3, seed=None
#     )
#     if selected_indices is not None:
#         edge_counts.append(sum(selected_indices))
#         success_count += 1
#     else:
#         fail_count += 1

# # 统计结果
# counter = Counter(edge_counts)
# print(f"\n成功生成次数: {success_count}")
# print(f"失败次数: {fail_count}")
# print(f"\n边数分布统计:")
# print(f"{'边数':<6} {'出现次数':<10} {'占比':<10}")
# print("-" * 30)
# for edge_num in sorted(counter.keys()):
#     count = counter[edge_num]
#     percentage = count / success_count * 100
#     print(f"{edge_num:<6} {count:<10} {percentage:<10.2f}%")

def make_random_individual():
    S=np.random.randint(0, 2, size=(13,))
    selected_indices, selected_branches, G, degree_count = generate_connected_network_with_degree_constraint(
        Branch, min_degree=1, max_degree=3, seed=None
    )
    D=np.random.randint(0, 2, size=(3,))
    return [int(x) for x in np.concatenate([S, selected_indices, D])]
print(make_random_individual())




if selected_indices:
    print("\n=== 生成的网络信息 ===")
    print(f"选择的支路索引（0/1列表）：")
    print(selected_indices)
    print(f"\n总共选择了 {sum(selected_indices)} 条支路，共 {len(Branch)} 条候选支路")
    print(f"选择的支路：{selected_branches}")

    print("\n各节点度数：")
    for node in sorted(degree_count.keys()):
        status = "✓" if 1 <= degree_count[node] <= 3 else "✗"
        print(f"节点 {node}: 度数 = {degree_count[node]} {status}")

    # 验证连通性
    print(f"\n网络连通性: {'✓ 全连通' if nx.is_connected(G) else '✗ 不连通'}")

    # 验证度数约束
    all_degree_ok = all(1 <= degree_count[node] <= 3 for node in degree_count)
    print(f"度数约束满足: {'✓ 全部满足' if all_degree_ok else '✗ 存在违规'}")

    # 可视化（可选）
    import matplotlib.pyplot as plt


    def Draw_Grid(U=None, W=None):
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
        circle_x = [x[i] for i in range(len(x)) if n__wind[i] == 0 and n__pv[i] == 0]
        circle_y = [y[i] for i in range(len(y)) if n__wind[i] == 0 and n__pv[i] == 0]
        triangle_x = [x[i] for i in range(len(x)) if n__wind[i] == 1 or n__pv[i] == 1]
        triangle_y = [y[i] for i in range(len(y)) if n__wind[i] == 1 or n__pv[i] == 1]

        # 设置颜色
        colors = ['blue' if w == 0 else 'red' for w in W]
        colors_circle = [colors[i] for i in range(len(colors)) if n__wind[i] == 0 and n__pv[i] == 0]
        colors_triangle = [colors[i] for i in range(len(colors)) if n__wind[i] == 1 or n__pv[i] == 1]

        # 绘图
        fig, ax = plt.subplots(figsize=(12, 10))

        edges = []
        if U is not None:
            for i in range(len(U)):
                if U[i] == 1:
                    edges.append(Branch[i])

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



else:
    print("未能生成满足所有约束的网络，请检查约束条件是否合理")