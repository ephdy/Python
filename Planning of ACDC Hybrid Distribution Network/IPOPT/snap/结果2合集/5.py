
import pandas as pd
import numpy as np

# 读取文件
file_path = '100万fop_cleaned.csv'
df = pd.read_csv(file_path)

# 将参与计算的列转换为数值类型（非数值转为NaN）
cols_for_calc = [49, 51, 53, 55, 57, 59]
for col in cols_for_calc:
    df.iloc[:, col] = pd.to_numeric(df.iloc[:, col], errors='coerce')

# 检查列48,50,52是否全为optimal
cond1 = (df.iloc[:, 48] == 'optimal') & \
        (df.iloc[:, 50] == 'optimal') & \
        (df.iloc[:, 52] == 'optimal')

# 计算x1：列49,51,53的加权和
df['x1'] = -1.0  # 默认值，使用浮点数
df.loc[cond1, 'x1'] = df.iloc[cond1, 49] * 0.7 + \
                      df.iloc[cond1, 51] * 0.15 + \
                      df.iloc[cond1, 53] * 0.15

# 检查列54,56,58是否全为optimal
cond2 = (df.iloc[:, 54] == 'optimal') & \
        (df.iloc[:, 56] == 'optimal') & \
        (df.iloc[:, 58] == 'optimal')

# 计算x2：列55,57,59的加权和
df['x2'] = -1.0
df.loc[cond2, 'x2'] = df.iloc[cond2, 55] * 0.7 + \
                      df.iloc[cond2, 57] * 0.15 + \
                      df.iloc[cond2, 59] * 0.15

# 计算x1 - x2
df['x1_minus_x2'] = df['x1'] - df['x2']

# 保存到新文件
output_path = '100万fop_with_values.csv'
df.to_csv(output_path, index=False)

# 统计信息
total_rows = len(df)
x1_valid = (df['x1'] != -1).sum()
x2_valid = (df['x2'] != -1).sum()
both_valid = ((df['x1'] != -1) & (df['x2'] != -1)).sum()

print(f'总行数: {total_rows:,}')
print(f'x1计算有效行数（48,50,52全为optimal）: {x1_valid:,}')
print(f'x2计算有效行数（54,56,58全为optimal）: {x2_valid:,}')
print(f'两个都有效的行数: {both_valid:,}')
print(f'输出文件已保存为: {output_path}')

# 显示前几行结果
print('\n前5行的x1、x2、x1-x2预览:')
print(df[['x1', 'x2', 'x1_minus_x2']].head())