
import pandas as pd
import glob
import os

# 指定目录路径
folder_path = 'C:\Hub\Python\Planning of ACDC Hybrid Distribution Network\IPOPT\snap\结果2合集'  # 改成你的目录

# 获取所有 CSV 文件
csv_files = glob.glob(os.path.join(folder_path, '*.csv'))

empty_first_col_files = []

for file in csv_files:
    try:
        df = pd.read_csv(file)
        # 检查第一列（第0列）是否有空值
        first_col = df.iloc[:, 0]
        if first_col.isna().any():
            empty_first_col_files.append(file)
            print(f'❌ {os.path.basename(file)}: 第一列有 {first_col.isna().sum()} 个空值')
        else:
            print(f'✓ {os.path.basename(file)}: 第一列无空值')
    except Exception as e:
        print(f'⚠️ {os.path.basename(file)}: 读取失败 - {e}')

print('\n' + '='*50)
if empty_first_col_files:
    print(f'发现 {len(empty_first_col_files)} 个文件的第一列有空值:')
    for f in empty_first_col_files:
        print(f'  - {os.path.basename(f)}')
else:
    print('所有文件的第一列都没有空值')