import itertools
import pandas as pd
import networkx as nx

# 候选线路（固定顺序）
Branch = [
    (0,1),(0,2),(0,4),
    (1,2),(1,3),(1,4),(1,6),
    (2,4),(2,5),
    (3,4),(3,6),
    (4,5),(4,6)
]

n_nodes = 7

results = []

# 四种组合
extra_states = [
    (0,0),
    (0,1),
    (1,0),
    (1,1)
]

# 树结构：7节点 => 6条边
for selected_idx in itertools.combinations(range(len(Branch)), n_nodes - 1):

    # 构图
    G = nx.Graph()
    G.add_nodes_from(range(n_nodes))

    selected_edges = [Branch[i] for i in selected_idx]
    G.add_edges_from(selected_edges)

    # 判断是否为树
    if not nx.is_tree(G):
        continue

    # 度数约束：1 <= degree <= 3
    degrees = dict(G.degree())

    feasible = True
    for d in degrees.values():
        if d < 1 or d > 3:
            feasible = False
            break

    if not feasible:
        continue

    # 0-1支路向量
    base_row = [0] * len(Branch)

    for idx in selected_idx:
        base_row[idx] = 1

    # 每棵树扩展4行
    for mu, epsilon in extra_states:
        row = base_row + [mu, epsilon]
        results.append(row)

# 列名
columns = [str(b) for b in Branch] + ['mu', 'epsilon']

# DataFrame
df = pd.DataFrame(results, columns=columns)

# 保存
df.to_csv("trees_7nodes_expand.csv", index=False)

print(f"原始树数量: {len(results)//4}")
print(f"扩展后数据量: {len(df)}")
print("已保存为 trees_7nodes_expand.csv")