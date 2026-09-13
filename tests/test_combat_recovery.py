import unittest

from module.combat.assets import EXP_INFO_S
from module.combat.combat import Combat
from module.combat_ui.assets import PAUSE_Cyber
from module.ui.ui import UI


class _Config:
    Campaign_UseFleetLock = True


class _CombatProbe:
    config = _Config()

    def __init__(self, *, executing=False, matches=()):
        self.executing = executing
        self.matches = set(matches)
        self.recovered_expected_end = None

    def is_in_map(self):
        return False

    def is_combat_loading(self):
        return False

    def is_combat_executing(self):
        return PAUSE_Cyber if self.executing else False

    def appear(self, button, **kwargs):
        return button in self.matches

    def handle_combat_automation_confirm(self):
        return False

    def combat_status(self, expected_end=None):
        self.recovered_expected_end = expected_end

    combat_status_appear = Combat.combat_status_appear


class _UIProbe:
    def __init__(self, matches=()):
        self.matches = set(matches)
        self.clicked = []

    def appear_then_click(self, button, **kwargs):
        if button not in self.matches:
            return False
        self.clicked.append(button)
        return True


class TestCombatRecovery(unittest.TestCase):
    def test_combat_appear_recovers_after_loading_screen_was_missed(self):
        probe = _CombatProbe(executing=True)

        self.assertTrue(Combat.combat_appear(probe))

    def test_combat_status_recover_resumes_post_battle_cleanup(self):
        probe = _CombatProbe(matches=(EXP_INFO_S,))

        self.assertTrue(Combat.combat_status_recover(probe, expected_end='with_searching'))
        self.assertEqual(probe.recovered_expected_end, 'with_searching')

    def test_combat_status_recover_ignores_unrelated_pages(self):
        probe = _CombatProbe()

        self.assertFalse(Combat.combat_status_recover(probe, expected_end='with_searching'))
        self.assertIsNone(probe.recovered_expected_end)

    def test_ui_startup_recovers_from_exp_info(self):
        probe = _UIProbe(matches=(EXP_INFO_S,))

        self.assertTrue(UI.ui_combat_status_cleanup(probe))
        self.assertEqual(probe.clicked, [EXP_INFO_S])


if __name__ == '__main__':
    unittest.main()
