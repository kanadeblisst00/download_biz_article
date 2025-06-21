import asyncio
import json
import os
from contextlib import asynccontextmanager
from ..browser.launch import ChromeManager
from ..browser.manager import PlaywrightHtmlManager
from ..settings import ROOT_DIR


async def download_task_handler(app, task_event):
    task_queue = app.state.task_queue
    chrome_manager = app.state.chrome_manager
    manager = PlaywrightHtmlManager(chrome_manager)
    while not task_event.is_set():
        task = await task_queue.get()
        if task is None: 
            await asyncio.sleep(1)  
            continue
        try:
            await manager.browser_get(task)
        except Exception as e:
            print(f"处理任务时发生错误: {e}")
        await asyncio.sleep(5)

async def save_unfinished_tasks(task_queue):
    tasks = []
    while not task_queue.empty():
        task = await task_queue.get()
        if task is not None:
            tasks.append(task)
    if tasks:
        path = os.path.join(ROOT_DIR, "unfinished_tasks.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

async def load_unfinished_tasks(task_queue):
    unfinished_path = os.path.join(ROOT_DIR, "unfinished_tasks.json")
    if os.path.exists(unfinished_path):
        with open(unfinished_path, "r", encoding="utf-8") as f:
            try:
                unfinished_tasks = json.load(f)
                for task in unfinished_tasks:
                    await task_queue.put(task)
            except Exception as e:
                print(f"恢复未完成任务时发生错误: {e}")
        try:
            os.remove(unfinished_path)  
        except Exception as e:
            print(f"删除未完成任务文件时发生错误: {e}")

def get_lifespan(settings):
    @asynccontextmanager
    async def lifespan(app):
        task_queue = asyncio.Queue()
        task_event = asyncio.Event()
        # 从文件恢复未完成的任务到队列
        await load_unfinished_tasks(task_queue)
        app.state.task_queue = task_queue
        app.state.settings = settings["base"]
        app.state.chrome_manager = ChromeManager(app, settings)
        await app.state.chrome_manager.__aenter__()
        if not settings["base"].get("save_path"):
            raise ValueError("Save path is not configured in settings.")
        app.state.save_path = settings["base"]["save_path"]
        asyncio.create_task(download_task_handler(app, task_event))
        yield {"task_queue": task_queue}
        await app.state.chrome_manager.__aexit__(None, None, None)
        task_event.set()
        # 保存未完成的任务
        await save_unfinished_tasks(task_queue)
        
    return lifespan