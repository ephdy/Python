import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.datasets import TUDataset
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv, global_mean_pool
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import seaborn as sns

# 设置随机种子，确保结果可重复
torch.manual_seed(42)
np.random.seed(42)

# 设置设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'使用设备: {device}')

# ==================== 1. 加载数据集 ====================
print("加载数据集...")
# 使用PROTEINS数据集（蛋白质图数据集，用于分类）
dataset = TUDataset(root='data/TUDataset', name='PROTEINS')
print(f'数据集大小: {len(dataset)}')
print(f'类别数量: {dataset.num_classes}')
print(f'节点特征维度: {dataset.num_node_features}')

# 划分训练集、验证集、测试集
dataset = dataset.shuffle()
train_ratio = 0.7
val_ratio = 0.15
test_ratio = 0.15

train_len = int(len(dataset) * train_ratio)
val_len = int(len(dataset) * val_ratio)
test_len = len(dataset) - train_len - val_len

train_dataset = dataset[:train_len]
val_dataset = dataset[train_len:train_len+val_len]
test_dataset = dataset[train_len+val_len:]

print(f'训练集大小: {len(train_dataset)}')
print(f'验证集大小: {len(val_dataset)}')
print(f'测试集大小: {len(test_dataset)}')

# 创建数据加载器
batch_size = 32
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# ==================== 2. 定义GNN模型 ====================
class GNNClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, num_layers=3, dropout=0.5):
        super(GNNClassifier, self).__init__()
        
        self.num_layers = num_layers
        
        # 图卷积层
        self.convs = nn.ModuleList()
        self.convs.append(GCNConv(input_dim, hidden_dim))
        
        for i in range(num_layers - 1):
            self.convs.append(GCNConv(hidden_dim, hidden_dim))
        
        # 批量归一化层
        self.bns = nn.ModuleList()
        for i in range(num_layers):
            self.bns.append(nn.BatchNorm1d(hidden_dim))
        
        # 全连接层
        self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc2 = nn.Linear(hidden_dim // 2, output_dim)
        
        self.dropout = dropout
        
    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        
        # 处理特征维度为0的情况
        if x is None:
            x = torch.ones((batch.size(0), 1), device=x.device if x is not None else device)
        
        # 图卷积层
        for i in range(self.num_layers):
            x = self.convs[i](x, edge_index)
            x = self.bns[i](x)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        
        # 全局平均池化
        x = global_mean_pool(x, batch)
        
        # 全连接层
        x = F.relu(self.fc1(x))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.fc2(x)
        
        return F.log_softmax(x, dim=1)

# ==================== 3. 训练和评估函数 ====================
def train(model, loader, optimizer, criterion):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        
        output = model(data)
        loss = criterion(output, data.y)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item() * data.num_graphs
        pred = output.max(1)[1]
        correct += pred.eq(data.y).sum().item()
        total += data.num_graphs
    
    return total_loss / total, correct / total

def evaluate(model, loader, criterion):
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for data in loader:
            data = data.to(device)
            output = model(data)
            loss = criterion(output, data.y)
            
            total_loss += loss.item() * data.num_graphs
            pred = output.max(1)[1]
            correct += pred.eq(data.y).sum().item()
            total += data.num_graphs
            
            all_preds.extend(pred.cpu().numpy())
            all_labels.extend(data.y.cpu().numpy())
    
    # 计算各种指标
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds, average='weighted')
    recall = recall_score(all_labels, all_preds, average='weighted')
    f1 = f1_score(all_labels, all_preds, average='weighted')
    
    return total_loss / total, correct / total, accuracy, precision, recall, f1, all_preds, all_labels

# ==================== 4. 训练模型 ====================
# 模型参数
input_dim = dataset.num_node_features
if input_dim == 0:
    input_dim = 1  # 处理没有节点特征的情况
    
hidden_dim = 64
output_dim = dataset.num_classes
num_layers = 3
dropout = 0.5
learning_rate = 0.001
num_epochs = 100

# 初始化模型
model = GNNClassifier(input_dim, hidden_dim, output_dim, num_layers, dropout).to(device)
print(f'\n模型结构:')
print(model)

# 优化器和损失函数
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=5e-4)
criterion = nn.NLLLoss()

# 训练历史记录
train_losses = []
val_losses = []
train_accs = []
val_accs = []

best_val_acc = 0
best_model_state = None

print("\n开始训练...")
for epoch in range(num_epochs):
    train_loss, train_acc = train(model, train_loader, optimizer, criterion)
    val_loss, val_acc, val_accuracy, val_precision, val_recall, val_f1, _, _ = evaluate(model, val_loader, criterion)
    
    train_losses.append(train_loss)
    val_losses.append(val_loss)
    train_accs.append(train_acc)
    val_accs.append(val_acc)
    
    # 保存最佳模型
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        best_model_state = model.state_dict().copy()
    
    if (epoch + 1) % 10 == 0:
        print(f'Epoch {epoch+1:3d}/{num_epochs} | '
              f'Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | '
              f'Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}')

print(f'\n最佳验证准确率: {best_val_acc:.4f}')

# 加载最佳模型
model.load_state_dict(best_model_state)

# ==================== 5. 测试模型 ====================
test_loss, test_acc, test_accuracy, test_precision, test_recall, test_f1, test_preds, test_labels = evaluate(model, test_loader, criterion)

print("\n=== 测试集结果 ===")
print(f'准确率 (Accuracy): {test_accuracy:.4f}')
print(f'精确率 (Precision): {test_precision:.4f}')
print(f'召回率 (Recall): {test_recall:.4f}')
print(f'F1分数 (F1-Score): {test_f1:.4f}')

# ==================== 6. 可视化结果 ====================
# 6.1 训练曲线
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].plot(train_losses, label='Train Loss', color='blue')
axes[0].plot(val_losses, label='Val Loss', color='red')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('Loss')
axes[0].set_title('Loss Curves')
axes[0].legend()
axes[0].grid(True)

axes[1].plot(train_accs, label='Train Accuracy', color='blue')
axes[1].plot(val_accs, label='Val Accuracy', color='red')
axes[1].set_xlabel('Epoch')
axes[1].set_ylabel('Accuracy')
axes[1].set_title('Accuracy Curves')
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig('training_curves.png', dpi=100)
plt.show()

# 6.2 混淆矩阵
cm = confusion_matrix(test_labels, test_preds)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=range(output_dim), 
            yticklabels=range(output_dim))
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.savefig('confusion_matrix.png', dpi=100)
plt.show()

# ==================== 7. 模型预测示例 ====================
def predict_single_graph(model, graph_data):
    """对单个图进行预测"""
    model.eval()
    with torch.no_grad():
        graph_data = graph_data.to(device)
        output = model(graph_data)
        pred = output.max(1)[1]
        probs = torch.exp(output)
        return pred.item(), probs.cpu().numpy()[0]

# 测试几个样本
print("\n=== 预测示例 ===")
for i in range(min(5, len(test_dataset))):
    graph = test_dataset[i]
    pred, probs = predict_single_graph(model, graph)
    true_label = graph.y.item()
    print(f'样本 {i+1}:')
    print(f'  真实标签: {true_label}')
    print(f'  预测标签: {pred}')
    print(f'  预测概率: {probs}')
    print(f'  预测正确: {"✓" if pred == true_label else "✗"}')
    print()

print("\n训练完成！")