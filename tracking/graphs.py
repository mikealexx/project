import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# === CONFIG ===
TRACKING_DIR = "tracking"
FIGURE_DIR = "figures"
os.makedirs(FIGURE_DIR, exist_ok=True)

# === Load Data ===
fold_summary_path = os.path.join(TRACKING_DIR, "fold_summary.csv")
epoch_metrics_path = os.path.join(TRACKING_DIR, "epoch_metrics.csv")
misclassifications_path = os.path.join(TRACKING_DIR, "misclassifications.csv")

fold_df = pd.read_csv(fold_summary_path)
epoch_df = pd.read_csv(epoch_metrics_path)
misclass_df = pd.read_csv(misclassifications_path)

# === 1. Fold Accuracy Bar Plot ===
plt.figure(figsize=(10, 6))
sns.barplot(data=fold_df, x="fold", y="val_accuracy (%)", hue="label_column", palette="muted")
plt.title("Validation Accuracy per Fold", fontsize=14)
plt.xlabel("Fold", fontsize=12)
plt.ylabel("Validation Accuracy (%)", fontsize=12)
plt.ylim(0, 100)
plt.grid(axis='y', linestyle='--', alpha=0.6)
plt.legend(title="Label Type")
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "fold_accuracy_barplot.png"), dpi=300)
plt.show(block=False)

# === 2. Mean Epoch Loss per Fold and Label ===
plt.figure(figsize=(10, 6))
sns.barplot(data=fold_df, x="fold", y="mean_epoch_loss", hue="label_column", palette="muted")
plt.title("Mean Epoch Training Loss per Fold", fontsize=14)
plt.xlabel("Fold", fontsize=12)
plt.ylabel("Mean Training Loss", fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.6)
plt.legend(title="Label Type")
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "mean_loss_per_fold.png"), dpi=300)
plt.show(block=False)

# === 3. Training Loss Across Epochs ===
plt.figure(figsize=(10, 6))
sns.lineplot(data=epoch_df, x="epoch", y="train_loss", hue="label_column", style="fold", markers=True, dashes=False, palette="dark")
plt.title("Training Loss Across Epochs", fontsize=14)
plt.xlabel("Epoch", fontsize=12)
plt.ylabel("Training Loss", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "loss_curve.png"), dpi=300)
plt.show(block=False)

# === 4. Validation Accuracy Across Epochs ===
plt.figure(figsize=(10, 6))
sns.lineplot(data=epoch_df, x="epoch", y="val_accuracy (%)", hue="label_column", style="fold", markers=True, dashes=False, palette="deep")
plt.title("Validation Accuracy Across Epochs", fontsize=14)
plt.xlabel("Epoch", fontsize=12)
plt.ylabel("Validation Accuracy (%)", fontsize=12)
plt.ylim(0, 100)
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "val_accuracy_curve.png"), dpi=300)
plt.show(block=False)

# === 5. Misclassified Labels Histogram per Fold and Label Column ===
for (label_column, fold), group_df in misclass_df.groupby(["label_column", "fold"]):
    plt.figure(figsize=(10, 6))
    sorted_df = group_df.sort_values("label_id")
    sns.barplot(data=sorted_df, x="label_id", y="misclassified_count", palette="rocket")
    plt.title(f"Misclassified Label Histogram (Fold {fold}, {label_column})", fontsize=14)
    plt.xlabel("Label ID", fontsize=12)
    plt.ylabel("Misclassified Count", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()

    fname = f"misclass_histogram_fold{fold}_{label_column}.png"
    plt.savefig(os.path.join(FIGURE_DIR, fname), dpi=300)
    plt.show(block=False)

print("All graphs generated and saved in ./figures/")
input("Press Enter to close all figures and exit...")
plt.close('all')
