import os
import sys
import asyncio
import uvicorn
from loguru import logger
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from module.api.lifespan import get_lifespan
from module.api.route import api_router
from module.settings import *
from module.api.exception_handler import global_exception_handler, http_exception_handler
from module.middlewares import *
from module.tools import read_ini_file

# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
config_dict = read_ini_file()

api_port = int(config_dict["base"].get("api_port", API_PORT))
log_level = config_dict.get("logger", {}).get("log_level", "INFO")

def main():
    logger.remove(handler_id=None)
    log_path = os.path.join(ROOT_DIR, "logger")
    os.makedirs(log_path, exist_ok=True)
    logger.add(sys.stdout,  level=log_level)
    logger.add(os.path.join(log_path, "web_app.log"),  level=log_level, compression="zip", rotation="1 days")

    app = FastAPI(lifespan=get_lifespan(config_dict), debug=DEBUG)
    # 后进先执行

    app.add_exception_handler(Exception, global_exception_handler) 
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.include_router(api_router)
    return app


if __name__ == "__main__":
    uvicorn.run(main(), host="0.0.0.0", port=API_PORT, lifespan="on")
