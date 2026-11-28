# Phase 4 data and cache decisions

Verdicts depend on the idea, student, profile version, rubric version and engine version. M2 incorporates all five into each verdict cache key. Retrieval depends on the query, filters and knowledge-base version. Both kinds expire after one hour. Cache reads expose the result in the response and run trace.

The snapshot uses public Hacker News stories, crates.io packages and RubyGems package descriptions. GitHub's robots check denied collection during this run. Product Hunt and Reddit require credentials. Those three schedules start suspended. The API and CLI support all six sources.

M6i uses 512-dimensional signed feature hashing for an offline, deterministic baseline. Its cosine similarity measures token overlap. The index stores citation IDs alongside Qdrant-compatible UUIDs. Similarity of at least 0.92 flags a review candidate. Canonical URLs and normalized names control exact deduplication. The later retrieval phase evaluates relevance.

Collection references include the [HN Search API](https://hn.algolia.com/api), [crates.io data-access policy](https://crates.io/policies/data-access) and [RubyGems API](https://guides.rubygems.org/rubygems-org-api/).
