import pandas as pd
import os


def split_csv_by_target(input_file, threshold=3e8):
    """
    根据目标值分割CSV文件

    Parameters:
    input_file: 输入的CSV文件路径
    threshold: 阈值，默认为3e8
    """

    # 读取CSV文件
    print(f"正在读取文件: {input_file}")
    df = pd.read_csv(input_file)

    # 获取最后一列的列名（目标值列）
    target_column = df.columns[-1]
    print(f"目标值列: {target_column}")

    # 根据阈值分割数据
    df_less = df[df[target_column] < threshold]  # 小于阈值
    df_greater = df[df[target_column] > threshold]  # 大于阈值

    # 生成输出文件名
    base_name = os.path.splitext(input_file)[0]
    output_less = f"{base_name}_可行解.csv"
    output_greater = f"{base_name}_不可行解.csv"

    # 保存到新文件
    print(f"小于 {threshold} 的记录数: {len(df_less)}")
    print(f"大于 {threshold} 的记录数: {len(df_greater)}")

    df_less.to_csv(output_less, index=False)
    df_greater.to_csv(output_greater, index=False)

    print(f"已保存小于阈值的文件: {output_less}")
    print(f"已保存大于阈值的文件: {output_greater}")

    # 显示一些统计信息
    print(f"\n目标值范围统计:")
    print(f"最小值: {df[target_column].min()}")
    print(f"最大值: {df[target_column].max()}")
    print(f"平均值: {df[target_column].mean()}")

    return df_less, df_greater


# 使用示例
if __name__ == "__main__":
    # 请将下面的文件名替换为你的CSV文件路径
    input_csv = "训练数据.CSV"  # 修改这里

    try:
        less_df, greater_df = split_csv_by_target(input_csv)
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_csv}")
        print("请确保文件路径正确，或者修改代码中的文件名")
    except Exception as e:
        print(f"处理过程中出现错误: {e}")