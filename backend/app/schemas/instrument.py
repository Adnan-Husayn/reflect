from pydantic import BaseModel


class ItemOut(BaseModel):
    id: str
    text: str


class OptionOut(BaseModel):
    value: int
    label: str


class InstrumentOut(BaseModel):
    """No severity bands are returned, by design.

    The score and its maximum are enough to render the form and plot the
    series. Mapping a total onto "mild" or "moderately severe" would be a
    clinical interpretation the project does not make.
    """

    code: str
    name: str
    prompt: str
    max_score: int
    items: list[ItemOut]
    options: list[OptionOut]
