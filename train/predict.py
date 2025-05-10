import os
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import pandas as pd
from cnn import SimpleCNN
import yaml

# === CONFIG ===
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

IMAGE_SIZE = config['image_size']
MODEL_DIR = 'models'
IMAGES_DIR = config['png_output_directory']
LABELS_PATH = config['label_output_directory'] + '/labels.csv'

# === PREDICT FUNCTION ===
def predict_image(model_path, label_column, image_path):
    df = pd.read_csv(LABELS_PATH)
    if 'category_application' not in df.columns:
        df['category_application'] = df['category'] + '_' + df['application']

    labels = sorted(df[label_column].unique())
    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    idx_to_label = {idx: label for label, idx in label_to_idx.items()}

    model = SimpleCNN(num_classes=len(labels))
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor()
    ])

    image = Image.open(image_path).convert('RGB')
    image = transform(image).unsqueeze(0)

    with torch.no_grad():
        outputs = model(image)
        _, predicted = torch.max(outputs, 1)
        predicted_label = idx_to_label[predicted.item()]

    return predicted_label

# === MAIN ===
def main():
    image_path = "data/png/video/vimeo/vimeo-[2025-05-06-18-49-18].png"

    category = predict_image(os.path.join(MODEL_DIR, 'model_category.pt'), 'category', image_path)
    category_app = predict_image(os.path.join(MODEL_DIR, 'model_category_application.pt'), 'category_application', image_path)

    print(f"Predicted Category: {category}")
    print(f"Predicted Category_Application: {category_app}")

if __name__ == '__main__':
    main()
