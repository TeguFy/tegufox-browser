import pytest
from tegufox_flow.agent import (
    AgentAction, ParseError, parse_action, AGENT_VERBS,
)


def test_verb_catalogue_has_10():
    assert set(AGENT_VERBS.keys()) == {
        "goto", "click", "click_text", "type", "scroll",
        "wait_for", "read_text", "screenshot", "done", "ask_user",
    }


def test_parse_minimal_goto():
    a = parse_action('{"verb": "goto", "args": {"url": "https://x"}}')
    assert a.verb == "goto"
    assert a.args == {"url": "https://x"}
    assert a.reasoning == ""


def test_parse_with_reasoning():
    a = parse_action(
        '{"reasoning": "go to login", "verb": "goto", '
        '"args": {"url": "https://x"}}'
    )
    assert a.reasoning == "go to login"


def test_parse_strips_markdown_fence():
    raw = '```json\n{"verb": "done", "args": {"reason": "ok"}}\n```'
    a = parse_action(raw)
    assert a.verb == "done"


def test_parse_unknown_verb_raises():
    with pytest.raises(ParseError) as e:
        parse_action('{"verb": "nope", "args": {}}')
    assert "nope" in str(e.value)


def test_parse_missing_required_arg_raises():
    with pytest.raises(ParseError) as e:
        parse_action('{"verb": "goto", "args": {}}')
    assert "url" in str(e.value)


def test_parse_extra_args_allowed():
    a = parse_action(
        '{"verb": "goto", "args": {"url": "https://x", "wait_until": "load"}}'
    )
    assert a.args["wait_until"] == "load"


def test_parse_invalid_json_raises():
    with pytest.raises(ParseError):
        parse_action("not json {")


def test_parse_done_required_reason():
    with pytest.raises(ParseError):
        parse_action('{"verb": "done", "args": {}}')


def test_parse_ask_user_required_question():
    with pytest.raises(ParseError):
        parse_action('{"verb": "ask_user", "args": {}}')
