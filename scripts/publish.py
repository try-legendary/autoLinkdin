
"""Publish a post to Buffer via their GraphQL API (stdlib only)."""

import json
import urllib.error
import urllib.request

BUFFER_API = "https://api.buffer.com"
HTTP_TIMEOUT = 30

CREATE_POST_MUTATION = """
mutation CreatePost {
  createPost(input: {
    text: %s
    channelId: %s
    schedulingType: automatic
    mode: addToQueue
  }) {
    ... on PostActionSuccess {
      post { id dueAt }
    }
    ... on MutationError {
      message
    }
  }
}
"""


def graphql(api_key, query, variables=None, timeout=HTTP_TIMEOUT,
            transport=None):
    """Run a GraphQL query, optionally using a mock transport."""
    if transport is not None:
        body = transport(api_key, query)
    else:
        payload = {"query": query}
        if variables is not None:
            payload["variables"] = variables

        req = urllib.request.Request(
            BUFFER_API,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "daily-tech-post/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(
                f"Buffer API HTTP {exc.code}: {detail}"
            ) from exc

    if body.get("errors"):
        raise RuntimeError(f"Buffer GraphQL error: {body['errors']}")
    return body.get("data")


def create_post(api_key, channel_id, text, transport=None):
    """Queue a text post on the given channel."""
    mutation = CREATE_POST_MUTATION % (
        json.dumps(text, ensure_ascii=False),
        json.dumps(channel_id),
    )

    data = graphql(
        api_key,
        mutation,
        transport=transport,
    )

    if data is None or data.get("createPost") is None:
        raise RuntimeError(f"unexpected Buffer response: {data}")

    result = data["createPost"]
    if result.get("post"):
        return result["post"]

    message = result.get("message", "unknown Buffer error")
    raise RuntimeError(f"Buffer rejected the post: {message}")
