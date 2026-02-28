from pathlib import Path

from sbm.core import migration
from sbm.oem.landrover import LandRoverHandler


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _setup_theme(tmp_path: Path, slug: str) -> Path:
    theme_dir = tmp_path / "dealer-themes" / slug
    _write(theme_dir / "sb-inside.scss", "/* base */\n")
    return theme_dir


def _setup_common_theme(tmp_path: Path) -> Path:
    common = tmp_path / "common-theme"
    _write(
        common / "css/dealer-groups/landrover/_inside-pages-v2.scss",
        "#cpo-offers { color: red; }\n.offer-disclaimer { color: red; }\n",
    )
    _write(
        common / "css/dealer-groups/landrover/_inside-pages.scss",
        "#cpo-offers { color: green; }\n",
    )
    _write(
        common / "css/dealer-inspire-plugins/_national-offers.scss",
        ".national-incentive-offers { color: blue; }\n",
    )
    return common


def test_landrover_predetermined_styles_append_v2_and_national(tmp_path, monkeypatch):
    slug = "landroverreno"
    theme_dir = _setup_theme(tmp_path, slug)
    common = _setup_common_theme(tmp_path)

    _write(
        theme_dir / "css/inside.scss",
        "@import '../../DealerInspireCommonTheme/css/dealer-groups/landrover/_inside-pages-v2.scss';\n",
    )
    _write(
        theme_dir / "css/style.scss",
        "// @import '../../DealerInspireCommonTheme/css/dealer-inspire-plugins/_national-offers.scss';\n",
    )

    monkeypatch.setattr(migration, "get_dealer_theme_dir", lambda _: str(theme_dir))
    monkeypatch.setattr(migration, "get_common_theme_path", lambda: str(common))

    assert migration.add_predetermined_styles(slug, LandRoverHandler(slug))

    content = (theme_dir / "sb-inside.scss").read_text(encoding="utf-8")
    assert "Land Rover Inside Pages Styles" in content
    assert "#cpo-offers" in content
    assert "Land Rover National Offers Styles" in content
    assert ".national-incentive-offers" in content


def test_landrover_predetermined_styles_no_duplicate_on_rerun(tmp_path, monkeypatch):
    slug = "landroverreno"
    theme_dir = _setup_theme(tmp_path, slug)
    common = _setup_common_theme(tmp_path)

    _write(
        theme_dir / "css/inside.scss",
        "@import '../../DealerInspireCommonTheme/css/dealer-groups/landrover/_inside-pages-v2.scss';\n",
    )
    _write(
        theme_dir / "css/style.scss",
        "// @import '../../DealerInspireCommonTheme/css/dealer-inspire-plugins/_national-offers.scss';\n",
    )

    monkeypatch.setattr(migration, "get_dealer_theme_dir", lambda _: str(theme_dir))
    monkeypatch.setattr(migration, "get_common_theme_path", lambda: str(common))

    assert migration.add_predetermined_styles(slug, LandRoverHandler(slug))
    assert migration.add_predetermined_styles(slug, LandRoverHandler(slug))

    content = (theme_dir / "sb-inside.scss").read_text(encoding="utf-8")
    assert content.count("Land Rover Inside Pages Styles") == 1
    assert content.count("Land Rover National Offers Styles") == 1


def test_landrover_predetermined_styles_fallback_to_legacy_inside(tmp_path, monkeypatch):
    slug = "landroverreno"
    theme_dir = _setup_theme(tmp_path, slug)
    common = _setup_common_theme(tmp_path)

    # Remove v2 partial to force fallback.
    (common / "css/dealer-groups/landrover/_inside-pages-v2.scss").unlink()

    _write(
        theme_dir / "css/inside.scss",
        "@import '../../DealerInspireCommonTheme/css/dealer-groups/landrover/_inside-pages.scss';\n",
    )
    _write(theme_dir / "css/style.scss", "/* none */\n")

    monkeypatch.setattr(migration, "get_dealer_theme_dir", lambda _: str(theme_dir))
    monkeypatch.setattr(migration, "get_common_theme_path", lambda: str(common))

    assert migration.add_predetermined_styles(slug, LandRoverHandler(slug))

    content = (theme_dir / "sb-inside.scss").read_text(encoding="utf-8")
    assert "Land Rover Inside Pages Styles" in content
    assert "#cpo-offers { color: green; }" in content
