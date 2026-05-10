import pandas as pd

# 读取CSV文件
input_file = "小规模样本.csv"   # 请修改为你的输入文件名
output_file = "小规模样本end.csv" # 输出文件名

df = pd.read_csv(input_file)

# 确保列数足够
if df.shape[1] < 5:
    raise ValueError("CSV文件列数不足5列，无法读取倒数第5列")

# 获取倒数第5、倒数第3、倒数第1列（索引从0开始）
col_minus5 = df.iloc[:, -5]   # 倒数第5列
col_minus3 = df.iloc[:, -3]   # 倒数第3列
col_minus1 = df.iloc[:, -1]   # 倒数第1列

# 按权重计算加权和
weights = [0.8, 0.1, 0.1]
df['avr'] = weights[0] * col_minus5 + weights[1] * col_minus3 + weights[2] * col_minus1

# 保存到新CSV
df.to_csv(output_file, index=False)

print(f"处理完成，结果已保存至 {output_file}")