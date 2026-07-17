import unittest

import numpy as np

from module.device.resolution import ResolutionAdapter
from module.device.method.droidcast import DroidCast


class DummyDroidCast(ResolutionAdapter, DroidCast):
    is_mumu_over_version_356 = False

    def resolution_uiautomator2(self, cal_rotation=True):
        return 2560, 1440

    def get_orientation(self):
        return 0


class TestResolutionAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = ResolutionAdapter()

    def test_reference_screenshot_is_unchanged(self):
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = self.adapter.resolution_normalize_image(image)

        self.assertIs(result, image)
        self.assertEqual(self.adapter.resolution_native_size, (1280, 720))

    def test_high_resolution_screenshot_is_normalized(self):
        image = np.zeros((1440, 2560, 3), dtype=np.uint8)
        result = self.adapter.resolution_normalize_image(image)

        self.assertEqual(result.shape, (720, 1280, 3))
        self.assertEqual(self.adapter.resolution_native_size, (2560, 1440))

    def test_streamed_reference_image_preserves_known_native_size(self):
        self.adapter.resolution_set_native_size((2560, 1440))
        image = np.zeros((720, 1280, 3), dtype=np.uint8)

        self.adapter.resolution_normalize_image(image)

        self.assertEqual(self.adapter.resolution_native_size, (2560, 1440))

    def test_native_backend_scales_virtual_coordinates(self):
        self.adapter.resolution_set_native_size((2560, 1440))

        self.assertEqual(
            self.adapter.resolution_control_point((320, 180), 'ADB'),
            (640, 360),
        )
        self.assertEqual(
            self.adapter.resolution_control_vector((-10, -5, 10, 5), 'ADB'),
            (-20, -10, 20, 10),
        )

    def test_virtual_backend_keeps_virtual_coordinates(self):
        self.adapter.resolution_set_native_size((2560, 1440))

        self.assertEqual(
            self.adapter.resolution_control_point((320, 180), 'MaaTouch'),
            (320, 180),
        )

    def test_native_hierarchy_coordinates_follow_backend_space(self):
        self.adapter.resolution_set_native_size((2560, 1440))

        self.assertEqual(
            self.adapter.resolution_control_point((640, 360), 'ADB', native_input=True),
            (640, 360),
        )
        self.assertEqual(
            self.adapter.resolution_control_point((640, 360), 'MaaTouch', native_input=True),
            (320, 180),
        )

    def test_portrait_device_size_is_recognized(self):
        self.assertTrue(self.adapter.resolution_is_supported((1440, 2560)))
        self.adapter.resolution_set_native_size((1440, 2560))
        self.assertEqual(self.adapter.resolution_native_size, (2560, 1440))

    def test_droidcast_raw_uses_the_device_framebuffer_size(self):
        droidcast = object.__new__(DummyDroidCast)

        droidcast._droidcast_update_resolution()

        self.assertEqual((droidcast.droidcast_width, droidcast.droidcast_height), (2560, 1440))
        self.assertEqual(droidcast.resolution_native_size, (2560, 1440))


if __name__ == '__main__':
    unittest.main()
