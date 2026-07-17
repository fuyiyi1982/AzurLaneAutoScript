import unittest
from pathlib import Path

import numpy as np

from module.base.button import Button
from module.base.utils import load_image
from module.os.zone_detection import match_pinned_zone


FIXTURE = Path(__file__).parent / 'fixtures' / 'zone_obscure_2560x1440_downsampled.png'
ZONE_OBSCURE = Button(
    area=(85, 302, 172, 322),
    color=(142, 147, 186),
    button=(85, 302, 172, 322),
    file=str(Path(__file__).parents[1] / 'assets' / 'cn' / 'os' / 'ZONE_OBSCURE.png'),
    name='ZONE_OBSCURE',
)


class ImageDetector:
    def __init__(self, image):
        self.image = image

    def appear(self, button, offset):
        return button.match(self.image, offset=offset)

    def match_template_color(self, button, offset, similarity, threshold):
        return button.match_template_color(
            self.image,
            offset=offset,
            similarity=similarity,
            threshold=threshold,
        )


class TestOSGlobeHighResolution(unittest.TestCase):
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

        self.assertTrue(
            match_pinned_zone(
                ImageDetector(image),
                ZONE_OBSCURE,
                ZONE_OBSCURE,
            )
        )

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
        self.assertFalse(
            match_pinned_zone(
                ImageDetector(image),
                ZONE_OBSCURE,
                ZONE_OBSCURE,
            )
        )


if __name__ == '__main__':
    unittest.main()
