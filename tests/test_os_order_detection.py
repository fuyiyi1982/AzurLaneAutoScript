import unittest
from pathlib import Path

import numpy as np

from module.base.button import Button
from module.base.utils import color_similarity_2d, crop, load_image
from module.os.order_detection import is_map_order_page


PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE = PROJECT_ROOT / 'tests' / 'fixtures' / 'order_gms_2560x1440_downsampled.png'
LEGACY_ASSET = PROJECT_ROOT / 'assets' / 'cn' / 'os_handler' / 'ORDER_CHECK.png'
ORDER_CHECK = Button(
    area=(60, 623, 98, 659),
    color=(60, 77, 122),
    button=(106, 77, 224, 94),
    file=str(LEGACY_ASSET),
    name='ORDER_CHECK',
)


class ImageDetector:
    def __init__(self, image):
        self.image = image

    def appear(self, button, offset):
        return button.match(self.image, offset=offset)

    def image_color_count(self, area, color, threshold, count):
        similarity = color_similarity_2d(crop(self.image, area, copy=False), color)
        return int(np.sum(similarity >= threshold)) > count


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


if __name__ == '__main__':
    unittest.main()
