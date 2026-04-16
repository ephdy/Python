import _13_nodes_distribution_network as H
import numpy as np
import pandas as pd


def save_csv(data,new_path):
    new_df = pd.DataFrame([data])
    new_df.to_csv(new_path, mode='a', header=False, index=False, encoding='utf-8')


path="新样本可行解.CSV"
data = pd.read_csv(path)
base, ext = path.rsplit('.', 1)
new_path = base + '热值' + '.' + ext
X = data.iloc[:,:].values
for x in X:
    S_vsc = 0
    C_line = 0
    S_c = 0
    S=x[:13]
    U=x[13:13+33]
    fop=x[-1]
    for k in range(len(H.Branch)):
        i,j=H.Branch[k]
        C_line += H.c_l[0] * H.Length[i][j] * U[k]
        S_vsc += H.S_vsc_ij*abs(S[i]-S[j])*U[k]

    for i in range (H.n):
        S_c = S_c + H.S_c_load * (H.n__ac[i] * S[i] + H.n__dc[i] * (1 - S[i]))
        S_c = S_c + H.S_c_wind * (S[i] + 2 * (1 - S[i])) * H.n__wind[i]
        S_c = S_c + H.S_c_pv * H.n__pv[i]

    C_cvt = H.c_c * S_c + H.c_v * S_vsc

    C_invest = C_line * (H.r * (pow(1+H.r,H.T_line)/(pow(1+H.r,H.T_line)-1)) +H.beta_line)+ C_cvt * (H.r *(pow(1+H.r,H.T_cvt)/(pow(1+H.r,H.T_cvt)-1)) + H.beta_cvt)
    C_operation = fop * H.N_d
    res=list(x)+[C_invest,C_operation,C_invest+C_operation]

    save_csv(res, new_path)


