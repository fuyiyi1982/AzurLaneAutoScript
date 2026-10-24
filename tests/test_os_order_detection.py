import unittest
from pathlib import Path

import cv2
import numpy as np

from module.base.button import Button
from module.base.utils import color_mask, crop, load_image
from module.os.order_detection import is_map_order_page
from module.ui.daily_detection import is_daily_page


PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE = PROJECT_ROOT / 'tests' / 'fixtures' / 'order_gms_2560x1440_downsampled.png'
DAILY_FIXTURE = PROJECT_ROOT / 'tests' / 'fixtures' / 'daily_page_2560x1440_downsampled.png'
LEGACY_ASSET = PROJECT_ROOT / 'assets' / 'cn' / 'os_handler' / 'ORDER_CHECK.png'
LEGACY_DAILY_ASSET = PROJECT_ROOT / 'assets' / 'cn' / 'ui' / 'DAILY_CHECK.png'
BACK_ARROW_ASSET = PROJECT_ROOT / 'assets' / 'cn' / 'ui' / 'BACK_ARROW.png'
ORDER_CHECK = Button(
    area=(60, 623, 98, 659),
    color=(60, 77, 122),
    button=(106, 77, 224, 94),
    file=str(LEGACY_ASSET),
    name='ORDER_CHECK',
)
DAILY_CHECK = Button(
    area=(23, 656, 67, 698),
    color=(84, 139, 210),
    button=(23, 656, 67, 698),
    file=str(LEGACY_DAILY_ASSET),
    name='DAILY_CHECK',
)
BACK_ARROW = Button(
    area=(33, 44, 47, 64),
    color=(112, 118, 152),
    button=(33, 31, 81, 78),
    file=str(BACK_ARROW_ASSET),
    name='BACK_ARROW',
)


class ImageDetector:
    def __init__(self, image):
        self.image = image
        self.interval_timer = {}

    def appear(self, button, offset):
        return button.match(self.image, offset=offset)

    def image_color_count(self, area, color, threshold, count):
        mask = color_mask(crop(self.image, area, copy=False), color, threshold=threshold)
        return cv2.countNonZero(mask) > count


class TestOSOrderDetection(unittest.TestCase):
    def test_new_gms_page_uses_the_stable_exit_icon(self):
        image = load_image(FIXTURE)

        self.assertFalse(ORDER_CHECK.match(image, offset=(20, 20), similarity=0.85))
        self.assertTrue(is_map_order_page(ImageDetector(image), ORDER_CHECK))

    def test_legacy_information_icon_remains_supported(self):
        image = load_image(LEGACY_ASSET)

        self.assertTrue(is_map_order_page(ImageDetector(image), ORDER_CHECK))

    def test_unrelated_page_is_not_detected_as_map_order(self):
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertFalse(is_map_order_page(ImageDetector(image), ORDER_CHECK))

        sea_map = np.full((720, 1280, 3), (45, 65, 95), dtype=np.uint8)
        self.assertFalse(is_map_order_page(ImageDetector(sea_map), ORDER_CHECK))

    def test_daily_page_uses_carousel_arrows_when_info_icon_is_occluded(self):
        image = load_image(DAILY_FIXTURE)

        self.assertFalse(DAILY_CHECK.match(image, offset=(30, 30), similarity=0.85))
        self.assertTrue(is_daily_page(ImageDetector(image), DAILY_CHECK, BACK_ARROW))

    def test_daily_page_legacy_information_icon_remains_supported(self):
        image = load_image(LEGACY_DAILY_ASSET)

        self.assertTrue(is_daily_page(ImageDetector(image), DAILY_CHECK, BACK_ARROW))

    def test_daily_subpanel_without_carousel_arrows_is_not_detected_as_daily_page(self):
        image = load_image(DAILY_FIXTURE)
        image[328:392, 20:58] = 0
        image[328:392, 1222:1260] = 0

        self.assertFalse(is_daily_page(ImageDetector(image), DAILY_CHECK, BACK_ARROW))


if __name__ == '__main__':
    unittest.main()
