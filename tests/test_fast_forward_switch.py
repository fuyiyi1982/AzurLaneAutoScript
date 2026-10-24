import unittest
from pathlib import Path

import cv2
import numpy as np

from module.base.button import Button
from module.base.utils import color_mask, crop, load_image
from module.config.server import set_server
from module.handler.assets import CLEAR_MODE_TITLE
from module.handler.fast_forward import AUTO_SEARCH, CLEAR_MODE, FastForwardSwitch


PROJECT_ROOT = Path(__file__).parents[1]
CLEAR_MODE_FIXTURE = PROJECT_ROOT / 'tests' / 'fixtures' / 'clear_mode_2560x1440_downsampled.png'


class DummyDevice:
    def __init__(self, image):
        self.image = image


class DummyMain:
    def __init__(self, image):
        self.device = DummyDevice(image)

    def appear(self, _button, offset):
        self.last_offset = offset
        return False

    def match_template_color(self, button, offset=(20, 20), similarity=0.85, threshold=30):
        return button.match_template_color(
            self.device.image,
            offset=offset,
            similarity=similarity,
            threshold=threshold,
        )

    def image_color_count(self, area, color, threshold=30, count=50):
        mask = color_mask(crop(self.device.image, area, copy=False), color, threshold=threshold)
        return cv2.countNonZero(mask) > count


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

    def test_clear_mode_and_auto_search_survive_high_resolution_downsampling(self):
        set_server('cn')
        image = load_image(CLEAR_MODE_FIXTURE)

        self.assertFalse(CLEAR_MODE_TITLE.match(image, offset=(20, 20), similarity=0.85))
        self.assertEqual(CLEAR_MODE.get(DummyMain(image)), 'on')
        self.assertEqual(AUTO_SEARCH.get(DummyMain(image)), 'off')


if __name__ == '__main__':
    unittest.main()
