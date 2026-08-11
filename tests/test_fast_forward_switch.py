import unittest

import numpy as np

from module.base.button import Button
from module.handler.fast_forward import FastForwardSwitch


class DummyDevice:
    def __init__(self, image):
        self.image = image


class DummyMain:
    def __init__(self, image):
        self.device = DummyDevice(image)

    def appear(self, _button, offset):
        self.last_offset = offset
        return False


def make_switch():
    switch = FastForwardSwitch('Fast_Forward', offset=(5, 5))
    switch.add_state(
        'on',
        check_button=Button(area=(4, 0, 8, 4), color=(250, 250, 250), button=(4, 0, 8, 4)),
    )
    switch.add_state(
        'off',
        check_button=Button(area=(0, 0, 4, 4), color=(250, 250, 250), button=(0, 0, 4, 4)),
    )
    return switch


class TestFastForwardSwitch(unittest.TestCase):
    def test_color_fallback_detects_on(self):
        image = np.full((4, 8, 3), 60, dtype=np.uint8)
        image[:, 4:8] = 242

        self.assertEqual(make_switch().get(DummyMain(image)), 'on')

    def test_color_fallback_detects_off(self):
        image = np.full((4, 8, 3), 60, dtype=np.uint8)
        image[:, 0:4] = 242

        self.assertEqual(make_switch().get(DummyMain(image)), 'off')

    def test_color_fallback_rejects_ambiguous_image(self):
        image = np.full((4, 8, 3), 242, dtype=np.uint8)

        self.assertEqual(make_switch().get(DummyMain(image)), 'unknown')


if __name__ == '__main__':
    unittest.main()
