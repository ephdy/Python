import pandas as pd

# 设置 low_memory=False 解决混合类型警告
df = pd.read_csv('100Loss.csv', low_memory=False)

original_rows = len(df)

# 删除任何包含"err"的行（不区分大小写）
df_cleaned = df[~df.astype(str).apply(lambda x: x.str.contains('err', case=False, na=False)).any(axis=1)]

cleaned_rows = len(df_cleaned)

print(f"原始行数: {original_rows}")
print(f"删除后行数: {cleaned_rows}")
print(f"删除行数: {original_rows - cleaned_rows}")

# 保存到新文件
df_cleaned.to_csv('cleaned_100Loss.csv', index=False)
print("✅ 已保存到 cleaned_100Loss.csv")