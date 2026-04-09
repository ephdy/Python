import os
from gams import *
import _13_nodes_distribution_network as H
import pandas as pd

ws = GamsWorkspace(system_directory=r"D:\tool\Gams\42")

def get_Y(S,Edges):
    G_matrix=[]
    B_matrix=[]
    for i,j in Edges:
        if S[i] != S[j]:
            R=H.r_line[i][j][1]
            X=H.x_line[i][j][1]
        else:
            R = H.r_line[i][j][0]
            X = H.x_line[i][j][0]
        G_matrix.append((i, j, R / (R ** 2 + X ** 2)))
        B_matrix.append((i, j, -X / (R ** 2 + X ** 2)))
    return G_matrix, B_matrix

def get_Load():
    load_P=[]
    load_Q=[]
    for i in H.nodes:
        for t in H.times:
            load_P.append((i, t,H.n_Load[i]*H.P_load[t]))
            load_Q.append((i, t,H.n_Load[i]*H.Q_load[t]))

    return load_P, load_Q

def get_DG(Gain_DG):
    Pmax_DG=[]
    for i in H.nodes:
        if i in [7,12]:
            p=2 / 9
        elif i in [8,10]:
            p=2.5 / 9
        else:
            p=0
        if H.n_DG[i]!=0:
            for t in H.times:
                Pmax_DG.append((i,t,H.n_DG[i] * H.DG_curve[t] * p * Gain_DG))
    return Pmax_DG



def solve_one_case(data):
    db = ws.add_database()

    # ===== Sets =====
    N = db.add_set("N", 1)
    for n in data["nodes"]:
        N.add_record(str(n))

    tset = db.add_set("t", 1)
    for tt in data["times"]:
        tset.add_record(str(tt))

    E = db.add_set("E", 2)
    for i,j in data["Edges"]:
        E.add_record((str(i), str(j)))

    # 子集
    def add_subset(name, items):
        s = db.add_set(name, 1)
        for i in items:
            s.add_record(str(i))
        return s

    add_subset("AC", data["AC"])
    add_subset("DC", data["DC"])
    add_subset("DG", data["DG"])
    add_subset("Slack", ['0'])
    add_subset("Ess", ['5'])

    # ===== Parameters =====
    def add_param2(name, records):
        p = db.add_parameter(name, 2)
        for (i,j,v) in records:
            p.add_record((str(i),str(j))).value = v

    add_param2("G", data["G"])
    add_param2("B", data["B"])

    Pd = db.add_parameter("Pd", 2)
    for (i,t,v) in data["Pd"]:
        Pd.add_record((str(i),str(t))).value = v

    # ===== Scalars =====
    db.add_parameter("c_s", 0).add_record().value = data["c_s"]
    db.add_parameter("c_e", 0).add_record().value = data["c_e"]
    db.add_parameter("c_d", 0).add_record().value = data["c_d"]
    db.add_parameter("P_ess_max", 0).add_record().value = data["P_ess_max"]

    # ===== Run GAMS =====
    job = ws.add_job_from_file(r"C:\Hub\Python\Planning of ACDC Hybrid Distribution Network\XGboost_NLP\acdc_opf.gms")
    job.run(databases=db)

    # ===== 读取结果 =====
    fop = job.out_db["fop"].find_record().level
    return fop



def create_data(S,Edges,Gain_DG):
    G_matrix, B_matrix = get_Y(S, Edges)
    load_P, load_Q = get_Load()
    data = {
        # ===== 集合 =====
        "nodes": H.nodes,  # 节点集合 N
        "times": H.times,  # 时间集合 t
        "Edges": Edges,  # 边集合 E (i,j)

        "AC": [i for i in H.nodes if S[i] == 0],  # AC节点
        "DC": [i for i in H.nodes if S[i] == 1],  # DC节点
        "DG": [i for i in H.nodes if H.n_DG[i] == 1],  # DG节点

        # ===== 参数 =====
        "G": G_matrix,  # (i,j,value)
        "B": B_matrix,  # (i,j,value)

        "Pd": load_P,  # (i,t,value)
        "Qd": load_Q,

        "Pmax_DG": get_DG(Gain_DG),  # (i,t,value)

        # ===== 标量 =====
        "c_s": H.c_s,
        "c_e": H.c_e,
        "c_d": H.c_d,

        "P_ess_max": H.P_ess_max,
        "S_ess": H.S_ess,
    }
    return data
data1 = pd.read_csv('节点类型.csv')
data2 = pd.read_csv('受限邻接矩阵可行解.CSV')
X = data1.iloc[:,:13].values
Y = data2.iloc[:,:33].values
# print(X[94])
# print(Y[94])
S=X[0]
a=Y[94]
Edges=[]
for i in range(len(H.Branch)):
    if a[i]==1:
        Edges.append(H.Branch[i])

data=create_data(S,Edges,1)
re=solve_one_case(data)
print(re)