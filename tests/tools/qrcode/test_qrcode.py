from dify_plugin.core.entities.plugin.request import (
    PluginInvokeType,
    ToolActions,
    ToolInvokeRequest,
)
from dify_plugin.entities.tool import ToolInvokeMessage

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _invoke(plugin_runner, tool_parameters):
    response_chunks = []
    for result in plugin_runner.invoke(
        access_type=PluginInvokeType.Tool,
        access_action=ToolActions.InvokeTool,
        payload=ToolInvokeRequest(
            provider="qrcode",
            tool="qrcode_generator",
            action=ToolActions.InvokeTool,
            credentials={},
            tool_parameters=tool_parameters,
            user_id="test_user",
            type=PluginInvokeType.Tool,
        ),
        response_type=ToolInvokeMessage,
    ):
        response_chunks.append(result)
    return response_chunks


def _reassemble_blob(chunks):
    """Concatenate the streamed blob chunks (ordered by sequence) into bytes."""
    blob_chunks = [
        c for c in chunks if c.type == ToolInvokeMessage.MessageType.BLOB_CHUNK
    ]
    blob_chunks.sort(key=lambda c: c.message.sequence)
    return b"".join(c.message.blob for c in blob_chunks)


def test_generate_png_blob(plugin_runner):
    """A valid request streams back a PNG image blob."""
    chunks = _invoke(
        plugin_runner,
        {"content": "https://dify.ai", "error_correction": "M", "border": 2},
    )
    blob = _reassemble_blob(chunks)
    assert blob.startswith(PNG_SIGNATURE)
    assert len(blob) > 0


def test_generate_all_error_correction_levels(plugin_runner):
    """Every supported error-correction level produces a valid PNG."""
    for level in ("L", "M", "Q", "H"):
        chunks = _invoke(
            plugin_runner,
            {"content": "test", "error_correction": level, "border": 1},
        )
        blob = _reassemble_blob(chunks)
        assert blob.startswith(PNG_SIGNATURE), f"level {level} did not yield a PNG"


def test_invalid_error_correction(plugin_runner):
    """An unsupported error-correction value is rejected with a message."""
    chunks = _invoke(
        plugin_runner,
        {"content": "test", "error_correction": "Z", "border": 1},
    )
    text_messages = [
        c.message.text
        for c in chunks
        if c.type == ToolInvokeMessage.MessageType.TEXT
    ]
    assert "Invalid parameter error_correction" in text_messages


def test_empty_content(plugin_runner):
    """Empty content is rejected with a validation message."""
    chunks = _invoke(
        plugin_runner,
        {"content": "", "error_correction": "M", "border": 1},
    )
    text_messages = [
        c.message.text
        for c in chunks
        if c.type == ToolInvokeMessage.MessageType.TEXT
    ]
    assert "Invalid parameter content" in text_messages
