import pandas as pd

# 读取 CSV
df = pd.read_csv('100万fop.csv')

# 随机抽取 20% 的数据（不重置索引）
sample_df = df.sample(frac=0.2, random_state=42)  # random_state 可删或改数字保证可重复

# 保存到新 CSV，保留列名
sample_df.to_csv('sample.csv', index=False)