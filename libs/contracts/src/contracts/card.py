from datetime import date, datetime

from pydantic import HttpUrl, NonNegativeFloat

from .common import Record, Text


class Card(Record):
    id: Text
    name: Text
    summary: Text
    problem: Text
    customer: Text
    niche_tags: list[Text]
    stage: Text
    funding_usd: NonNegativeFloat | None
    source: Text
    url: HttpUrl
    published_at: date | datetime | None
    fetched_at: date | datetime
    text: Text
