import numpy as np
from collections import deque
import pandas as pd

def find_parents_from_upper_triangular(name,upper_triangular_input, num_nodes=13, root_idx=0):

    # 构建完整的邻接矩阵
    adj_matrix = np.zeros((num_nodes, num_nodes), dtype=int)

    # 处理不同类型的输入
    if isinstance(upper_triangular_input, (list, np.ndarray)):
        if len(upper_triangular_input) == num_nodes * (num_nodes - 1) // 2:
            # 输入是上三角元素的列表
            idx = 0
            for i in range(num_nodes):
                for j in range(i + 1, num_nodes):
                    adj_matrix[i][j] = upper_triangular_input[idx]
                    adj_matrix[j][i] = upper_triangular_input[idx]  # 无向图
                    idx += 1
        elif upper_triangular_input.shape == (num_nodes, num_nodes):
            # 输入已经是矩阵形式，但可能只包含上三角部分的信息
            for i in range(num_nodes):
                for j in range(i + 1, num_nodes):
                    adj_matrix[i][j] = upper_triangular_input[i][j]
                    adj_matrix[j][i] = upper_triangular_input[i][j]
        else:
            raise ValueError(
                f"输入格式不正确。需要长度为{num_nodes * (num_nodes - 1) // 2}的列表或{num_nodes}x{num_nodes}的矩阵")
    else:
        raise ValueError("输入必须是列表或numpy数组")

    # 使用BFS从根节点开始遍历，构建树并确定父节点
    visited = [False] * num_nodes
    parents = [-1] * num_nodes
    parents[root_idx] = root_idx  # 根节点的父节点为自身
    visited[root_idx] = True

    queue = deque([root_idx])


    while queue:
        current = queue.popleft()

        # 找出所有相邻节点
        neighbors = []
        for i in range(num_nodes):
            if adj_matrix[current][i] == 1 and not visited[i]:
                neighbors.append(i)

        for neighbor in neighbors:
            visited[neighbor] = True
            parents[neighbor] = current
            queue.append(neighbor)

    # 检查是否所有节点都被访问到
    if not all(visited):
        print(f"\n警告: {name}不是所有节点都从根节点可达!")
        print()
        for i in range(num_nodes):
            if not visited[i]:
                print(f"节点 {i} 不可达")

    return parents




# 主函数
if __name__ == "__main__":
    data = pd.read_csv("训练数据_可行解.csv")
    Vals=data.iloc[:, :].values.tolist()
    for i in range(len(Vals)):
        a=Vals[i][:1+13]
        b=Vals[i][1+13:1+13+78]
        c=Vals[i][1+13+78:]
        bb = find_parents_from_upper_triangular(Vals[i][0],b)

        new_df = pd.DataFrame([a+bb+c])
        new_df.to_csv('训练数据_可行解_Tree.CSV', mode='a', header=False, index=False, encoding='utf-8')
        # print(new_df)
    #     new_df.to_csv('训练数据_可行解_Tree.CSV', mode='a', header=False, index=False, encoding='utf-8')
    # X = data.iloc[:, 1+13:1+13+78].values
    # custom_parents = find_parents_from_upper_triangular(X[0])
    # print(len(X[0]))
    # print(X[0])




    # print(f"\n自定义父节点向量: {custom_parents}")