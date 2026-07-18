ZONE_TYPE_SIMILARITY = 0.80
ZONE_TYPE_COLOR_THRESHOLD = 20
ZONE_TYPE_OFFSET = (20, 20)


def match_pinned_zone(detector, zone):
    """
    Match a zone title on the globe.

    A 2560x1440 screenshot is downsampled before recognition. This changes
    the anti-aliasing of zone titles enough to miss the default 0.85
    template threshold. Use a slightly relaxed template threshold paired
    with a conservative color check for every zone type.
    """
    return detector.match_template_color(
        zone,
        offset=ZONE_TYPE_OFFSET,
        similarity=ZONE_TYPE_SIMILARITY,
        threshold=ZONE_TYPE_COLOR_THRESHOLD,
    )
