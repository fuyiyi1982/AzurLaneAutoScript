from module.base.timer import Timer

DAILY_CHECK_OFFSET = (30, 30)
DAILY_LEFT_ARROW_AREA = (20, 328, 58, 392)
DAILY_RIGHT_ARROW_AREA = (1222, 328, 1260, 392)
DAILY_ARROW_COLOR = (255, 255, 255)
DAILY_ARROW_THRESHOLD = 25
DAILY_ARROW_PIXEL_COUNT = 300


def is_daily_page(detector, legacy_check, back_check, offset=DAILY_CHECK_OFFSET, interval=0):
    """
    Detect the Daily Raid carousel page across old and new game layouts.

    The legacy layout checks the blue information icon at the bottom left.
    Newer layouts or overlays may cover that corner with a character portrait,
    while the top-left back arrow and left/right carousel arrows remain stable
    on the carousel and disappear inside the stage selection sub-panel.
    """
    timer = None
    if interval and hasattr(detector, 'interval_timer'):
        key = getattr(legacy_check, 'name', str(legacy_check))
        if key in detector.interval_timer and detector.interval_timer[key].limit == interval:
            timer = detector.interval_timer[key]
        else:
            timer = Timer(interval)
            detector.interval_timer[key] = timer
        if not timer.reached():
            return False

    if detector.appear(legacy_check, offset=offset):
        if timer is not None:
            timer.reset()
        return True

    appear = (
        detector.image_color_count(
            DAILY_LEFT_ARROW_AREA,
            color=DAILY_ARROW_COLOR,
            threshold=DAILY_ARROW_THRESHOLD,
            count=DAILY_ARROW_PIXEL_COUNT,
        )
        and detector.image_color_count(
            DAILY_RIGHT_ARROW_AREA,
            color=DAILY_ARROW_COLOR,
            threshold=DAILY_ARROW_THRESHOLD,
            count=DAILY_ARROW_PIXEL_COUNT,
        )
        and detector.appear(back_check, offset=offset)
    )
    if appear and timer is not None:
        timer.reset()
    return appear
