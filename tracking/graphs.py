import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime

# === CONFIG ===
TRACKING_DIR = "tracking"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
FIGURE_DIR = os.path.join("figures", TIMESTAMP)
os.makedirs(FIGURE_DIR, exist_ok=True)

# === Load Data ===
fold_df = pd.read_csv(os.path.join(TRACKING_DIR, "fold_summary.csv"))
epoch_df = pd.read_csv(os.path.join(TRACKING_DIR, "epoch_metrics.csv"))
misclass_df = pd.read_csv(os.path.join(TRACKING_DIR, "misclassifications.csv"))

# === Separate Figure: Training Loss ===
plt.figure(figsize=(10, 6))
sns.lineplot(data=epoch_df, x="epoch", y="train_loss", hue="label_column", style="fold",
             markers=True, dashes=False, palette="dark")
plt.title("Training Loss Across Epochs", fontsize=14)
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "training_loss.png"), dpi=300)
plt.close()

# === Separate Figure: Validation Accuracy ===
plt.figure(figsize=(10, 6))
sns.lineplot(data=epoch_df, x="epoch", y="val_accuracy (%)", hue="label_column", style="fold",
             markers=True, dashes=False, palette="deep")
plt.title("Validation Accuracy Across Epochs", fontsize=14)
plt.xlabel("Epoch")
plt.ylabel("Accuracy (%)")
plt.ylim(0, 100)
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(os.path.join(FIGURE_DIR, "val_accuracy.png"), dpi=300)
plt.close()

# === Build Confusion Matrices ===
conf_matrices = {}

for label_column, group_df in misclass_df.groupby("label_column"):
    label_names = sorted(group_df["label_name"].unique())
    matrix = pd.DataFrame(0, index=label_names, columns=label_names)

    for _, row in group_df.iterrows():
        true_label = row["label_name"]
        total = row["total_count"]
        misclassified = row["misclassified_count"]
        correct = total - misclassified
        matrix.at[true_label, true_label] += correct

        if pd.notna(row["wrongly_predicted_labels"]) and row["wrongly_predicted_labels"].strip():
            for entry in row["wrongly_predicted_labels"].split(";"):
                pred_label, count = entry.split(":")
                matrix.at[true_label, pred_label] += int(count)

    matrix_normalized = matrix.div(matrix.sum(axis=1), axis=0) * 100
    conf_matrices[label_column] = (matrix_normalized, label_names)

    # === Save Separate Heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(matrix_normalized, annot=True, fmt=".1f", cmap="Blues", cbar=True,
                xticklabels=label_names, yticklabels=label_names)
    plt.title(f"Confusion Matrix – {label_column}", fontsize=14)
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, f"confusion_matrix_{label_column}.png"), dpi=300)
    plt.close()

# === Combined Figure with 2x2 layout ===
fig, axs = plt.subplots(2, 2, figsize=(20, 14))
plt.subplots_adjust(hspace=0.35, wspace=0.25)

# Top-left: Training Loss
ax = axs[0, 0]
sns.lineplot(data=epoch_df, x="epoch", y="train_loss", hue="label_column", style="fold",
             markers=True, dashes=False, palette="dark", ax=ax)
ax.set_title("Training Loss Across Epochs", fontsize=14)
ax.set_xlabel("Epoch")
ax.set_ylabel("Loss")
ax.grid(True, linestyle="--", alpha=0.6)

# Top-right: Validation Accuracy
ax = axs[0, 1]
sns.lineplot(data=epoch_df, x="epoch", y="val_accuracy (%)", hue="label_column", style="fold",
             markers=True, dashes=False, palette="deep", ax=ax)
ax.set_title("Validation Accuracy Across Epochs", fontsize=14)
ax.set_xlabel("Epoch")
ax.set_ylabel("Accuracy (%)")
ax.set_ylim(0, 100)
ax.grid(True, linestyle="--", alpha=0.6)

for i, label_column in enumerate(["category", "category_application"]):
    ax = axs[1, i]
    matrix, label_names = conf_matrices[label_column]
    sns.heatmap(matrix, annot=True, fmt=".1f", cmap="Blues", cbar=True,
                xticklabels=label_names, yticklabels=label_names, ax=ax)
    ax.set_title(f"Confusion Matrix – {label_column}", fontsize=14)
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.tick_params(axis='x', rotation=90)
    ax.tick_params(axis='y', rotation=0)

fig.suptitle("Training Summary and Confusion Matrices", fontsize=18)
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(os.path.join(FIGURE_DIR, "combined_summary.png"), dpi=300)
plt.show()