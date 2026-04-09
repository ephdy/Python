import numpy as np
import pandas as pd

data = pd.read_csv("受限邻接矩阵.CSV")

X = data.iloc[:].values
print(X[0])
print(data.columns.tolist())
