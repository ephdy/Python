# =========================================================
# GINE for Graph Regression
# 适用于：
# 配电网拓扑 / 开关状态 / 潮流优化结果预测
# =========================================================
import _13_nodes_distribution_network as H
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd

from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

from torch_geometric.nn import (
    GINEConv,
    global_add_pool
)

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_percentage_error,
    r2_score,
    mean_squared_error
)

# =========================================================
# 1. 构造示例数据
# =========================================================

"""
你最终需要替换这里：

node_features
edge_index
edge_attr
target

为你自己的真实配电网数据
"""
load = []
for i in range(H.n):
    n_load = []
    for t in range(H.T):
        n_load.append(H.P_load[t] * H.n_Load[i])
    load.append(n_load)
DG = []
for i in range(H.n):
    n_DG = []
    if i == 7:
        for t in range(H.T):
            n_DG.append(H.DG_curve[t] * 2 / 9 / H.S_base)
    elif i == 8:
        for t in range(H.T):
            n_DG.append(H.DG_curve[t] * 2.5 / 9 / H.S_base)
    elif i == 10:
        for t in range(H.T):
            n_DG.append(H.DG_curve[t] * 2.0 / 9 / H.S_base)
    elif i == 12:
        for t in range(H.T):
            n_DG.append(H.DG_curve[t] * 2 / 9 / H.S_base)
    else:
        n_DG = [0 for k in range(H.T)]
    DG.append(n_DG)

r_l = []
x_l = []
for (i, j) in H.Branch:
    r_l.append(H.r_line[i][j][0])
    x_l.append(H.x_line[i][j][0])

r_l = np.array(r_l)
x_l = np.array(x_l)

load = np.array(load)
DG = np.array(DG)
h_stack = np.hstack([load, DG])

data = pd.read_csv("100万fop.CSV")
# Split features and labels
X = data.iloc[:, :13 + 33 + 2].values
Y = data.iloc[:, -1].values
dataset = []

NUM_SAMPLES = len(X)

for k in range(1000):

    # -------------------------
    # 假设13节点
    # -------------------------

    num_nodes = 13

    # -------------------------
    # 节点特征
    # 例如：
    # [负荷, DG, 节点类型]
    # -------------------------
    type = X[k][:13]
    mu = X[k][13 + 33] * 0.1
    epsilon = 0.1 + X[k][13 + 33 + 1] * 0.1
    node_type = type.reshape(-1, 1)
    Q = []
    for i in range(H.n):
        n_Q = []
        if i == 7:
            n_Q = ([(1 + mu), (1 + mu) * (1 - epsilon), (1 + mu) * (1 + epsilon)])
        elif i == 8:
            n_Q = ([(1 + mu), (1 + mu) * (1 - epsilon), (1 + mu) * (1 + epsilon)])
        elif i == 10:
            n_Q = ([(1 + mu), (1 + mu) * (1 - epsilon), (1 + mu) * (1 + epsilon)])
        elif i == 12:
            n_Q = ([(1 + mu), (1 + mu) * (1 - epsilon), (1 + mu) * (1 + epsilon)])
        else:
            n_Q = [0 for k in range(3)]
        Q.append(n_Q)
    Q = np.array(Q)
    node_feature_matrix = np.hstack([node_type, h_stack, Q])
    x = torch.tensor(
        node_feature_matrix,
        dtype=torch.float
    )

    # -------------------------
    # 边连接
    # -------------------------
    edge_0 = []
    edge_1 = []
    for edge in H.Branch:
        edge_0.append(edge[0])
        edge_1.append(edge[1])
    edge_index = torch.tensor([
        edge_0,
        edge_1
    ], dtype=torch.long)

    # 无向图
    edge_index = torch.cat([
        edge_index,
        edge_index.flip(0)
    ], dim=1)

    # -------------------------
    # 边特征
    #
    # [开关状态, 电阻, 电抗]
    # -------------------------

    U = X[k][13:13 + 33]

    edge_feature_matrix = np.column_stack([U, r_l, x_l])

    edge_attr = torch.tensor(
        edge_feature_matrix,
        dtype=torch.float
    )
    edge_attr = torch.cat([
        edge_attr,
        edge_attr
    ], dim=0)

    # -------------------------
    # 回归目标
    # -------------------------

    y = Y[k]

    data = Data(
        x=x,
        edge_index=edge_index,
        edge_attr=edge_attr,
        y=y
    )

    dataset.append(data)

# =========================================================
# 2. 标准化目标值
# =========================================================

y_all = np.array([
    d.y.item() for d in dataset
]).reshape(-1, 1)

y_scaler = StandardScaler()

y_scaled = y_scaler.fit_transform(y_all)

for i, d in enumerate(dataset):
    d.y = torch.tensor(
        y_scaled[i],
        dtype=torch.float
    )

# =========================================================
# 3. 划分训练测试
# =========================================================

train_dataset, test_dataset = train_test_split(
    dataset,
    test_size=0.2,
    random_state=42
)

train_loader = DataLoader(
    train_dataset,
    batch_size=64,
    shuffle=True
)

test_loader = DataLoader(
    test_dataset,
    batch_size=64,
    shuffle=False
)


# =========================================================
# 4. GINE网络
# =========================================================

class GINEModel(nn.Module):

    def __init__(
            self,
            node_dim,
            edge_dim,
            hidden_dim=128):

        super().__init__()

        hidden_dim = 64

        # =====================================
        # 节点编码
        # =====================================

        self.node_encoder = nn.Linear(
            52,
            hidden_dim
        )

        # =====================================
        # 边编码
        # =====================================

        self.edge_encoder = nn.Linear(
            3,
            hidden_dim
        )

        # =====================================
        # GINE layer 1
        # =====================================

        nn1 = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )

        self.conv1 = GINEConv(nn1)

        # =====================================
        # GINE layer 2
        # =====================================

        nn2 = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )

        self.conv2 = GINEConv(nn2)

        # =====================================
        # Regression Head
        # =====================================

        self.mlp = nn.Sequential(

            nn.Linear(hidden_dim, 128),
            nn.ReLU(),

            nn.Dropout(0.2),

            nn.Linear(128, 64),
            nn.ReLU(),

            nn.Linear(64, 1)
        )

    def forward(
        self,
        x,
        edge_index,
        edge_attr,
        batch
    ):

        # =====================================
        # encoder
        # =====================================

        x = self.node_encoder(x)

        edge_attr = self.edge_encoder(
            edge_attr
        )

        # =====================================
        # GINE
        # =====================================

        h = self.conv1(
            x,
            edge_index,
            edge_attr
        )

        h = F.relu(h)

        h = self.conv2(
            h,
            edge_index,
            edge_attr
        )

        h = F.relu(h)

        # =====================================
        # Global Pooling
        # =====================================

        hg = global_add_pool(
            h,
            batch
        )

        # =====================================
        # Regression
        # =====================================

        out = self.mlp(hg)

        return out

# =========================================================
# 5. 初始化
# =========================================================

device = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

model = GINEModel(
    node_dim=52,
    edge_dim=3,
    hidden_dim=128
).to(device)

criterion = nn.MSELoss()

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=1e-3,
    weight_decay=1e-4
)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode='min',
    factor=0.5,
    patience=10
)

# =========================================================
# 6. 训练
# =========================================================

EPOCHS = 200

best_loss = 1e9

for epoch in range(EPOCHS):

    # =====================================================
    # Train
    # =====================================================

    model.train()

    total_loss = 0

    for batch_data in train_loader:
        batch_data = batch_data.to(device)

        pred = model(
            batch_data.x,
            batch_data.edge_index,
            batch_data.edge_attr,
            batch_data.batch
        )

        loss = criterion(
            pred,
            batch_data.y.reshape(-1, 1)
        )

        optimizer.zero_grad()

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            1.0
        )

        optimizer.step()

        total_loss += loss.item()

    train_loss = total_loss / len(train_loader)

    # =====================================================
    # Eval
    # =====================================================

    model.eval()

    preds = []
    trues = []

    with torch.no_grad():

        for batch_data in test_loader:
            batch_data = batch_data.to(device)

            pred = model(
                batch_data.x,
                batch_data.edge_index,
                batch_data.edge_attr,
                batch_data.batch
            )

            preds.append(
                pred.cpu().numpy().reshape(-1,1)
            )

            trues.append(
                batch_data.y.cpu().numpy().reshape(-1,1)
            )

    preds = np.vstack(preds)

    trues = np.vstack(trues)

    # 反标准化
    preds_real = y_scaler.inverse_transform(preds)

    trues_real = y_scaler.inverse_transform(trues)

    # =====================================================
    # Metrics
    # =====================================================

    rmse = np.sqrt(
        mean_squared_error(
            trues_real,
            preds_real
        )
    )

    mape = mean_absolute_percentage_error(
        trues_real,
        preds_real
    )

    r2 = r2_score(
        trues_real,
        preds_real
    )

    scheduler.step(train_loss)

    print(
        f"Epoch {epoch + 1:03d} | "
        f"Loss {train_loss:.6f} | "
        f"RMSE {rmse:.4f} | "
        f"MAPE {mape:.6f} | "
        f"R2 {r2:.4f}"
    )

    # =====================================================
    # 保存最好模型
    # =====================================================

    if train_loss < best_loss:
        best_loss = train_loss

        torch.save(
            model.state_dict(),
            "best_gine_model.pth"
        )

# =========================================================
# 7. 加载模型
# =========================================================

model.load_state_dict(
    torch.load("best_gine_model.pth")
)

print("Training Finished")
