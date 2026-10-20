
"""Publish a post to Buffer via their GraphQL API (stdlib only)."""

import json
import urllib.error
import urllib.request

BUFFER_API = "https://api.buffer.com"
HTTP_TIMEOUT = 30

CREATE_POST_MUTATION = """
mutation CreatePost {
  createPost(input: __POST_INPUT__) {
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


def _graphql_literal(value):
    """Render Python data as a GraphQL literal."""
    if isinstance(value, dict):
        fields = ", ".join(f"{key}: {_graphql_literal(val)}"
                           for key, val in value.items())
        return "{" + fields + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_graphql_literal(item) for item in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def create_post(api_key, channel_id, text, transport=None):
    """Queue a text post on the given channel."""
    post_input = {
        "text": text,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
    }

    query = CREATE_POST_MUTATION.replace("__POST_INPUT__",
                                         _graphql_literal(post_input))
    data = graphql(api_key, query, transport=transport)

    if data is None or data.get("createPost") is None:
        raise RuntimeError(f"unexpected Buffer response: {data}")

    result = data["createPost"]
    if result.get("post"):
        return result["post"]

    message = result.get("message", "unknown Buffer error")
    raise RuntimeError(f"Buffer rejected the post: {message}")
