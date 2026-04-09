


import pandas as pd


def process_csv_with_index(file_path, output_path=None):
    """
    读取CSV文件，处理数据（保留原始序号列）

    参数:
    file_path: 输入的CSV文件路径
    output_path: 输出的CSV文件路径（可选）

    返回:
    处理后的DataFrame
    """
    # 读取CSV文件
    df = pd.read_csv(file_path)

    print(f"原始数据行数: {len(df)}")
    print(f"原始列名: {list(df.columns)}")

    # 获取除第一列（序号）和最后一列外的所有列名
    feature_columns = df.columns[1:-1]  # 跳过第一列（序号）和最后一列
    target_column = df.columns[-1]  # 最后一列是目标列

    print(f"特征列: {list(feature_columns)}")
    print(f"目标列: {target_column}")

    # 统计最后一列目标值小于1e9的行数（不含1e9）
    count_less_than_1e9 = (df[target_column] < 4e8).sum()
    print(f"目标值小于4e8的行数: {count_less_than_1e9} (不含等于1e9)")

    # 打印原始数据中目标列的最小的n个值
    min_10_target_original = df[target_column].nsmallest(10)
    print(f"原始数据中目标列的最小的10个值:\n{min_10_target_original}")

    # 新增：打印原始数据中目标列小于1e9的最大的10个值
    target_less_than_1e9 = df[df[target_column] < 4e8][target_column]
    if len(target_less_than_1e9) > 0:
        max_10_less_than_1e9_original = target_less_than_1e9.nlargest(10)
        print(f"原始数据中目标列小于1e9的最大的10个值:\n{max_10_less_than_1e9_original}")
    else:
        print("原始数据中没有目标列小于1e9的值")

    # 新增：把目标值中的1e9改为4e8
    print(f"\n正在将目标列中的 1e9 替换为 4e8...")
    original_count_1e9 = (df[target_column] == 1e9).sum()
    df.loc[df[target_column] == 1e9, target_column] = 4e8
    modified_count = (df[target_column] == 4e8).sum()
    print(f"替换了 {original_count_1e9} 个 1e9 为 4e8")
    print(f"现在目标列中等于 4e8 的数量: {modified_count}")

    # 按特征列分组，对目标列取最小值，获取对应行的索引
    result_df = df.loc[
        df.groupby(list(feature_columns))[target_column].idxmin()
    ].reset_index(drop=True)


    # 删除原始序号列（第一列）
    result_df = result_df.iloc[:, 1:].reset_index(drop=True)
    result_df = result_df.copy()
    # 在最前面插入新的顺序序号列（从1开始）
    result_df.insert(0, '序号', range(1, len(result_df) + 1))

    print(f"处理后数据行数: {len(result_df)}")
    print(f"删除了 {len(df) - len(result_df)} 行重复数据")

    # 统计处理后最后一列目标值小于4e8的行数
    result_count_less_than_1e9 = (result_df[target_column] < 4e8).sum()
    print(f"处理后目标值小于4e8的行数: {result_count_less_than_1e9} (不含等于4e8)")

    # 打印处理后数据中目标列的最小值
    min_target_processed = result_df[target_column].min()
    print(f"处理后数据中目标列的最小值: {min_target_processed}")

    # 保存结果
    if output_path:
        result_df.to_csv(output_path, index=False)
        print(f"结果已保存到: {output_path}")
    else:
        # 生成默认输出文件名
        default_output = file_path.replace('.csv', '_processed.csv')
        result_df.to_csv(default_output, index=False)
        print(f"结果已保存到: {default_output}")

    return result_df


# 使用示例
if __name__ == "__main__":
    # 请将下面的路径替换为您的实际文件路径
    file_path = "../抽样数据.CSV"  # 修改这里！

    try:
        result = process_csv_with_index(file_path)
        print("\n处理完成！")

    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}")
        print("请检查文件路径是否正确")
    except Exception as e:
        print(f"处理过程中出现错误: {e}")