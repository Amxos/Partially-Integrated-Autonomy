import unittest
from collections import deque
import threading

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
            if not self.health_scores:
                return 0  # Handle empty list case, though unlikely with initial_health
            ewma = self.health_scores[0] # Initialize with the first value in the deque
            for i in range(1, len(self.health_scores)): # Iterate from the second element
                score = self.health_scores[i]
                ewma = alpha * score + (1 - alpha) * ewma
            return ewma

class TestHealthHistory(unittest.TestCase):
    # ... (previous tests: test_initialization, test_add_score, test_get_average, test_get_ewma_initial_values, test_get_ewma_different_scores, test_get_ewma_varying_alpha) ...

    def test_get_ewma_empty_history(self): # Corrected: No need for this as initial_health ensures non-empty
        history = HealthHistory(window_size=3, initial_health=0.0) # Still initialized, not empty in practice
        history.health_scores.clear() # Artificially empty it for test
        self.assertEqual(history.get_ewma(), 0) # Expect 0 for empty history (as per code change)


    def test_get_ewma_extreme_alpha(self):
        history = HealthHistory(window_size=3, initial_health=1.0)
        history.add_score(0.5)
        history.add_score(0.0)

        # alpha close to 0 (almost no weight to current score)
        self.assertAlmostEqual(history.get_ewma(alpha=0.001), 0.997501, places=6) # Should be close to initial value

        # alpha close to 1 (almost all weight to current score)
        self.assertAlmostEqual(history.get_ewma(alpha=0.999), 0.0004995, places=6) # Should be close to last score

    def test_get_ewma_negative_scores(self):
        history = HealthHistory(window_size=3, initial_health=1.0)
        history.add_score(-0.5)
        history.add_score(-1.0)
        # EWMA should handle negative scores correctly
        # ewma_0 = 1.0
        # ewma_1 = 0.1 * (-0.5) + 0.9 * 1.0 = -0.05 + 0.9 = 0.85
        # ewma_2 = 0.1 * (-1.0) + 0.9 * 0.85 = -0.1 + 0.765 = 0.665
        self.assertAlmostEqual(history.get_ewma(alpha=0.1), 0.665, places=5)

    def test_get_ewma_complex_score_sequence(self):
        history = HealthHistory(window_size=5, initial_health=1.0)
        scores = [0.8, 0.9, 0.5, 0.2, 0.7]
        for score in scores:
            history.add_score(score)
        # [1.0, 0.8, 0.9, 0.5, 0.2, 0.7] -> window is [0.8, 0.9, 0.5, 0.2, 0.7]
        # alpha = 0.2 (example)
        # ewma_0 = 0.8
        # ewma_1 = 0.2 * 0.9 + 0.8 * 0.8 = 0.18 + 0.64 = 0.82
        # ewma_2 = 0.2 * 0.5 + 0.8 * 0.82 = 0.1 + 0.656 = 0.756
        # ewma_3 = 0.2 * 0.2 + 0.8 * 0.756 = 0.04 + 0.6048 = 0.6448
        # ewma_4 = 0.2 * 0.7 + 0.8 * 0.6448 = 0.14 + 0.51584 = 0.65584
        self.assertAlmostEqual(history.get_ewma(alpha=0.2), 0.65584, places=5)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)