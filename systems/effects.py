"""V1 visual effects system: SLASH + TEXT only. Pure logic, no curses here.
Effect.char must stay ASCII only in V1 ('/', '\\', '*', '!', '+5', 'CRIT', 'MISS')
because _draw_map_row() indexes columns by char count, not display width,
and CJK would break that. That bug is tracked separately and not fixed here.
"""
from dataclasses import dataclass


@dataclass
class Effect:
    kind: str
    x: int
    y: int
    char: str
    age: int = 0
    duration: int = 1


class EffectManager:
    """Holds currently-alive effects for one Game instance."""

    def __init__(self):
        self._effects = []

    def spawn(self, kind, x, y, char, duration=1):
        # NOTE: duration counts update() calls, not real turns.
        # update() is called at the start of advance_turn(), which runs
        # in the SAME input cycle as the action that spawns the effect
        # (spawn happens before advance_turn, in the same handle_input call).
        # So an effect born this cycle gets aged once before the next
        # render(). duration=1 means it never survives to be drawn.
        # Use duration=2 for "visible for one render, gone on next action".
        self._effects.append(
            Effect(kind=kind, x=x, y=y, char=char, age=0, duration=duration))

    def update(self):
        """Call once per turn (end of advance_turn). Ages all effects,
        drops expired ones."""
        still_alive = []
        for eff in self._effects:
            eff.age += 1
            if eff.age < eff.duration:
                still_alive.append(eff)
        self._effects = still_alive

    def active(self):
        """Read-only snapshot for the renderer."""
        return list(self._effects)

    def clear(self):
        """Empty the list without replacing the manager object itself."""
        self._effects.clear()
