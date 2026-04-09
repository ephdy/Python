import pandas as pd
import gamspy as gp
from _13_nodes_distribution_network import *
import time
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
    #参数
    G_matrix, B_matrix=get_Y(S,Edges)

    G = gp.Parameter(m, "G", domain=[i, j], records=G_matrix)
    B = gp.Parameter(m, "B", domain=[i, j], records=B_matrix)

    load_P,load_Q=get_Load()

    Pd = gp.Parameter(m, "Pd", domain=[N,t], records=load_P)
    Qd = gp.Parameter(m, "Qd", domain=[N,t], records=load_Q)

    Pmax_Buy=gp.Parameter(m, "Pmax_Buy", domain=[N,t], records=get_Buy())
    Pmax_DG = gp.Parameter(m, "Pmax_DG", domain=[N,t], records=get_DG(Gain_DG)[0])
    Qmax_DG = gp.Parameter(m, "Qmax_DG", domain=[N,t], records=get_DG(Gain_DG)[1])

    max_Ess = gp.Parameter(m, "Pmax_Ess", domain=[N, t], records=get_Ess())

    SOC_init = gp.Parameter(m, name="SOC_init", domain=N,records=[(5,0.5)])

    # 定义电压
    V = gp.Variable(m, "V", domain=[N, t])  #
    V.lo[...] = 0.9
    V.up[...] = 1.1
    theta = gp.Variable(m, "theta", domain=[N, t])
    theta.lo[...] = -3.14
    theta.up[...] = 3.14

    # 定义传输功率
    P = gp.Variable(m, "P", domain=[i, j, t])
    P.lo[...] = -1
    P.up[...] = 1
    Q = gp.Variable(m, "Q", domain=[i, j, t])
    Q.lo[...] = -1
    Q.up[...] = 1

    # 定义DG出力
    P_DG = gp.Variable(m, "P_DG", domain=[N, t])
    P_DG.lo[...] = 0
    P_DG.up[...] = Pmax_DG
    Q_DG = gp.Variable(m, "Q_DG", domain=[N, t])
    Q_DG.lo[...] = 0
    Q_DG.up[...] = Qmax_DG


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
    )

    AC_P_balance = gp.Equation(m, "AC_P_balance", domain=[i, t])

    AC_P_balance[i, t] = (
            P_in[i, t]
            == gp.Sum(j,
                   V[i, t] * V[j, t] *
                   (G[i, j] * gp.math.cos(theta[i, t] - theta[j, t])
                    + B[i, j] * gp.math.sin(theta[i, t] - theta[j, t]))
                   )
    )


    AC_Q_balance = gp.Equation(m, "AC_Q_balance", domain=[i, t])
    AC_Q_balance[i, t] = (
            Q_in[i, t]
            == gp.Sum(j,
                   V[i, t] * V[j, t] *
                   (G[i, j] * gp.math.sin(theta[i, t] - theta[j, t])
                    - B[i, j] * gp.math.cos(theta[i, t] - theta[j, t]))
                   )
    )

    # soc_eq = gp.Equation(m, name="soc_eq", domain=[N_ess, t])
    #
    # soc_eq[N_ess, t] = (
    #         SOC[N_ess, t] == (
    #         SOC_init[N_ess].where[t.ord == 0]
    #         + SOC[N_ess, t - 1].where[t.ord > 0]
    #         + 0.9 * P_ess_ch[N_ess, t]
    #         - (1 / 0.9) * P_ess_dis[N_ess, t]
    # )
    # )
    soc_init_eq = gp.Equation(m, name="soc_init_eq", domain=[N_ess])

    soc_init_eq[N_ess] = (
            SOC[N_ess, 0] == SOC_init[N_ess]+ 0.9 * P_ess_ch[N_ess, 0] - (1 / 0.9) * P_ess_dis[N_ess, 0]

    )
    soc_dyn_eq = gp.Equation(m, name="soc_dyn_eq", domain=[N_ess, tt])

    soc_dyn_eq[N_ess, tt] = (
            SOC[N_ess, tt] ==
            SOC[N_ess, tt - 1]
            + 0.9 * P_ess_ch[N_ess, tt]
            - (1 / 0.9) * P_ess_dis[N_ess, tt]
    )


    energy_balance = gp.Equation(m, name="energy_balance", domain=N_ess)

    energy_balance[N_ess] = (
            SOC_init[N_ess] == SOC[N_ess, 23]
    )

    # 定义系统安全运行方程
    line_P = gp.Equation(m, "line_P", domain=[i, j, t])
    line_Q = gp.Equation(m, "line_Q", domain=[i, j, t])

    line_P[i, j, t].where[E[i, j]] = (
            P[i, j, t]
            ==
            V[i, t] * V[i, t] * G[i, j]
            - V[i, t] * V[j, t] *
            (G[i, j] * gp.math.cos(theta[i, t] - theta[j, t])
             + B[i, j] * gp.math.sin(theta[i, t] - theta[j, t]))
    )

    line_Q[i, j, t].where[E[i, j]] = (
            Q[i, j, t]
            ==
            - V[i, t] * V[i, t] * B[i, j]
            - V[i, t] * V[j, t] *
            (G[i, j] * gp.math.sin(theta[i, t] - theta[j, t])
             - B[i, j] * gp.math.cos(theta[i, t] - theta[j, t]))
    )

    line_limit = gp.Equation(m, "line_limit", domain=[i, j, t])

    line_limit[i, j, t].where[E[i, j]] = (
            P[i, j, t] * P[i, j, t]
            + Q[i, j, t] * Q[i, j, t]
            <= 2.5 * 2.5 * 0.8 * 0.8
    )

    # df = Pd.records
    # print(df[df['N'] == "12"])
    if Default==None:
        V.l[i, t] = 1.0
        theta.l[i, t] = 0.0
        P_DG.l[...] = Pmax_DG
        P_buy.l[...] = Pmax_Buy


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

    summary=opf.solve(solver="CONOPT")

    # summary = opf.solve(solver="IPOPT")
    print(summary)

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
    return opf.objective_value



def get_Y(S,Edges):
    G_matrix=[]
    B_matrix=[]
    for i,j in Edges:
        if S[i] != S[j]:
            R=r_line[i][j][1]
            X=x_line[i][j][1]
        else:
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
                if S[i] != S[j]:
                    R = r_line[i][j][1]
                    X = x_line[i][j][1]
                else:
                    R = r_line[i][j][0]
                    X = x_line[i][j][0]
                Ri+=R / (R ** 2 + X ** 2)
                Xi+=-X / (R ** 2 + X ** 2)
        G_matrix.append((node, node, Ri))
        B_matrix.append((node, node, Xi))
    return G_matrix, B_matrix

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
                a=n_DG[i] * DG_curve[t] * p * Gain_DG
                b=(3**2-a**2)** 0.5
                max_DG[0].append((i,t,a/S_base))
                max_DG[1].append((i,t,b/S_base))
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


data1 = pd.read_csv('节点类型.csv')
data2 = pd.read_csv('受限邻接矩阵可行解.CSV')
X = data1.iloc[:,:13].values
Y = data2.iloc[:,:33].values
# print(X[94])
# print(Y[94])
S=X[0]
for d in range(20):
    a = Y[d]
    Edges = []
    for k in range(len(Branch)):
        if a[k] == 1:
            i, j = Branch[k]
            Edges.append((i, j))
            Edges.append((j, i))

    print(d,GAMS_Solve(S, Edges, 1))