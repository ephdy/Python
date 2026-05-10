import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score
)
import matplotlib.pyplot as plt
import warnings
from sklearn.model_selection import train_test_split
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class LightGBMRegressorValidator:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None

    def load_model(self):
        """加载模型"""
        try:
            self.model = lgb.Booster(model_file=self.model_path)
            print(f"✅ 模型加载成功: {self.model_path}")
            return self.model
        except:
            try:
                import joblib
                self.model = joblib.load(self.model_path)
                print(f"✅ sklearn模型加载成功: {self.model_path}")
                return self.model
            except Exception as e:
                print(f"❌ 模型加载失败: {e}")
                return None

    def calculate_backfitting_error(self, y_true, y_pred):
        """计算回代误差"""
        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()
        mask = y_true_arr != 0
        backfitting_error = np.full_like(y_true_arr, np.nan, dtype=float)
        backfitting_error[mask] = np.abs((y_true_arr[mask] - y_pred_arr[mask]) / y_true_arr[mask]) * 100
        return backfitting_error

    def analyze_problem_samples(self, y_true, y_pred, threshold=7):
        """
        分析高误差样本的特征
        """
        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        # 计算误差
        abs_error = np.abs(y_true_arr - y_pred_arr)
        rel_error = self.calculate_backfitting_error(y_true_arr, y_pred_arr)

        # 找出高误差样本
        high_error_mask = rel_error > threshold
        high_error_samples = pd.DataFrame({
            'y_true': y_true_arr[high_error_mask],
            'y_pred': y_pred_arr[high_error_mask],
            'abs_error': abs_error[high_error_mask],
            'rel_error(%)': rel_error[high_error_mask],
            'bias': y_pred_arr[high_error_mask] - y_true_arr[high_error_mask]
        })

        return high_error_samples

    def diagnose_model_issues(self, y_true, y_pred, n_intervals=10):
        """
        诊断模型问题
        """
        print("\n" + "=" * 80)
        print("🔍 模型问题诊断")
        print("=" * 80)

        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        # 1. 检查预测偏差
        bias = y_pred_arr - y_true_arr
        mean_bias = np.mean(bias)

        print(f"\n📊 整体偏差分析:")
        print(f"   平均偏差 (预测-实际): {mean_bias:.2f}")
        print(f"   偏差标准差: {np.std(bias):.2f}")

        if abs(mean_bias) > y_true_arr.mean() * 0.01:
            print(f"   ⚠️ 存在系统性偏差: {'高估' if mean_bias > 0 else '低估'}")

        # 2. 分析不同区间的偏差特征
        print(f"\n📊 分区间偏差分析:")
        df = pd.DataFrame({
            'y_true': y_true_arr,
            'y_pred': y_pred_arr,
            'bias': bias,
            'rel_error': self.calculate_backfitting_error(y_true_arr, y_pred_arr)
        })

        df['interval'] = pd.qcut(df['y_true'], q=n_intervals, duplicates='drop')

        for interval, group in df.groupby('interval', observed=False):
            mean_bias_interval = group['bias'].mean()
            high_error_ratio = (group['rel_error'] > 7).sum() / len(group) * 100
            print(f"   {str(interval)[:25]}: 平均偏差={mean_bias_interval:.2f}, "
                  f"高误差率(>7%)={high_error_ratio:.1f}%")

        # 3. 残差异方差性检查
        from scipy import stats

        # 按预测值排序
        sorted_idx = np.argsort(y_pred_arr)
        sorted_pred = y_pred_arr[sorted_idx]
        sorted_residuals = bias[sorted_idx]

        # 分成两组检验异方差性
        n = len(sorted_pred)
        low_group = sorted_residuals[:n // 3]
        high_group = sorted_residuals[-n // 3:]

        stat, p_value = stats.levene(low_group, high_group)
        print(f"\n📊 异方差性检验 (Levene test):")
        print(f"   统计量: {stat:.4f}")
        print(f"   p值: {p_value:.4f}")
        if p_value < 0.05:
            print(f"   ⚠️ 存在显著的异方差性（不同区间的误差方差不同）")

        return {
            'mean_bias': mean_bias,
            'heteroscedastic': p_value < 0.05
        }

    def suggest_improvements(self, y_true, y_pred):
        """
        基于误差分析提供改进建议
        """
        print("\n" + "=" * 80)
        print("💡 模型改进建议")
        print("=" * 80)

        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        rel_error = self.calculate_backfitting_error(y_true_arr, y_pred_arr)
        valid_error = rel_error[~np.isnan(rel_error)]

        # 分析高误差样本
        high_error = valid_error[valid_error > 7]
        high_error_ratio = len(high_error) / len(valid_error) * 100

        suggestions = []

        # 1. 如果高误差样本多
        if high_error_ratio > 10:
            suggestions.append(
                "🔥 优先级高：{:.1f}%样本误差>7%\n".format(high_error_ratio) +
                "   1. 检查异常值：可能存在数据标注错误\n" +
                "   2. 目标变量变换：尝试对数变换 np.log1p(y)\n" +
                "   3. 加权学习：对高值/低值样本赋予更高权重"
            )

        # 2. 检查是否低值区误差大
        low_threshold = np.percentile(y_true_arr, 25)
        low_mask = y_true_arr <= low_threshold
        if low_mask.sum() > 0:
            low_error = np.nanmean(rel_error[low_mask])
            if low_error > np.nanmean(valid_error) * 1.5:
                suggestions.append(
                    "📌 低值区误差大：\n" +
                    "   1. 使用加权损失函数（给予低值样本更高权重）\n" +
                    "   2. 考虑分层建模（低值区单独训练模型）\n" +
                    "   3. 增加低值区相关特征"
                )

        # 3. 检查高值区误差
        high_threshold = np.percentile(y_true_arr, 75)
        high_mask = y_true_arr >= high_threshold
        if high_mask.sum() > 0:
            high_error = np.nanmean(rel_error[high_mask])
            if high_error > np.nanmean(valid_error) * 1.5:
                suggestions.append(
                    "📌 高值区误差大：\n" +
                    "   1. 对数空间建模（对y取log后训练，预测时exp回来）\n" +
                    "   2. 目标变量归一化（MinMaxScaler）\n" +
                    "   3. 使用Huber损失或Quantile loss"
                )

        # 4. 一般性建议
        suggestions.append(
            "🎯 通用优化方案：\n" +
            "   1. 特征工程：添加交叉特征、多项式特征\n" +
            "   2. 超参数调优：调整 learning_rate, num_leaves, min_child_samples\n" +
            "   3. 集成方法：结合XGBoost、CatBoost做模型融合\n" +
            "   4. 后处理校准：使用Platt Scaling或Isotonic Regression"
        )

        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n【建议 {i}】")
            print(suggestion)

    def plot_error_analysis(self, y_true, y_pred, save_plots=True):
        """
        绘制详细的误差分析图
        """
        y_true_arr = np.array(y_true).flatten()
        y_pred_arr = np.array(y_pred).flatten()

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        # 1. 预测值vs真实值（按误差着色）
        ax = axes[0, 0]
        rel_error = self.calculate_backfitting_error(y_true_arr, y_pred_arr)
        valid_mask = ~np.isnan(rel_error)

        scatter = ax.scatter(y_true_arr[valid_mask], y_pred_arr[valid_mask],
                             c=rel_error[valid_mask], cmap='RdYlGn_r',
                             alpha=0.5, s=10, vmin=0, vmax=30)
        ax.plot([y_true_arr.min(), y_true_arr.max()],
                [y_true_arr.min(), y_true_arr.max()], 'b--', linewidth=1)
        ax.set_xlabel('真实值')
        ax.set_ylabel('预测值')
        ax.set_title('预测值 vs 真实值（颜色=相对误差%）')
        plt.colorbar(scatter, ax=ax, label='相对误差(%)')

        # 2. 相对误差vs真实值
        ax = axes[0, 1]
        ax.scatter(y_true_arr[valid_mask], rel_error[valid_mask], alpha=0.3, s=5)
        ax.axhline(y=10, color='orange', linestyle='--', label='10%')
        ax.axhline(y=20, color='red', linestyle='--', label='20%')
        ax.set_xlabel('真实值')
        ax.set_ylabel('相对误差(%)')
        ax.set_title('相对误差 vs 真实值')
        ax.legend()
        ax.set_ylim(0, np.percentile(rel_error[valid_mask], 95))

        # 3. 残差vs预测值
        ax = axes[0, 2]
        residuals = y_pred_arr - y_true_arr
        ax.scatter(y_pred_arr, residuals, alpha=0.3, s=5)
        ax.axhline(y=0, color='red', linestyle='--')
        ax.set_xlabel('预测值')
        ax.set_ylabel('残差')
        ax.set_title('残差 vs 预测值')

        # 4. 误差分布(对数尺度)
        ax = axes[1, 0]
        ax.hist(rel_error[valid_mask], bins=100, edgecolor='black', alpha=0.7)
        ax.set_xlabel('相对误差(%)')
        ax.set_ylabel('频数')
        ax.set_title('相对误差分布')
        ax.set_yscale('log')

        # 5. 不同区间的误差箱线图
        ax = axes[1, 1]
        df = pd.DataFrame({'y_true': y_true_arr, 'rel_error': rel_error})
        df['decile'] = pd.qcut(df['y_true'], q=10, duplicates='drop')
        df.boxplot(column='rel_error', by='decile', ax=ax, rot=45)
        ax.set_title('各分位数区间误差箱线图')
        ax.set_xlabel('')
        ax.set_ylabel('相对误差(%)')

        # 6. 偏差分析
        ax = axes[1, 2]
        sorted_idx = np.argsort(y_pred_arr)
        window = len(y_pred_arr) // 100
        smoothed_bias = np.convolve(residuals[sorted_idx], np.ones(window) / window, mode='valid')
        smoothed_pred = np.convolve(y_pred_arr[sorted_idx], np.ones(window) / window, mode='valid')
        ax.plot(smoothed_pred, smoothed_bias, 'b-', linewidth=2)
        ax.axhline(y=0, color='red', linestyle='--')
        ax.set_xlabel('预测值')
        ax.set_ylabel('平均偏差')
        ax.set_title('局部偏差分析（移动平均）')

        plt.tight_layout()
        if save_plots:
            plt.savefig('error_diagnosis.png', dpi=300, bbox_inches='tight')
            print("\n✅ 诊断图表已保存: error_diagnosis.png")
        plt.show()

    def validate_with_diagnosis(self, X_test, y_test, n_intervals=10, save_plots=True):
        """
        完整验证 + 自动诊断
        """
        # 数据预处理
        X_test_arr = np.array(X_test)
        y_test_arr = np.array(y_test).flatten()

        print(f"\nX shape: {X_test_arr.shape}")
        print(f"y range: [{y_test_arr.min():.2f}, {y_test_arr.max():.2f}]")

        # 预测
        y_pred = self.model.predict(X_test_arr)
        # y_pred =np.exp(y_pred)
        if len(y_pred.shape) > 1:
            y_pred = y_pred.flatten()

        # 1. 基本指标
        mse = mean_squared_error(y_test_arr, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test_arr, y_pred)
        r2 = r2_score(y_test_arr, y_pred)

        print("\n" + "=" * 60)
        print("📊 整体性能指标:")
        print(f"R²={r2:.4f}, RMSE={rmse:.2f}, MAE={mae:.2f}")

        # 2. 误差诊断
        diagnosis = self.diagnose_model_issues(y_test_arr, y_pred, n_intervals)

        # 3. 改进建议
        self.suggest_improvements(y_test_arr, y_pred)

        # 4. 可视化诊断
        self.plot_error_analysis(y_test_arr, y_pred, save_plots)

        return {
            'y_true': y_test_arr,
            'y_pred': y_pred,
            'diagnosis': diagnosis
        }


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 加载模型
    model_path = "7AC_half.txt"
    validator = LightGBMRegressorValidator(model_path)
    model = validator.load_model()

    if model is not None:
        # 准备测试数据（使用你自己的测试集）
        data = pd.read_csv("小规模样本end.csv")

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

        # 运行诊断
        results = validator.validate_with_diagnosis(X_test, y_test)