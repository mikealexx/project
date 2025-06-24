import os
import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms
from torch.utils.data import DataLoader, Dataset
from PIL import Image
from cnn import SimpleCNN
import yaml
import glob
from collections import Counter

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# === CONFIG ===
LABELS_PATH = config['label_output_directory'] + '/labels_not_overlapped.csv'
IMAGES_DIR = config['png_output_directory']
BATCH_SIZE = 32
EPOCHS = 15
LEARNING_RATE = 0.001
IMAGE_SIZE = config['image_size']
MODEL_DIR = 'models'
NUM_FOLDS = 5
TRACKING_DIR = 'tracking'
os.makedirs(TRACKING_DIR, exist_ok=True)

fold_summary_records = []
epoch_metrics_records = []
misclass_data = []

def category_application_group_split(df, category_col="category", application_col="application", n_folds=5, random_state=42):
    np.random.seed(random_state)
    category_groups = df.groupby(category_col)
    per_category_apps = {
        cat: group[application_col].unique()
        for cat, group in category_groups
    }
    app_folds = {cat: np.array_split(np.random.permutation(apps), n_folds) for cat, apps in per_category_apps.items()}

    for fold in range(n_folds):
        test_keys = []
        train_keys = []
        for cat, folds in app_folds.items():
            test_apps = folds[fold]
            train_apps = np.concatenate([folds[i] for i in range(n_folds) if i != fold])
            test_keys.extend([(cat, app) for app in test_apps])
            train_keys.extend([(cat, app) for app in train_apps])

        train_mask = df.apply(lambda r: (r[category_col], r[application_col]) in train_keys, axis=1)
        test_mask = df.apply(lambda r: (r[category_col], r[application_col]) in test_keys, axis=1)
        train_indices = df[train_mask].index.values
        test_indices = df[test_mask].index.values
        yield train_indices, test_indices

class ImageLabelDataset(Dataset):
    def __init__(self, dataframe, label_column, transform=None, overlap=False):
        self.dataframe = dataframe
        self.label_column = label_column
        self.transform = transform
        self.overlap = overlap

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        row = self.dataframe.iloc[idx]
        filepath = row['filepath']
        label = row[self.label_column]

        if filepath.startswith("overlapped/"):
            relative_path = filepath[len("overlapped/"):]
        elif filepath.startswith("not_overlapped/"):
            relative_path = filepath[len("not_overlapped/"):]
        else:
            relative_path = filepath

        prefix_noext = os.path.splitext(relative_path)[0]

        if self.overlap:
            base_dir = os.path.join(IMAGES_DIR, "overlapped")
            safe_prefix = glob.escape(os.path.join(base_dir, prefix_noext))
            pattern = f"{safe_prefix}*.png"
            filepaths = sorted(glob.glob(pattern))
            if not filepaths:
                raise FileNotFoundError(f"No overlapped images found for prefix {prefix_noext} in {base_dir}")

            images = [Image.open(fp).convert('RGB').resize((IMAGE_SIZE, IMAGE_SIZE)) for fp in filepaths]
            if self.transform:
                images = [self.transform(img) for img in images]

            images = torch.stack(images)
            averaged_image = torch.mean(images, dim=0)
            return averaged_image, label
        else:
            base_dir = os.path.join(IMAGES_DIR, "not_overlapped")
            img_path = os.path.join(base_dir, relative_path)
            if not os.path.exists(img_path):
                raise FileNotFoundError(f"No image found at {img_path}")

            image = Image.open(img_path).convert('RGB').resize((IMAGE_SIZE, IMAGE_SIZE))
            if self.transform:
                image = self.transform(image)
            return image, label

def train_and_validate(train_loader, val_loader, num_classes, fold, label_column):
    model = SimpleCNN(num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    best_accuracy = 0
    best_epoch = 0
    epoch_losses = []

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        avg_loss = running_loss / len(train_loader)
        epoch_losses.append(avg_loss)

        model.eval()
        correct = total = 0
        all_true_labels = []
        all_predicted_labels = []
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                all_true_labels.extend(labels.cpu().numpy())
                all_predicted_labels.extend(predicted.cpu().numpy())

        accuracy = 100 * correct / total
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_epoch = epoch + 1

        epoch_metrics_records.append({
            "fold": fold,
            "label_column": label_column,
            "epoch": epoch + 1,
            "train_loss": avg_loss,
            "val_accuracy (%)": accuracy,
            "lr": LEARNING_RATE
        })

        print(f"Epoch {epoch + 1}/{EPOCHS}, Loss: {avg_loss:.4f}, Val Acc: {accuracy:.2f}%")

    # Track misclassified labels
    wrong_preds = [true for true, pred in zip(all_true_labels, all_predicted_labels) if true != pred]
    wrong_hist = Counter(wrong_preds)

    for label_id, count in wrong_hist.items():
        misclass_data.append({
            "fold": fold,
            "label_column": label_column,
            "label_id": label_id,
            "misclassified_count": count
        })

    return model, best_accuracy, best_epoch, np.mean(epoch_losses)

def kfold_train(label_column, model_prefix, servermode=False):
    df = pd.read_csv(LABELS_PATH)
    if 'category_application' not in df.columns and label_column == 'category_application':
        df['category_application'] = df['category'] + '_' + df['application']
    df[label_column] = LabelEncoder().fit_transform(df[label_column])
    num_classes = len(df[label_column].unique())
    transform = transforms.Compose([transforms.ToTensor()])
    accuracy_list = []

    if servermode:
        splits = category_application_group_split(
            df,
            category_col="category",
            application_col="application",
            n_folds=NUM_FOLDS
        )
    else:
        skf = StratifiedKFold(n_splits=NUM_FOLDS, shuffle=True, random_state=42)
        splits = skf.split(df, df[label_column])

    for fold, (train_idx, val_idx) in enumerate(splits):
        print(f"\n=== Fold {fold + 1}/{NUM_FOLDS} {'(ServerMode)' if servermode else '(Classic Stratified)'} ===")
        df_train = df.loc[train_idx].reset_index(drop=True)
        df_val = df.loc[val_idx].reset_index(drop=True)

        train_dataset = ImageLabelDataset(df_train, label_column, transform, overlap=False)
        val_dataset = ImageLabelDataset(df_val, label_column, transform, overlap=False)
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

        model, fold_acc, best_epoch, mean_loss = train_and_validate(train_loader, val_loader, num_classes, fold + 1, label_column)
        print(f"Fold {fold + 1} Validation Accuracy: {fold_acc:.2f}%")
        accuracy_list.append(fold_acc)

        fold_summary_records.append({
            "fold": fold + 1,
            "label_column": label_column,
            "num_train_samples": len(train_dataset),
            "num_val_samples": len(val_dataset),
            "val_accuracy (%)": fold_acc,
            "mean_epoch_loss": mean_loss,
            "best_epoch": best_epoch
        })

        os.makedirs(MODEL_DIR, exist_ok=True)
        fname = f"{model_prefix}_Fold{fold + 1}.pt" if servermode else f"{model_prefix}_fold{fold + 1}.pt"
        torch.save(model.state_dict(), os.path.join(MODEL_DIR, fname))

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    print("Training model for category with K-Fold cross-validation:")
    kfold_train('category', 'model_category')
    print("Training model for category_application with K-Fold cross-validation:")
    kfold_train('category_application', 'model_category_application')

    pd.DataFrame(fold_summary_records).to_csv(os.path.join(TRACKING_DIR, "fold_summary.csv"), index=False)
    pd.DataFrame(epoch_metrics_records).to_csv(os.path.join(TRACKING_DIR, "epoch_metrics.csv"), index=False)
    pd.DataFrame(misclass_data).to_csv(os.path.join(TRACKING_DIR, "misclassifications.csv"), index=False)

if __name__ == '__main__':
    main()
