import unittest

from module.webui.updater import Updater


class TestWebuiUpdaterSync(unittest.TestCase):
    @staticmethod
    def updater(state):
        updater = object.__new__(Updater)
        updater.state = state
        return updater

    def test_syncs_official_upstream_before_checking_stable_branch(self):
        updater = self.updater(0)
        calls = []
        updater.sync_upstream_at_startup = lambda: calls.append('sync')
        updater._check_update = lambda: calls.append('check') or False

        updater.check_update()

        self.assertEqual(calls, ['sync', 'check'])
        self.assertFalse(updater.state)

    def test_does_not_start_another_sync_while_updater_is_busy(self):
        updater = self.updater('checking')
        calls = []
        updater.sync_upstream_at_startup = lambda: calls.append('sync')
        updater._check_update = lambda: calls.append('check') or False

        updater.check_update()

        self.assertEqual(calls, [])
        self.assertEqual(updater.state, 'checking')


if __name__ == '__main__':
    unittest.main()
