import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import warnings
import json

warnings.filterwarnings('ignore')

print("=" * 80)
print("XGBoost Regression Training (Best Parameters)")
print("=" * 80)

# ==================== 1. Prepare Data ====================
print("\n1. Preparing data...")

# Read data
data = pd.read_csv("100万fop.CSV")

# Split features and labels
X = data.iloc[:, :13 + 33 + 2].values
y = data.iloc[:, -1].values
print(y.min(), y.max())
# y=(y-y.min())/(y.max()-y.min())
print(f"X shape: {X.shape}")
print(f"y range: [{y.min():.2f}, {y.max():.2f}]")
quantiles = pd.qcut(y, q=10, labels=False)
sample_weights = 10 - quantiles  # 最小的一组权重=5，最大的一组权重=1
# Split training and test sets (no log transformation)
X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
    X, y, sample_weights, test_size=0.2, random_state=42
)
# quantiles = pd.qcut(y_train, q=5, labels=False)
# sample_weights = 5 - quantiles  # 最小的一组权重=5，最大的一组权重=1
print(f"Training set size: {X_train.shape}")
print(f"Test set size: {X_test.shape}")

# ==================== 2. Set Best Parameters ====================
print("\n2. Setting best parameters...")

best_params = {
    'n_estimators': 10000,
'max_depth': 7,
'learning_rate': 0.2916154465106579,
'subsample': 0.9471050323802952,
'colsample_bytree': 0.8088445882284432,
'colsample_bylevel': 0.9687904573598144,
'reg_alpha': 7.728144440513873e-05,
'reg_lambda': 0.00011769379752688776,
'min_child_weight': 6,
'gamma': 0.2722950916433333,
    'random_state': 42,
    'objective': 'reg:squarederror',
    'eval_metric': 'rmse',
    'early_stopping_rounds': 50,
    'verbosity': 1,
    'n_jobs': -1
}

print("Best parameters:")
for param_name, param_value in best_params.items():
    print(f"  {param_name}: {param_value}")

# ==================== 3. Train Model ====================
print("\n3. Training model...")

# Create model with parameters
model = xgb.XGBRegressor(**best_params)

# Train with original y values
model.fit(
    X_train, y_train,
    sample_weight=w_train,
    eval_set=[(X_train, y_train), (X_test, y_test)],
    verbose=50
)

print("\n✅ Training completed!")

# ==================== 4. Save Model ====================
print("\n4. Saving model...")

# Save as JSON format
model.save_model('xgboost_best_model.json')
print("✅ Model saved: xgboost_best_model.json")

# Save as UBJ format
# model.save_model('xgboost_best_model.ubj')
# print("✅ Model saved: xgboost_best_model.ubj")

# Save parameters to JSON file
with open('best_params.json', 'w') as f:
    serializable_params = {}
    for k, v in best_params.items():
        if isinstance(v, (np.integer, np.int64, np.int32)):
            serializable_params[k] = int(v)
        elif isinstance(v, (np.floating, np.float64, np.float32)):
            serializable_params[k] = float(v)
        else:
            serializable_params[k] = v
    json.dump(serializable_params, f, indent=4)
print("✅ Parameters saved: best_params.json")

# ==================== 5. Predict and Evaluate ====================
print("\n5. Predicting and evaluating...")

# Predict using original scale
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

# Calculate metrics
train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
test_mae = mean_absolute_error(y_test, y_pred_test)
test_r2 = r2_score(y_test, y_pred_test)

# Calculate MAPE
def mape(y_true, y_pred):
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

test_mape = mape(y_test, y_pred_test)

print(f"\n========== Evaluation Results ==========")
print(f"Training RMSE: {train_rmse:.4f}")
print(f"Test RMSE: {test_rmse:.4f}")
print(f"Test MAE: {test_mae:.4f}")
print(f"Test MAPE: {test_mape:.2f}%")
print(f"Test R²: {test_r2:.4f}")
print("=" * 50)

# ==================== 6. Visualization ====================
print("\n6. Generating visualizations...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Actual vs Predicted
ax1 = axes[0, 0]
ax1.scatter(y_test, y_pred_test, alpha=0.5, s=10)
ax1.plot([y_test.min(), y_test.max()],
         [y_test.min(), y_test.max()], 'r--', lw=2)
ax1.set_xlabel('Actual Values')
ax1.set_ylabel('Predicted Values')
ax1.set_title(f'Actual vs Predicted (R² = {test_r2:.4f})')
ax1.grid(True, alpha=0.3)

# 2. Residuals Distribution
ax2 = axes[0, 1]
residuals = y_test - y_pred_test
ax2.hist(residuals, bins=50, edgecolor='black', alpha=0.7)
ax2.axvline(x=0, color='r', linestyle='--', lw=2)
ax2.set_xlabel('Residuals')
ax2.set_ylabel('Frequency')
ax2.set_title('Residuals Distribution')
ax2.grid(True, alpha=0.3)

# 3. Relative Residuals vs Actual
ax3 = axes[1, 0]
relative_residuals = residuals / y_test * 100
ax3.scatter(y_test, relative_residuals, alpha=0.5, s=10)
ax3.axhline(y=0, color='r', linestyle='--')
ax3.axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='20%')
ax3.axhline(y=-20, color='orange', linestyle='--', alpha=0.5)
ax3.set_xlabel('Actual Values')
ax3.set_ylabel('Relative Residuals (%)')
ax3.set_title('Relative Residuals Distribution')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 4. Feature Importance
ax4 = axes[1, 1]
feature_importance = model.feature_importances_
feature_names = [f'F{i}' for i in range(X.shape[1])]
sorted_idx = np.argsort(feature_importance)[::-1][:20]
ax4.barh(range(20), feature_importance[sorted_idx][::-1])
ax4.set_yticks(range(20))
ax4.set_yticklabels([feature_names[i] for i in sorted_idx][::-1])
ax4.set_xlabel('Feature Importance')
ax4.set_title('Top 20 Important Features')
ax4.grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig('training_results.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Visualization saved: training_results.png")

# ==================== 7. Save Results Summary ====================
print("\n7. Saving results summary...")

results_summary = {
    'best_params': {k: float(v) if isinstance(v, (np.floating,)) else int(v) if isinstance(v, (np.integer,)) else v
                    for k, v in best_params.items()},
    'train_rmse': float(train_rmse),
    'test_rmse': float(test_rmse),
    'test_mae': float(test_mae),
    'test_mape': float(test_mape),
    'test_r2': float(test_r2),
    'data_info': {
        'n_features': X.shape[1],
        'n_train_samples': len(X_train),
        'n_test_samples': len(X_test)
    }
}

with open('training_results.json', 'w') as f:
    json.dump(results_summary, f, indent=4)
print("✅ Results saved: training_results.json")

print("\n" + "=" * 80)
print("Training completed successfully!")
print(f"Test RMSE: {test_rmse:.4f}")
print(f"Test MAPE: {test_mape:.2f}%")
print(f"Test R²: {test_r2:.4f}")
print("=" * 80)

# ==================== 分区间评估 ====================
print("\n========== Quantile Evaluation ==========")


def quantile_evaluation(y_true, y_pred, n_quantiles=5):
    """
    Evaluate model performance by y value quantiles

    Parameters:
    - y_true: actual values
    - y_pred: predicted values
    - n_quantiles: number of quantiles (default: 5)
    """
    # Create quantile bins
    quantiles = pd.qcut(y_true, q=n_quantiles, labels=False, duplicates='drop')
    n_quantiles = len(np.unique(quantiles))  # Adjust if duplicates dropped

    results = []
    for q in range(n_quantiles):
        mask = quantiles == q
        if mask.sum() > 0:
            y_t = y_true[mask]
            y_p = y_pred[mask]

            # Calculate metrics
            rmse = np.sqrt(mean_squared_error(y_t, y_p))

            # Calculate MAPE (avoid division by zero)
            mask_nonzero = y_t != 0
            if mask_nonzero.sum() > 0:
                # 计算每个样本的百分比误差
                percentage_errors = np.abs((y_t[mask_nonzero] - y_p[mask_nonzero]) / y_t[mask_nonzero]) * 100
                mape_val = np.mean(percentage_errors)

                # 计算误差小于特定阈值的样本比例
                mape_lt_10_pct = np.mean(percentage_errors < 10) * 100
                mape_lt_20_pct = np.mean(percentage_errors < 20) * 100
                mape_lt_5_pct = np.mean(percentage_errors < 5) * 100
                mape_lt_30_pct = np.mean(percentage_errors < 30) * 100
            else:
                mape_val = np.nan
                mape_lt_10_pct = np.nan
                mape_lt_20_pct = np.nan
                mape_lt_5_pct = np.nan
                mape_lt_30_pct = np.nan

            # Calculate MAE
            mae = mean_absolute_error(y_t, y_p)

            # Calculate R²
            r2 = r2_score(y_t, y_p)

            results.append({
                'Quantile': f'Q{q + 1}',
                'Range': f'[{y_t.min():.0f}, {y_t.max():.0f}]',
                'Samples': mask.sum(),
                'RMSE': rmse,
                'MAE': mae,
                'MAPE(%)': mape_val,
                'R²': r2,
                'Error<5%(%)': mape_lt_5_pct,
                'Error<10%(%)': mape_lt_10_pct,
                'Error<20%(%)': mape_lt_20_pct,
                'Error<30%(%)': mape_lt_30_pct
            })

    return pd.DataFrame(results)


# Perform quantile evaluation
print("\n--- Test Set Quantile Evaluation ---")
quantile_results = quantile_evaluation(y_test, y_pred_test, n_quantiles=5)
print(quantile_results.to_string(index=False))

# Save to CSV
quantile_results.to_csv('quantile_evaluation_results.csv', index=False)
print("\n✅ Quantile evaluation results saved to: quantile_evaluation_results.csv")

# ==================== 详细分区间评估（更多区间） ====================
print("\n========== Detailed Quantile Evaluation (10 quantiles) ==========")
quantile_results_10 = quantile_evaluation(y_test, y_pred_test, n_quantiles=10)
print(quantile_results_10.to_string(index=False))
quantile_results_10.to_csv('quantile_evaluation_results_10.csv', index=False)

# ==================== 可视化分区间结果 ====================
print("\n========== Visualizing Quantile Evaluation ==========")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 1. RMSE by quantile
ax1 = axes[0]
ax1.bar(range(len(quantile_results)), quantile_results['RMSE'],
        color='steelblue', alpha=0.7, edgecolor='black')
ax1.set_xlabel('Quantile (Q1=smallest, Q5=largest)')
ax1.set_ylabel('RMSE')
ax1.set_title('RMSE by Value Range')
ax1.set_xticks(range(len(quantile_results)))
ax1.set_xticklabels(quantile_results['Quantile'])
ax1.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for i, (idx, row) in enumerate(quantile_results.iterrows()):
    ax1.text(i, row['RMSE'] + max(quantile_results['RMSE']) * 0.02,
             f'{row["RMSE"]:.0f}', ha='center', fontsize=9)

# 2. MAPE by quantile
ax2 = axes[1]
colors = ['green' if x < 5 else 'orange' if x < 10 else 'red'
          for x in quantile_results['MAPE(%)']]
ax2.bar(range(len(quantile_results)), quantile_results['MAPE(%)'],
        color=colors, alpha=0.7, edgecolor='black')
ax2.set_xlabel('Quantile (Q1=smallest, Q5=largest)')
ax2.set_ylabel('MAPE (%)')
ax2.set_title('MAPE by Value Range')
ax2.set_xticks(range(len(quantile_results)))
ax2.set_xticklabels(quantile_results['Quantile'])
ax2.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for i, (idx, row) in enumerate(quantile_results.iterrows()):
    ax2.text(i, row['MAPE(%)'] + max(quantile_results['MAPE(%)']) * 0.02,
             f'{row["MAPE(%)"]:.2f}%', ha='center', fontsize=9)

plt.tight_layout()
plt.savefig('quantile_evaluation.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Quantile evaluation plot saved: quantile_evaluation.png")

# ==================== 额外：自定义区间划分 ====================
print("\n========== Custom Range Evaluation ==========")

# Define custom ranges based on your data distribution
custom_ranges = [
    (0, 5500, 'Small'),
    (5500, 6000, 'Medium-Small'),
    (6000, 9500, 'Medium'),
    (9500, 10000, 'Medium-Large'),
    (10000, float('inf'), 'Large')
]

custom_results = []
for low, high, label in custom_ranges:
    if high == float('inf'):
        mask = y_test >= low
        range_name = f'[{low:.0f}, +∞)'
    else:
        mask = (y_test >= low) & (y_test < high)
        range_name = f'[{low:.0f}, {high:.0f})'

    if mask.sum() > 0:
        y_t = y_test[mask]
        y_p = y_pred_test[mask]

        rmse = np.sqrt(mean_squared_error(y_t, y_p))
        mae = mean_absolute_error(y_t, y_p)

        # MAPE
        mask_nonzero = y_t != 0
        if mask_nonzero.sum() > 0:
            mape_val = np.mean(np.abs((y_t[mask_nonzero] - y_p[mask_nonzero]) / y_t[mask_nonzero])) * 100
        else:
            mape_val = np.nan

        custom_results.append({
            'Range': range_name,
            'Label': label,
            'Samples': mask.sum(),
            'RMSE': rmse,
            'MAE': mae,
            'MAPE(%)': mape_val
        })

custom_df = pd.DataFrame(custom_results)
print(custom_df.to_string(index=False))
custom_df.to_csv('custom_range_evaluation.csv', index=False)

# ==================== 打印详细统计 ====================
print("\n========== Summary Statistics ==========")
print(f"Overall Test RMSE: {test_rmse:.4f}")
print(f"Overall Test MAPE: {test_mape:.2f}%")
print(f"Overall Test R²: {test_r2:.4f}")

print(f"\n--- Worst Performing Quantile ---")
worst_rmse = quantile_results.loc[quantile_results['RMSE'].idxmax()]
print(f"Worst RMSE: Q{worst_rmse['Quantile']} ({worst_rmse['Range']}) - RMSE: {worst_rmse['RMSE']:.2f}")

worst_mape = quantile_results.loc[quantile_results['MAPE(%)'].idxmax()]
print(f"Worst MAPE: Q{worst_mape['Quantile']} ({worst_mape['Range']}) - MAPE: {worst_mape['MAPE(%)']:.2f}%")

print(f"\n--- Best Performing Quantile ---")
best_rmse = quantile_results.loc[quantile_results['RMSE'].idxmin()]
print(f"Best RMSE: Q{best_rmse['Quantile']} ({best_rmse['Range']}) - RMSE: {best_rmse['RMSE']:.2f}")

best_mape = quantile_results.loc[quantile_results['MAPE(%)'].idxmin()]
print(f"Best MAPE: Q{best_mape['Quantile']} ({best_mape['Range']}) - MAPE: {best_mape['MAPE(%)']:.2f}%")