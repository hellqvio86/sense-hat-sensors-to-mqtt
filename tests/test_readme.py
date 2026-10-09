import argparse
from pathlib import Path

from sensehatsensorstomqtt.args import _port_arg

README_PATH = Path(__file__).resolve().parent.parent / "README.md"


def _build_test_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str, required=False)
    parser.add_argument("--password", type=str, required=False)
    parser.add_argument("--password_file", type=str, required=False)
    parser.add_argument("--host", type=str, required=False)
    parser.add_argument("--port", type=_port_arg, required=False)
    parser.add_argument("--topics", type=str, required=False)
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], required=False)
    parser.add_argument("--retain", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--temperature_offset", type=float, required=False)
    parser.add_argument("--compensate_cpu_temp", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--cpu_temp_factor", type=float, required=False)
    parser.add_argument("--interval", type=float, required=False)
    parser.add_argument("--measurements", type=int, required=False)
    parser.add_argument("--sample_spacing", type=float, required=False)
    parser.add_argument("--status_topic", type=str, required=False)
    parser.add_argument("--display", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--display_pause", type=float, required=False)
    parser.add_argument("--night_start", type=int, required=False)
    parser.add_argument("--night_end", type=int, required=False)
    parser.add_argument("--config_file", type=str, required=False)
    parser.add_argument("--log_file", type=str, required=False)
    parser.add_argument("-D", "--debug", action="store_true")
    return parser


def test_readme_documents_all_argparse_options():
    readme_content = README_PATH.read_text(encoding="utf-8")
    parser = _build_test_parser()

    for action in parser._actions:
        for opt in action.option_strings:
            if opt == "-h" or opt == "--help":
                continue
            assert opt in readme_content, f"CLI option '{opt}' is missing from README.md documentation"
