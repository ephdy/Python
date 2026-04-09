import networkx as nx
import pandas as pd
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt


def get_detailed_graph_info(G, branch_list):
    """
    获取图的详细信息
    """
    info = {
        'num_nodes': G.number_of_nodes(),
        'num_edges': G.number_of_edges(),
        'num_components': nx.number_connected_components(G),
        'is_connected': nx.is_connected(G),
        'is_tree': nx.is_tree(G),
        'is_forest': nx.is_forest(G),
    }

    # 计算环数
    if info['num_edges'] == 0:
        info['cyclomatic'] = 0
    else:
        info['cyclomatic'] = info['num_edges'] - info['num_nodes'] + info['num_components']

    # 获取各连通分量的信息
    components = list(nx.connected_components(G))
    info['component_sizes'] = [len(c) for c in components]

    # 检查是否有自环或重边（本数据应该没有）
    info['has_self_loops'] = nx.number_of_selfloops(G) > 0

    return info


def analyze_graphs_from_csv(csv_file, branch_list, nodes):
    """
    从CSV文件分析所有图
    """
    # 读取CSV
    df = pd.read_csv(csv_file, header=None)

    results = []
    detailed_results = []

    for idx, row in df.iterrows():
        # 构建图
        G = nx.Graph()
        G.add_nodes_from(nodes)

        # 添加存在的边
        for edge_idx, exists in enumerate(row.values):
            if exists == 1:
                G.add_edge(branch_list[edge_idx][0], branch_list[edge_idx][1])

        # 获取详细信息
        info = get_detailed_graph_info(G, branch_list)
        info['graph_id'] = idx + 1
        detailed_results.append(info)
        results.append(info['cyclomatic'])

    return results, detailed_results, df


def print_statistics(results, detailed_results):
    """
    打印统计信息
    """
    total = len(results)
    counter = Counter(results)

    print("=" * 60)
    print("图结构统计分析报告")
    print("=" * 60)
    print(f"总图数: {total}\n")

    # 环数统计
    print("各类环数图统计：")
    print("-" * 60)
    for cycle_num in sorted(counter.keys()):
        count = counter[cycle_num]
        percentage = (count / total) * 100
        if cycle_num == 0:
            print(f"树（0环）       : {count:5} 个 ({percentage:6.2f}%)")
        else:
            print(f"{cycle_num}环图          : {count:5} 个 ({percentage:6.2f}%)")

    print("=" * 60)

    # 连通性统计
    connected_count = sum(1 for r in detailed_results if r['is_connected'])
    print(f"\n连通图数量: {connected_count} 个 ({connected_count / total * 100:.2f}%)")
    print(f"非连通图数量: {total - connected_count} 个 ({(total - connected_count) / total * 100:.2f}%)")

    # 森林统计
    forest_count = sum(1 for r in detailed_results if r['is_forest'])
    print(f"\n森林（无环图）数量: {forest_count} 个 ({forest_count / total * 100:.2f}%)")

    # 基本统计
    print(f"\n平均环数: {np.mean(results):.3f}")
    print(f"中位数环数: {np.median(results):.0f}")
    print(f"标准差: {np.std(results):.3f}")
    print(f"最大环数: {max(results)}")
    print(f"最小环数: {min(results)}")

    # 边数统计
    edges_list = [r['num_edges'] for r in detailed_results]
    print(f"\n平均边数: {np.mean(edges_list):.2f}")
    print(f"边数范围: {min(edges_list)} - {max(edges_list)}")

    return counter


def plot_results(results):
    """
    绘制统计图表
    """
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 环数分布直方图
    ax1 = axes[0]
    unique, counts = np.unique(results, return_counts=True)
    ax1.bar(unique, counts, alpha=0.7, color='steelblue', edgecolor='black')
    ax1.set_xlabel('环数')
    ax1.set_ylabel('图的数量')
    ax1.set_title('环数分布直方图')
    ax1.grid(True, alpha=0.3)

    # 添加数值标签
    for i, (u, c) in enumerate(zip(unique, counts)):
        ax1.text(u, c + 0.1, str(c), ha='center', va='bottom')

    # 环数占比饼图
    ax2 = axes[1]
    labels = ['树(0环)'] + [f'{u}环' for u in unique if u > 0]
    sizes = counts
    colors = plt.cm.Set3(range(len(labels)))
    ax2.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    ax2.set_title('各类环数图占比')

    plt.tight_layout()
    plt.savefig('graph_analysis_results.png', dpi=150, bbox_inches='tight')
    plt.show()


# 使用示例
if __name__ == "__main__":
    # 定义数据
    nodes = list(range(13))
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

    # 读取CSV文件
    csv_file = '10万样本_蓄水池.csv'  # 替换为你的CSV文件路径

    try:
        results, detailed_results, df = analyze_graphs_from_csv(csv_file, Branch, nodes)
        counter = print_statistics(results, detailed_results)

        # 可选：绘制统计图表
        plot_results(results)

        # 可选：保存详细结果到CSV
        results_df = pd.DataFrame(detailed_results)
        results_df.to_csv('graph_analysis_detailed.csv', index=False)
        print("\n详细结果已保存到 'graph_analysis_detailed.csv'")

    except FileNotFoundError:
        print(f"错误：找不到文件 '{csv_file}'")
        print("请确保文件路径正确，或修改代码中的 'csv_file' 变量")
    except Exception as e:
        print(f"发生错误：{e}")