import pandas as pd
import numpy as np

# 读取CSV文件，设置 low_memory=False 并指定数据类型
df = pd.read_csv('cleaned_100Loss.csv', low_memory=False)

# 将第48到80列强制转换为数值类型（非数值转为NaN）
start_col = 48
end_col = 80

# 方法：先转换为字符串，再转换为数值（错误值变为NaN）
for col in df.columns[start_col:end_col+1]:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# 提取需要计算的列范围
cols_data = df.iloc[:, start_col:end_col+1].values

# 创建掩码（-1的位置为False，NaN的位置也为False）
mask = (cols_data != -1) & (~np.isnan(cols_data))

# 计算有效值的和
masked_sum = np.where(mask, cols_data, 0).sum(axis=1)

# 计算有效值的数量
valid_count = mask.sum(axis=1)

# 计算平均值（避免除零）
mean_values = np.where(valid_count > 0, masked_sum / valid_count, np.nan)

# 添加平均值列
df['Average'] = mean_values

print(f"处理完成！")
print(f"原数据形状: {df.shape}")
print(f"有有效值的行数: {(valid_count > 0).sum()}")
print(f"全是无效值的行数: {(valid_count == 0).sum()}")
print(f"\n平均值统计:")
print(pd.Series(mean_values).describe())

# 保存到新文件
df.to_csv('output_with_average.csv', index=False)
print("✅ 已保存到 output_with_average.csv")