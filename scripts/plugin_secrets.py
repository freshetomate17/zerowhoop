#!/usr/bin/env python3
"""
CLI for managing encrypted plugin secrets.
Equivalent to: zeroclaw plugin secrets <command> <plugin> <key>

Commands:
    set  <plugin> <key>         Prompt for a value, encrypt it, and store it
    get  <plugin> <key>         Decrypt and print a secret (use carefully)
    list <plugin>               List stored key names (values are never shown)
    delete <plugin> <key>       Remove a secret

Examples:
    python scripts/plugin_secrets.py set whoop whoop_client_id
    python scripts/plugin_secrets.py set whoop whoop_client_secret
    python scripts/plugin_secrets.py set whoop whoop_access_token
    python scripts/plugin_secrets.py set whoop whoop_refresh_token
    python scripts/plugin_secrets.py set whoop discord_bot_token
    python scripts/plugin_secrets.py list whoop
"""

import argparse
import getpass
import sys
from pathlib import Path

# Resolve lib/ relative to this script's location (scripts/ -> repo root -> lib/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from secret_store import SecretStore, _PLUGINS_DIR  # noqa: E402


def cmd_set(args: argparse.Namespace) -> None:
    value = getpass.getpass(f"Value for '{args.key}' (hidden): ").strip()
    if not value:
        sys.exit("Aborted — no value entered.")
    SecretStore(args.plugin).set(args.key, value)
    print(f"✓ Secret '{args.key}' saved for plugin '{args.plugin}' (encrypted).")


def cmd_get(args: argparse.Namespace) -> None:
    print(SecretStore(args.plugin).get(args.key))


def cmd_list(args: argparse.Namespace) -> None:
    store = SecretStore(args.plugin)
    keys = store.list_keys()
    if not keys:
        print(f"No secrets stored for plugin '{args.plugin}'.")
        return
    print(f"Secrets for plugin '{args.plugin}'  ({store.secrets_path}):")
    for k in keys:
        print(f"  {k} = [encrypted]")


def cmd_delete(args: argparse.Namespace) -> None:
    store = SecretStore(args.plugin)
    raw = store._read_raw()
    if args.key not in raw:
        sys.exit(f"Key '{args.key}' not found for plugin '{args.plugin}'.")
    del raw[args.key]
    store._write_raw(raw)
    print(f"✓ Secret '{args.key}' deleted from plugin '{args.plugin}'.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage encrypted ZeroWhoop plugin secrets.\n"
                    "Equivalent to: zeroclaw plugin secrets <command>",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [
        ("set",    "Encrypt and store a secret (prompts for value)"),
        ("get",    "Decrypt and print a secret"),
        ("list",   "List stored key names"),
        ("delete", "Remove a stored secret"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("plugin", help="Plugin name, e.g. whoop")
        if name != "list":
            p.add_argument("key", help="Secret key name, e.g. whoop_client_id")

    args = parser.parse_args()
    {"set": cmd_set, "get": cmd_get, "list": cmd_list, "delete": cmd_delete}[args.command](args)


if __name__ == "__main__":
    main()
