from purplelab import atomics


def test_load_techniques_nonempty():
    techniques = atomics.load_techniques()
    assert len(techniques) > 0
    assert all(t.id.startswith("T") for t in techniques)


def test_get_technique_known_id():
    t = atomics.get_technique("T1053.003")
    assert t is not None
    assert t.tactic == "persistence"


def test_get_technique_unknown_id_returns_none():
    assert atomics.get_technique("T9999.999") is None


def test_pick_uncovered_skips_covered_ids():
    techniques = atomics.load_techniques()
    first_two = {techniques[0].id, techniques[1].id}
    picked = atomics.pick_uncovered(covered_ids=first_two)
    assert picked.id == techniques[2].id


def test_pick_uncovered_respects_tactic_filter():
    picked = atomics.pick_uncovered(covered_ids=set(), tactic="discovery")
    assert picked is not None
    assert picked.tactic == "discovery"


def test_pick_uncovered_returns_none_when_all_covered():
    all_ids = {t.id for t in atomics.load_techniques()}
    assert atomics.pick_uncovered(covered_ids=all_ids) is None
