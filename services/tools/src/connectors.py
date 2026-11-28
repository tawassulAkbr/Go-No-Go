"""Translate validated connector parameters to fixed public API operations."""

import os
import re
from dataclasses import dataclass, field

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Literal


class Params(BaseModel):
    operation: Literal["search", "get", "topstories", "newstories"] = "search"
    query: str = Field(default="", max_length=256)
    page: int = Field(default=0, ge=0, le=999)
    size: int = Field(default=50, ge=1, le=100)
    id: str = Field(default="", max_length=200)
    cursor: str | None = Field(default=None, max_length=512)
    kind: Literal["repositories", "issues"] = "repositories"


@dataclass
class Request:
    url: str
    headers: dict = field(default_factory=dict)
    body: dict | None = None


def query(url, **params):
    return str(httpx.URL(url, params=params))


def identifier(value, pattern):
    if not re.fullmatch(pattern, value):
        raise HTTPException(422, "Invalid source identifier")
    return value


def bearer(key, optional=False):
    if token := os.getenv(key):
        return {"Authorization": "Bearer " + token}
    if optional:
        return {}
    raise HTTPException(503, "Source credentials unavailable")


def item(name, summary, url, date=None, tags=()):
    return {
        "name": name,
        "summary": summary or name,
        "url": url,
        "published_at": date,
        "niche_tags": list(tags or []),
    }


class HackerNews:
    def search(self, p):
        return Request(
            query(
                "https://hn.algolia.com/api/v1/search",
                query=p.query or "Show HN",
                tags="story",
                page=p.page,
                hitsPerPage=p.size,
            )
        )

    def get(self, p):
        path = (
            p.operation
            if p.operation in ("topstories", "newstories")
            else "item/" + identifier(p.id, r"[0-9]+")
        )
        return Request(f"https://hacker-news.firebaseio.com/v0/{path}.json")

    def results(self, data):
        return [
            item(
                r["title"],
                r.get("story_text"),
                r.get("url") or "https://news.ycombinator.com/item?id=" + r["objectID"],
                r["created_at"],
            )
            for r in data["hits"]
            if r.get("title")
        ], None


class GitHub:
    def search(self, p):
        return Request(
            query(
                "https://api.github.com/search/" + p.kind,
                q=(p.query or "topic:developer-tools") + " is:public",
                page=p.page + 1,
                per_page=p.size,
            ),
            bearer("GITHUB_TOKEN", True),
        )

    def get(self, p):
        path = identifier(p.id, r"[\w-]+/[\w.-]+(?:/issues/[0-9]+)?")
        return Request(
            "https://api.github.com/repos/" + path, bearer("GITHUB_TOKEN", True)
        )

    def results(self, data):
        return [
            item(
                r.get("name") or r.get("title"),
                r.get("description") or r.get("body"),
                r["html_url"],
                r["created_at"],
                r.get("topics"),
            )
            for r in data["items"]
            if not r.get("private")
        ], None


class ProductHunt:
    fields = "name tagline website createdAt"

    def request(self, statement, variables):
        return Request(
            "https://api.producthunt.com/v2/api/graphql",
            bearer("PRODUCTHUNT_TOKEN"),
            {"query": statement, "variables": variables},
        )

    def search(self, p):
        return self.request(
            "query($n:Int!,$after:String,$topic:String){posts(first:$n,after:$after,topic:$topic){nodes{"
            + self.fields
            + "} pageInfo{endCursor hasNextPage}}}",
            {"n": min(20, p.size), "after": p.cursor, "topic": p.query or None},
        )

    def get(self, p):
        return self.request(
            "query($id:ID!){post(id:$id){" + self.fields + "}}", {"id": p.id}
        )

    def results(self, data):
        posts = data["data"]["posts"]
        info = posts["pageInfo"]
        return [
            item(r["name"], r["tagline"], r["website"], r["createdAt"])
            for r in posts["nodes"]
        ], info["endCursor"] if info["hasNextPage"] else None


class Reddit:
    def search(self, p):
        return Request(
            query(
                "https://oauth.reddit.com/search",
                q=p.query or "alternative to",
                limit=p.size,
                after=p.cursor or "",
                type="link",
            ),
            bearer("REDDIT_ACCESS_TOKEN"),
        )

    def get(self, p):
        return Request(
            "https://oauth.reddit.com/comments/" + identifier(p.id, r"[a-z0-9]+"),
            bearer("REDDIT_ACCESS_TOKEN"),
        )

    def results(self, data):
        from datetime import datetime, timezone

        rows = [c["data"] for c in data["data"]["children"]]
        return [
            item(
                r["title"],
                r.get("selftext"),
                "https://www.reddit.com" + r["permalink"],
                datetime.fromtimestamp(r["created_utc"], timezone.utc).isoformat(),
            )
            for r in rows
        ], data["data"]["after"]


class Crates:
    def search(self, p):
        return Request(
            query(
                "https://crates.io/api/v1/crates",
                q=p.query,
                page=p.page + 1,
                per_page=p.size,
                sort="downloads",
            )
        )

    def get(self, p):
        return Request("https://crates.io/api/v1/crates/" + identifier(p.id, r"[\w-]+"))

    def results(self, data):
        return [
            item(
                r["name"],
                r["description"],
                "https://crates.io/crates/" + r["id"],
                r["created_at"],
            )
            for r in data["crates"]
        ], None


class RubyGems:
    def search(self, p):
        return Request(
            query(
                "https://rubygems.org/api/v1/search.json",
                query=p.query or "api",
                page=p.page + 1,
            )
        )

    def get(self, p):
        return Request(
            "https://rubygems.org/api/v1/gems/" + identifier(p.id, r"[\w.-]+") + ".json"
        )

    def results(self, data):
        return [
            item(r["name"], r["info"], r["project_uri"], r.get("version_created_at"))
            for r in data
        ], None


CONNECTORS = {
    "rubygems": RubyGems(),
    "hn": HackerNews(),
    "github": GitHub(),
    "producthunt": ProductHunt(),
    "reddit": Reddit(),
    "crates": Crates(),
}
