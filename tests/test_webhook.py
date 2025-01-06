import os
from uuid import uuid4

import pytest
from aiohttp import web

from media_workflow.activities.utils import WebhookParams
from media_workflow.client import connect
from media_workflow.workflows import Webhook


@pytest.mark.skipif(not os.environ.get("MEDIA_WORKFLOW_TEST_WEBHOOK"), reason="Webhook worker not running")
async def test_webhook():
    async def handle(request: web.Request):
        json = await request.json()
        assert json["name"] == "my-payload"
        return web.Response()

    app = web.Application()
    app.add_routes([web.post("/", handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8848)
    await site.start()

    client = await connect()
    params = WebhookParams(url="http://localhost:8848", msg_id=f"{uuid4()}", payload={"name": "my-payload"})
    await client.execute_workflow(Webhook.run, params, id=f"{uuid4()}", task_queue="webhook")
