"""Print a ready-to-paste Slack app configuration for one employee."""

import argparse
import json
from urllib.parse import urlsplit


def manifest(name, callback):
    url = urlsplit(callback)
    if url.scheme != "https" or not url.netloc or url.path != "/api/slack/oauth/callback":
        raise ValueError("Use an HTTPS URL ending in /api/slack/oauth/callback.")
    return {
        "display_information": {"name": name, "description": "An OpenHuman AI coworker with Meko memory."},
        "features": {
            "bot_user": {"display_name": name, "always_online": False},
            "app_home": {"home_tab_enabled": False, "messages_tab_enabled": True, "messages_tab_read_only_enabled": False},
        },
        "oauth_config": {
            "redirect_urls": [callback],
            "scopes": {"bot": ["app_mentions:read", "channels:history", "groups:history", "chat:write", "im:history", "im:write", "mpim:history"]},
        },
        "settings": {
            "socket_mode_enabled": True,
            "token_rotation_enabled": False,
            "event_subscriptions": {"bot_events": ["app_mention", "message.channels", "message.groups", "message.im", "message.mpim"]},
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="Alex")
    parser.add_argument("--callback", required=True)
    args = parser.parse_args()
    print(json.dumps(manifest(args.name, args.callback), indent=2))
