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

### Combined Scoring

The final score is calculated as:

```
final_score = original_score * boost * decay
```

Where `original_score` is the relevance score from ZCTextIndex.

### Control Panel

All settings are configurable through the Plone control panel (Site Setup > Search Reranker Settings) and the REST API (`@controlpanels/reranker`).

### Vector Search Integration (Planned)

The control panel includes settings for optional vector search integration via `collective.vectorsearch`, with a configurable keyword/vector search ratio. This feature is planned for a future release.

### Browser View for Testing

A test view is available at `@@reranker-search?SearchableText=keyword` that displays reranked results with detailed score breakdowns (original score, boost, decay, final score).

### REST API Summary Serializer

Extends plone.restapi listing responses with additional metadata fields: `image_field`, `image_scales`, `effective`, and `Subject`.

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
