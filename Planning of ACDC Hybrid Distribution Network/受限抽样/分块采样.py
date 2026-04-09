import random

input_file = "全连接图.csv"
output_file = "采样结果_分块随机.csv"
sample_size = 100000
num_blocks = 100  # 分成100块，每块采1000行（100*1000=10万）

samples_per_block = sample_size // num_blocks  # = 1000

# 先统计总行数
print("正在统计总行数...")
with open(input_file, 'r', encoding='utf-8') as f:
    total_lines = sum(1 for _ in f)
print(f"总行数: {total_lines}")

block_size = total_lines // num_blocks  # 每块的行数
print(f"每块大小: {block_size} 行")
print(f"每块采样: {samples_per_block} 行")

# 第二遍扫描：分块采样
print("正在采样...")
sampled_lines = []
block_id = 0
line_in_block = 0

# 为每个块准备一个蓄水池（只存当前块的采样）
with open(input_file, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        # 确定当前行属于哪个块
        current_block = i // block_size

        if current_block > block_id:
            # 块切换：将当前块的采样结果保存
            block_id = current_block
            line_in_block = 0

        # 对当前块进行蓄水池采样
        if line_in_block < samples_per_block:
            sampled_lines.append(line)
        else:
            r = random.randint(0, line_in_block)
            if r < samples_per_block:
                # 找到这个块在总采样列表中的起始位置
                block_start = current_block * samples_per_block
                sampled_lines[block_start + r] = line

        line_in_block += 1

        # 显示进度
        if (i + 1) % 5000000 == 0:
            print(f"已处理 {(i + 1) / 1000000:.0f} 百万行", end='\r')

print(f"\n采样完成，共 {len(sampled_lines)} 行")
print("正在写入文件...")
with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(sampled_lines)

print("完成！")