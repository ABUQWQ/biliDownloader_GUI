import unittest
from unittest.mock import Mock, patch

from BiliWorker.api_adapter import (
    DownloadError,
    RequestOptions,
    create_passport,
    get_media_info,
    get_stream_options,
    map_api_error,
    parse_source,
)
from Lib.bili_api.utils import network


class ApiAdapterTests(unittest.TestCase):
    def test_parse_supported_sources(self):
        cases = {
            "https://www.bilibili.com/video/BV1xx411c7mD?p=2": ("video", "BV1xx411c7mD", 2),
            "https://www.bilibili.com/video/av170001": ("video", "170001", None),
            "https://www.bilibili.com/bangumi/play/ep123": ("bangumi", "123", None),
            "https://www.bilibili.com/bangumi/play/ss456": ("bangumi", "456", None),
            "https://www.bilibili.com/bangumi/media/md789": ("bangumi", "789", None),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                source = parse_source(value)
                self.assertEqual((source.kind, source.identifier, source.page), expected)

    def test_parse_rejects_unknown_source(self):
        with self.assertRaises(Exception):
            parse_source("https://example.com/video/123")

    def test_create_passport_filters_cookie_fields(self):
        passport = create_passport("SESSDATA=masked; bili_jct=csrf; ignored=value")
        self.assertEqual(passport.get_data(), {"SESSDATA": "masked", "bili_jct": "csrf"})
        self.assertIsNone(create_passport(""))

    @patch("BiliWorker.api_adapter.video.get_video_pages")
    @patch("BiliWorker.api_adapter.video.get_video_info")
    def test_video_media_normalization(self, get_info, get_pages):
        get_info.return_value = {
            "title": "Example",
            "bvid": "BV1xx411c7mD",
            "aid": 170001,
            "duration": 120,
        }
        get_pages.return_value = [
            {"cid": 11, "part": "First"},
            {"cid": 22, "part": "Second"},
        ]
        media = get_media_info(parse_source("BV1xx411c7mD?p=2"))
        self.assertEqual(media.cid, 22)
        self.assertEqual([page.title for page in media.pages], ["First", "Second"])

    @patch("BiliWorker.api_adapter.bangumi.get_bangumi_detailed_info")
    def test_bangumi_episode_selection(self, get_detail):
        get_detail.return_value = {
            "info": {"media": {"title": "Series"}},
            "data": {
                "episodes": [
                    {"id": 123, "cid": 31, "aid": 41, "bvid": "BV1xx411c7mD", "long_title": "One", "duration": 60000},
                    {"id": 124, "cid": 32, "aid": 42, "bvid": "BV1xx411c7mE", "long_title": "Two", "duration": 90000},
                ]
            },
        }
        media = get_media_info(parse_source("https://www.bilibili.com/bangumi/play/ep124"))
        self.assertEqual(media.cid, 32)
        self.assertEqual(media.duration, 90)
        self.assertTrue(media.is_bangumi)

    @patch("BiliWorker.api_adapter.video.get_video_url")
    def test_dash_stream_normalization(self, get_url):
        get_url.return_value = {
            "accept_quality": [80],
            "accept_description": ["1080P"],
            "dash": {
                "duration": 10,
                "video": [{
                    "id": 80,
                    "codecs": "avc1",
                    "baseUrl": "https://video/main",
                    "backupUrl": ["https://video/backup"],
                    "SegmentBase": {"Initialization": "0-1"},
                }],
                "audio": [{
                    "codecs": "mp4a",
                    "bandwidth": 128000,
                    "base_url": "https://audio/main",
                    "backup_url": ["https://audio/backup"],
                    "segment_base": {"initialization": "0-2"},
                }],
            },
        }
        source = parse_source("BV1xx411c7mD")
        media = type("Media", (), {"cid": 11, "bvid": source.identifier, "avid": None, "is_bangumi": False})()
        streams = get_stream_options(media, RequestOptions(cookie="SESSDATA=masked"))
        self.assertEqual(streams.video[0][1], ["https://video/main", "https://video/backup"])
        self.assertEqual(streams.audio[0][1], ["https://audio/main", "https://audio/backup"])
        self.assertEqual(streams.video[0][2], "bytes=0-1")

    @patch("BiliWorker.api_adapter.video.get_video_url")
    def test_mp4_and_no_audio_normalization(self, get_url):
        get_url.return_value = {
            "quality": 64,
            "accept_quality": [64],
            "accept_description": ["720P"],
            "durl": [{"url": "https://video/mp4", "backup_url": []}],
        }
        source = parse_source("BV1xx411c7mD")
        media = type("Media", (), {"cid": 11, "bvid": source.identifier, "avid": None, "is_bangumi": False})()
        streams = get_stream_options(media)
        self.assertEqual(streams.video[0][1], ["https://video/mp4"])
        self.assertEqual(streams.audio[0], ["无音轨", [], ""])

    def test_error_mapping(self):
        mapped = map_api_error(ValueError("bad input"))
        self.assertIsInstance(mapped, DownloadError)
        self.assertEqual(str(mapped), "bad input")

    @patch("Lib.bili_api.utils.network.requests.request")
    def test_network_context_applies_proxy_auth_and_timeout(self, request):
        response = Mock()
        response.json.return_value = {"code": 0, "data": {}}
        request.return_value = response
        with network.request_context({
            "cookie": "SESSDATA=masked",
            "proxy": {"https": "http://127.0.0.1:8080"},
            "proxy_auth": ("user", "password"),
            "timeout": 7,
        }):
            network.get_data("https", "api.bilibili.com", "GET", "/x/test")
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["proxies"], {"https": "http://127.0.0.1:8080"})
        self.assertEqual(kwargs["timeout"], 7)
        self.assertEqual(kwargs["auth"].username, "user")
        self.assertEqual(kwargs["headers"]["Cookie"], "SESSDATA=masked")


if __name__ == "__main__":
    unittest.main()
