import pandas as pd


def deduplicate_csv(input_file, output_file):
    """
    读取CSV文件，去重后保存，保持整数类型

    参数:
        input_file: 输入CSV文件路径
        output_file: 输出CSV文件路径
    """
    # 读取CSV，指定数据类型为整数
    df = pd.read_csv(input_file, dtype=int)

    # 记录原始行数
    original_count = len(df)

    # 去重
    df_deduplicated = df.drop_duplicates()

    # 记录去重后的行数
    deduplicated_count = len(df_deduplicated)

    # 保存，设置index=False避免保存索引列
    # dtype=int确保保存为整数，float_format='%.0f'确保没有小数点
    df_deduplicated.to_csv(output_file, index=False, float_format='%.0f')

    print(f"原始行数: {original_count}")
    print(f"去重后行数: {deduplicated_count}")
    print(f"删除重复行数: {original_count - deduplicated_count}")
    print(f"已保存到: {output_file}")

    return df_deduplicated


# 使用示例
if __name__ == "__main__":
    input_file = "受限邻接矩阵.CSV"
    output_file = "受限邻接矩阵_去重.CSV"

    result = deduplicate_csv(input_file, output_file)
