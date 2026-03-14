import pyautogui
import time
import random
import logging
 
logger = logging.getLogger(__name__)
 
 
def human_type(text):
    """
    Types text fast. Splits on newlines, types each line instantly via
    pyautogui.write(), with a small pause at line ends and a longer pause
    at paragraph breaks.
    """
    logger.info(f"Typing text (human style): {text[:30]}...")
 
    paragraphs = text.split('\n\n')
    for p_idx, paragraph in enumerate(paragraphs):
        lines = paragraph.split('\n')
        for line in lines:
            if line:
                pyautogui.write(line, interval=0)
            pyautogui.press('enter')
            time.sleep(random.uniform(0.05, 0.15))   # small line-end pause
        # paragraph break pause (skip after last paragraph)
        if p_idx < len(paragraphs) - 1:
            pyautogui.press('enter')
            time.sleep(random.uniform(0.3, 0.4))
 
 
TEXT = """
import pandas as pd
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

class Perceptron:
    def __init__(self, max_iters=1000, patience=10, min_delta=0.01,min_iters=10):
        self.max_iters = max_iters
        self.patience = patience
        self.min_delta = min_delta
        self.weights = None
        self.best_weights = None
        self.min_iters = min_iters
        self.validation_loss_history = []
        self.accuracy_history = []

    def fit(self, X, y, test_size=0.2):
        X_train_epoch, X_val_epoch, y_train_epoch, y_val_epoch = train_test_split(
            X, y, test_size=test_size, random_state=308
        )

        self.weights = np.zeros(X_train_epoch.shape[1])
        best_loss = float('inf')
        patience_counter = 0

        for i in range(self.max_iters):
            for j in range(X_train_epoch.shape[0]):
                if y_train_epoch.iloc[j] * np.dot(self.weights, X_train_epoch.iloc[j]) <= 0:
                    self.weights = self.weights + y_train_epoch.iloc[j] * X_train_epoch.iloc[j]

            validation_loss = np.sum(np.maximum(0, 1 - y_val_epoch * np.dot(X_val_epoch, self.weights)))
            self.validation_loss_history.append(validation_loss)

            accuracy = np.mean(np.sign(np.dot(X, self.weights)) == y)
            self.accuracy_history.append(accuracy)
            if i < self.min_iters:
                continue
            if validation_loss < best_loss - self.min_delta:
                best_loss = validation_loss
                patience_counter = 0
                self.best_weights = self.weights.copy()
            else:
                patience_counter += 1
                if patience_counter >= self.patience:
                    print(f"Early stopping at iteration {i+1}")
                    break

    def predict(self, X):
        return np.sign(np.dot(X, self.best_weights))

    def evaluate(self, X_test, y_test):
        y_pred = self.predict(X_test)
        accuracy = np.mean(y_pred == y_test)
        print(f"Accuracy: {accuracy}")

        true_positives = np.sum((y_pred == 1) & (y_test == 1))
        false_positives = np.sum((y_pred == 1) & (y_test == -1))
        false_negatives = np.sum((y_pred == -1) & (y_test == 1))
        true_negatives = np.sum((y_pred == -1) & (y_test == -1))

        precision = true_positives / (true_positives + false_positives)
        print(f"Precision: {precision}")

        recall = true_positives / (true_positives + false_negatives)
        print(f"Recall: {recall}")

        f1_score = 2 * (precision * recall) / (precision + recall)
        print(f"F1 Score: {f1_score}")

    def plot_metrics(self):
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(self.validation_loss_history)
        plt.xlabel('Epochs')
        plt.ylabel('Validation Loss')
        plt.title('Validation Loss vs. Epochs')

        plt.subplot(1, 2, 2)
        plt.plot(self.accuracy_history)
        plt.xlabel('Epochs')
        plt.ylabel('Accuracy')
        plt.title('Accuracy vs. Epochs')
        plt.tight_layout()
        plt.show()

    def plot_decision_boundary(self, X, y):
        plt.scatter(X['sepal_length'], X['petal_length'], c=y, cmap='coolwarm')

        if isinstance(self.best_weights, pd.Series):
            boundary_line = (-self.best_weights['bias'] - self.best_weights['sepal_length'] * X['sepal_length']) / self.best_weights['petal_length']
        else:
            # Access by index if best_weights is a numpy array
            boundary_line = (-self.best_weights[2] - self.best_weights[0] * X['sepal_length']) / self.best_weights[1]

        plt.plot(X['sepal_length'], boundary_line, color='black', linestyle='--')
        plt.xlabel('Sepal Length')
        plt.ylabel('Petal Length')
        plt.title('Perceptron Decision Boundary')
        plt.show()
"""
 
time.sleep(2)
human_type(TEXT)
 