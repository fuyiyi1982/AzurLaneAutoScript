ZONE_OBSCURE_SIMILARITY = 0.80
ZONE_OBSCURE_COLOR_THRESHOLD = 10
ZONE_TYPE_OFFSET = (20, 20)


def match_pinned_zone(detector, zone, obscure_zone):
    """
    Match a zone title on the globe.

    A 2560x1440 screenshot is downsampled before recognition. This changes
    the anti-aliasing of ZONE_OBSCURE enough to miss the default 0.85
    template threshold, so only that title uses a relaxed threshold paired
    with a strict color check.
    """
    if zone == obscure_zone:
        return detector.match_template_color(
            zone,
            offset=ZONE_TYPE_OFFSET,
            similarity=ZONE_OBSCURE_SIMILARITY,
            threshold=ZONE_OBSCURE_COLOR_THRESHOLD,
        )

    return detector.appear(zone, offset=ZONE_TYPE_OFFSET)
