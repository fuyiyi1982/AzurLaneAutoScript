import unittest
from pathlib import Path

import numpy as np

from module.base.utils import load_image
from module.os.globe_operation import ASSETS_PINNED_ZONE, GlobeOperation, ZONE_OBSCURE


FIXTURE = Path(__file__).parent / 'fixtures' / 'zone_obscure_2560x1440_downsampled.png'


class DummyDevice:
    def __init__(self, image):
        self.image = image

    @staticmethod
    def stuck_record_add(button):
        pass


class TestOSGlobeHighResolution(unittest.TestCase):
    def tearDown(self):
        for button in ASSETS_PINNED_ZONE:
            button.clear_offset()

    @staticmethod
    def operation_with(image):
        operation = object.__new__(GlobeOperation)
        operation.device = DummyDevice(image)
        return operation

    def test_obscure_zone_survives_high_resolution_downsampling(self):
        image = load_image(FIXTURE)

        self.assertFalse(
            ZONE_OBSCURE.match_template_color(
                image,
                offset=(20, 20),
                similarity=0.85,
                threshold=10,
            )
        )

        pinned = self.operation_with(image).get_zone_pinned()

        self.assertIs(pinned, ZONE_OBSCURE)

    def test_relaxed_template_still_requires_the_obscure_zone_color(self):
        image = load_image(FIXTURE)
        area = image[282:342, 65:192].astype(np.int16)
        image[282:342, 65:192] = np.clip(area + 15, 0, 255).astype(np.uint8)

        self.assertTrue(
            ZONE_OBSCURE.match_luma(
                image,
                offset=(20, 20),
                similarity=0.80,
            )
        )
        self.assertIsNone(self.operation_with(image).get_zone_pinned())


if __name__ == '__main__':
    unittest.main()
