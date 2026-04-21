import pandas as pd

# 读取原始CSV文件
df = pd.read_csv('全连接图.csv')

# 随机抽取20万行数据（如果总行数少于20万，则抽取全部）
n_samples = min(200000, len(df))
sampled_df = df.sample(n=n_samples)  # random_state保证可重复性

# 保存到新的CSV文件
sampled_df.to_csv('20万连接图.csv', index=False)

print(f"已从 {len(df)} 行中随机抽取 {n_samples} 行并保存到 output.csv")