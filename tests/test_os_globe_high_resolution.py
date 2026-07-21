import unittest
from pathlib import Path

import cv2
import numpy as np

from module.base.button import Button
from module.base.utils import load_image
from module.os.zone_detection import match_pinned_zone


FIXTURES = Path(__file__).parent / 'fixtures'
OBSCURE_FIXTURE = FIXTURES / 'zone_obscure_2560x1440_downsampled.png'
DANGEROUS_FIXTURE = FIXTURES / 'zone_dangerous_2560x1440_downsampled.png'
DANGEROUS_MISSION_FIXTURE = (
    FIXTURES / 'zone_dangerous_mission_checkout_2560x1440_downsampled.png'
)
DANGEROUS_WARNING_FIXTURE = (
    FIXTURES / 'zone_dangerous_warning_2560x1440_downsampled.png'
)
DANGEROUS_CARIBBEAN_D_FIXTURE = (
    FIXTURES / 'zone_dangerous_caribbean_d_2560x1440_downsampled.png'
)
ZONE_DANGEROUS = Button(
    area=(87, 310, 171, 322),
    color=(153, 177, 197),
    button=(87, 310, 171, 322),
    file=str(Path(__file__).parents[1] / 'assets' / 'cn' / 'os' / 'ZONE_DANGEROUS.png'),
    name='ZONE_DANGEROUS',
)
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

    def match_template_color(self, button, offset, similarity, threshold):
        return button.match_template_color(
            self.image,
            offset=offset,
            similarity=similarity,
            threshold=threshold,
        )


class TestOSGlobeHighResolution(unittest.TestCase):
    def test_obscure_zone_survives_high_resolution_downsampling(self):
        image = load_image(OBSCURE_FIXTURE)

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
            )
        )
        self.assertFalse(match_pinned_zone(ImageDetector(image), ZONE_DANGEROUS))

    def test_dangerous_zone_survives_high_resolution_downsampling(self):
        image = load_image(DANGEROUS_FIXTURE)

        self.assertFalse(
            ZONE_DANGEROUS.match_template_color(
                image,
                offset=(20, 20),
                similarity=0.85,
                threshold=10,
            )
        )
        self.assertTrue(match_pinned_zone(ImageDetector(image), ZONE_DANGEROUS))
        self.assertFalse(match_pinned_zone(ImageDetector(image), ZONE_OBSCURE))

    def test_dangerous_zone_survives_mission_checkout_color_variation(self):
        image = load_image(DANGEROUS_MISSION_FIXTURE)

        self.assertFalse(
            ZONE_DANGEROUS.match_template_color(
                image,
                offset=(20, 20),
                similarity=0.80,
                threshold=10,
            )
        )
        self.assertTrue(match_pinned_zone(ImageDetector(image), ZONE_DANGEROUS))
        self.assertFalse(match_pinned_zone(ImageDetector(image), ZONE_OBSCURE))

    def test_dangerous_zone_survives_warning_color_variation(self):
        image = load_image(DANGEROUS_WARNING_FIXTURE)

        self.assertFalse(
            ZONE_DANGEROUS.match_template_color(
                image,
                offset=(20, 20),
                similarity=0.80,
                threshold=20,
            )
        )
        self.assertTrue(match_pinned_zone(ImageDetector(image), ZONE_DANGEROUS))
        self.assertFalse(match_pinned_zone(ImageDetector(image), ZONE_OBSCURE))

    def test_dangerous_zone_survives_caribbean_d_title_antialiasing(self):
        image = load_image(DANGEROUS_CARIBBEAN_D_FIXTURE)

        self.assertFalse(
            ZONE_DANGEROUS.match_template_color(
                image,
                offset=(20, 20),
                similarity=0.80,
                threshold=30,
            )
        )
        self.assertTrue(match_pinned_zone(ImageDetector(image), ZONE_DANGEROUS))
        self.assertFalse(match_pinned_zone(ImageDetector(image), ZONE_OBSCURE))

    def test_relaxed_template_still_requires_the_obscure_zone_color(self):
        image = load_image(OBSCURE_FIXTURE)
        area = image[282:342, 65:192]
        yuv = cv2.cvtColor(area, cv2.COLOR_RGB2YUV)
        chroma = yuv[:, :, 1].astype(np.int16) + 40
        yuv[:, :, 1] = np.clip(chroma, 0, 255).astype(np.uint8)
        image[282:342, 65:192] = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)

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
            )
        )


if __name__ == '__main__':
    unittest.main()
