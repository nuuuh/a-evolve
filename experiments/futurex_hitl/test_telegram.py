#!/usr/bin/env python3
"""Test Telegram bot connectivity before running the experiment.

Usage:
    python experiments/futurex_hitl/test_telegram.py

Setup:
    1. Create a bot via @BotFather on Telegram (send /newbot)
    2. Save the bot token (e.g., 7123456789:AAF...)
    3. Message your bot in Telegram (send anything like "hello")
    4. Run this script — it will auto-detect your chat ID and test round-trip

This script:
    1. Reads token from config or prompts you
    2. Finds your chat ID from recent messages
    3. Sends a test message
    4. Waits for your reply
    5. Confirms round-trip works
"""
import json
import sys
import time
import urllib.request
from pathlib import Path


def telegram_api(token: str, method: str, data: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    if data:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(url, payload, {"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def main():
    # Try to load token from config
    config_path = Path(__file__).resolve().parent / "configs" / "full_evo.yaml"
    token = None
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        token = cfg.get("telegram_bot_token")
        if token == "PLACEHOLDER":
            token = None

    if not token:
        token = input("Enter your Telegram bot token: ").strip()
        if not token:
            print("No token provided. Exiting.")
            sys.exit(1)

    # Verify bot
    print(f"Checking bot...")
    try:
        me = telegram_api(token, "getMe")
        bot_name = me["result"]["username"]
        print(f"  Bot: @{bot_name}")
    except Exception as e:
        print(f"  ERROR: Invalid token — {e}")
        sys.exit(1)

    # Find chat ID from recent messages
    print(f"\nLooking for your messages to @{bot_name}...")
    print(f"  (If none found, message the bot in Telegram first, then re-run)")
    updates = telegram_api(token, "getUpdates")
    chats = {}
    for u in updates.get("result", []):
        msg = u.get("message", {})
        chat = msg.get("chat", {})
        if chat.get("id"):
            chats[chat["id"]] = chat.get("first_name", chat.get("username", "unknown"))

    if not chats:
        print("  No messages found. Please message your bot in Telegram first.")
        sys.exit(1)

    if len(chats) == 1:
        chat_id = list(chats.keys())[0]
        chat_name = chats[chat_id]
    else:
        print("  Found multiple chats:")
        for cid, name in chats.items():
            print(f"    {cid}: {name}")
        chat_id = int(input("  Enter the chat ID to use: "))
        chat_name = chats.get(chat_id, "unknown")

    print(f"  Using chat: {chat_id} ({chat_name})")

    # Send test message
    print(f"\nSending test message...")
    telegram_api(token, "sendMessage", {
        "chat_id": chat_id,
        "text": "🤖 A-Evolve HITL test: Connection successful!\n\nReply to this message to confirm round-trip works.",
    })
    print("  Sent! Check your Telegram.")

    # Wait for reply
    print("\nWaiting for your reply (60s timeout)...")
    last_update_id = max((u["update_id"] for u in updates.get("result", [])), default=0)
    deadline = time.time() + 60
    while time.time() < deadline:
        resp = telegram_api(token, "getUpdates", {"offset": last_update_id + 1, "timeout": 5})
        for u in resp.get("result", []):
            last_update_id = u["update_id"]
            msg = u.get("message", {})
            if msg.get("chat", {}).get("id") == chat_id and msg.get("text"):
                print(f"  Received: {msg['text']}")
                print(f"\n{'=' * 50}")
                print("SUCCESS! Round-trip communication works.")
                print(f"{'=' * 50}")
                print(f"\nAdd these to experiments/futurex_hitl/configs/full_evo.yaml:")
                print(f'  telegram_bot_token: "{token}"')
                print(f"  telegram_chat_id: {chat_id}")
                return
        time.sleep(1)

    print("  Timeout — no reply received. But sending works!")
    print(f"\nAdd these to experiments/futurex_hitl/configs/full_evo.yaml:")
    print(f'  telegram_bot_token: "{token}"')
    print(f"  telegram_chat_id: {chat_id}")


if __name__ == "__main__":
    main()
