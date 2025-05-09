import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms, datasets
from torch.utils.data import DataLoader, Dataset
from PIL import Image
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# === CONFIG ===
LABELS_PATH = config['label_output_directory'] + '/labels.csv'
IMAGES_DIR = config['png_output_directory']
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.001
IMAGE_SIZE = config['image_size']
MODEL_DIR = 'models'

# === DATASET CLASS ===
class ImageLabelDataset(Dataset):
    def __init__(self, dataframe, label_column, transform=None):
        self.dataframe = dataframe
        self.label_column = label_column
        self.transform = transform

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        row = self.dataframe.iloc[idx]
        img_path = os.path.join(IMAGES_DIR, row['filepath'])
        image = Image.open(img_path).convert('RGB').resize((IMAGE_SIZE, IMAGE_SIZE))
        label = row[self.label_column]

        if self.transform:
            image = self.transform(image)

        return image, label

# === MODEL ===
class SimpleCNN(nn.Module):
    def __init__(self, num_classes):
        super(SimpleCNN, self).__init__()
        self.conv_layers = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.fc_layers = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * (IMAGE_SIZE // 8) * (IMAGE_SIZE // 8), 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        x = self.conv_layers(x)
        x = self.fc_layers(x)
        return x

# === TRAIN FUNCTION ===
def train_model(label_column, model_save_path):
    df = pd.read_csv(LABELS_PATH)
    
    if 'category_application' not in df.columns and label_column == 'category_application':
        df['category_application'] = df['category'] + '_' + df['application']
    
    df[label_column] = LabelEncoder().fit_transform(df[label_column])


    train_df, test_df = train_test_split(df, test_size=0.2, stratify=df[label_column], random_state=42)

    transform = transforms.Compose([
        transforms.ToTensor()
    ])

    train_dataset = ImageLabelDataset(train_df, label_column, transform)
    test_dataset = ImageLabelDataset(test_df, label_column, transform)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    num_classes = len(df[label_column].unique())
    model = SimpleCNN(num_classes)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        print(f"Epoch {epoch+1}/{EPOCHS}, Loss: {running_loss/len(train_loader):.4f}")

    # Evaluate
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in test_loader:
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    print(f"Test Accuracy for {label_column}: {100 * correct / total:.2f}%")
    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), model_save_path)

# === MAIN ===
def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    train_model('category', os.path.join(MODEL_DIR, 'model_category.pt'))
    train_model('category_application', os.path.join(MODEL_DIR, 'model_category_application.pt'))

if __name__ == '__main__':
    main()