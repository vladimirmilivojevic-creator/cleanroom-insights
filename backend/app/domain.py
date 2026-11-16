"""Training content and scoring rules.

Two VR modules, inspired by EU GMP Annex 1 (cleanroom gowning and aseptic behaviour
in a Grade A zone). Scoring is deliberately simple and explainable:

    score  = 100 - sum of deviation penalties (never below 0)
    passed = score >= 80 and no critical deviation

A step that was never completed counts as a critical "skipped_step" deviation.
"""

from dataclasses import dataclass

SEVERITY_PENALTY = {"minor": 3, "major": 10, "critical": 25}
PASS_SCORE = 80


@dataclass(frozen=True)
class Step:
    code: str
    title: str


@dataclass(frozen=True)
class Deviation:
    code: str
    title: str
    severity: str  # minor | major | critical


@dataclass(frozen=True)
class Module:
    code: str
    title: str
    description: str
    steps: tuple[Step, ...]
    deviations: tuple[str, ...]  # deviation codes that can happen in this module

    def has_step(self, code: str) -> bool:
        return any(step.code == code for step in self.steps)


DEVIATIONS: dict[str, Deviation] = {
    d.code: d
    for d in (
        Deviation("fast_movement", "Fast movement (air turbulence)", "minor"),
        Deviation("leaning_on_surface", "Leaning on a surface", "minor"),
        Deviation("wrong_order", "Step done in the wrong order", "major"),
        Deviation("touched_floor", "Garment touched the floor", "major"),
        Deviation("touched_non_sterile", "Touched a non-sterile surface", "major"),
        Deviation("overreaching", "Reaching over open product", "major"),
        Deviation("first_air_blocked", "First air blocked (hand above open container)", "critical"),
        Deviation("skipped_step", "Step skipped", "critical"),
    )
}

MODULES: dict[str, Module] = {
    m.code: m
    for m in (
        Module(
            code="gowning",
            title="Grade B gowning",
            description="Correct gowning sequence before entering a Grade B cleanroom.",
            steps=(
                Step("hand_disinfection", "Disinfect hands"),
                Step("cleanroom_shoes", "Change shoes over the cross-over bench"),
                Step("hood", "Put on sterile hood"),
                Step("face_mask", "Put on face mask"),
                Step("coverall", "Put on sterile coverall"),
                Step("overboots", "Put on sterile overboots"),
                Step("goggles", "Put on goggles"),
                Step("gloves", "Put on sterile gloves"),
                Step("mirror_check", "Check the gown in the mirror"),
            ),
            deviations=(
                "fast_movement",
                "leaning_on_surface",
                "wrong_order",
                "touched_floor",
                "touched_non_sterile",
            ),
        ),
        Module(
            code="aseptic_intervention",
            title="Aseptic intervention (Grade A)",
            description="Clearing a stopper jam on a filling line inside a RABS.",
            steps=(
                Step("glove_disinfection", "Disinfect gloves"),
                Step("prepare_tool", "Take the sterile tool"),
                Step("approach_line", "Approach the filling line slowly"),
                Step("clear_stopper_jam", "Clear the stopper jam"),
                Step("remove_tool", "Remove and discard the tool"),
                Step("environmental_monitoring", "Take a contact plate sample"),
                Step("document_intervention", "Document the intervention"),
            ),
            deviations=(
                "fast_movement",
                "overreaching",
                "touched_non_sterile",
                "first_air_blocked",
            ),
        ),
    )
}


@dataclass(frozen=True)
class Evaluation:
    missing_steps: list[str]
    score: int
    passed: bool


def evaluate(module: Module, completed_steps: set[str], severities: list[str]) -> Evaluation:
    """Score a session from its completed steps and the severities of its deviations."""
    missing = [step.code for step in module.steps if step.code not in completed_steps]
    all_severities = severities + ["critical"] * len(missing)

    score = max(0, 100 - sum(SEVERITY_PENALTY[s] for s in all_severities))
    passed = score >= PASS_SCORE and "critical" not in all_severities
    return Evaluation(missing_steps=missing, score=score, passed=passed)
