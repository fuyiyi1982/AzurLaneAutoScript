ORDER_CHECK_OFFSET = (20, 20)
ORDER_GMS_EXIT_AREA = (45, 58, 90, 105)
ORDER_GMS_EXIT_COLOR = (255, 229, 91)
ORDER_GMS_EXIT_SIMILARITY = 221
ORDER_GMS_EXIT_PIXEL_COUNT = 100


def is_map_order_page(detector, legacy_check):
    """
    Detect the navigational order page across old and new game layouts.

    The legacy layout has a blue information icon at the bottom left. Newer
    layouts may replace it with a character portrait, while the yellow G.M.
    exit icon at the top left remains stable.
    """
    if detector.appear(legacy_check, offset=ORDER_CHECK_OFFSET):
        return True

    return detector.image_color_count(
        ORDER_GMS_EXIT_AREA,
        color=ORDER_GMS_EXIT_COLOR,
        threshold=ORDER_GMS_EXIT_SIMILARITY,
        count=ORDER_GMS_EXIT_PIXEL_COUNT,
    )
