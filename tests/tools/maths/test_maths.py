from dify_plugin.core.entities.plugin.request import (
    PluginInvokeType,
    ToolActions,
    ToolInvokeRequest,
)
from dify_plugin.entities.tool import ToolInvokeMessage


def _invoke(plugin_runner, expression):
    response_chunks = []
    for result in plugin_runner.invoke(
        access_type=PluginInvokeType.Tool,
        access_action=ToolActions.InvokeTool,
        payload=ToolInvokeRequest(
            provider="maths",
            tool="eval_expression",
            action=ToolActions.InvokeTool,
            credentials={},
            tool_parameters={
                "expression": expression,
            },
            user_id="test_user",
            type=PluginInvokeType.Tool,
        ),
        response_type=ToolInvokeMessage,
    ):
        response_chunks.append(result)
    return response_chunks


def test_eval_addition(plugin_runner):
    """Basic integer arithmetic is evaluated locally with NumExpr."""
    chunks = _invoke(plugin_runner, "2+2")
    assert len(chunks) == 1
    assert chunks[0].message.text == 'The result of the expression "2+2" is 4'


def test_eval_division_float(plugin_runner):
    """Division yields a floating point result."""
    chunks = _invoke(plugin_runner, "10/4")
    assert len(chunks) == 1
    assert chunks[0].message.text == 'The result of the expression "10/4" is 2.5'


def test_eval_function(plugin_runner):
    """NumExpr functions such as sqrt are supported."""
    chunks = _invoke(plugin_runner, "sqrt(16)")
    assert len(chunks) == 1
    assert chunks[0].message.text == 'The result of the expression "sqrt(16)" is 4.0'


def test_eval_operator_precedence(plugin_runner):
    """Operator precedence follows standard math rules."""
    chunks = _invoke(plugin_runner, "2+3*4")
    assert len(chunks) == 1
    assert chunks[0].message.text == 'The result of the expression "2+3*4" is 14'


def test_eval_invalid_expression(plugin_runner):
    """A malformed expression is caught and reported as invalid."""
    chunks = _invoke(plugin_runner, "2+")
    assert len(chunks) == 1
    assert chunks[0].message.text.startswith("Invalid expression: 2+, error:")
