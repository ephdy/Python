import pandas as pd

# 读取文件
file_path = '100万fop.csv'  # 如果文件在其他目录，请修改为完整路径
df = pd.read_csv(file_path)

# 需要检查的列（0-indexed）
cols_to_check = [48, 50, 52, 54, 56, 58]

# 向量化操作，快速判断
first_three_optimal = (df.iloc[:, 48] == 'optimal') & \
                      (df.iloc[:, 50] == 'optimal') & \
                      (df.iloc[:, 52] == 'optimal')

last_three_optimal = (df.iloc[:, 54] == 'optimal') & \
                     (df.iloc[:, 56] == 'optimal') & \
                     (df.iloc[:, 58] == 'optimal')

# 无效条件：前三列不全是optimal AND 后三列不全是optimal
invalid = (~first_three_optimal) & (~last_three_optimal)
invalid_count = invalid.sum()
total_rows = len(df)
valid_count = total_rows - invalid_count

# 输出结果
print(f'文件名: 100万fop.csv')
print(f'总行数: {total_rows:,}')
print(f'有效行数: {valid_count:,}')
print(f'无效行数: {invalid_count:,}')
print(f'有效率: {valid_count/total_rows*100:.2f}%')