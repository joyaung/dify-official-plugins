from dify_plugin.core.entities.plugin.request import (
    PluginInvokeType,
    ToolActions,
    ToolInvokeRequest,
)
from dify_plugin.entities.tool import ToolInvokeMessage


def _invoke(plugin_runner, content, expression):
    response_chunks = []
    for result in plugin_runner.invoke(
        access_type=PluginInvokeType.Tool,
        access_action=ToolActions.InvokeTool,
        payload=ToolInvokeRequest(
            provider="regex",
            tool="regex_extract",
            action=ToolActions.InvokeTool,
            credentials={},
            tool_parameters={
                "content": content,
                "expression": expression,
            },
            user_id="test_user",
            type=PluginInvokeType.Tool,
        ),
        response_type=ToolInvokeMessage,
    ):
        response_chunks.append(result)
    return response_chunks


def test_regex_extract_single_match(plugin_runner):
    """A single match is returned as a one-element list string."""
    chunks = _invoke(plugin_runner, "the year is 2024", r"\d+")
    assert len(chunks) == 1
    assert chunks[0].message.text == "['2024']"


def test_regex_extract_multiple_matches(plugin_runner):
    """All non-overlapping matches are returned in order."""
    chunks = _invoke(plugin_runner, "a1 b2 c3", r"\d")
    assert len(chunks) == 1
    assert chunks[0].message.text == "['1', '2', '3']"


def test_regex_extract_with_groups(plugin_runner):
    """When the expression has groups, findall returns tuples."""
    chunks = _invoke(plugin_runner, "2024-01-31", r"(\d{4})-(\d{2})-(\d{2})")
    assert len(chunks) == 1
    assert chunks[0].message.text == "[('2024', '01', '31')]"


def test_regex_extract_no_match(plugin_runner):
    """No match yields an empty list string."""
    chunks = _invoke(plugin_runner, "no digits here", r"\d+")
    assert len(chunks) == 1
    assert chunks[0].message.text == "[]"


def test_regex_extract_invalid_expression(plugin_runner):
    """An invalid regex is caught and reported as a failure message."""
    chunks = _invoke(plugin_runner, "some content", r"(unclosed")
    assert len(chunks) == 1
    assert chunks[0].message.text.startswith("Failed to extract result, error:")


def test_regex_extract_empty_expression(plugin_runner):
    """An empty expression is rejected before extraction runs."""
    chunks = _invoke(plugin_runner, "some content", "")
    assert any(c.message.text == "Invalid expression" for c in chunks)
