import json
import os
import socket
import tempfile
from pathlib import Path

import c4d

from media_workflow.otel import tracer


def preview(file: str):
    print(f"processing {file}")

    tempdir = tempfile.mkdtemp()
    gltf = f"{tempdir}/{Path(file).stem}.gltf"
    png = f"{tempdir}/{Path(file).stem}.png"

    with tracer.start_as_current_span("c4d-load-document"):
        doc = c4d.documents.LoadDocument(file, c4d.SCENEFILTER_OBJECTS)
        assert doc is not None
        print(f"loaded {file}")

    with tracer.start_as_current_span("c4d-export-gltf"):
        c4d.documents.SaveDocument(doc, gltf, 0, c4d.FORMAT_GLTFEXPORT)
        print(f"exported {gltf}")

    with tracer.start_as_current_span("c4d-export-png"):
        bitmap = doc.GetDocPreviewBitmap()
        ret = bitmap.Save(str(png), c4d.FILTER_PNG)
        assert ret == c4d.IMAGERESULT_OK
        print(f"exported {png}")

    return {"gltf": gltf, "png": png}


def main():
    host = os.environ.get("C4D_SERVER_HOST", "localhost")
    port = os.environ.get("C4D_SERVER_PORT", 8848)
    print(f"C4D server listening on {host}:{port}")
    with socket.create_server((host, port)) as server:
        while True:
            (conn, _) = server.accept()
            request = json.loads(conn.recv(1000))
            assert isinstance(request, str)
            try:
                response = preview(request)
                response["status"] = "success"
                conn.send(json.dumps(response).encode())
            except Exception as e:
                response = {"status": "error", "reason": str(e)}
                conn.send(json.dumps(response).encode())
            conn.close()


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Unhandled exception: {e}")
