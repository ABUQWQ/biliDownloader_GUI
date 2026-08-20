"""Compatibility adapter between the current Bilibili API and the legacy GUI."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from Lib.bili_api import bangumi, video
from Lib.bili_api.exceptions.BiliVideoIdException import BiliVideoIdException
from Lib.bili_api.exceptions.GetWbiException import GetWbiException
from Lib.bili_api.exceptions.NetWorkException import NetWorkException
from Lib.bili_api.utils import BiliPassport
from Lib.bili_api.utils import network


class DownloadError(RuntimeError):
    """Normalized error exposed to the legacy worker and GUI."""


@dataclass
class RequestOptions:
    cookie: str = ""
    proxy: Optional[Dict[str, str]] = None
    proxy_auth: Optional[Tuple[str, str]] = None
    timeout: float = 10.0


@dataclass
class SourceInfo:
    kind: str
    identifier: str
    page: Optional[int] = None
    episode_id: Optional[int] = None
    season_id: Optional[int] = None
    media_id: Optional[int] = None


@dataclass
class PageInfo:
    index: int
    cid: int
    title: str
    bvid: Optional[str] = None
    avid: Optional[int] = None
    episode_id: Optional[int] = None
    url: str = ""


@dataclass
class MediaInfo:
    source: SourceInfo
    title: str
    duration: float
    pages: List[PageInfo] = field(default_factory=list)
    bvid: Optional[str] = None
    avid: Optional[int] = None
    cid: Optional[int] = None
    is_bangumi: bool = False


@dataclass
class StreamInfo:
    video: Dict[int, List[Any]]
    audio: Dict[int, List[Any]]
    duration: float = 0
    raw: Dict[str, Any] = field(default_factory=dict)


def create_passport(cookie_text: str) -> Optional[BiliPassport]:
    """Create a passport from the legacy semicolon-separated Cookie field."""
    values: Dict[str, str] = {}
    for item in cookie_text.split(";"):
        key, separator, value = item.strip().partition("=")
        if separator and key and value:
            values[key] = value
    values = {
        key: values[key]
        for key in ("DedeUserID", "DedeUserID__ckMd5", "SESSDATA", "bili_jct", "sid")
        if key in values
    }
    return BiliPassport(values) if values else None


def parse_source(url: str, options: Optional[RequestOptions] = None) -> SourceInfo:
    """Normalize legacy address input into a stable source descriptor."""
    value = url.strip()
    if not value:
        raise BiliVideoIdException("地址不能为空")
    match = re.search(r"(?:^|/)BV([A-Za-z0-9]{10})", value, re.IGNORECASE)
    if match:
        query = parse_qs(urlparse(value).query)
        page = int(query["p"][0]) if query.get("p", [""])[0].isdigit() else None
        page = page if page and page > 0 else None
        return SourceInfo("video", "BV" + match.group(1), page=page)
    match = re.search(r"(?:^|/)av(\d+)", value, re.IGNORECASE)
    if match:
        query = parse_qs(urlparse(value).query)
        page = int(query["p"][0]) if query.get("p", [""])[0].isdigit() else None
        page = page if page and page > 0 else None
        return SourceInfo("video", match.group(1), page=page)
    match = re.search(r"(?:^|/)(?:ep)(\d+)", value, re.IGNORECASE)
    if match:
        return SourceInfo("bangumi", match.group(1), episode_id=int(match.group(1)))
    match = re.search(r"(?:^|/)(?:ss)(\d+)", value, re.IGNORECASE)
    if match:
        return SourceInfo("bangumi", match.group(1), season_id=int(match.group(1)))
    match = re.search(r"(?:^|/)md(\d+)", value, re.IGNORECASE)
    if match:
        return SourceInfo("bangumi", match.group(1), media_id=int(match.group(1)))
    raise BiliVideoIdException("无法识别地址，请输入 BV、AV、EP、SS 或 MD")


def _is_bvid(identifier: str) -> bool:
    return identifier.upper().startswith("BV")


def _network_options(options: Optional[RequestOptions]) -> Dict[str, Any]:
    if options is None:
        return {}
    return {
        "cookie": options.cookie,
        "proxy": options.proxy,
        "proxy_auth": options.proxy_auth,
        "timeout": options.timeout,
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _video_identity(source: SourceInfo) -> Dict[str, Any]:
    return {
        "bvid" if _is_bvid(source.identifier) else "avid":
        source.identifier if _is_bvid(source.identifier) else int(source.identifier)
    }


def get_media_info(source: SourceInfo, options: Optional[RequestOptions] = None) -> MediaInfo:
    """Fetch metadata and normalize video or bangumi page information."""
    try:
        with network.request_context(_network_options(options)):
            if source.kind == "video":
                identity = _video_identity(source)
                info = video.get_video_info(**identity)
                pages = video.get_video_pages(**identity)
            else:
                if source.media_id is not None:
                    detail = bangumi.get_bangumi_detailed_info(media_id=source.media_id)
                elif source.season_id is not None:
                    detail = bangumi.get_bangumi_detailed_info(season_id=source.season_id)
                else:
                    detail = bangumi.get_bangumi_detailed_info(ep_id=source.episode_id)

        if source.kind == "video":
            page_items = [
                PageInfo(
                    index=index,
                    cid=_safe_int(item.get("cid")),
                    title=item.get("part") or item.get("title") or f"P{index}",
                    bvid=info.get("bvid"),
                    avid=_safe_int(info.get("aid")) or None,
                    url=f"https://www.bilibili.com/video/{info.get('bvid') or 'av' + str(info.get('aid'))}?p={index}",
                )
                for index, item in enumerate(pages, 1)
            ]
            selected = source.page or _safe_int(info.get("p"), 1)
            selected_page = page_items[selected - 1] if page_items and selected <= len(page_items) else None
            if selected_page is None and page_items:
                selected_page = page_items[0]
            return MediaInfo(
                source=source,
                title=info.get("title") or "未命名视频",
                duration=float(info.get("duration") or 0),
                pages=page_items,
                bvid=info.get("bvid"),
                avid=_safe_int(info.get("aid")) or None,
                cid=selected_page.cid if selected_page else _safe_int(info.get("cid")) or None,
            )

        info = detail["info"]
        data = detail["data"]
        sections = data.get("section") or []
        episodes = data.get("episodes") or (sections[0].get("episodes", []) if sections else [])
        pages = []
        for index, item in enumerate(episodes, 1):
            pages.append(
                PageInfo(
                    index=index,
                    cid=_safe_int(item.get("cid")),
                    title=item.get("long_title") or item.get("show_title") or item.get("title") or f"第{index}集",
                    bvid=item.get("bvid"),
                    avid=_safe_int(item.get("aid")) or None,
                    episode_id=_safe_int(item.get("id")) or None,
                    url=item.get("share_url") or item.get("link") or "",
                )
            )
        current = next(
            (item for item in pages if item.episode_id == source.episode_id),
            pages[0] if pages else None,
        )
        raw_current = next(
            (item for item in episodes if _safe_int(item.get("id")) == source.episode_id),
            episodes[0] if episodes else {},
        )
        return MediaInfo(
            source=source,
            title=info.get("media", {}).get("title") or data.get("season_title") or "未命名番剧",
            duration=float(raw_current.get("duration") or 0) / 1000,
            pages=pages,
            bvid=current.bvid if current else None,
            avid=current.avid if current else None,
            cid=current.cid if current else None,
            is_bangumi=True,
        )
    except (BiliVideoIdException, NetWorkException, GetWbiException, KeyError, TypeError, ValueError) as error:
        raise map_api_error(error) from error


def _stream_url(item: Dict[str, Any]) -> str:
    return item.get("baseUrl") or item.get("base_url") or item.get("url") or ""


def _stream_backups(item: Dict[str, Any]) -> List[str]:
    values = item.get("backupUrl") or item.get("backup_url") or []
    return list(values) if isinstance(values, list) else []


def _initialization(item: Dict[str, Any]) -> str:
    segment = item.get("SegmentBase") or item.get("segment_base") or {}
    value = segment.get("Initialization") or segment.get("initialization") or ""
    return f"bytes={value}" if value else ""


def _display(kind: str, item: Dict[str, Any]) -> str:
    codec = item.get("codecs") or item.get("mimeType") or "未知编码"
    if kind == "video":
        return f"{item.get('id', 0)} {codec}"
    return f"{codec} 音频带宽：{item.get('bandwidth', 0)}"


def _legacy_streams(data: Dict[str, Any]) -> StreamInfo:
    dash = data.get("dash") or {}
    descriptions = dict(zip(data.get("accept_quality") or [], data.get("accept_description") or []))
    videos: Dict[int, List[Any]] = {}
    for index, item in enumerate(dash.get("video") or []):
        label = descriptions.get(item.get("id")) or _display("video", item)
        videos[index] = [
            f"{label} {item.get('codecs', '')}".strip(),
            [_stream_url(item), *_stream_backups(item)],
            _initialization(item),
        ]
    audios: Dict[int, List[Any]] = {}
    audio_items: List[Dict[str, Any]] = []
    dolby = dash.get("dolby") or {}
    if isinstance(dolby.get("audio"), list):
        audio_items.extend(dolby["audio"])
    flac = dash.get("flac") or {}
    if isinstance(flac.get("audio"), dict):
        audio_items.append(flac["audio"])
    if isinstance(dash.get("audio"), list):
        audio_items.extend(dash["audio"])
    for index, item in enumerate(audio_items):
        audios[index] = [
            _display("audio", item),
            [_stream_url(item), *_stream_backups(item)],
            _initialization(item),
        ]
    if not audios:
        audios[0] = ["无音轨", [], ""]
    if not videos and isinstance(data.get("durl"), list):
        for index, item in enumerate(data["durl"]):
            videos[index] = [
                descriptions.get(data.get("quality"), "MP4"),
                [item.get("url", ""), *(item.get("backup_url") or [])],
                "bytes=0-",
            ]
    return StreamInfo(video=videos, audio=audios, duration=data.get("dash", {}).get("duration", 0), raw=data)


def get_stream_options(media: MediaInfo, options: Optional[RequestOptions] = None) -> StreamInfo:
    """Fetch the selected page's current media URLs."""
    if media.cid is None:
        raise DownloadError("当前视频没有可用 CID")
    passport = create_passport(options.cookie) if options else None
    try:
        with network.request_context(_network_options(options)):
            if media.is_bangumi:
                data = bangumi.get_bangumi_url(
                    bvid=media.bvid,
                    avid=media.avid,
                    cid=media.cid,
                    passport=passport,
                )
                data = data.get("video_info", data)
            else:
                data = video.get_video_url(
                    bvid=media.bvid,
                    avid=media.avid,
                    cid=media.cid,
                    passport=passport,
                )
        streams = _legacy_streams(data)
        if not streams.video:
            raise DownloadError("接口未返回可下载的视频流")
        return streams
    except (BiliVideoIdException, NetWorkException, GetWbiException, KeyError, TypeError, ValueError) as error:
        raise map_api_error(error) from error


def map_api_error(error: Exception) -> DownloadError:
    return DownloadError(str(error) or error.__class__.__name__)


def legacy_detail(media: MediaInfo, streams: StreamInfo) -> Tuple[str, float, Dict[str, Dict[int, List[Any]]]]:
    return media.title, media.duration or streams.duration, {"video": streams.video, "audio": streams.audio}
