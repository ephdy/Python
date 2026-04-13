import pandas as pd

df = pd.read_csv("新组合3.csv")

# 前面列转 int，最后一列保持 float
df.iloc[:, :-2] = df.iloc[:, :-2].astype(int)
# 最后两列保留两位小数
df.iloc[:, -2:] = df.iloc[:, -2:].round(2)
# 去重
df = df.drop_duplicates()

# 保存
df.to_csv("deduplicated.csv", index=False)