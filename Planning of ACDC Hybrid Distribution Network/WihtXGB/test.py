import xgboost as xgb
import os

# 加载你的模型
model = xgb.Booster()
model.load_model('../XGBoost_main/model1.ubj')

# 分析模型复杂度
dump = model.get_dump()
n_trees = len(dump)
total_nodes = sum(len(tree.split('\n')) for tree in dump)

print(f"文件大小: {os.path.getsize('../XGBoost_main/model1.ubj') / (1024*1024):.1f} MB")
print(f"树的数量: {n_trees}")
print(f"总节点数: {total_nodes}")

# 给出可行性建议
if total_nodes < 50000:
    print("✅ 模型规模适中，构建时间预计5-15分钟")
elif total_nodes < 150000:
    print("⚠️ 模型较大，构建时间可能超过30分钟，建议简化")
else:
    print("❌ 节点数过多，建议进一步压缩模型")