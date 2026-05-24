import numpy as np
from sklearn.linear_model import LogisticRegression
from typing import List

def extract_features(prompt: str) -> List[float]:
    tokens = len(prompt.split())
    verbs = sum(1 for v in ["analyze", "evaluate", "compare", "write"] if v in prompt.lower())
    constraints = sum(1 for c in ["json", "format", "must", "limit"] if c in prompt.lower())
    return [float(tokens), float(verbs), float(constraints)]

class PromptComplexityClassifier:
    def __init__(self):
        self.model = LogisticRegression()
        # Train immediately on initialization to prevent incoming runtime request latency
        self._train_v1()
        
    def _train_v1(self):
        X, y = [], []
        # Algorithmically generate standard training distributions for tiers 0, 1, and 2
        for _ in range(50): X.append([float(np.random.randint(1, 8)), 0.0, 0.0]); y.append(0)
        for _ in range(50): X.append([float(np.random.randint(10, 25)), 1.0, 1.0]); y.append(1)
        for _ in range(50): X.append([float(np.random.randint(30, 150)), 3.0, 2.0]); y.append(2)
        self.model.fit(X, y)

    def predict_tier(self, prompt: str) -> int:
        return int(self.model.predict(np.array(extract_features(prompt)).reshape(1, -1))[0])

# Instantiate global singleton instance to retain trained parameters in memory
classifier = PromptComplexityClassifier()