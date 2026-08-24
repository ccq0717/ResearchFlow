from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_ERROR_MESSAGES = {
    "RUN_NOT_FOUND": "研究任务不存在",
}

_VALIDATION_MESSAGES = {
    "goal_too_short": "研究目标至少需要 10 个字符",
    "string_too_long": "字段内容超过允许长度",
    "missing": "缺少必填字段",
}


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(HTTPException, _http_error_handler)


async def _validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": _field_name(item.get("loc", ())),
            "message": _VALIDATION_MESSAGES.get(str(item.get("type")), "字段值不符合要求"),
        }
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求数据不符合要求",
            "details": details,
        },
    )


async def _http_error_handler(_: Request, error: HTTPException) -> JSONResponse:
    detail = error.detail if isinstance(error.detail, dict) else {}
    code = str(detail.get("code", "HTTP_ERROR"))
    message = str(detail.get("message") or _ERROR_MESSAGES.get(code, "请求失败"))
    return JSONResponse(
        status_code=error.status_code,
        content={
            "code": code,
            "message": message,
            "details": detail.get("details"),
        },
        headers=error.headers,
    )


def _field_name(location: Any) -> str:
    parts = [str(part) for part in location if part not in {"body", "query", "path"}]
    return ".".join(parts) or "request"
