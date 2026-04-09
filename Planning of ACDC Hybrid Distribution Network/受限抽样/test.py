import Box2 as B
import numpy as np
import pandas as pd
import networkx as nx
from networkx.algorithms.tree.mst import SpanningTreeIterator
import csv
# data = pd.read_csv("spanning_trees.csv")
#
# X = data.iloc[:].values
# B.Draw_Grid(X[21424])

def shushu():
    import numpy as np

    nodes = list(range(13))
    edges = [(0, 1), (0, 2), (0, 4),
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

    n = len(nodes)

    # 邻接矩阵
    A = np.zeros((n, n))
    for i, j in edges:
        A[i][j] = 1
        A[j][i] = 1

    # 度矩阵
    D = np.diag(A.sum(axis=1))

    # 拉普拉斯矩阵
    L = D - A

    # 删除最后一行一列
    L_minor = L[:-1, :-1]

    # 行列式
    num_trees = round(np.linalg.det(L_minor))

    print(num_trees)

def zaoshu():
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

    # 创建图
    G = nx.Graph()
    G.add_edges_from(Branch)

    # 创建边到索引的映射（标准化边，确保 u < v）
    edge_to_index = {}
    for idx, (u, v) in enumerate(Branch):
        if u > v:
            u, v = v, u
        edge_to_index[(u, v)] = idx

    print(f"图信息:")
    print(f"  节点数: {G.number_of_nodes()}")
    print(f"  边数: {len(Branch)}")
    print(f"  需要选 {G.number_of_nodes() - 1} 条边构成生成树")
    print()

    # 使用 SpanningTreeIterator 枚举所有生成树
    print("开始枚举生成树...")
    import time
    start_time = time.time()

    # 创建迭代器
    spanning_tree_iterator = SpanningTreeIterator(G)

    # 打开CSV文件准备写入
    with open('spanning_trees.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # 写入表头（可选）
        header = [f'edge_{i}:{Branch[i]}' for i in range(len(Branch))]
        writer.writerow(header)

        count = 0
        # 遍历所有生成树
        for tree in spanning_tree_iterator:
            # 创建二进制向量，初始全0
            vector = [0] * len(Branch)

            # 将生成树中的边对应的位置设为1
            for u, v in tree.edges():
                # 标准化边的顺序
                if u > v:
                    u, v = v, u
                edge_key = (u, v)

                if edge_key in edge_to_index:
                    vector[edge_to_index[edge_key]] = 1
                else:
                    print(f"警告: 边 {edge_key} 不在 Branch 中")

            # 写入CSV
            writer.writerow(vector)
            count += 1

            # 每1000棵打印进度
            if count % 1000 == 0:
                elapsed = time.time() - start_time
                print(f"  已找到并写入 {count} 棵生成树，用时 {elapsed:.2f} 秒")

    end_time = time.time()
    print(f"\n完成！")
    print(f"总共找到 {count} 棵生成树")
    print(f"总用时: {end_time - start_time:.2f} 秒")
    print(f"数据已保存到 spanning_trees.csv")
zaoshu()

