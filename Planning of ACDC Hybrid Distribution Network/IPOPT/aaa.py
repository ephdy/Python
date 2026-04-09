import sys
import os
import pyomo

# 获取程序运行时的实际路径（打包前后都适用）
if getattr(sys, 'frozen', False):
    # 打包后的 exe 运行
    base_path = sys._MEIPASS
else:
    # 普通 Python 脚本运行
    base_path = os.path.dirname(__file__)

ipopt_path = os.path.join(base_path, 'ipopt.exe')  # Windows
# ipopt_path = os.path.join(base_path, 'ipopt')   # Linux/macOS
print(ipopt_path)
# 创建求解器时指定路径
# solver = pyomo.SolverFactory('ipopt', executable=ipopt_path)