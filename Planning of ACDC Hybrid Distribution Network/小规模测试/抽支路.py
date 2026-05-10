from itertools import combinations

# 所有点 0~6
nodes = list(range(7))

# 仅涉及0~6的候选边
edges = [
    (0,1), (0,2), (0,4),
    (1,2), (1,3), (1,4), (1,6),
    (2,4), (2,5),
    (3,4), (3,6),
    (4,5), (4,6)
]

# 判断连通性（BFS）
def is_connected(selected_edges):
    if not selected_edges:
        return False
    adj = {v: [] for v in nodes}
    for u, v in selected_edges:
        adj[u].append(v)
        adj[v].append(u)
    visited = set()
    stack = [nodes[0]]
    while stack:
        v = stack.pop()
        if v not in visited:
            visited.add(v)
            for nb in adj[v]:
                if nb not in visited:
                    stack.append(nb)
    return len(visited) == len(nodes)

# 度数条件检查
def degree_ok(selected_edges):
    deg = {v: 0 for v in nodes}
    for u, v in selected_edges:
        deg[u] += 1
        deg[v] += 1
    return all(1 <= deg[v] <= 3 for v in nodes)

# 枚举所有子图并计数
count = 0
valid_graphs = []

for r in range(6, 11):  # 树至少6边，最大边数受度数≤3限制
    for edge_set in combinations(edges, r):
        if degree_ok(edge_set) and is_connected(edge_set):
            count += 1
            valid_graphs.append(edge_set)

print(f"符合条件的连通网络数量: {count}")