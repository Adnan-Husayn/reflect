"""GAD-7.

The seven-item generalised anxiety scale, scored the same way as PHQ-8: each
item 0 to 3, totalled. It carries no item comparable to PHQ-9's ninth, so
there is no equivalent exclusion to make here.

The same rule as PHQ-8 applies: **no severity bands.** The score is shown and
plotted; it is never mapped onto a category or a cutpoint.
"""

from app.instruments.phq8 import Instrument, Item, Option

GAD7 = Instrument(
    code="GAD-7",
    name="Generalised Anxiety Disorder-7",
    prompt="Over the last 2 weeks, how often have you been bothered by the following problems?",
    items=(
        Item("q1", "Feeling nervous, anxious, or on edge"),
        Item("q2", "Not being able to stop or control worrying"),
        Item("q3", "Worrying too much about different things"),
        Item("q4", "Trouble relaxing"),
        Item("q5", "Being so restless that it is hard to sit still"),
        Item("q6", "Becoming easily annoyed or irritable"),
        Item("q7", "Feeling afraid, as if something awful might happen"),
    ),
    options=(
        Option(0, "Not at all"),
        Option(1, "Several days"),
        Option(2, "More than half the days"),
        Option(3, "Nearly every day"),
    ),
)
