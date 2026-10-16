"""In-memory fake of the Buffer GraphQL API, for offline end-to-end testing.

Used by `run.py --test` and `buffer_channels.py --mock` so the whole pipeline
can be exercised - including the publish step - without a Buffer account or
network access.
"""

from datetime import datetime, timedelta, timezone

MOCK_ORGANIZATIONS = [{"id": "mock_org_1", "name": "Mock Workspace"}]

MOCK_CHANNELS = [
    {
        "id": "mock_linkedin_channel",
        "name": "you",
        "displayName": "You (LinkedIn)",
        "service": "linkedin",
        "isQueuePaused": False,
    },
    {
        "id": "mock_facebook_page",
        "name": "My Page",
        "displayName": "My Page (Facebook)",
        "service": "facebook",
        "isQueuePaused": False,
    },
]

BAD_KEYS = {"", "invalid", "bad", "wrong", "test"}


class MockBufferTransport:
    """Drop-in replacement for the real HTTP transport in publish.graphql."""

    def __init__(self, api_key="mock_api_key", verbose=True):
        self.api_key = api_key
        self.verbose = verbose
        self.queries = []
        self.api_calls = 0

    def __call__(self, api_key, query):
        self.queries.append(query)
        self.api_calls += 1
        if self.verbose:
            first_line = query.strip().splitlines()[0] if query.strip() else query
            print(f"  [mock buffer] call #{self.api_calls}: {first_line}")

        if api_key in BAD_KEYS:
            return {"errors": [{"message": "Invalid API key (mock)"}]}

        if "organizations" in query:
            return {"data": {"account": {"organizations": MOCK_ORGANIZATIONS}}}
        if "channels(" in query:
            return {"data": {"channels": MOCK_CHANNELS}}
        if "createPost" in query:
            due_at = datetime.now(timezone.utc) + timedelta(hours=1)
            return {
                "data": {
                    "createPost": {
                        "post": {
                            "id": "mock_post_20261016",
                            "dueAt": due_at.isoformat(timespec="seconds").replace(
                                "+00:00", "Z"
                            ),
                        }
                    }
                }
            }
        return {"errors": [{"message": f"mock got an unexpected query: {query[:80]!r}"}]}
