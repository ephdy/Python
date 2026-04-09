import itertools
import csv
import time
from collections import defaultdict, deque


def is_connected(nodes, edges):
    """检查图是否全连通"""
    if not nodes:
        return True

    # 构建邻接表
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)

    # BFS检查连通性
    visited = set()
    start = nodes[0]
    queue = deque([start])
    visited.add(start)

    while queue:
        node = queue.popleft()
        for neighbor in adj[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return len(visited) == len(nodes)


def check_degree_constraints(edges, nodes, max_degree=3, min_degree=1):
    """检查所有节点度数是否在[min_degree, max_degree]范围内"""
    degree = defaultdict(int)
    for u, v in edges:
        degree[u] += 1
        degree[v] += 1

    # 检查所有节点是否都在度数范围内
    for node in nodes:
        if degree[node] < min_degree or degree[node] > max_degree:
            return False
    return True


def edges_to_string(edges):
    """将边集转换为字符串格式"""
    return ";".join([f"({u},{v})" for u, v in sorted(edges)])


def enumerate_and_save_to_csv(nodes, candidate_edges, csv_filename, min_degree=1, max_degree=3, save_interval=1000):
    """枚举所有满足条件的连通图并实时保存到CSV"""

    # 创建CSV文件并写入表头
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['graph_id', 'edge_count', 'edges', 'timestamp'])

    valid_count = 0
    seen = set()
    total_candidates = len(candidate_edges)

    # 记录开始时间和上次保存时间
    start_time = time.time()
    last_save_time = start_time

    # 从选择最小边数到最大边数进行枚举
    min_edges = len(nodes) - 1  # 至少需要这么多边才能连通
    max_edges = len(candidate_edges)

    print(f"节点数: {len(nodes)}")
    print(f"候选边数: {len(candidate_edges)}")
    print(f"最小边数: {min_edges}, 最大边数: {max_edges}")
    print(f"开始枚举...")
    print(f"结果将保存到: {csv_filename}")
    print("=" * 60)

    for r in range(min_edges, max_edges + 1):
        print(f"\n正在尝试选择 {r} 条边...")
        combination_count = 0
        r_start_time = time.time()

        for edge_subset in itertools.combinations(candidate_edges, r):
            combination_count += 1

            # 每检查10万种组合打印一次进度
            if combination_count % 100000 == 0:
                elapsed = time.time() - r_start_time
                print(f"  已检查 {combination_count} 种组合，用时 {elapsed:.2f} 秒")

            # 转换为边列表
            edges_list = list(edge_subset)

            # 检查度数约束
            if not check_degree_constraints(edges_list, nodes, max_degree, min_degree):
                continue

            # 检查连通性
            if not is_connected(nodes, edges_list):
                continue

            # 去重并保存
            graph_key = tuple(sorted(edges_list))
            if graph_key not in seen:
                seen.add(graph_key)
                valid_count += 1

                # 准备数据
                edges_str = edges_to_string(edges_list)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                # 立即写入CSV
                with open(csv_filename, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([valid_count, len(edges_list), edges_str, timestamp])

                # 每找到save_interval个图打印一次统计信息
                if valid_count % save_interval == 0:
                    current_time = time.time()
                    elapsed_total = current_time - start_time
                    elapsed_since_last = current_time - last_save_time
                    print(f"\n{'=' * 60}")
                    print(f"✓ 已找到 {valid_count} 个有效图")
                    print(f"  总用时: {elapsed_total:.2f} 秒")
                    print(f"  最近 {save_interval} 个图用时: {elapsed_since_last:.2f} 秒")
                    print(f"  平均每图: {elapsed_since_last / save_interval:.4f} 秒")
                    print(f"  当前边数: {r}")
                    print(f"  已检查组合数: {combination_count}")
                    print(f"{'=' * 60}\n")
                    last_save_time = current_time

        # 打印当前边数的统计
        r_elapsed = time.time() - r_start_time
        print(f"完成 {r} 条边的搜索，检查了 {combination_count} 种组合，用时 {r_elapsed:.2f} 秒")
        print(f"当前总共找到 {valid_count} 个有效图")

    # 最终统计
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"枚举完成！")
    print(f"共找到 {valid_count} 个满足条件的连通图")
    print(f"总用时: {total_time:.2f} 秒 ({total_time / 60:.2f} 分钟)")
    print(f"平均每图: {total_time / valid_count if valid_count > 0 else 0:.4f} 秒")
    print(f"结果已保存到: {csv_filename}")
    print("=" * 60)

    return valid_count


def quick_preview_csv(csv_filename, num_preview=10):
    """快速预览CSV文件的前几行"""
    try:
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            print(f"\nCSV文件预览 (前{num_preview}行):")
            print("-" * 80)
            for i, row in enumerate(reader):
                if i > num_preview:
                    break
                if i == 0:
                    print(f"表头: {row}")
                else:
                    print(f"图{row[0]}: 边数={row[1]}, 边={row[2][:100]}..." if len(
                        row[2]) > 100 else f"图{row[0]}: 边数={row[1]}, 边={row[2]}")
    except FileNotFoundError:
        print(f"文件 {csv_filename} 不存在")


# 给定的节点和候选边
nodes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
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

# 设置CSV文件名
csv_filename = "connected_graphs.csv"

# 开始枚举并保存
valid_count = enumerate_and_save_to_csv(
    nodes,
    Branch,
    csv_filename,
    min_degree=1,
    max_degree=3,
    save_interval=1000  # 每1000个图打印一次时间
)

# 预览结果
if valid_count > 0:
    quick_preview_csv(csv_filename, min(10, valid_count))