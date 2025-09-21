import pathlib


def test_no_legacy_paths():
    # no legacy tests tree
    assert not (
        pathlib.Path("tests").exists()
    ), "Legacy 'tests/' dir found; use 'addon/tests/'."


def test_canonical_verify_discovery():
    # verify_discovery.py only under addon/bb8_core
    dupes = [p.as_posix() for p in pathlib.Path().rglob("verify_discovery.py")]
    assert (
        dupes.count("addon/bb8_core/verify_discovery.py") == 1
    ), f"Missing canonical: {dupes}"
    others = [d for d in dupes if d != "addon/bb8_core/verify_discovery.py"]
    assert not others, f"Duplicates present: {others}"
