from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger


async def global_exception_handler(request: Request, exc: Exception):
    """
    捕获所有未处理的异常
    """
    logger.exception(f"框架内部异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后再试！"}
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    捕获 HTTPException
    """
    logger.warning(f"HTTP 异常: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )