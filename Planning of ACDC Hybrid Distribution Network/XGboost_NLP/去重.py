import pandas as pd

df = pd.read_csv("新组合.csv")

# 前面列转 int，最后一列保持 float
df.iloc[:, :-1] = df.iloc[:, :-1].astype(int)

# 去重
df = df.drop_duplicates()

# 保存
df.to_csv("deduplicated.csv", index=False)