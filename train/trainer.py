import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models
from torch.utils.data import DataLoader

#squeezenet1_0


class Trainer:
    def __init__(self, train_dataset, test_dataset, num_classes, class_names, device=None):
        self.train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        self.test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
        self.class_names = class_names
        self.num_classes = num_classes
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = models.squeezenet1_0(pretrained=True)
        self.model.classifier[1] = nn.Conv2d(512, num_classes, kernel_size=1)
        self.model.num_classes = num_classes
        self.model.to(self.device)

        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)

    def train(self, epochs=10):
        for epoch in range(epochs):
            self.model.train()
            running_loss = 0.0
            correct = 0
            total = 0

            for images, labels in self.train_loader:
                images, labels = images.to(self.device), labels.to(self.device)

                self.optimizer.zero_grad()
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()

                running_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

            epoch_loss = running_loss / total
            epoch_acc = 100. * correct / total
            print(f"Epoch {epoch+1}: Loss={epoch_loss:.4f}, Accuracy={epoch_acc:.2f}%")

    def evaluate(self):
        self.model.eval()
        correct = 0
        total = 0

        with torch.no_grad():
            for images, labels in self.test_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                outputs = self.model(images)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

        acc = 100. * correct / total
        print(f"Test Accuracy: {acc:.2f}%")
        return acc

    def save(self, path="model.pth"):
        checkpoint = {
            'model_state': self.model.state_dict(),
            'class_names': self.class_names,
            'num_classes': self.num_classes
        }
        torch.save(checkpoint, path)
        print(f"Model and metadata saved to {path}")
