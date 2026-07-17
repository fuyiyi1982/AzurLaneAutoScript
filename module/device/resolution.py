import typing as t

import cv2

from module.base.utils import image_size
from module.logger import logger


class ResolutionAdapter:
    """Keep Alas on a 1280x720 virtual canvas on high-resolution devices."""

    REFERENCE_RESOLUTION = (1280, 720)
    HIGH_RESOLUTION = (2560, 1440)
    SUPPORTED_RESOLUTIONS = (REFERENCE_RESOLUTION, HIGH_RESOLUTION)

    # These backends already translate Alas' 1280x720 coordinates themselves.
    VIRTUAL_CONTROL_METHODS = frozenset(('minitouch', 'MaaTouch', 'scrcpy'))

    @classmethod
    def resolution_landscape_size(cls, size: t.Tuple[int, int]) -> t.Tuple[int, int]:
        width, height = map(int, size)
        if width < height:
            width, height = height, width
        return width, height

    @classmethod
    def resolution_is_supported(cls, size: t.Tuple[int, int]) -> bool:
        return cls.resolution_landscape_size(size) in cls.SUPPORTED_RESOLUTIONS

    @property
    def resolution_native_size(self) -> t.Tuple[int, int]:
        return self.__dict__.get('_resolution_native_size', self.REFERENCE_RESOLUTION)

    @property
    def resolution_scale(self) -> t.Tuple[float, float]:
        width, height = self.resolution_native_size
        ref_width, ref_height = self.REFERENCE_RESOLUTION
        return width / ref_width, height / ref_height

    def resolution_set_native_size(self, size: t.Tuple[int, int]) -> bool:
        """Record a supported device size in landscape orientation."""
        size = self.resolution_landscape_size(size)
        if size not in self.SUPPORTED_RESOLUTIONS:
            return False

        previous = self.__dict__.get('_resolution_native_size')
        self.__dict__['_resolution_native_size'] = size
        if previous != size:
            logger.attr('Native resolution', f'{size[0]}x{size[1]}')
            if size != self.REFERENCE_RESOLUTION:
                logger.info('Use 1280x720 virtual resolution for image recognition and controls')
        return True

    def resolution_normalize_image(self, image):
        """Downsample a supported native screenshot to the Alas reference size."""
        size = image_size(image)
        if size == self.REFERENCE_RESOLUTION:
            # A streaming backend such as scrcpy can already return 1280x720
            # while the physical display is 2560x1440. Preserve a native size
            # learned earlier from uiautomator2 in that case.
            if '_resolution_native_size' not in self.__dict__:
                self.resolution_set_native_size(size)
            return image

        if size == self.HIGH_RESOLUTION:
            self.resolution_set_native_size(size)
            return cv2.resize(image, self.REFERENCE_RESOLUTION, interpolation=cv2.INTER_AREA)

        return image

    def resolution_to_native_point(self, point) -> t.Tuple[int, int]:
        scale_x, scale_y = self.resolution_scale
        x, y = point
        return int(round(x * scale_x)), int(round(y * scale_y))

    def resolution_to_virtual_point(self, point) -> t.Tuple[int, int]:
        scale_x, scale_y = self.resolution_scale
        x, y = point
        return int(round(x / scale_x)), int(round(y / scale_y))

    def resolution_control_point(self, point, method: str, native_input: bool = False) -> t.Tuple[int, int]:
        """Translate a point into the coordinate space expected by a backend."""
        backend_uses_virtual = method in self.VIRTUAL_CONTROL_METHODS
        if native_input and backend_uses_virtual:
            return self.resolution_to_virtual_point(point)
        if not native_input and not backend_uses_virtual:
            return self.resolution_to_native_point(point)
        x, y = point
        return int(x), int(y)

    def resolution_control_vector(self, values, method: str) -> t.Tuple[int, ...]:
        """Scale an x/y vector or rectangle for a native-coordinate backend."""
        if method in self.VIRTUAL_CONTROL_METHODS:
            return tuple(values)

        scale_x, scale_y = self.resolution_scale
        result = []
        for index, value in enumerate(values):
            scale = scale_x if index % 2 == 0 else scale_y
            result.append(int(round(value * scale)))
        return tuple(result)
