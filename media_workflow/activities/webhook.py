import hmac
import os
from base64 import b64decode, b64encode
from json import dumps as json_dumps
from time import time

import aiohttp
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class WebhookParams(BaseModel):
    url: str
    msg_id: str
    payload: dict


@instrument
@activity.defn
async def webhook(params: WebhookParams) -> None:
    msg_id = params.msg_id
    timestamp = int(time())
    payload = json_dumps(params.payload)

    key = b64decode(os.environ["WEBHOOK_SIGNATURE_KEY"].removeprefix("whsec_"))
    content = f"{msg_id}.{timestamp}.{payload}".encode()
    signature = hmac.digest(key, content, "sha256")

    async with aiohttp.ClientSession() as session:
        headers = {
            "content-type": "application/json",
            "webhook-id": msg_id,
            "webhook-timestamp": str(timestamp),
            "webhook-signature": f"v1,{b64encode(signature).decode()}",
        }
        async with session.post(params.url, headers=headers, data=payload) as response:
            response.raise_for_status()
