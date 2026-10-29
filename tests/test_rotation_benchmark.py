import json
import subprocess
import sys
import unittest

class BenchmarkTests(unittest.TestCase):
    def test_offline_benchmark_labels_simulation(self):
        run = subprocess.run([sys.executable, '-m', 'tools.agent_rotation.benchmark', '--iterations', '5'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report['mode'], 'offline-simulated')
        self.assertEqual(report['api_requests'], 0)
        self.assertEqual(report['successful_reservations'], 5)
        self.assertIsNone(report['model_success_rate'])
