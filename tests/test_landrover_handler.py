from sbm.oem.factory import OEMFactory
from sbm.oem.landrover import LandRoverHandler


def test_landrover_handler_detection():
    # Test that the Land Rover handler is correctly detected
    slug = "germainlandrover"
    handler = OEMFactory.detect_from_theme(slug)
    assert isinstance(handler, LandRoverHandler)


def test_landrover_handler_no_styles():
    # Test that map and directions styles are empty and not forced
    handler = LandRoverHandler("germainlandrover")
    assert handler.get_map_styles() == ""
    assert handler.get_directions_styles() == ""
    assert not handler.should_force_map_migration()


def test_landrover_map_partials():
    # Test that the patterns correctly resolve Land Rover specific partials
    handler = LandRoverHandler("germainlandrover")
    patterns = handler.get_map_partial_patterns()
    assert r"dealer-groups/landrover/map-row" in patterns
    assert r"dealer-groups/landrover/directions-row" in patterns
    assert r"dealer-groups/landrover/location" in patterns


def test_landrover_brand_match():
    # Test that brand detection covers landrover variations
    handler = LandRoverHandler("germainlandrover")
    brand_patterns = handler.get_brand_match_patterns()
    assert r"landrover" in brand_patterns
    assert r"land-rover" in brand_patterns
    assert r"land_rover" in brand_patterns


def test_landrover_factory_dealer_info():
    # Test that OEMFactory routes correctly using dealer_info brand field
    handler = OEMFactory.create_handler("unknown", dealer_info={"brand": "Land Rover"})
    assert isinstance(handler, LandRoverHandler)


def test_landrover_predetermined_style_configs():
    handler = LandRoverHandler("germainlandrover")
    configs = handler.get_predetermined_inside_style_configs()

    assert len(configs) == 2
    assert any(c["label"] == "Land Rover Inside Pages Styles" for c in configs)
    assert any(c["label"] == "Land Rover National Offers Styles" for c in configs)
