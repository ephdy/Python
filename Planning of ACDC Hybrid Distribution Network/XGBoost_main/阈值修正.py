import json
import numpy as np


def modify_xgboost_split_conditions(input_json_path, output_json_path, delta=1e-6):
    """
    修改XGBoost JSON模型文件中所有树的split_conditions数组中的值

    Parameters:
    -----------
    input_json_path : str
        输入的JSON文件路径
    output_json_path : str
        输出的JSON文件路径
    delta : float
        要减去的值（小量）
    """

    # 读取JSON文件
    with open(input_json_path, 'r', encoding='utf-8') as f:
        model = json.load(f)

    # 统计修改的节点数
    total_modified = 0

    # 访问路径: $.learner.gradient_booster.model.trees
    try:
        trees = model['learner']['gradient_booster']['model']['trees']

        # 遍历每一棵树
        for tree_idx, tree in enumerate(trees):
            if 'split_conditions' in tree:
                split_conditions = tree['split_conditions']
                original_values = split_conditions.copy()

                # 对每个split_condition值减去delta
                modified_values = [val - delta for val in split_conditions]
                tree['split_conditions'] = modified_values

                # 统计修改数量
                num_modified = len(split_conditions)
                total_modified += num_modified


            else:
                print(f"警告: 树 {tree_idx} 中没有找到 'split_conditions' 字段")

    except KeyError as e:
        print(f"错误: 找不到预期的路径结构 - {e}")
        print("请检查JSON文件结构是否包含: learner.gradient_booster.model.trees")
        return 0

    # 保存修改后的模型
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(model, f, indent=2, ensure_ascii=False)

    print(f"\n修改完成！")
    print(f"- 共处理了 {len(trees)} 棵树")
    print(f"- 总共修改了 {total_modified} 个 split_conditions 值")
    print(f"- 每个值减去了 {delta}")
    print(f"- 输出文件保存至: {output_json_path}")

    return total_modified



# 使用示例
if __name__ == "__main__":
    # 示例1：修改所有树的split_conditions
    modify_xgboost_split_conditions(
        input_json_path="model1.json",
        output_json_path="model1_m.json",
        delta=1e-4
    )

