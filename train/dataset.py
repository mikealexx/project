from PIL import Image
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
import yaml, os
from torch.utils.data import Dataset
from torchvision import transforms

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# # Your CSV includes columns like:
# # filename,category,application
# df = pd.read_csv(config["label_output_directory"] + "/labels.csv")

# # Create a combined label for stratification
# df['stratify_label'] = df['category'] + '_' + df['application']

# """""
# train_df, test_df = train_test_split(
#     df,
#     test_size=0.2,
#     random_state=42,
#     stratify=df['stratify_label']
# )

# """

# # Set up Stratified K-Fold
# k = 5  # or any other number of folds you want
# skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)

# # Example: iterate through each fold
# for fold, (train_index, test_index) in enumerate(skf.split(df, df['stratify_label'])):
#     train_df = df.iloc[train_index]
#     test_df = df.iloc[test_index]

#     print(f"Fold {fold}")
#     print("Train size:", len(train_df), "| Test size:", len(test_df))
#     # Optionally save to file or train a model here
#     # train_df.to_csv(f'train_fold_{fold}.csv', index=False)
#     # test_df.to_csv(f'test_fold_{fold}.csv', index=False)




class QUICDataset(Dataset):

    def __init__(self, dataframe, transform=None):
        self.png_output_directory = config["png_output_directory"]
        self.test_size = config["test_size"]
        self.random_state = config["random_state"]

        self.dataframe = dataframe.reset_index(drop=True)
        self.img_dir = self.png_output_directory
        self.transform = transform

        # Combine category + application as label
        self.dataframe['combined_label'] = self.dataframe['category'] + "_" + self.dataframe['application']
        self.classes = sorted(self.dataframe['combined_label'].unique())
        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}
        self.labels = self.dataframe['combined_label'].map(self.class_to_idx)


    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        img_name = self.dataframe.iloc[idx]['filepath']
        img_path = os.path.join(self.img_dir, img_name)
        image = Image.open(img_path).convert("RGB")
        label = self.labels.iloc[idx]
        if self.transform:
            image = self.transform(image)
        return image, label

    @classmethod
    def from_csv_kfold(cls, csv_path, transform=None, stratify_by="application", k=5):
        df = pd.read_csv(csv_path)

        if stratify_by == "category_application":
            df['stratify_label'] = df['category'] + "_" + df['application']
            stratify_col = df['stratify_label']
        elif stratify_by == "category":
            stratify_col = df['category']
        else:
            stratify_col = df['application']

        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
        folds = []

        for fold, (train_index, test_index) in enumerate(skf.split(df, stratify_col)):
            train_df = df.iloc[train_index].reset_index(drop=True)
            test_df = df.iloc[test_index].reset_index(drop=True)

            train_dataset = cls(train_df, transform=transform)
            test_dataset = cls(test_df, transform=transform)

            folds.append((train_dataset, test_dataset))
            print(f"[Fold {fold}] Train size: {len(train_df)}, Test size: {len(test_df)}")

        return folds
    

if __name__ == "__main__":
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor()
    ])

    folds = QUICDataset.from_csv_kfold(config["label_output_directory"] + "/labels.csv", transform=transform)

    for i, (train_dataset, test_dataset) in enumerate(folds):
        print(f"\nFold {i} ready with {len(train_dataset)} train samples and {len(test_dataset)} test samples")

    # Use with DataLoader
    # from torch.utils.data import DataLoader
    # train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    # test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
    print("Datasets created successfully:")
    print(f"train dataset: {len(train_dataset)}")
    print(f"test dataset: {len(test_dataset)}")