import pandas as pd

# 读取文件
file_path = '100万fop.csv'
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

# 保留有效行（删除无效行）
valid_df = df[~invalid]

# 保存为新文件
output_path = '100万fop_cleaned.csv'
valid_df.to_csv(output_path, index=False)

# 输出统计信息
total_rows = len(df)
valid_count = len(valid_df)
invalid_count = total_rows - valid_count

print(f'原始总行数: {total_rows:,}')
print(f'删除无效行数: {invalid_count:,}')
print(f'保留有效行数: {valid_count:,}')
print(f'有效率: {valid_count/total_rows*100:.2f}%')
print(f'清洗后的文件已保存为: {output_path}')