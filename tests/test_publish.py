import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from publish import GraphQLEnum, _to_graphql_literal, create_post


class PublishSerializationTests(unittest.TestCase):
    def test_ordinary_string_serialization_stays_quoted_and_escaped(self):
        text = 'he said "hello"\nnew line'
        self.assertEqual(_to_graphql_literal(text), json.dumps(text, ensure_ascii=False))

    def test_enum_fields_are_emitted_without_quotes(self):
        literal = _to_graphql_literal({
            "text": "Hello",
            "channelId": "channel_123",
            "schedulingType": GraphQLEnum("automatic"),
            "mode": GraphQLEnum("addToQueue"),
        })

        self.assertIn('text: "Hello"', literal)
        self.assertIn('channelId: "channel_123"', literal)
        self.assertIn('schedulingType: automatic', literal)
        self.assertIn('mode: addToQueue', literal)
        self.assertNotIn('schedulingType: "automatic"', literal)
        self.assertNotIn('mode: "addToQueue"', literal)

    def test_create_post_sends_mutation_with_unquoted_enums(self):
        seen = {}

        def transport(_api_key, query):
            seen["query"] = query
            return {
                "data": {
                    "createPost": {"post": {"id": "post_1", "dueAt": "2026-10-20T10:00:00Z"}}
                }
            }

        post = create_post("api_key", "channel_123", 'hello "world"', transport=transport)

        self.assertEqual(post["id"], "post_1")
        query = seen["query"]
        self.assertIn('schedulingType: automatic', query)
        self.assertIn('mode: addToQueue', query)
        self.assertNotIn('schedulingType: "automatic"', query)
        self.assertNotIn('mode: "addToQueue"', query)
        self.assertIn('channelId: "channel_123"', query)
        self.assertIn('text: "hello \\"world\\""', query)


if __name__ == "__main__":
    unittest.main()
