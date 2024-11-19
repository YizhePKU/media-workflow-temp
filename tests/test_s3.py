import aiohttp

from media_workflow.s3 import upload


async def test_upload():
    data = b"Hello world!"
    url = upload("my-key", data)
    async with aiohttp.ClientSession() as client:
        async with client.get(url) as response:
            retrived_data = await response.read()
    assert retrived_data == data
