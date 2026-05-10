import torch
import torch.nn as nn
import torch.nn.functional as F
import pandas as pd
from torch_geometric.data import Data
import _13_nodes_distribution_network as H
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv, global_mean_pool

# =========================
# 1. 构造数据（示例）
def build_graph(node_types, edge_list, y_value):
    num_nodes = 13

    # 1️⃣ 节点特征 x（只用类型）
    x = torch.tensor(node_types, dtype=torch.float).reshape(-1, 1)

    # 2️⃣ 边 edge_index
    edge_index = torch.tensor(edge_list, dtype=torch.long).t()

    # 3️⃣ 无向图（必须）
    edge_index = torch.cat([edge_index, edge_index.flip(0)], dim=1)

    # 4️⃣ 标签
    y = torch.tensor([y_value], dtype=torch.float)

    return Data(x=x, edge_index=edge_index, y=y)
# =========================
data = pd.read_csv("100万fop.CSV")
# Split features and labels
X = data.iloc[:, :13 + 33 + 2].values
y = data.iloc[:, -1].values

dataset = []

for i in range(len(X)):
    U=X[i][13:13+33]

    edges=[]
    for k in range(len(H.Branch)):
        if U[k] == 1:
            i, j = H.Branch[k]
            edges.append((i, j))

    data = build_graph(
        X[i][:13],
        edges,
        y[i]
    )
    dataset.append(data)

train_loader = DataLoader(dataset, batch_size=32, shuffle=True)
print(len(dataset))        # 样本数
print(dataset[0])          # 看第一个图

for batch in train_loader:
    print(batch.x.shape)          # [总节点数, 特征数]
    print(batch.edge_index.shape)
    print(batch.batch.shape)      # 批信息（重要）
    break


# =========================
# 2. 定义 GNN 模型
# =========================
class GNNModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(1, 32)
        self.conv2 = GCNConv(32, 32)
        self.fc = nn.Linear(32, 1)

    def forward(self, x, edge_index, batch):
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index))

        # 图级聚合（关键）
        x = global_mean_pool(x, batch)

        x = self.fc(x)
        return x.squeeze()


# =========================
# 3. 初始化
# =========================
device = torch.device("cpu")

model = GNNModel().to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = nn.MSELoss()

# =========================
# 4. 训练函数
# =========================
def train():
    model.train()
    total_loss = 0

    for batch in train_loader:
        batch = batch.to(device)

        optimizer.zero_grad()
        out = model(batch.x, batch.edge_index, batch.batch)

        loss = criterion(out, batch.y.view(-1))
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(train_loader)


# =========================
# 5. 验证函数
# =========================
def evaluate(loader):
    model.eval()
    preds, targets = [], []

    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)

            out = model(batch.x, batch.edge_index, batch.batch)
            preds.append(out.cpu())
            targets.append(batch.y.view(-1).cpu())

    preds = torch.cat(preds)
    targets = torch.cat(targets)

    rmse = torch.sqrt(F.mse_loss(preds, targets))
    r2 = 1 - torch.sum((preds - targets) ** 2) / torch.sum((targets - targets.mean()) ** 2)

    return rmse.item(), r2.item()


# =========================
# 6. 训练循环
# =========================
for epoch in range(1, 101):
    loss = train()
    rmse, r2 = evaluate(train_loader)

    if epoch % 10 == 0:
        print(f"Epoch {epoch:03d} | Loss {loss:.4f} | RMSE {rmse:.4f} | R2 {r2:.4f}")


# =========================
# 7. 保存模型
# =========================
torch.save(model.state_dict(), "gnn_model.pth")
