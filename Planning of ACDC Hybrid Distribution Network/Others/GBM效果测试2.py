import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error, explained_variance_score,
    max_error, median_absolute_error
)
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from sklearn.model_selection import train_test_split
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

    def calculate_backfitting_error(self, y_true, y_pred):
        """
        计算回代误差（相对误差的绝对值百分比）
        """
        # 将输入转换为numpy数组
        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        # 避免除零错误
        mask = y_true_arr != 0
        backfitting_error = np.full_like(y_true_arr, np.nan, dtype=float)
        backfitting_error[mask] = np.abs((y_true_arr[mask] - y_pred_arr[mask]) / y_true_arr[mask]) * 100

        return backfitting_error

    def calculate_interval_errors_detailed(self, y_true, y_pred, n_intervals=10, interval_type='equal_frequency'):
        """
        按目标值大小分区间计算详细的回代误差

        Args:
            y_true: 真实值
            y_pred: 预测值
            n_intervals: 区间数量
            interval_type: 区间划分方式
                - 'equal_width': 等宽区间
                - 'equal_frequency': 等频区间（推荐）

        Returns:
            DataFrame: 每个区间的详细误差统计
        """
        # 确保数据格式正确
        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        # 创建数据框
        df = pd.DataFrame({
            'y_true': y_true_arr,
            'y_pred': y_pred_arr
        })

        # 计算回代误差（相对误差的绝对值）
        df['回代误差(%)'] = self.calculate_backfitting_error(y_true_arr, y_pred_arr)

        # 按目标值排序
        df = df.sort_values('y_true').reset_index(drop=True)

        # 划分区间
        if interval_type == 'equal_width':
            # 等宽区间
            df['区间'] = pd.cut(df['y_true'], bins=n_intervals, include_lowest=True)

        elif interval_type == 'equal_frequency':
            # 等频区间（每个区间样本数相近）
            df['区间'] = pd.qcut(df['y_true'], q=n_intervals, duplicates='drop')

        # 计算每个区间的详细统计
        interval_stats = []

        for interval, group in df.groupby('区间', observed=False):
            # 过滤掉无效的回代误差
            valid_errors = group['回代误差(%)'].dropna()

            if len(valid_errors) == 0:
                continue

            stats = {
                '区间': str(interval),
                '样本数': len(group),
                '占比(%)': round(len(group) / len(df) * 100, 2),
                '真实值范围': f"[{group['y_true'].min():.4f}, {group['y_true'].max():.4f}]",
                '真实值均值': group['y_true'].mean(),
                '预测值均值': group['y_pred'].mean(),

                # 回代误差统计
                '平均回代误差(%)': valid_errors.mean(),
                '最小回代误差(%)': valid_errors.min(),
                '最大回代误差(%)': valid_errors.max(),
                '回代误差中位数(%)': valid_errors.median(),
                '回代误差标准差(%)': valid_errors.std(),

                # 误差区间比例
                '样本数(<5%)': (valid_errors < 5).sum(),
                '比例(<5%)': round((valid_errors < 5).sum() / len(valid_errors) * 100, 2),
                '样本数(<10%)': (valid_errors < 10).sum(),
                '比例(<10%)': round((valid_errors < 10).sum() / len(valid_errors) * 100, 2),

                # 传统指标
                'RMSE': np.sqrt(mean_squared_error(group['y_true'], group['y_pred'])),
                'MAE': mean_absolute_error(group['y_true'], group['y_pred']),
                'R²': r2_score(group['y_true'], group['y_pred']) if len(group) > 1 else np.nan,
            }
            interval_stats.append(stats)

        result_df = pd.DataFrame(interval_stats)
        return result_df

    def print_interval_backfitting_errors(self, y_true, y_pred, n_intervals=10, interval_type='equal_frequency'):
        """
        打印按目标值大小分区间的回代误差详细统计
        """
        print("\n" + "=" * 100)
        print(f"📊 按目标值大小分区间回代误差统计（{n_intervals}个区间）")
        print(f"   区间划分方式: {interval_type}")
        print("=" * 100)

        # 确保数据格式正确
        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        # 计算总体回代误差（修复：使用numpy操作而非pandas的replace）
        backfitting_error = self.calculate_backfitting_error(y_true_arr, y_pred_arr)
        valid_errors = backfitting_error[~np.isnan(backfitting_error)]

        if len(valid_errors) > 0:
            print("\n📈 整体回代误差统计:")
            print("-" * 60)
            print(f"平均回代误差: {np.mean(valid_errors):.2f}%")
            print(f"最小回代误差: {np.min(valid_errors):.2f}%")
            print(f"最大回代误差: {np.max(valid_errors):.2f}%")
            print(f"回代误差中位数: {np.median(valid_errors):.2f}%")
            print(f"回代误差<5%的样本比例: {(valid_errors < 5).sum() / len(valid_errors) * 100:.2f}%")
            print(f"回代误差<10%的样本比例: {(valid_errors < 10).sum() / len(valid_errors) * 100:.2f}%")
        else:
            print("\n⚠️ 警告: 所有回代误差都无法计算（可能真实值全为0）")

        # 计算分区间的详细统计
        df = self.calculate_interval_errors_detailed(y_true_arr, y_pred_arr, n_intervals, interval_type)

        if len(df) == 0:
            print("\n⚠️ 无法计算分区间统计")
            return df

        # 格式化输出 - 表1：基本信息和回代误差
        print("\n" + "=" * 100)
        print("📋 分区间回代误差详细统计表 (Part 1: 基本信息)")
        print("=" * 100)
        print(f"{'区间':<25} {'样本数':>6} {'占比(%)':>8} {'真实值范围':>20} {'真实值均值':>10} {'预测值均值':>10}")
        print("-" * 100)

        for _, row in df.iterrows():
            interval_str = str(row['区间'])[:25]
            print(f"{interval_str:<25} {int(row['样本数']):>6} {row['占比(%)']:>8.2f} "
                  f"{row['真实值范围']:>20} {row['真实值均值']:>10.4f} {row['预测值均值']:>10.4f}")

        print("\n" + "=" * 100)
        print("📋 分区间回代误差详细统计表 (Part 2: 回代误差)")
        print("=" * 100)
        print(f"{'区间':<25} {'平均回代误差%':>13} {'最小回代误差%':>13} {'最大回代误差%':>13} "
              f"{'中位数误差%':>10} {'标准差%':>8}")
        print("-" * 100)

        for _, row in df.iterrows():
            interval_str = str(row['区间'])[:25]
            print(f"{interval_str:<25} {row['平均回代误差(%)']:>13.2f} {row['最小回代误差(%)']:>13.2f} "
                  f"{row['最大回代误差(%)']:>13.2f} {row['回代误差中位数(%)']:>10.2f} "
                  f"{row['回代误差标准差(%)']:>8.2f}")

        print("\n" + "=" * 100)
        print("📋 分区间回代误差详细统计表 (Part 3: 误差小于阈值比例)")
        print("=" * 100)
        print(f"{'区间':<25} {'样本数(<5%)':>10} {'比例(<5%)%':>11} {'样本数(<10%)':>11} {'比例(<10%)%':>12}")
        print("-" * 100)

        for _, row in df.iterrows():
            interval_str = str(row['区间'])[:25]
            print(f"{interval_str:<25} {int(row['样本数(<5%)']):>10} {row['比例(<5%)']:>11.2f} "
                  f"{int(row['样本数(<10%)']):>11} {row['比例(<10%)']:>12.2f}")

        return df

    def plot_interval_errors(self, y_true, y_pred, n_intervals=10, save_plots=True):
        """
        可视化分区间回代误差
        """
        # 确保数据格式正确
        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        df = self.calculate_interval_errors_detailed(y_true_arr, y_pred_arr, n_intervals)

        if len(df) == 0:
            print("⚠️ 无法生成图表：没有有效数据")
            return df

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. 各区间的平均回代误差柱状图
        ax1 = axes[0, 0]
        intervals = [str(x)[:20] for x in df['区间']]
        ax1.bar(range(len(intervals)), df['平均回代误差(%)'], color='steelblue', edgecolor='black')
        ax1.set_xticks(range(len(intervals)))
        ax1.set_xticklabels(intervals, rotation=45, ha='right')
        ax1.set_ylabel('平均回代误差 (%)')
        ax1.set_title('各区间平均回代误差')
        ax1.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for i, v in enumerate(df['平均回代误差(%)']):
            if not np.isnan(v):
                ax1.text(i, v + 0.5, f'{v:.2f}%', ha='center', fontsize=8)

        # 2. 回代误差<5%和<10%的比例
        ax2 = axes[0, 1]
        x = np.arange(len(intervals))
        width = 0.35
        ax2.bar(x - width / 2, df['比例(<5%)'], width, label='<5%', color='green', alpha=0.7, edgecolor='black')
        ax2.bar(x + width / 2, df['比例(<10%)'], width, label='<10%', color='orange', alpha=0.7, edgecolor='black')
        ax2.set_xticks(x)
        ax2.set_xticklabels(intervals, rotation=45, ha='right')
        ax2.set_ylabel('样本比例 (%)')
        ax2.set_title('回代误差小于阈值的样本比例')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. 最小/最大回代误差
        ax3 = axes[1, 0]
        ax3.plot(range(len(intervals)), df['平均回代误差(%)'], 'o-', label='平均', linewidth=2, color='blue')
        ax3.plot(range(len(intervals)), df['最小回代误差(%)'], 's-', label='最小', linewidth=2, color='green')
        ax3.plot(range(len(intervals)), df['最大回代误差(%)'], '^-', label='最大', linewidth=2, color='red')
        ax3.set_xticks(range(len(intervals)))
        ax3.set_xticklabels(intervals, rotation=45, ha='right')
        ax3.set_ylabel('回代误差 (%)')
        ax3.set_title('各区间的平均/最小/最大回代误差')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. 样本数分布
        ax4 = axes[1, 1]
        ax4.bar(range(len(intervals)), df['样本数'], color='purple', edgecolor='black', alpha=0.7)
        ax4.set_xticks(range(len(intervals)))
        ax4.set_xticklabels(intervals, rotation=45, ha='right')
        ax4.set_ylabel('样本数')
        ax4.set_title('各区间样本数分布')
        ax4.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for i, v in enumerate(df['样本数']):
            ax4.text(i, v + 5, str(int(v)), ha='center', fontsize=8)

        plt.tight_layout()

        if save_plots:
            plt.savefig('interval_backfitting_errors.png', dpi=300, bbox_inches='tight')
            print("\n✅ 区间误差图表已保存为: interval_backfitting_errors.png")

        plt.show()

        return df

    def validate_regression_complete(self, X_test, y_test, n_intervals=10, save_plots=True):
        """
        完整的回归模型验证（包含整体指标和分区间误差）
        """
        print("\n" + "=" * 60)
        print("📊 回归模型完整性能评估")
        print("=" * 60)

        # 数据预处理
        if isinstance(X_test, pd.DataFrame):
            X_test_arr = X_test.values
        else:
            X_test_arr = np.array(X_test)

        if isinstance(y_test, pd.Series):
            y_test_arr = y_test.values.flatten()
        else:
            y_test_arr = np.array(y_test).flatten()

        # 预测
        y_pred = self.model.predict(X_test_arr)
        if len(y_pred.shape) > 1:
            y_pred = y_pred.flatten()

        # ==================== 整体回归指标 ====================
        print("\n📈 整体回归性能指标:")
        print("-" * 40)

        mse = mean_squared_error(y_test_arr, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test_arr, y_pred)
        r2 = r2_score(y_test_arr, y_pred)

        print(f"MSE:  {mse:.4f}")
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE:  {mae:.4f}")
        print(f"R²:   {r2:.4f}")

        # ==================== 分区间回代误差 ====================
        df_intervals = self.print_interval_backfitting_errors(
            y_test_arr, y_pred, n_intervals, interval_type='equal_frequency'
        )

        # ==================== 可视化 ====================
        self.plot_interval_errors(y_test_arr, y_pred, n_intervals, save_plots)

        # 额外：回代误差总体分布图
        try:
            fig, axes = plt.subplots(1, 2, figsize=(14, 5))

            # 回代误差分布直方图
            backfitting_error = self.calculate_backfitting_error(y_test_arr, y_pred)
            valid_errors = backfitting_error[~np.isnan(backfitting_error)]

            if len(valid_errors) > 0:
                ax1 = axes[0]
                ax1.hist(valid_errors, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
                ax1.axvline(x=5, color='red', linestyle='--', linewidth=2, label='5%阈值')
                ax1.axvline(x=10, color='orange', linestyle='--', linewidth=2, label='10%阈值')
                ax1.set_xlabel('回代误差 (%)')
                ax1.set_ylabel('样本数')
                ax1.set_title(f'回代误差分布\n<5%: {(valid_errors < 5).sum() / len(valid_errors) * 100:.2f}%, '
                              f'<10%: {(valid_errors < 10).sum() / len(valid_errors) * 100:.2f}%')
                ax1.legend()
                ax1.grid(True, alpha=0.3)

                # 累计分布
                ax2 = axes[1]
                sorted_errors = np.sort(valid_errors)
                cumulative = np.arange(1, len(sorted_errors) + 1) / len(sorted_errors) * 100
                ax2.plot(sorted_errors, cumulative, linewidth=2, color='steelblue')
                ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
                ax2.axvline(x=5, color='red', linestyle='--', alpha=0.7, label='5%')
                ax2.axvline(x=10, color='orange', linestyle='--', alpha=0.7, label='10%')
                ax2.set_xlabel('回代误差 (%)')
                ax2.set_ylabel('累计样本比例 (%)')
                ax2.set_title('回代误差累计分布')
                ax2.legend()
                ax2.grid(True, alpha=0.3)

                plt.tight_layout()
                if save_plots:
                    plt.savefig('backfitting_error_distribution.png', dpi=300, bbox_inches='tight')
                    print("✅ 回代误差分布图已保存为: backfitting_error_distribution.png")
                plt.show()
        except Exception as e:
            print(f"⚠️ 生成回代误差分布图时出错: {e}")

        return {
            'y_true': y_test_arr,
            'y_pred': y_pred,
            'interval_stats': df_intervals
        }


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 1. 初始化验证器
    model_path = "7nodos.txt"  # 替换为你的模型路径
    validator = LightGBMRegressorValidator(model_path)

    # 2. 加载模型
    model = validator.load_model()

    if model is not None:
        # 3. 准备测试数据（示例数据）
        df = pd.read_csv("小规模样本end.CSV")
        data = df
        # Split features and labels
        X = data.iloc[:, :15].values
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

        # 4. 完整验证（包含分区间回代误差）
        results = validator.validate_regression_complete(
            X_test, y_test,
            n_intervals=10,  # 分为10个区间
            save_plots=True
        )

        print("\n✅ 验证完成！")