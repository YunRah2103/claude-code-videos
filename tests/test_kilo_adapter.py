import unittest
from unittest.mock import patch

from tools.agent_rotation.kilo_adapter import assess_kilo, prepare_kilo_run

class KiloAdapterTests(unittest.TestCase):
    def test_missing_binary_is_unavailable_without_launching(self):
        with patch('tools.agent_rotation.kilo_adapter.shutil.which', return_value=None):
            status = assess_kilo()
        self.assertFalse(status.available)
        self.assertIn('not installed', status.reason)

    def test_executable_presence_alone_does_not_verify_free_background_model(self):
        with patch('tools.agent_rotation.kilo_adapter.shutil.which', return_value='/opt/kilo'):
            status = assess_kilo()
        self.assertFalse(status.available)
        self.assertIn('background', status.reason)

    def test_preparing_run_always_fails_closed_even_if_binary_present(self):
        with patch('tools.agent_rotation.kilo_adapter.shutil.which', return_value='/opt/kilo'):
            with self.assertRaisesRegex(RuntimeError, 'not enabled'):
                prepare_kilo_run('Implement a wheel helper')
