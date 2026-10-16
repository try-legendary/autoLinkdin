"""List your Buffer channels so you can copy the LinkedIn channel ID.

Usage:
    BUFFER_API_KEY=... python3 scripts/buffer_channels.py
    python3 scripts/buffer_channels.py --api-key ...
    python3 scripts/buffer_channels.py --mock     # offline demo, no key needed
"""

import argparse
import json
import os
import sys

from publish import graphql
from mock_buffer import MockBufferTransport

ORGANIZATIONS_QUERY = """
query GetOrganizations {
  account {
    organizations { id name }
  }
}
"""

CHANNELS_QUERY = """
query GetChannels {
  channels(input: {organizationId: %s}) {
    id name displayName service isQueuePaused
  }
}
"""


def main():
    parser = argparse.ArgumentParser(description="List Buffer channels")
    parser.add_argument("--api-key", default=os.environ.get("BUFFER_API_KEY"))
    parser.add_argument("--mock", action="store_true",
                        help="use canned data instead of calling the Buffer API")
    args = parser.parse_args()

    transport = MockBufferTransport() if args.mock else None
    if not args.mock and not args.api_key:
        sys.exit("error: provide BUFFER_API_KEY env var or --api-key (or use --mock)")
    if args.mock:
        print("mode: MOCK (canned Buffer data, no network)")
        args.api_key = "mock_api_key"

    data = graphql(args.api_key, ORGANIZATIONS_QUERY, transport=transport)
    organizations = (data.get("account") or {}).get("organizations") or []
    if not organizations:
        sys.exit("error: no Buffer organizations found on this account")

    for org in organizations:
        print(f"\nOrganization: {org.get('name')} ({org.get('id')})")
        channels = graphql(
            args.api_key, CHANNELS_QUERY % json.dumps(org["id"]), transport=transport
        ).get("channels") or []
        if not channels:
            print("  (no channels - connect a social account in Buffer first)")
        for ch in channels:
            paused = " [queue paused]" if ch.get("isQueuePaused") else ""
            marker = "  <-- use this" if ch.get("service") == "linkedin" else ""
            print(
                f"  {ch.get('service'):12} {ch.get('id')}  "
                f"{ch.get('displayName') or ch.get('name')}{paused}{marker}"
            )

    print("\nNext step (GitHub repo settings > Secrets and variables > Actions):")
    print("  BUFFER_API_KEY      = your API key")
    print("  BUFFER_CHANNEL_ID   = the LinkedIn channel id printed above")


if __name__ == "__main__":
    main()
