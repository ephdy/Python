import gurobipy as gp
from gurobipy import GRB

m = gp.Model()

x = m.addVar()
y = m.addVar()

f1 = x + y
f2 = -x

# priority 越大优先级越高
m.setObjectiveN(f1, index=0, priority=2)
m.setObjectiveN(f2, index=1, priority=1)

m.optimize()

print("NumObj =", m.NumObj)
for i in range(m.NumObj):
    print(f"Objective {i} value =", m.getObjective(i).getValue())
