import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from publish import _to_graphql_literal, create_post


class PublishTests(unittest.TestCase):
    def test_to_graphql_literal_object_keys_are_unquoted(self):
        literal = _to_graphql_literal({"text": "hello", "enabled": True, "count": 2})
        self.assertIn("text: \"hello\"", literal)
        self.assertIn("enabled: true", literal)
        self.assertIn("count: 2", literal)
        self.assertNotIn("\"text\":", literal)

    def test_create_post_sends_valid_graphql_input_literal(self):
        def transport(_api_key, query):
            self.assertIn("createPost(input:", query)
            self.assertIn("text: \"hello world\"", query)
            self.assertNotIn("\"text\":", query)
            return {
                "data": {
                    "createPost": {"post": {"id": "post_1", "dueAt": "2026-10-16T00:00:00Z"}}
                }
            }

        post = create_post("api_key", "channel_1", "hello world", transport=transport)
        self.assertEqual(post["id"], "post_1")


if __name__ == "__main__":
    unittest.main()
