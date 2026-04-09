import random

total_lines = 79003894
sample_size = 100000
input_file = "全连接图.csv"
output_file = "采样结果.csv"

# 第一遍：计算总行数（可选，如果你确定总行数就是79003894可以跳过）
# 但为了保险，建议还是先数一下
print("正在统计总行数...")
with open(input_file, 'r', encoding='utf-8') as f:
    total = sum(1 for _ in f)
print(f"实际总行数: {total}")

# 使用蓄水池采样
print("正在采样...")
sampled = []
with open(input_file, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i < sample_size:
            sampled.append(line)
        else:
            r = random.randint(0, i)
            if r < sample_size:
                sampled[r] = line

        # 每处理100万行显示进度
        if (i + 1) % 1000000 == 0:
            print(f"已处理 {(i + 1) / 1000000:.0f} 百万行")

print(f"采样完成，共 {len(sampled)} 行")
print("正在写入文件...")
with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(sampled)

print("完成！")