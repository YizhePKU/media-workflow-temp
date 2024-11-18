import requests

from media_workflow.s3 import upload


def test_upload():
    data = b"Hello world!"
    url = upload("my-key", data)
    retrived_data = requests.get(url).content
    assert retrived_data == data
