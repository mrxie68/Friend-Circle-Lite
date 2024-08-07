from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from threading import Lock
import logging
import os
import json
import random

from friend_circle_lite.get_info import fetch_and_process_data, sort_articles_by_time
from friend_circle_lite.get_conf import load_config

app = FastAPI()

# 配置APScheduler
scheduler = AsyncIOScheduler()
scheduler.start()

# 配置日志记录
log_file = "grab.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 全局变量
articles_data = {
    "statistical_data": {},
    "article_data": []
}
error_friends_info = []
data_lock = Lock()

def fetch_articles():
    global articles_data, error_friends_info
    logging.info("开始抓取文章...")
    config = load_config("./conf.yaml")
    if config["spider_settings"]["enable"]:
        json_url = config['spider_settings']['json_url']
        article_count = config['spider_settings']['article_count']
        logging.info(f"正在从 {json_url} 中获取，每个博客获取 {article_count} 篇文章")
        try:
            result, errors = fetch_and_process_data(json_url=json_url, count=article_count)
            sorted_result = sort_articles_by_time(result)
            with data_lock:
                articles_data = sorted_result
                error_friends_info = errors
            logging.info("文章抓取成功")
        except Exception as e:
            logging.error(f"抓取文章时出错: {e}")

# 每四个小时抓取一次文章
scheduler.add_job(fetch_articles, 'interval', hours=4)

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Friend Circle Lite</title>
    </head>
    <body>
        <h1>欢迎使用 Friend Circle Lite</h1>
        <p>这是一个轻量版友链朋友圈，有两种部署方式，其中自部署使用 fastAPI，还有 github action 部署方式，可以很方便的从友链中获取文章并展示到前端。</p>
        <ul>
            <li><a href="/all">查看所有文章，按照时间进行排序</a></li>
            <li><a href="/errors">查看出错误数据，包含所有的错误友链信息，可自行发挥</a></li>
            <li><a href="/random">随机文章</a></li>
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get('/all')
async def get_all_articles():
    with data_lock:
        return JSONResponse(content=articles_data)

@app.get('/errors')
async def get_error_friends():
    with data_lock:
        return JSONResponse(content=error_friends_info)

@app.get('/random')
async def get_random_article():
    with data_lock:
        if articles_data["article_data"]:
            random_article = random.choice(articles_data["article_data"])
            return JSONResponse(content=random_article)
        else:
            return JSONResponse(content={"error": "No articles available"}, status_code=404)

if __name__ == '__main__':
    import uvicorn

    # 清空日志文件
    if os.path.exists(log_file):
        with open(log_file, 'w'):
            pass

    fetch_articles()  # 启动时立即抓取一次
    uvicorn.run(app, host='0.0.0.0', port=1223)
