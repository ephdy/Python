import Box2 as B
import pandas as pd
import numpy as np
if __name__ == "__main__":
    data = pd.read_csv('采样结果.csv')
    X = data.iloc[:].values
    B.Draw_Grid(X[45])
    # for i in range(len(X)):
    #     print(f"\r进度: {i+1}/{len(X)}", end='', flush=True)
    #     res=B.Operation(X[i], 1)
    #     B.save_csv(np.concatenate([X[i], res]),'受限邻接矩阵结果.CSV')
