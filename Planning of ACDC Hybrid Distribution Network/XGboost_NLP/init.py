import os

# 原始代码模板
template = '''import Box3 as B
import pandas as pd
import os
import _13_nodes_distribution_network as H
path='../snap/50万样本_{n}.csv'
base, ext = path.rsplit('.', 1)
new_path = base + '结果' + '.' + ext
data1 = pd.read_csv(path)
X = data1.iloc[:, :13].values
Y = data1.iloc[:, 13:33 + 13].values
Z = data1.iloc[:, 33 + 13:].values
print(X.shape, Y.shape, Z.shape)
if os.path.exists(new_path):
    data2 = pd.read_csv(new_path)
    R = data2.iloc[:, :2].values
    ex = len(R)+1
else:
    ex = 0

for d in range(ex, len(Z)):
    S = X[d]
    U = Y[d]
    Gain = Z[d][0]
    Edges = []

    for k in range(len(H.Branch)):
        if U[k] == 1:
            i, j = H.Branch[k]
            Edges.append((i, j))
            Edges.append((j, i))

    # B.Draw_Grid(a, S)
    try:
        obj, Model, Solver = B.GAMS_Solve(S, Edges, Gain)
    except Exception as e:
        print(f"GAMS求解出错: {e}")
        obj, Model, Solver = 'None', 'None', 'None'  # 或设置默认值
    data=list(S) + list(U) + [Gain] + [Model,Solver,obj]
    B.save_csv(data, new_path)
'''

# 生成文件 1 到 100（可根据需要修改范围）
start_num = 1
end_num = 100  # 修改为你需要的最大数字
output_dir = "runpy"  # 输出目录

# 创建输出目录
os.makedirs(output_dir, exist_ok=True)

for n in range(start_num, end_num + 1):
    # 替换模板中的数字
    code = template.replace('{n}', str(n))

    # 生成文件名
    filename = f"run{n}.py"
    filepath = os.path.join(output_dir, filename)

    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"已生成: {filename}")

print(f"\n完成！共生成 {end_num - start_num + 1} 个文件，保存在 '{output_dir}' 目录中")