import os
import pandas as pd

directory = './'

for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        file_path = os.path.join(directory, filename)

        # 读取 CSV，空值会变成 NaN
        df = pd.read_csv(file_path, header=None)

        # 将所有 NaN（包括空元素和 None）替换为 -1
        df = df.fillna(-1)

        # 保存（不保留索引）
        df.to_csv(file_path, index=False)

        print(f'已处理: {filename}')