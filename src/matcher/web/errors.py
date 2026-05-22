"""Web 層錯誤類別（不繼承 MatcherError）。"""

from __future__ import annotations


class WebError(Exception):
    status_code: int = 500


class MatchRecordNotFound(WebError):
    status_code = 404


class UploadTooLarge(WebError):
    status_code = 400


class UploadInvalidMime(WebError):
    status_code = 400
