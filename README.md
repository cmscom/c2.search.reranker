# c2.search.reranker

A Plone addon that reranks search results using content type boost weighting and half-life time decay.

[Japanese / 日本語](README-ja.md)

## Features

### Content Type Boost Weighting

Assign content types to groups (General Pages, Announcements, Knowledge, Other) and configure a boost multiplier for each group. Content types with a higher boost value appear higher in search results.

### Half-life Time Decay

Each group has a configurable half-life (in days). Older content gradually loses relevance based on an exponential decay formula:

```
decay = 0.5 ^ (age_in_days / halflife_days)
```

### Vector Search Integration (Optional)

When `collective.vectorsearch` is installed, keyword search and vector search (semantic similarity) can be combined. The keyword/vector ratio is configurable (e.g. 50% keyword / 50% vector).

### Control Panel

All settings are configurable through the Plone control panel (Site Setup > Search Reranker Settings) and the REST API (`@controlpanels/reranker`).

### Browser Views for Testing

Two test views are available for debugging and comparing search results:

- `@@reranker-search?SearchableText=keyword` — Keyword-only reranking with score details
- `@@hybrid-search?SearchableText=keyword` — Hybrid search (keyword + vector) with all score breakdowns

### REST API Summary Serializer

Extends plone.restapi listing responses with additional metadata fields: `image_field`, `image_scales`, `effective`, and `Subject`.

## Scoring Algorithm

This addon provides three scoring patterns. In all patterns, **boost** and **decay** are applied as the final step after the base relevance score is calculated.

### Pattern 1: Keyword Only (without vector search)

When vector search is disabled or `collective.vectorsearch` is not installed:

```
final_score = original_score * boost * decay
```

- `original_score`: Relevance score from ZCTextIndex (`data_record_normalized_score_`)
- `boost`: Content type group multiplier (configurable per group, default 1.0)
- `decay`: Time decay factor `0.5 ^ (age_in_days / halflife_days)` (configurable per group, default halflife 60 days)

### Pattern 2: Hybrid — Score Mode (Weighted Average)

Combines keyword and vector search using normalized scores:

```
keyword_score  = normalized ZCTextIndex score (0.0 - 1.0)
vector_score   = cosine similarity from VectorIndex (0.0 - 1.0)
combined_score = keyword_score * keyword_weight + vector_score * vector_weight
final_score    = combined_score * boost * decay
```

- Keyword scores are normalized by dividing by the maximum score in the result set
- `keyword_weight = keyword_search_ratio / 100` (configurable, default 50%)
- `vector_weight = 1.0 - keyword_weight`
- Results found by only one method get 0.0 for the missing score

### Pattern 3: Hybrid — RRF Mode (Reciprocal Rank Fusion) [Default]

Combines keyword and vector search using rank positions instead of raw scores. This is robust against score scale differences between the two search methods.

```
keyword_rrf    = 1 / (k + keyword_rank)
vector_rrf     = 1 / (k + vector_rank)
combined_score = keyword_rrf * keyword_weight + vector_rrf * vector_weight
final_score    = combined_score * boost * decay
```

- `k = 60` (constant to prevent top-ranked items from dominating)
- Ranks are assigned by sorting each result set by its own score (1 = best)
- Results found by only one method get `rrf = 0.0` for the missing search
- `keyword_weight` and `vector_weight` are the same as in Score mode

### Scoring Pipeline Summary

```
Step 1: Execute keyword search (always)
Step 2: Execute vector search (if enabled and available)
Step 3: Combine scores (Score mode or RRF mode)
Step 4: Apply boost * decay to get final_score
Step 5: Sort by final_score descending
```

## Requirements

- Python 3.10 - 3.13
- Plone 6.0 or 6.1

## Installation

Install c2.search.reranker with `pip`:

```shell
pip install c2.search.reranker
```

Then install the addon from **Site Setup > Add-ons** in your Plone site.

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- [Make](https://www.gnu.org/software/make/)
- [Git](https://git-scm.com/)

### Setup

```shell
git clone git@github.com:terapyon/c2.search.reranker.git
cd c2.search.reranker
make install
```

### Common Commands

```shell
make test           # Run tests
make format         # Format code
make lint           # Run linter checks
make i18n           # Update locale files
make start          # Start Plone instance on localhost:8080
make create-site    # Create a new Plone site
```

### Tools

- **Linter / Formatter**: [ruff](https://docs.astral.sh/ruff/)
- **Tests**: [pytest](https://docs.pytest.org/)
- **Build**: [hatchling](https://hatch.pypa.io/)

## Contribute

- [Issue tracker](https://github.com/terapyon/c2.search.reranker/issues)
- [Source code](https://github.com/terapyon/c2.search.reranker/)

## License

This project is licensed under the [GPL-2.0-only](https://spdx.org/licenses/GPL-2.0-only.html).
