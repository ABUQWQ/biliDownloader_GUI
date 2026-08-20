import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeSignal:
    def __init__(self, *args, **kwargs):
        self.values = []

    def emit(self, value=None):
        self.values.append(value)

    def connect(self, callback):
        self.callback = callback


class FakeThread:
    def __init__(self, *args, **kwargs):
        pass


qtcore = types.ModuleType("PySide6.QtCore")
qtcore.QThread = FakeThread
qtcore.Signal = FakeSignal
pyside = types.ModuleType("PySide6")
pyside.QtCore = qtcore
sys.modules.setdefault("PySide6", pyside)
sys.modules.setdefault("PySide6.QtCore", qtcore)

worker_module = importlib.import_module("BiliWorker.main")


class FakeResponse:
    def __init__(self, chunks, status_code=206, headers=None):
        self._chunks = chunks
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def iter_content(self, chunk_size):
        return iter(self._chunks)

    def close(self):
        pass


class WorkerContractTests(unittest.TestCase):
    def make_worker(self):
        worker = object.__new__(worker_module.biliWorker)
        worker.business_info = FakeSignal()
        worker.progr_bar = FakeSignal()
        worker.vq_list = FakeSignal()
        worker.aq_list = FakeSignal()
        worker.media_list = FakeSignal()
        worker.is_finished = FakeSignal()
        worker.interact_info = FakeSignal()
        worker.second_headers = {}
        worker.Proxy = None
        worker.ProxyAuth = None
        worker.chunk_size = 4
        worker.set_err = 1
        worker.pauseprocess = False
        worker.killprocess = False
        return worker

    def test_show_detail_emits_legacy_lists(self):
        worker = self.make_worker()
        worker.index_url = "BV1xx411c7mD"
        worker.search_preinfo = lambda url: (1, "Title", 10, {"video": {0: ["1080P", ["v"], ""]}, "audio": {0: ["AAC", ["a"], ""]}})
        worker.search_videoList = lambda url: (1, {"bvid": "BV1xx411c7mD", "p": 1, "pages": [{"page": 1, "part": "One"}]})
        self.assertEqual(worker.show_preDetail(), 1)
        self.assertEqual(worker.vq_list.values, ["1.1080P"])
        self.assertEqual(worker.aq_list.values, ["1.AAC"])
        self.assertEqual(worker.media_list.values, [[1, "1-->One"]])

    def test_downloader_counts_actual_bytes(self):
        worker = self.make_worker()
        responses = [
            FakeResponse([], headers={"Content-Range": "bytes 0-0/6", "Content-Length": "1"}),
            FakeResponse([b"abc", b"def"], headers={"Content-Length": "6"}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "stream.bin"
            with patch.object(worker_module.request, "get", side_effect=responses):
                result = worker.d_processor(["https://media/test"], directory, str(output), "下载视频")
            self.assertEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"abcdef")
            self.assertEqual(worker.progr_bar.values[-1]["Now"], 6)
            self.assertEqual(worker.progr_bar.values[-1]["finish"], 1)

    def test_downloader_resumes_existing_file(self):
        worker = self.make_worker()
        calls = []

        def fake_get(url, headers, **kwargs):
            calls.append(dict(headers))
            if len(calls) == 1:
                return FakeResponse([], headers={"Content-Range": "bytes 0-0/6"})
            return FakeResponse([b"def"], headers={"Content-Length": "3"})

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "stream.bin"
            output.write_bytes(b"abc")
            with patch.object(worker_module.request, "get", side_effect=fake_get):
                result = worker.d_processor(["https://media/test"], directory, str(output), "下载视频")
            self.assertEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"abcdef")
            self.assertEqual(calls[1]["range"], "bytes=3-5")

    def test_downloader_skips_complete_file(self):
        worker = self.make_worker()
        response = FakeResponse([], headers={"Content-Range": "bytes 0-0/3"})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "stream.bin"
            output.write_bytes(b"abc")
            with patch.object(worker_module.request, "get", return_value=response) as get:
                result = worker.d_processor(["https://media/test"], directory, str(output), "下载视频")
            self.assertEqual(result, 0)
            self.assertEqual(get.call_count, 1)
            self.assertEqual(worker.progr_bar.values[-1], {"Max": 3, "Now": 3, "finish": 1})

    def test_pause_resume_and_stop_flags(self):
        worker = self.make_worker()
        worker.subpON = False
        worker.pause()
        self.assertTrue(worker.pauseprocess)
        worker.resume()
        self.assertFalse(worker.pauseprocess)
        worker.close_process()
        self.assertTrue(worker.killprocess)


if __name__ == "__main__":
    unittest.main()
