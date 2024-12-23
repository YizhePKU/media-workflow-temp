from uuid import uuid4

from media_workflow.client import get_client


async def test_color_calibrate():
    client = await get_client()
    arg = ["#000001", "#fffffd"]
    result = await client.execute_workflow("color-calibrate", arg, id=f"{uuid4()}", task_queue="media")
    assert result == {"#000001": "#000000", "#fffffd": "#ffffff"}
