import os
import pandas as pd
from gams import GamsWorkspace
import time
import csv
import itertools
import matplotlib.pyplot as plt
import numpy as np
import math
from datetime import datetime
import gamspy as gp
from _13_nodes_distribution_network import *
from gams import *
def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')

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

def GAMS_Solve(S,Edges,Gain_DG,Default=None):
    a=time.time()

    m = gp.Container()
    # 节点
    N = gp.Set(m, name="N", records=nodes)
    t = gp.Set(m, name="t", records=times)
    tt =gp.Set(m, name="tt", domain=t,records=[t for t in times if t != 0])
    i = gp.Alias(m, name="i", alias_with=N)
    j = gp.Alias(m, name="j", alias_with=N)
    # 边
    E = gp.Set(m, name="E", domain=[N, N], records=Edges)
    N_ess = gp.Set(m, name="N_ess", domain=N, records=[5])
    # AC / DC 节点集合
    AC = gp.Set(m, name="AC", domain=N)
    DC = gp.Set(m, name="DC", domain=N)
    ac_nodes = [i for i in nodes if S[i] == 0]
    if ac_nodes:
        AC.setRecords(ac_nodes)
    dc_nodes = [i for i in nodes if S[i] == 1]
    if dc_nodes:
        DC.setRecords(dc_nodes)
    x = gp.Alias(m, name="x", alias_with=AC)
    y = gp.Alias(m, name="y", alias_with=AC)
    k = gp.Alias(m, name="k", alias_with=DC)
    l = gp.Alias(m, name="l", alias_with=DC)

    VSC = gp.Set(m, name="VSC")
    link_L,list_L=get_L(S,Edges)
    if list_L:
        VSC.setRecords(list_L)

    #参数
    G_matrix, B_matrix=get_Y(S,Edges)

    G = gp.Parameter(m, "G", domain=[i, j], records=G_matrix)
    B = gp.Parameter(m, "B", domain=[i, j], records=B_matrix)
    R1 = gp.Parameter(m, "R", domain=[i, j], records=get_R1(S,Edges))

    load_P,load_Q=get_Load()

    Pd = gp.Parameter(m, "Pd", domain=[N,t], records=load_P)
    Qd = gp.Parameter(m, "Qd", domain=[N,t], records=load_Q)

    Pmax_Buy=gp.Parameter(m, "Pmax_Buy", domain=[N,t], records=get_Buy())
    Pmax_DG = gp.Parameter(m, "Pmax_DG", domain=[N,t], records=get_DG(Gain_DG)[0])
    # Qmax_DG = gp.Parameter(m, "Qmax_DG", domain=[N,t], records=get_DG(Gain_DG)[1])


    max_Ess = gp.Parameter(m, "Pmax_Ess", domain=[N, t], records=get_Ess())

    SOC_init = gp.Parameter(m, name="SOC_init", domain=N,records=[(5,0.5)])

    # VSC连接AC节点
    map_ac = gp.Parameter(m, name="map_ac", domain=[VSC, N], records=link_L[0])

    # VSC连接DC节点
    map_dc = gp.Parameter(m, name="map_dc", domain=[VSC, N], records=link_L[1])

    # 定义电压
    V = gp.Variable(m, "V", domain=[N, t])  #
    V.lo[...] = 0.9
    V.up[...] = 1.1
    theta = gp.Variable(m, "theta", domain=[N, t])
    theta.lo[...] = -3.14
    theta.up[...] = 3.14

    Vdc = gp.Variable(m, "Vdc", domain=[DC, t])
    Vdc.lo[...] = 0.9
    Vdc.up[...] = 1.1

    # 定义传输功率
    P = gp.Variable(m, "P", domain=[x, y, t])
    P.lo[...] = -1
    P.up[...] = 1
    Q = gp.Variable(m, "Q", domain=[x, y, t])
    Q.lo[...] = -1
    Q.up[...] = 1

    # 定义DG出力
    P_DG = gp.Variable(m, "P_DG", domain=[N, t])
    P_DG.lo[...] = 0
    P_DG.up[...] = 0.3
    Q_DG = gp.Variable(m, "Q_DG", domain=[N, t])
    Q_DG.lo[...] = 0
    Q_DG.up[...] = 0.3


    # 定义购电功率
    P_buy = gp.Variable(m, "P_buy", domain=[N, t])
    P_buy.lo[...] = 0
    P_buy.up[...] = Pmax_Buy
    Q_buy = gp.Variable(m, "Q_buy", domain=[N, t])
    Q_buy.lo[...] = -Pmax_Buy
    Q_buy.up[...] = Pmax_Buy

    # 定义储能
    P_ess_ch = gp.Variable(m, "P_ess_ch", domain=[N, t])
    P_ess_ch.lo[...] = 0
    P_ess_ch.up[...] = max_Ess
    P_ess_dis = gp.Variable(m, "P_ess_dis", domain=[N, t])
    P_ess_dis.lo[...] = 0
    P_ess_dis.up[...] = max_Ess

    SOC=gp.Variable(m, "SOC", domain=[N, t])
    SOC.lo[...] = 0.1
    SOC.up[...] = 0.9

    # 定义注入功率
    P_in = gp.Variable(m, "P_in", domain=[i, t])
    Q_in = gp.Variable(m, "Q_in", domain=[i, t])

    # 定义VSC功率
    P_vsc_ac = gp.Variable(m, name="P_vsc_ac", domain=[VSC, t])
    P_vsc_ac.lo[...] = -0.5
    P_vsc_ac.up[...] = 0.5
    P_vsc_dc = gp.Variable(m, name="P_vsc_dc", domain=[VSC, t])
    P_vsc_dc.lo[...] = -0.5
    P_vsc_dc.up[...] = 0.5
    Q_vsc = gp.Variable(m, name="Q_vsc", domain=[VSC, t])
    Q_vsc.lo[...] = -0.5
    Q_vsc.up[...] = 0.5

    P_vsc_loss = gp.Variable(m, name="P_vsc_loss", domain=[VSC, t])
    P_vsc_loss.lo[...] = 0
    # 定义方程
    #
    slack_angle = gp.Equation(m, domain=[t])

    slack_angle[t] = (theta[0, t] == 0)

    # 注入功率
    P_in_def = gp.Equation(m, domain=[i, t])
    P_in_def[i, t] = (
            P_in[i, t]
            ==
            P_buy[i, t]
            + P_DG[i, t]
            + P_ess_dis[i, t] - P_ess_ch[i, t]
            - Pd[i, t]
    )

    Q_in_def = gp.Equation(m, domain=[i, t])
    Q_in_def[i, t] = (
            Q_in[i, t]
            ==
            Q_buy[i, t]
            + Q_DG[i, t]
            - Qd[i, t]
            - gp.Sum(VSC, map_ac[VSC, i] * Q_vsc[VSC, t])
    )

    AC_P_balance = gp.Equation(m, "AC_P_balance", domain=[x, t])

    AC_P_balance[x, t] = (
            P_in[x, t] - gp.Sum(VSC, map_ac[VSC, x] * P_vsc_ac[VSC, t])
            == gp.Sum(y,
                   V[x, t] * V[y, t] *
                   (G[x, y] * gp.math.cos(theta[x, t] - theta[y, t])
                    + B[x, y] * gp.math.sin(theta[x, t] - theta[y, t]))
                   )
    )


    AC_Q_balance = gp.Equation(m, "AC_Q_balance", domain=[x, t])
    AC_Q_balance[x, t] = (
            Q_in[x, t]
            == gp.Sum(y,
                   V[x, t] * V[y, t] *
                   (G[x, y] * gp.math.sin(theta[x, t] - theta[y, t])
                    - B[x, y] * gp.math.cos(theta[x, t] - theta[y, t]))
                   )
    )
    DC_balance = gp.Equation(m, "DC_balance", domain=[DC, t])

    DC_balance[DC, t] = (
            P_in[DC, t] - gp.Sum(VSC, map_dc[VSC, DC] * P_vsc_dc[VSC, t])
            == gp.Sum(k, Vdc[DC, t]*(Vdc[DC, t] - Vdc[k, t]) * R1[DC, k])
            # == gp.Sum(k,  (Vdc[DC, t] - Vdc[k, t])*R1[DC, k])
    )

    vsc_balance = gp.Equation(m, name="vsc_balance", domain=[VSC, t])

    vsc_balance[VSC, t] = (
           P_vsc_ac[VSC, t] + P_vsc_dc[VSC, t] == P_vsc_loss[VSC, t]
    )
    vsc_loss = gp.Equation(m, name="vsc_loss", domain=[VSC, t])
    vsc_loss[VSC, t] = (
            P_vsc_loss[VSC, t] == 1e-2 *( P_vsc_ac[VSC, t]**2 + Q_vsc[VSC, t]**2)**0.5
    )


    soc_init_eq = gp.Equation(m, name="soc_init_eq", domain=[N_ess])

    soc_init_eq[N_ess] = (
            SOC[N_ess, 0] == SOC_init[N_ess]+ 0.9 * P_ess_ch[N_ess, 0] - (1 / 0.9) * P_ess_dis[N_ess, 0]

    )

    soc_dyn_eq = gp.Equation(m, name="soc_dyn_eq", domain=[N_ess, t])
    soc_dyn_eq[N_ess, t].where[t.ord > 1] = (
            SOC[N_ess, t] ==
            SOC[N_ess, t - 1]
            + 0.9 * P_ess_ch[N_ess, t]
            - (1 / 0.9) * P_ess_dis[N_ess, t]
    )


    energy_balance = gp.Equation(m, name="energy_balance", domain=N_ess)

    energy_balance[N_ess] = (
            SOC_init[N_ess] == SOC[N_ess, 23]
    )

    # 定义系统安全运行方程
    line_P = gp.Equation(m, "line_P", domain=[x, y, t])
    line_Q = gp.Equation(m, "line_Q", domain=[x, y, t])

    line_P[x, y, t].where[E[x, y]] = (
            P[x, y, t]
            ==
            V[x, t] * V[x, t] * G[x, y]
            - V[x, t] * V[y, t] *
            (G[x, y] * gp.math.cos(theta[x, t] - theta[y, t])
             + B[x, y] * gp.math.sin(theta[x, t] - theta[y, t]))
    )

    line_Q[x, y, t].where[E[x, y]] = (
            Q[x, y, t]
            ==
            - V[x, t] * V[x, t] * B[x, y]
            - V[x, t] * V[y, t] *
            (G[x, y] * gp.math.sin(theta[x, t] - theta[y, t])
             - B[x, y] * gp.math.cos(theta[x, t] - theta[y, t]))
    )
    line_limit = gp.Equation(m, "line_limit", domain=[x, y, t])

    line_limit[x, y, t].where[E[x, y]] = (
            P[x, y, t] * P[x, y, t]
            + Q[x, y, t] * Q[x, y, t]
            <= 2.5 * 2.5 * 0.8 * 0.8
    )

    line_vsc = gp.Equation(m, "line_vsc", domain=[VSC, t])
    line_vsc[VSC, t] = (P_vsc_ac[VSC, t]**2+Q_vsc[VSC, t]**2 <= 2.5 * 2.5 * 0.8 * 0.8)

    line_DC = gp.Equation(m, "line_DC", domain=[k, l, t])
    line_DC[k, l, t] = (
            (Vdc[k, t] - Vdc[l, t]) * R1[k, l] <= 2.5 * 2.5 * 0.8 * 0.8
    )

    DG_limit = gp.Equation(m, "DG_limit", domain=[N, t])
    DG_limit[N, t] = (P_DG <= Pmax_DG[N, t])
    # df = Pd.records
    # print(df[df['N'] == "12"])
    if Default==None:
        V.l[N, t] = 1.0
        theta.l[N, t] = 0.0
        SOC.l[N, t] = 0.5
        P_DG.l[...] = Pmax_DG
        P_buy.l[...] = 0


    fop = gp.Variable(m, "fop")

    objective = gp.Equation(m, "objective")

    objective[...] = (
            fop
            ==
            gp.Sum(t,
                   # 购电成本
                   c_s * gp.Sum(N, P_buy[N, t])
                   # 储能成本
                   + c_e * gp.Sum(N, P_ess_ch[N, t] + P_ess_dis[N, t])
                   # DG惩罚项
                   + c_d * gp.Sum(N,
                                  Pmax_DG[N, t] - P_DG[N, t])
                   )*S_base
    )

    opf = gp.Model(
        m,
        name="ACDC_OPF",
        equations=m.getEquations(),
        problem="NLP",
        sense=gp.Sense.MIN,
        objective=fop
    )

    result=opf.solve(solver="CONOPT")


    # result = opf.solve(solver="IPOPT")
    # print(result)
    # V_val = V.toDict()
    # theta_val = theta.toDict()
    # G_val = G.toDict()
    # B_val = B.toDict()
    # res = 0
    # x_val = '4'
    # t_val = '0'
    # for y_val in AC.toList():
    #     temp=( V_val[(x_val, t_val)] *
    #         V_val[(y_val, t_val)] *
    #         (
    #                 G_val.get((x_val, y_val), 0) * math.sin(theta_val[(x_val, t_val)] - theta_val[(y_val, t_val)])
    #                 - B_val.get((x_val, y_val), 0) * math.cos(theta_val[(x_val, t_val)] - theta_val[(y_val, t_val)])
    #         ))
    #
    #     if G_val.get((x_val, y_val), 0) != 0:
    #         print(y_val,'G', G_val.get((x_val, y_val)))
    #         print('temp',temp)
    #         print('sin', math.sin(theta_val[(x_val, t_val)] - theta_val[(y_val, t_val)]))
    #         print('cos', math.cos(theta_val[(x_val, t_val)] - theta_val[(y_val, t_val)]))
    #     if B_val.get((x_val, y_val), 0) != 0:
    #         print(y_val, 'B', B_val.get((x_val, y_val)))
    #
    #     res += temp
    # print(res)


    # 求解后

    # 筛选 N=0 的记录
    # p_buy_filtered = P_buy.records[P_buy.records['N'] == '0']
    # a=P_DG.records[P_DG.records['N'] == '12']
    # b = P_ess_dis.records[P_ess_dis.records['N'] == '5']
    # c = P_ess_ch.records[P_ess_ch.records['N'] == '5']
    # d = SOC.records[SOC.records['N'] == '5']
    # # 或者直接打印整个 DataFrame
    # print(d[['t', 'level']])
    # print(b[['t', 'level']])
    # print(c[['t', 'level']])

    # a = P_vsc_ac.records[P_vsc_ac.records['VSC'] == '0']
    # b = P_vsc_dc.records[P_vsc_dc.records['VSC'] == '0']
    # # print(a, b)
    # d1 = Q_vsc.records[Q_vsc.records['VSC'] == '0']
    # d2 = Q_vsc.records[Q_vsc.records['VSC'] == '1']
    # d3 = Q_vsc.records[Q_vsc.records['VSC'] == '2']
    # d4 = Q_vsc.records[Q_vsc.records['VSC'] == '3']
    # d5 = Q_vsc.records[Q_vsc.records['VSC'] == '4']
    # d6 = Q_vsc.records[Q_vsc.records['VSC'] == '5']
    # print(link_L[0])
    # e0 = Q_in.records[Q_in.records['i'] == '0']
    # e1=Q_in.records[Q_in.records['i'] == '1']
    # e2 = Q_in.records[Q_in.records['i'] == '2']
    # e3 = Q_in.records[Q_in.records['i'] == '3']
    # e4 = Q_in.records[Q_in.records['i'] == '4']
    # f=Q_buy.records[Q_buy.records['N'] == '0']
    # q=Q_buy.records[Q_buy.records['N'] == '4']
    # w=Q_DG.records[Q_DG.records['N'] == '4']
    # r=Qd.records[Qd.records['N'] == '4']
    # print(f)
    # print(e0)
    # print(e1)
    # print(e2)
    # print(e3)
    # print(e4)

    # print(c)

    # print(d2)
    # print(e)
    return opf.objective_value,result.loc[0, "Model Status"],result.loc[0, "Solver Status"]



def get_Y(S,Edges):
    G_matrix=[]
    B_matrix=[]
    for i,j in Edges:
        R = r_line[i][j][0]
        X = x_line[i][j][0]
        G_matrix.append((i, j, -R / (R ** 2 + X ** 2)))
        B_matrix.append((i, j, X / (R ** 2 + X ** 2)))
        # G_matrix.append((j, i, -R / (R ** 2 + X ** 2)))
        # B_matrix.append((j, i, X / (R ** 2 + X ** 2)))
    for node in nodes:
        Ri=0
        Xi=0
        for i,j in Edges:
            if i==node :
                R = r_line[i][j][0]
                X = x_line[i][j][0]
                if S[i] ==0 and S[j]==0:
                    Ri+=R / (R ** 2 + X ** 2)
                    Xi+=-X / (R ** 2 + X ** 2)
        G_matrix.append((node, node, Ri))
        B_matrix.append((node, node, Xi))
    return G_matrix, B_matrix

def get_R1(S,Edges):
    R_matrix=[]
    for i,j in Edges:
        if S[i] != S[j]:
            R=r_line[i][j][1]
        else:
            R = r_line[i][j][0]
        R_matrix.append((i,j,1/R))
    return R_matrix

def get_Load():
    load_P=[]
    load_Q=[]
    for i in nodes:
        for t in times:
            load_P.append((i, t,n_Load[i]*P_load[t]/S_base))
            load_Q.append((i, t,n_Load[i]*Q_load[t]/S_base))

    return load_P, load_Q

def get_DG(Gain_DG):
    max_DG = []
    max_DG.append([])  # 添加第一个空子列表
    max_DG.append([])
    for i in nodes:
        if i in [7,12]:
            p=2 / 9
        elif i in [8,10]:
            p=2.5 / 9
        else:
            p=0
        if n_DG[i]!=0:
            for t in times:
                a0=n_DG[i] * DG_curve[t] * p * Gain_DG
                if a0>=3:
                    a=3
                else:
                    a=a0

                b=(3**2-a**2)** 0.5
                max_DG[0].append((i,t,round(a/S_base,4)))
                max_DG[1].append((i,t,round(b/S_base,4)))
    return max_DG

def get_Buy():
    Pmax_buy=[]
    for t in times:
        Pmax_buy.append((0,t,1))
    return Pmax_buy

def get_Ess():
    max_ess=[]
    for t in times:
        max_ess.append((5,t,2.5))
    return max_ess

def get_L(S,Edges):
    L=[]
    link=[]
    link.append([])
    link.append([])
    k=0
    visted=[]
    for i,j in Edges:
        if S[i] != S[j] and (j,i) not in visted:
            visted.append((i,j))
            L.append((i,j))
            if S[i] ==0:
                link[0].append((k,i,1))
                link[1].append((k,j,1))
            else:
                link[0].append((k,j,1))
                link[1].append((k,i,1))
            k=k+1

    return link,list(range(int(len(L))))
