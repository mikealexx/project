import os
import sys

# === Mute C++ backend (stderr) ===
def silence_stderr():
    sys.stderr.flush()
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 2)  # Redirect stderr (fd 2) to /dev/null
    os.close(devnull_fd)

silence_stderr()

# === Python-level logging suppressions ===
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TF Python logs

import numpy as np
import logging
import absl.logging
absl.logging.set_verbosity(absl.logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)

from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array

def predict_label(image_path: str, model_path: str, labels_path: str) -> str:
    model = load_model(model_path)

    with open(labels_path, "r") as f:
        classes = [line.strip() for line in f.readlines()]

    img = load_img(image_path, target_size=(32, 32))
    img = img_to_array(img) / 255.0
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img, verbose=0)[0]
    return classes[np.argmax(pred)]

if __name__ == "__main__":
    image_path = "data/png/browsing/adobe/adobe-[2025-05-06-17-00-14].png"
    model_path = "model_label2.keras"
    labels_path = "labels_label2.txt"
    label = predict_label(image_path, model_path, labels_path)
    print(f"Predicted label: {label}")
