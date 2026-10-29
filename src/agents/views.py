import logging
from typing import Any

from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from pydantic import ValidationError

from agents.chat_errors import StrategyTimeoutError, UnknownStrategyError
from agents.chat_schemas import ChatRequest
from agents.chat_service import get_chat_service

logger = logging.getLogger(__name__)


def _validation_issues(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": list(error["loc"]),
            "code": error["type"],
            "message": error["msg"],
        }
        for error in exc.errors(
            include_input=False,
            include_context=False,
            include_url=False,
        )
    ]


def _error_response(code: str, message: str, status: int) -> JsonResponse:
    return JsonResponse(
        {"error": {"code": code, "message": message}},
        status=status,
    )


async def chat(request: HttpRequest) -> JsonResponse | HttpResponseNotAllowed:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = ChatRequest.model_validate_json(request.body)
    except ValidationError as exc:
        return JsonResponse(
            {"issues": _validation_issues(exc)},
            status=400,
        )

    try:
        result = await get_chat_service().execute(payload)
    except UnknownStrategyError:
        return _error_response(
            "unknown_strategy",
            "The requested strategy is not available.",
            422,
        )
    except StrategyTimeoutError:
        return _error_response(
            "strategy_timeout",
            "The strategy execution exceeded the time limit.",
            504,
        )
    except Exception:
        logger.exception("Unhandled failure while executing chat request")
        return _error_response(
            "internal_error",
            "The request could not be completed.",
            500,
        )

    return JsonResponse(result.model_dump(mode="json", exclude_none=True))
