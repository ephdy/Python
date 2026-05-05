import pandas as pd
import glob
import os

# 指定目录路径（改成你的目录）
folder_path = 'C:\Hub\Python\Planning of ACDC Hybrid Distribution Network\IPOPT\snap\结果2合集'   # 例如 './csv_files' 或 '/path/to/csvs'

# 获取目录下所有 CSV 文件
csv_files = glob.glob(os.path.join(folder_path, '*.csv'))

# 只保留第一个文件的表头
combined = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)

# 保存合并后的文件
combined.to_csv('merged.csv', index=False)

print(f'合并完成，共 {len(csv_files)} 个文件，总行数：{len(combined)}')