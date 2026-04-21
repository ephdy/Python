import pandas as pd

# 读取原始 CSV
df = pd.read_csv('20万连接图.csv')  # 改成你的输入文件名

# 要添加的后缀列表
suffixes = [[0, 0], [1, 0], [0, 1], [1, 1]]

# 用于存放所有新行的列表
new_rows = []

# 对原数据每一行进行处理
for _, row in df.iterrows():
    for s in suffixes:
        new_row = row.to_dict()
        # 在末尾增加两列：例如 add_0, add_1
        new_row['mu'] = s[0]
        new_row['epsilon'] = s[1]
        new_rows.append(new_row)

# 生成新 DataFrame
new_df = pd.DataFrame(new_rows)

# 保存到新 CSV
new_df.to_csv('output.csv', index=False)

print("处理完成，已保存到 output.csv")