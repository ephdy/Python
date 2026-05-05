from pyomo.environ import *
import numpy as np
from _13_nodes_distribution_network import *
import pandas as pd
import time
import matplotlib.pyplot as plt
import math
import os
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

if __name__ == '__main__':
    S=[0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1]
    U=[0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1]
    Draw_Grid(U, S)