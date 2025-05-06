from torchvision import transforms
from dataset import QUICDataset
from trainer import Trainer
import yaml, torch
from torchvision import transforms
from PIL import Image
from torchvision.models import squeezenet1_0, SqueezeNet1_0_Weights

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def predict_image_label(image_path, model_path, model_builder, device=None):
    """
    Predict the label of a single PNG image using a saved model (.pth).

    Args:
        image_path (str): Path to the PNG image.
        model_path (str): Path to the .pth file with model + metadata.
        model_builder (callable): Function that builds the model given num_classes.
        device (torch.device): Device to use.

    Returns:
        str: Predicted label
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device)
    num_classes = checkpoint["num_classes"]
    class_names = checkpoint["class_names"]

    # Build and load model
    model = model_builder(num_classes).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    # Transform image
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    image = Image.open(image_path).convert("RGB")
    image = transform(image).unsqueeze(0).to(device)

    # Predict
    with torch.no_grad():
        output = model(image)
        output = output.squeeze()  # shape: [num_classes]
        _, predicted = torch.max(output, 0)  # dim=0 since it's now flat

        label_idx = predicted.item()

    return class_names[label_idx]


def build_model(num_classes):
    model = squeezenet1_0(weights=SqueezeNet1_0_Weights.DEFAULT)  # or weights=SqueezeNet1_0_Weights.DEFAULT if pretrained
    model.classifier[1] = torch.nn.Conv2d(512, num_classes, kernel_size=1)
    model.num_classes = num_classes
    return model

if __name__ == "__main__":
    # transform = transforms.Compose([
    #     transforms.Resize((224, 224)),
    #     transforms.ToTensor()
    # ])

    # folds = QUICDataset.from_csv_kfold(config["label_output_directory"] + "/labels.csv", stratify_by="category_application", transform=transform, k=5)

    # # Train on fold 0
    # train_ds, test_ds = folds[0]
    # trainer = Trainer(train_ds, test_ds,
    #               num_classes=len(train_ds.classes),
    #               class_names=train_ds.classes)


    # trainer.train(epochs=25)
    # trainer.evaluate()
    # trainer.save("resnet18_quic_fold0.pth")
    label = predict_image_label(
        "data/png/video/youtube/youtube-[2025-05-06-18-28-20].png",
        "resnet18_quic_fold0.pth",
        build_model
    )
    print("Predicted label:", label)