import csv
import re
from collections import defaultdict
# 读取CSV文件并复原为二维列表
def read_csv_to_list(filename):
    data = []
    with open(filename, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            data.append(row)
    return data

Result = read_csv_to_list('Result.csv')
# name=[]
# for i in Result:
#     name.append(i[0])
# for i in range(len(name)):
#     name[i]=name[i].split('[')[0]
# Name = []
# for i in name:
#     if i not in Name:
#         Name.append(i)
# # print(Result)
#
# vars_dict = defaultdict(list)
# for name, value in Result:
#     var_name = name.split('[')[0]  # 提取变量名，如 W、U、x
#     vars_dict[var_name].append(value)
# # 转换为整合列表形式
# result = {var: [var] + vals for var, vals in vars_dict.items()}
#
# # 输出
# for var, vals in result.items():
#     print(vals)
import re
from collections import defaultdict

def parse_mixed_data(data):
    result = {}
    temp = defaultdict(list)

    # 分类存储
    for name, value in data:
        var_name = re.match(r'([A-Za-z_][A-Za-z0-9_]*)', name).group(1)  # 变量名
        indices = tuple(map(int, re.findall(r'\d+', name)))  # 索引元组
        temp[var_name].append((indices, value))
    for var, items in temp.items():
        # 根据索引长度确定维度
        dims = [len(idx) for idx, _ in items]
        print(dims)
        dim_set = set(dims)
        if len(dim_set) != 1:
            # 如果同一变量索引长度不一致，提示错误
            print(f"Warning: Variable {var} has mixed index lengths: {dim_set}")
        dim = max(dim_set)  # 使用最大维度安全处理
        if dim == 1:
            # 一维
            values = [v for idx, v in sorted(items, key=lambda x: x[0][0])]
            result[var] = [var] + values

        elif dim == 2:
            # 二维 → 生成矩阵
            items2d = [(idx, v) for idx, v in items if len(idx) == 2]
            if not items2d:
                continue
            max_i = max(idx[0] for idx, _ in items2d) + 1
            max_j = max(idx[1] for idx, _ in items2d) + 1
            mat = [[0.0 for _ in range(max_j)] for _ in range(max_i)]
            for idx, v in items2d:
                i, j = idx
                mat[i][j] = v
            result[var] = mat

        elif dim == 3:
            # 三维 → 一维列表，每个元素是二维矩阵
            items3d = [(idx, v) for idx, v in items if len(idx) == 3]
            if not items3d:
                continue
            max_j = max(idx[1] for idx, _ in items3d)
            max_k = max(idx[2] for idx, _ in items3d)
            grouped = defaultdict(list)
            for idx, v in items3d:
                i, j, k = idx
                grouped[i].append((j, k, v))
            list_of_matrices = []
            for i in sorted(grouped.keys()):
                mat = [[0.0 for _ in range(max_k+1)] for _ in range(max_j+1)]
                for j, k, v in grouped[i]:
                    mat[j][k] = v
                list_of_matrices.append(mat)
            result[var] = list_of_matrices

        else:
            # 高维 >3 → 排序输出值列表
            values = [v for idx, v in sorted(items, key=lambda x: x[0])]
            result[var] = values

    return result

def save_parsed_to_csv(parsed, filename):
    """
    将解析好的变量写入 CSV
    一维列表直接写一行
    二维矩阵按行写
    三维矩阵展开为 i,j,k,value
    """
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)

        for var, val in parsed.items():
            if isinstance(val, list):
                # 判断是否是一维 W
                if val and isinstance(val[0], str):
                    # 一维列表
                    writer.writerow(val)
                elif val and isinstance(val[0], list) and all(isinstance(r, list) for r in val):
                    # 二维矩阵
                    writer.writerow([f"{var} (2D)"])
                    for row in val:
                        writer.writerow(row)
                elif val and isinstance(val[0], list) and all(isinstance(r, list) for r in val[0]):
                    # 三维 → 展开成 i,j,value 或写块
                    writer.writerow([f"{var} (3D)"])
                    for idx, mat in enumerate(val):
                        writer.writerow([f"{var}[{idx}]"])
                        for row in mat:
                            writer.writerow(row)
                else:
                    # 高维 → 展开成一列
                    writer.writerow([f"{var} (high-D)"])
                    writer.writerow(val)
            else:
                # 单个值
                writer.writerow([var, val])
# ===== 示例使用 =====
if __name__ == "__main__":
    parsed = parse_mixed_data(Result)
    # save_parsed_to_csv(parsed, "parsed_result.csv")
    # for var, val in parsed.items():
    #     print(f"{var} -> {val}")

