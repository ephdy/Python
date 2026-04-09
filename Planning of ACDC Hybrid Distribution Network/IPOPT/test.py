# 首先安装: conda install -c conda-forge pyomo pyomo.extras ipopt

from pyomo.environ import *

# 创建模型
model = ConcreteModel()

# 定义变量
model.x1 = Var(bounds=(1, 5), initialize=1.0)
model.x2 = Var(bounds=(1, 5), initialize=5.0)
model.x3 = Var(bounds=(1, 5), initialize=5.0)
model.x4 = Var(bounds=(1, 5), initialize=1.0)

# 目标函数
model.obj = Objective(
    expr=model.x1 * model.x4 * (model.x1 + model.x2 + model.x3) + model.x3,
    sense=minimize
)

# 约束条件
model.con1 = Constraint(expr=model.x1 * model.x2 * model.x3 * model.x4 >= 25)
model.con2 = Constraint(expr=model.x1**2 + model.x2**2 + model.x3**2 + model.x4**2 == 40)

# 创建求解器并求解
solver = SolverFactory('ipopt')
solver.options['print_level'] = 5
solver.options['tol'] = 1e-7

results = solver.solve(model, tee=True)

# 输出结果
print("\n" + "="*50)
print("求解状态:", results.solver.termination_condition)
print("最优解:")
print(f"  x1 = {model.x1():.6f}")
print(f"  x2 = {model.x2():.6f}")
print(f"  x3 = {model.x3():.6f}")
print(f"  x4 = {model.x4():.6f}")
print(f"目标函数值: {model.obj():.6f}")
print(f"约束1 (x1*x2*x3*x4): {model.x1() * model.x2() * model.x3() * model.x4():.6f}")
print(f"约束2 (x1^2+x2^2+x3^2+x4^2): {model.x1()**2 + model.x2()**2 + model.x3()**2 + model.x4()**2:.6f}")
print("="*50)