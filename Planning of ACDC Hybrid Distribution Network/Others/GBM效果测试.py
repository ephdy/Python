import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error, explained_variance_score,
    max_error, median_absolute_error
)
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class LightGBMRegressorValidator:
    def __init__(self, model_path):
        """
        初始化回归模型验证器
        Args:
            model_path: LightGBM模型文件路径
        """
        self.model_path = model_path
        self.model = None

    def load_model(self):
        """加载LightGBM模型"""
        try:
            # 原生LightGBM模型
            self.model = lgb.Booster(model_file=self.model_path)
            print(f"✅ 模型加载成功: {self.model_path}")
            return self.model
        except:
            try:
                # sklearn接口的LightGBM模型
                import joblib
                self.model = joblib.load(self.model_path)
                print(f"✅ sklearn模型加载成功: {self.model_path}")
                return self.model
            except Exception as e:
                print(f"❌ 模型加载失败: {e}")
                return None

    def validate_regression(self, X_test, y_test, save_plots=True):
        """
        回归模型性能验证
        Args:
            X_test: 测试集特征
            y_test: 测试集真实值
            save_plots: 是否保存图表
        """
        print("\n" + "=" * 60)
        print("📊 回归模型性能评估")
        print("=" * 60)

        # 数据预处理
        if isinstance(X_test, pd.DataFrame):
            feature_names = X_test.columns.tolist()
            X_test_arr = X_test.values
        else:
            X_test_arr = X_test
            feature_names = [f'feature_{i}' for i in range(X_test_arr.shape[1])]

        if isinstance(y_test, pd.Series):
            y_test_arr = y_test.values
        else:
            y_test_arr = np.array(y_test).flatten()

        # 预测
        y_pred = self.model.predict(X_test_arr)
        if len(y_pred.shape) > 1:
            y_pred = y_pred.flatten()

        # 残差
        residuals = y_test_arr - y_pred

        # ==================== 计算所有回归指标 ====================
        metrics = {}

        # 1. 均方误差 (MSE)
        metrics['MSE'] = mean_squared_error(y_test_arr, y_pred)

        # 2. 均方根误差 (RMSE)
        metrics['RMSE'] = np.sqrt(metrics['MSE'])

        # 3. 平均绝对误差 (MAE)
        metrics['MAE'] = mean_absolute_error(y_test_arr, y_pred)

        # 4. 中位数绝对误差
        metrics['MedAE'] = median_absolute_error(y_test_arr, y_pred)

        # 5. R² 决定系数
        metrics['R²'] = r2_score(y_test_arr, y_pred)

        # 6. 解释方差分数
        metrics['Explained Variance'] = explained_variance_score(y_test_arr, y_pred)

        # 7. MAPE（平均绝对百分比误差）
        # 避免除零
        mask = y_test_arr != 0
        if mask.sum() > 0:
            metrics['MAPE'] = mean_absolute_percentage_error(
                y_test_arr[mask], y_pred[mask]
            ) * 100  # 转为百分比
        else:
            metrics['MAPE'] = np.nan

        # 8. 最大误差
        metrics['Max Error'] = max_error(y_test_arr, y_pred)

        # 9. 均方根对数误差 (RMSLE)
        # 确保数据为正
        if (y_test_arr > 0).all() and (y_pred > 0).all():
            metrics['RMSLE'] = np.sqrt(
                mean_squared_error(np.log1p(y_test_arr), np.log1p(y_pred))
            )
        else:
            metrics['RMSLE'] = np.nan

        # ==================== 打印指标 ====================
        print("\n📈 回归性能指标:")
        print("-" * 40)
        print(f"📌 MSE (均方误差):           {metrics['MSE']:.4f}")
        print(f"📌 RMSE (均方根误差):         {metrics['RMSE']:.4f}")
        print(f"📌 MAE (平均绝对误差):        {metrics['MAE']:.4f}")
        print(f"📌 MedAE (中位数绝对误差):    {metrics['MedAE']:.4f}")
        print(f"📌 R² Score (决定系数):       {metrics['R²']:.4f}")
        print(f"📌 Explained Variance (解释方差): {metrics['Explained Variance']:.4f}")

        if not np.isnan(metrics['MAPE']):
            print(f"📌 MAPE (平均绝对百分比误差):  {metrics['MAPE']:.2f}%")
        else:
            print(f"📌 MAPE: 无法计算（真实值含0）")

        print(f"📌 Max Error (最大误差):      {metrics['Max Error']:.4f}")

        if not np.isnan(metrics['RMSLE']):
            print(f"📌 RMSLE (均方根对数误差):    {metrics['RMSLE']:.4f}")

        # ==================== 可视化 ====================
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        # 1. 预测值 vs 真实值散点图
        ax1 = axes[0, 0]
        ax1.scatter(y_test_arr, y_pred, alpha=0.5, edgecolors='k', linewidth=0.5)
        # 理想线
        min_val = min(y_test_arr.min(), y_pred.min())
        max_val = max(y_test_arr.max(), y_pred.max())
        ax1.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='理想线')
        ax1.set_xlabel('真实值 (True Values)')
        ax1.set_ylabel('预测值 (Predictions)')
        ax1.set_title(f'预测值 vs 真实值\nR² = {metrics["R²"]:.4f}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 残差分布图
        ax2 = axes[0, 1]
        ax2.scatter(y_pred, residuals, alpha=0.5, edgecolors='k', linewidth=0.5)
        ax2.axhline(y=0, color='r', linestyle='--', linewidth=2)
        ax2.set_xlabel('预测值 (Predictions)')
        ax2.set_ylabel('残差 (Residuals)')
        ax2.set_title('残差分布图')
        ax2.grid(True, alpha=0.3)

        # 3. 残差直方图
        ax3 = axes[1, 0]
        ax3.hist(residuals, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
        ax3.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax3.set_xlabel('残差 (Residuals)')
        ax3.set_ylabel('频数')
        ax3.set_title(f'残差分布直方图\n均值={residuals.mean():.4f}, 标准差={residuals.std():.4f}')
        ax3.grid(True, alpha=0.3)

        # 4. 性能指标条形图
        ax4 = axes[1, 1]
        metrics_plot = {
            'MSE': metrics['MSE'],
            'RMSE': metrics['RMSE'],
            'MAE': metrics['MAE'],
            'MedAE': metrics['MedAE']
        }
        # 归一化以便显示
        max_metric = max(metrics_plot.values())
        metrics_plot_norm = {k: v / max_metric for k, v in metrics_plot.items()}

        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        bars = ax4.bar(metrics_plot_norm.keys(), metrics_plot_norm.values(), color=colors, edgecolor='black')
        ax4.set_ylabel('归一化值（相对最大指标）')
        ax4.set_title('误差指标对比（归一化）')
        ax4.grid(True, alpha=0.3, axis='y')

        # 在条形图上标注真实值
        for bar, (name, val) in zip(bars, metrics_plot.items()):
            ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                     f'{val:.4f}', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()

        if save_plots:
            plt.savefig('regression_validation_results.png', dpi=300, bbox_inches='tight')
            print("\n✅ 图表已保存为: regression_validation_results.png")

        plt.show()

        # ==================== 特征重要性 ====================
        if hasattr(self.model, 'feature_importance'):
            importance = self.model.feature_importance(importance_type='gain')
            feature_importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)

            print("\n📊 Top 10 特征重要性:")
            print("-" * 40)
            print(feature_importance_df.head(10).to_string(index=False))

            # 特征重要性图
            plt.figure(figsize=(10, 6))
            top_features = feature_importance_df.head(15)
            plt.barh(range(len(top_features)), top_features['importance'].values,
                     color='steelblue', edgecolor='black')
            plt.yticks(range(len(top_features)), top_features['feature'].values)
            plt.xlabel('重要性 (Gain)')
            plt.title('特征重要性 Top 15')
            plt.gca().invert_yaxis()
            plt.grid(True, alpha=0.3, axis='x')
            plt.tight_layout()

            if save_plots:
                plt.savefig('feature_importance.png', dpi=300, bbox_inches='tight')
                print("✅ 特征重要性图已保存为: feature_importance.png")

            plt.show()

        # ==================== 返回结果 ====================
        results = {
            'metrics': metrics,
            'y_true': y_test_arr,
            'y_pred': y_pred,
            'residuals': residuals
        }

        return results


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 1. 初始化验证器
    model_path = "2000trees.txt"  # 替换为你的模型路径
    validator = LightGBMRegressorValidator(model_path)

    # 2. 加载模型
    model = validator.load_model()

    if model is not None:
        data = pd.read_csv("100万fop.CSV")

        # Split features and labels
        X = data.iloc[:, :13 + 33 + 2].values
        y = data.iloc[:, -1].values
        print(y.min(), y.max())
        # y=(y-y.min())/(y.max()-y.min())
        print(f"X shape: {X.shape}")
        print(f"y range: [{y.min():.2f}, {y.max():.2f}]")
        # quantiles = pd.qcut(y, q=10, labels=False)
        # sample_weights = 10 - quantiles  # 最小的一组权重=5，最大的一组权重=1
        # Split training and test sets (no log transformation)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        # 3. 加载测试数据
        # 方式1: 从CSV加载
        # test_df = pd.read_csv('test_data.csv')GBM效果测试.py
        # X_test = test_df.drop(['target_column'], axis=1)
        # y_test = test_df['target_column']

        # 方式2: 使用numpy数组示例
        # np.random.seed(42)
        # X_test = np.random.randn(1000, 10)
        # y_test = 2 * X_test[:, 0] + 3 * X_test[:, 1] + np.random.randn(1000) * 0.5

        # 4. 验证模型性能
        results = validator.validate_regression(X_test, y_test)

        print("\n❓ 请替换测试数据路径，取消注释上面的代码并运行！")
        print("=" * 60)