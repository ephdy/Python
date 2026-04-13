import pandas as pd
path="新样本.csv"
df = pd.read_csv(path)
name=path.split(".")[0]
chunk_size = 20000

for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i + chunk_size]
    chunk.to_csv(f"{name}_{i//chunk_size + 1}.csv", index=False)