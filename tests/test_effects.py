import sys
sys.path.insert(0, '.')
from systems.effects import Effect, EffectManager


def test_spawn():
    em = EffectManager()
    em.spawn("slash", 5, 5, "/", duration=1)
    active = em.active()
    assert len(active) == 1
    eff = active[0]
    assert eff.kind == "slash" and eff.x == 5 and eff.y == 5 and eff.char == "/"
    assert eff.age == 0 and eff.duration == 1


def test_update_expires_duration_1():
    em = EffectManager()
    em.spawn("text", 1, 2, "MISS", duration=1)
    assert len(em.active()) == 1
    em.update()
    assert len(em.active()) == 0


def test_update_multi_duration():
    em = EffectManager()
    em.spawn("text", 1, 2, "CRIT", duration=2)
    em.update()
    assert len(em.active()) == 1
    em.update()
    assert len(em.active()) == 0


def test_clear():
    em = EffectManager()
    em.spawn("slash", 0, 0, "*", duration=5)
    em.clear()
    assert len(em.active()) == 0


def test_multiple_effects_independent_duration():
    em = EffectManager()
    em.spawn("slash", 0, 0, "/", duration=1)
    em.spawn("text", 1, 1, "+5", duration=2)
    em.update()
    active = em.active()
    assert len(active) == 1
    assert active[0].char == "+5"


if __name__ == "__main__":
    test_spawn()
    test_update_expires_duration_1()
    test_update_multi_duration()
    test_clear()
    test_multiple_effects_independent_duration()
    print("test_effects.py: all passed")
