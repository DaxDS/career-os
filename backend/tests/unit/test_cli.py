from app.cli import build_parser, cmd_version


def test_cli_version(capsys):
    parser = build_parser()
    args = parser.parse_args(["version"])
    assert args.func == cmd_version
    assert cmd_version(args) == 0
    assert "Career OS" in capsys.readouterr().out


def test_cli_parser_has_operational_commands():
    parser = build_parser()
    sub = [action for action in parser._actions if action.choices]
    assert sub
    assert "backup" in sub[0].choices
    assert "restore" in sub[0].choices
    assert "migrate" in sub[0].choices
    assert "health" in sub[0].choices
