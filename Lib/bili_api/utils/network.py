import copy
import gzip
import http.client
import json
import urllib.parse
import zlib
from contextlib import contextmanager
from contextvars import ContextVar
from http.client import HTTPMessage as _HTTPMessage
from typing import Union

import requests

try:
    import brotli
except ImportError:
    brotli = None

try:
    import zstandard
except ImportError:
    zstandard = None

from .defaultHeaders import DEFAULT_HEADERS
from ..exceptions.NetWorkException import NetWorkException


_request_options: ContextVar[dict] = ContextVar("bili_request_options", default={})


@contextmanager
def request_context(options=None):
    """Temporarily apply GUI network settings to API calls."""
    token = _request_options.set(options or {})
    try:
        yield
    finally:
        _request_options.reset(token)


def get_data(
        scheme: str,
        host: str,
        method: str,
        path: str,
        query: dict = None,
        header: dict = None,
        data=None,
        data_type: str = "application/json",
        options: dict = None,
):
    settings = options if options is not None else _request_options.get()
    head = copy.deepcopy(DEFAULT_HEADERS)
    head["Accept-Encoding"] = "gzip, deflate"
    if header is not None:
        for i in header:
            head[i] = header[i]
    if settings and settings.get("cookie") and "Cookie" not in head:
        head["Cookie"] = settings["cookie"]
    url = "{}://{}{}".format(scheme, host, path)
    proxies = settings.get("proxy") if settings else None
    auth = settings.get("proxy_auth") if settings else None
    timeout = settings.get("timeout", 10) if settings else 10
    if auth:
        from requests.auth import HTTPProxyAuth
        auth = HTTPProxyAuth(auth[0], auth[1])
    payload = data
    if data is not None and data_type == "application/x-www-form-urlencoded" and isinstance(data, dict):
        payload = urllib.parse.urlencode(data)
    if data is not None and data_type == "application/json":
        head["Content-Type"] = data_type
    try:
        response = requests.request(
            method,
            url,
            params=query or None,
            headers=head,
            json=payload if data_type == "application/json" and isinstance(payload, (dict, list)) else None,
            data=payload if not (data_type == "application/json" and isinstance(payload, (dict, list))) else None,
            proxies=proxies,
            auth=auth,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise NetWorkException("网络请求失败：{}".format(error)) from error
    try:
        return response.json()
    except ValueError as error:
        raise NetWorkException("服务返回了无法解析的 JSON") from error


class DataGetter:
    def __init__(
            self,
            scheme: str,
            host: str,
            method: str,
            path: str,
            query: dict = None,
            header: dict = None,
    ):
        self._scheme = scheme
        self._host = host
        self._method = method
        self._path = path
        self._query = query
        self._header = header
        self._c: Union[http.client.HTTPConnection, http.client.HTTPSConnection] = None
        self._response_headers: _HTTPMessage = None
        if method == "GET":
            self._qu = (
                ""
                if self._query is None
                else "?{}".format(urllib.parse.urlencode(self._query))
            )
        else:
            self._qu = urllib.parse.urlencode(self._query)
        self._head = copy.deepcopy(DEFAULT_HEADERS)
        if header is not None:
            for i in header:
                self._head[i] = header[i]
        self._linked = False

    def link(self):
        self._c = (
            http.client.HTTPSConnection(self._host)
            if self._scheme == "https"
            else http.client.HTTPConnection(self._host)
        )
        self._linked = True

    def request(self) -> dict:
        if not self._linked:
            raise NetWorkException("Not Linked...")
        if self._method == "GET":
            self._c.request(self._method, self._path + self._qu, headers=self._head)
        else:
            data = self._qu.encode("utf_8")
            self._head["Content-Type"] = "application/x-www-form-urlencoded"
            self._c.request(self._method, self._path, body=data, headers=self._head)
        r = self._c.getresponse()
        self._response_headers = r.headers
        data = r.read()
        encoding = r.headers.get("Content-Encoding")
        if encoding is not None:
            if encoding == "gzip":
                data = gzip.decompress(data)
            elif encoding == "deflate":
                data = zlib.decompress(data, -zlib.MAX_WBITS)
            elif encoding == "br":
                if brotli is None:
                    raise NetWorkException("缺少 brotli 依赖，无法解压响应")
                data = brotli.decompress(data)
            elif encoding == "zstd":
                if zstandard is None:
                    raise NetWorkException("缺少 zstandard 依赖，无法解压响应")
                data = zstandard.decompress(data)
        data = data.decode("utf-8")
        get = json.loads(data)
        r.close()
        return get

    def get_headers(self) -> _HTTPMessage:
        return self._response_headers

    def close(self):
        self._c.close()

    def __del__(self):
        if self._linked:
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
