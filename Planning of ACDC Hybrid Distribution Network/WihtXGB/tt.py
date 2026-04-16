import numpy as np
import xgboost as xgb
print(np.log(982523.6979893927))

XGB_model1 = xgb.Booster()
XGB_model1.load_model('../XGBoost_main/model3.json')
df = XGB_model1.trees_to_dataframe()
print(df.columns)



# 只保留 split 节点
splits = df[df["Feature"] != "Leaf"][["Feature", "Split"]]
print(splits.value_counts().head(20))
print("总 split 数:", len(splits))
print("唯一 split 数:", splits.drop_duplicates().shape[0])

print(splits.groupby("Feature")["Split"].nunique().sort_values(ascending=False))