import gurobipy as gp

# 直接加载之前保存的模型文件
m = gp.read("my_model.mps")

# 加载后，可以继续添加约束、修改变量或直接求解
# 设置调优参数
# m.setParam('TimeLimit', 600)        # 单次求解时间限制
# m.setParam('TuneTimeLimit', 3600)   # 调优总时间限制
# m.setParam('TuneCriterion', 3)      # 调优准则：最大化下界
#
# 运行调优
m.tune()

# 获取最优参数并应用到模型
for i in range(m.getParamInfo('TuneResults')[2]):
    m.getTuneResult(i)
    # 使用调优后的参数重新求解
    m.optimize()