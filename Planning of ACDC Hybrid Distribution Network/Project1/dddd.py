# import Gurobi_solving as Gs
import time
def find_upper_right_ones_python(arr):
    n = len(arr)
    result = []
    for i in range(n):
        for j in range(i+1, n):
            if arr[i][j] == 1:
                result.append((i, j))
    return result

import copy

from Gurobi_solving import *
N=n
x=[[0 for _ in range(n)] for _ in range(n)]
W=W0
U=U0
C_line = 0
S_vsc = 0
S_c = 0
L = [[0 for _ in range(N)] for _ in range(N)]

print(len(find_upper_right_ones_python(U)))
for i in range(N):
    S_c = S_c + S_c_load * (n__ac[i] * W[i] + n__dc[i] * (1 - W[i]))
    S_c = S_c + S_c_wind * (W[i] + 2 * (1 - W[i])) * n__wind[i]
    S_c = S_c + S_c_pv * (1 - W[i]) * n__pv[i]
    for j in range(N):
        L[i][j] = abs(W[i] - W[j])
        S_vsc += 0.5 * S_vsc_ij * U[i][j] * L[i][j]
        for k in range(kk):
            C_line += 0.5 * c_l[x[i][j]] * Length[i][j] * U[i][j]
C_cvt = c_c * S_c + c_v * S_vsc
C_invest = C_line + C_cvt
C_operation = 0
# f_op = Lower_layer_solving(W,U,X)
# f_op=Lower_layer_solving(W0,U0,x)

# # C_operation = 4596.9591*f_op*0.62972*C_line+0.64093*C_cvt
# for d in range(T_p):
#     C_operation += N_d * f_op / pow(1 + r, d + 1)
# for d in range(T_line):
#     C_operation += beta_line * C_line / pow(1 + r, d + 1)
# for d in range(T_cvt):
#     C_operation += beta_cvt * C_cvt / pow(1 + r, d + 1)
# f1 = C_invest + C_operation
# print(f1)
# print(f_op)
# print(Lower_layer_solving_2(W0,U0,x))
# U_1_index=find_upper_right_ones(U0)
# k_U_lack=len(U_1_index)
# U_lack_1=[]
# print(U_1_index)
# print(U0)
# for i in U_1_index:
#     U_new = copy.deepcopy(U0)
#     U_new[i[0]][i[1]]=0
#     U_new[i[1]][i[0]] = 0
#     print(U_new)
#     print('aaaaaaaaaaaaaaaaaaaaaaaaaaaa')
#     U_lack_1.append(U_new)
# print(U_lack_1)

U_1_index=find_upper_right_ones(U)
k_U_lack=len(U_1_index)
U_lack_1=[]
for i in U_1_index:
    U_new = copy.deepcopy(U)
    U_new[i[0]][i[1]]=0
    U_new[i[1]][i[0]] = 0
    U_lack_1.append(U_new)

obi,f_op,delta,mu=Lower_layer_solving_1(W0,U0,x)
a=0
start_time = time.time()
for i in range(len(U_lack_1)):
    b=Lower_layer_solving_3(W0, U_lack_1[i], x, delta, mu)
    a+=b
print(a/k_U_lack/15)
Lower_layer_solving
print(time.time()-start_time)