ZONE_TYPE_SIMILARITY = 0.70
ZONE_TYPE_COLOR_THRESHOLD = 30
ZONE_TYPE_OFFSET = (20, 20)


def match_pinned_zone(detector, zone):
    """
    Match a zone title on the globe.

    A 2560x1440 screenshot is downsampled before recognition. This changes
    the anti-aliasing of zone titles enough to miss the default template
    threshold. Use a locally relaxed template threshold paired with a
    conservative color check for every zone type.
    """
    return detector.match_template_color(
        zone,
        offset=ZONE_TYPE_OFFSET,
        similarity=ZONE_TYPE_SIMILARITY,
        threshold=ZONE_TYPE_COLOR_THRESHOLD,
    )
