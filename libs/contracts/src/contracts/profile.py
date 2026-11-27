from typing import Literal

from pydantic import PositiveInt

from .common import Record, Text


class Profile(Record):
    user_id: Text
    skills: list[Text]
    hours_per_week: PositiveInt
    weeks_available: PositiveInt
    team_size: PositiveInt
    compute: Literal["laptop", "free_gpu", "paid"]
    goal: Literal["startup", "portfolio", "course_project"]
    interests: list[Text]
