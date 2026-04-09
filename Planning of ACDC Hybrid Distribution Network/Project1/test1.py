from gurobipy import *
import csv
try:
    # Create a new model
    m = Model("mip1")
    # Create variables
    x = m.addVar(vtype=GRB.BINARY, name="x")
    y = m.addVar(vtype=GRB.BINARY, name="y")
    z = m.addVar(vtype=GRB.BINARY, name="z")
    # Set objective
    m.setObjective(x + y + 2 * z, GRB.MAXIMIZE)
    # Add constraint: x + 2 y + 3 z <= 4
    m.addConstr(x + 2 * y + 3 * z <= 4, "c0")
    # Add constraint: x + y >= 1
    m.addConstr(x + y >= 1, "c1")
    m.optimize()
    Result = []
    for v in m.getVars():
        print(v.varName, v.x)
        Result.append([v.VarName, v.X])
    print('Obj:', m.objVal)
    print(m.objVal+2)
    print(type(1.0))
    print(Result)

    # # 指定文件名和写入模式
    # filename = 'people.csv'
    #
    # # 使用with语句打开文件，确保正确关闭，并写入数据
    # with open(filename, mode='w', newline='', encoding='utf-8') as file:
    #     writer = csv.writer(file)
    #     for row in Result:
    #         writer.writerow(row)

except GurobiError:
    print('Error reported')