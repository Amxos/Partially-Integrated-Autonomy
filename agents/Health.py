#Python Libraries
import threading
from collections import deque

#External Libraries


#PIA Libraries




class HealthHistory:
    def __init__(self, window_size=10, initial_health=1.0):
        self.health_scores = deque([initial_health] * window_size, maxlen=window_size)
        self._lock = threading.RLock() #for good measure

    def add_score(self, score):
        with self._lock:
            self.health_scores.append(score)

    def get_average(self):
        with self._lock:
            return sum(self.health_scores) / len(self.health_scores)

    def get_ewma(self, alpha=0.1):
        """Calculate Exponential Weighted Moving Average"""
        with self._lock:
            ewma = self.health_scores[0]
            for score in self.health_scores:
                ewma = alpha * score + (1 - alpha) * ewma
            return ewma
