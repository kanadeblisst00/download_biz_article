from loguru import logger
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel


api_router = APIRouter()

class DownloadPostData(BaseModel):
    url: str
    title: str
    pub_time: str
    copyright_stat: int = 0
    nickname: str = None


@api_router.post("/download")
async def download(options: DownloadPostData, request: Request):
    queue = request.app.state.task_queue
    task_dict = {
        "url": options.url,
        "title": options.title,
        "pub_time": options.pub_time,
        "copyright_stat": options.copyright_stat,
        "nickname": options.nickname
    }
    await queue.put(task_dict)
    logger.info(f"已将下载任务添加到队列: {task_dict}")
    return Response(status_code=200, content="任务已添加到下载队列")

@api_router.post("/downloads")
async def downloads(options: list[DownloadPostData], request: Request):
    for option in options:
        await download(option, request)
    return Response(status_code=200, content="任务已添加到下载队列")