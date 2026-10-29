import tempfile
import unittest
from pathlib import Path
from tools.agent_rotation.metrics import Metrics

class MetricsTests(unittest.TestCase):
    def test_unknown_tokens_remain_unknown_and_duplicates_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics(Path(tmp) / 'metrics.db')
            metrics.record('task1', 'openrouter', 'success', prompt_tokens=23, completion_tokens=None, cost=None)
            result = Metrics(Path(tmp) / 'metrics.db').report()
            self.assertEqual(result['requests'], 1)
            self.assertEqual(result['known_prompt_tokens'], 23)
            self.assertEqual(result['unknown_completion_counts'], 1)
            self.assertEqual(result['unknown_cost_counts'], 1)
            with self.assertRaises(ValueError): metrics.record('task1', 'openrouter', 'success')

    def test_invalid_token_and_cost_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics(Path(tmp) / 'metrics.db')
            for kw in ({'prompt_tokens': -1}, {'completion_tokens': 1.2}, {'cost': float('nan')}):
                with self.assertRaises(ValueError): metrics.record('id', 'x', 'failed', **kw)
