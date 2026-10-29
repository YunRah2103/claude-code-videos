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

    def test_reports_known_totals_and_unknowns_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics(Path(tmp) / 'metrics.db')
            metrics.record('a', 'x', 'success', prompt_tokens=10, completion_tokens=4, reasoning_tokens=2, total_tokens=16, cost=0)
            metrics.record('b', 'x', 'failed')
            summary = metrics.report()
            self.assertEqual(summary['known_completion_tokens'], 4)
            self.assertEqual(summary['known_reasoning_tokens'], 2)
            self.assertEqual(summary['known_total_tokens'], 16)
            self.assertEqual(summary['unknown_total_counts'], 1)
            self.assertEqual(summary['known_cost'], 0)
            self.assertEqual(summary['unknown_cost_counts'], 1)

    def test_existing_metric_never_overwritten_by_failure(self):
        from tools.agent_rotation.openrouter_adapter import AdapterError
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'metrics.db'
            metrics = Metrics(path)
            metrics.record('a', 'x', 'response_received', prompt_tokens=5, cost=None)
            metrics.record_failure('a', 'x', AdapterError('OUTPUT_STAGING_FAILED', stage='staging', usage={'prompt_tokens':99, 'cost':0}))
            summary = metrics.report()
            self.assertEqual(summary['requests'], 1)
            self.assertEqual(summary['known_prompt_tokens'], 5)
            self.assertEqual(summary['unknown_cost_counts'], 1)
