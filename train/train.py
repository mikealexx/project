import os
# ✅ Suppress TensorFlow logs, use CPU only, disable oneDNN noise
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# ✅ Silence absl logging
import logging
import absl.logging
absl.logging.set_verbosity(absl.logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.utils import to_categorical, load_img, img_to_array
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, Input
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import LabelEncoder

# ✅ Load config
import yaml
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# ✅ Config
LABEL_CSV = config["label_output_directory"] + "/labels.csv"
IMAGE_SIZE = (config["image_size"], config["image_size"])
BATCH_SIZE = 32
EPOCHS = 10

# ✅ Load data
df = pd.read_csv(LABEL_CSV)
df["label1"] = df["category"]
df["label2"] = df["category"] + "_" + df["application"]

# ✅ Add full PNG paths
png_base_path = config["png_output_directory"].rstrip("/")
df["filepath"] = df["filepath"].apply(lambda x: os.path.join(png_base_path, x))

def load_images_and_labels(label_type):
    images = []
    labels = []
    for _, row in df.iterrows():
        try:
            img = load_img(row["filepath"], target_size=IMAGE_SIZE)
            img = img_to_array(img) / 255.0
            images.append(img)
            labels.append(row[label_type])
        except Exception as e:
            print(f"Failed to load {row['filepath']}: {e}")
    return np.array(images), np.array(labels)

def build_model(num_classes):
    model = Sequential([
        Input(shape=(32, 32, 3)),
        Conv2D(32, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer=Adam(), loss='categorical_crossentropy', metrics=['accuracy'])
    return model

# ✅ Training loop for label1 and label2
for label_type in ["label1", "label2"]:
    print(f"\n🚀 Training model for {label_type}...")
    X, y = load_images_and_labels(label_type)
    
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    y_cat = to_categorical(y_encoded)

    X_train, X_test, y_train, y_test = train_test_split(X, y_cat, test_size=0.2, random_state=42)

    model = build_model(num_classes=y_cat.shape[1])
    model.fit(X_train, y_train, validation_data=(X_test, y_test), batch_size=BATCH_SIZE, epochs=EPOCHS)

    # ✅ Save model in modern format
    model.save(f"model_{label_type}.keras")

    # ✅ Save label mappings
    with open(f"labels_{label_type}.txt", "w") as f:
        for label in le.classes_:
            f.write(f"{label}\n")

    # ✅ Final evaluation on test set
    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"✅ Test results for {label_type} — Accuracy: {acc:.4f}, Loss: {loss:.4f}")