import gurobipy as gp

# 直接加载之前保存的模型文件
loaded_model = gp.read("my_model.mps")

# 加载后，可以继续添加约束、修改变量或直接求解
loaded_model.optimize()