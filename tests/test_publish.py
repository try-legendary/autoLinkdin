import unittest

from scripts.publish import _graphql_literal, create_post


class TestPublish(unittest.TestCase):
    def test_graphql_literal_uses_unquoted_field_names(self):
        literal = _graphql_literal(
            {"text": "Hello", "channelId": "chan_123", "mode": "addToQueue"}
        )

        self.assertEqual(
            literal,
            '{text: "Hello", channelId: "chan_123", mode: "addToQueue"}',
        )

    def test_create_post_embeds_literal_input_in_query(self):
        captured = {}

        def transport(api_key, query):
            captured["api_key"] = api_key
            captured["query"] = query
            return {"data": {"createPost": {"post": {"id": "p1", "dueAt": "now"}}}}

        post = create_post("token", "channel_1", "Hello world", transport=transport)

        self.assertEqual(post["id"], "p1")
        self.assertEqual(captured["api_key"], "token")
        self.assertIn("mutation CreatePost {", captured["query"])
        self.assertNotIn("$input", captured["query"])
        self.assertIn('channelId: "channel_1"', captured["query"])
        self.assertIn('text: "Hello world"', captured["query"])


if __name__ == "__main__":
    unittest.main()
