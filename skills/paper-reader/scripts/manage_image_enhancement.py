#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from _paper_reader_runtime import (
    detect_image_backend,
    example_config,
    load_local_config,
    load_state,
    local_config_exists,
    output_root,
    reset_state,
    runtime_mode,
    set_user_choice,
    update_state_from_probe,
)


def print_payload(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")
    subparsers.add_parser("probe")
    init_parser = subparsers.add_parser("initialize")
    init_parser.add_argument("--choice", choices=["yes", "no"], required=True)
    choice_parser = subparsers.add_parser("set-choice")
    choice_parser.add_argument("choice", choices=["yes", "no", "unknown"])
    subparsers.add_parser("reset")

    args = parser.parse_args()

    if args.command == "status":
        print_payload(
            {
                "runtime_mode": runtime_mode(),
                "local_config_exists": local_config_exists(),
                "output_root": str(output_root()),
                "local_config": load_local_config(),
                "example_config": example_config(),
                "state": load_state(),
            }
        )
        return

    if args.command == "probe":
        state = update_state_from_probe(mark_initialized=False)
        print_payload({"state": state, "probe": detect_image_backend()})
        return

    if args.command == "initialize":
        set_user_choice(args.choice)
        state = update_state_from_probe(mark_initialized=True) if args.choice == "yes" else load_state()
        print_payload({"state": state, "probe": detect_image_backend() if args.choice == "yes" else {}})
        return

    if args.command == "set-choice":
        print_payload({"state": set_user_choice(args.choice)})
        return

    if args.command == "reset":
        print_payload({"state": reset_state()})


if __name__ == "__main__":
    main()
