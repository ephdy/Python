import itertools
import pandas as pd
import networkx as nx
from tqdm import tqdm

# -----------------------------
# 节点
# -----------------------------
N = 11
nodes = list(range(N))

# -----------------------------
# 候选支路（只保留0~10节点）
# -----------------------------
Branch_11 = [
    (0,1),(0,2),(0,4),

    (1,2),(1,3),(1,4),(1,6),

    (2,4),(2,5),(2,7),

    (3,4),(3,6),(3,8),

    (4,5),(4,6),(4,7),(4,9),

    (5,7),(5,10),

    (6,7),(6,8),(6,9),

    (7,9),(7,10),

    (8,9),

    (9,10)
]

m = len(Branch_11)

# -----------------------------
# 保存结果
# -----------------------------
results = []

# 树需要 n-1 条边
edge_num = N - 1

# 四种(mu, epsilon)
extra_pairs = [
    (0, 0),
    (0, 1),
    (1, 0),
    (1, 1)
]

# -----------------------------
# 枚举所有10边组合
# -----------------------------
all_combinations = itertools.combinations(range(m), edge_num)

for comb in tqdm(all_combinations):

    selected_edges = [Branch_11[i] for i in comb]

    # 建图
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(selected_edges)

    # 判断是否为树
    if not nx.is_tree(G):
        continue

    # 度约束
    degrees = dict(G.degree())

    feasible = True

    for node in nodes:
        d = degrees[node]

        if d < 1 or d > 3:
            feasible = False
            break

    if not feasible:
        continue

    # -----------------------------
    # 0-1线路向量
    # -----------------------------
    base_row = [0] * m

    for idx in comb:
        base_row[idx] = 1

    # -----------------------------
    # 每棵树扩展成4行
    # -----------------------------
    for mu, epsilon in extra_pairs:

        row = base_row.copy()

        row.append(mu)
        row.append(epsilon)

        results.append(row)

# -----------------------------
# 输出CSV
# -----------------------------
columns = [str(e) for e in Branch_11]
columns += ["mu", "epsilon"]

df = pd.DataFrame(results, columns=columns)

df.to_csv("trees_11nodes_mu_epsilon.csv", index=False)

print(f"共生成 {len(results)} 行数据")
print("已保存到 trees_11nodes_mu_epsilon.csv")