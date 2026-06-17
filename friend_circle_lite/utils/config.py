import logging
import os

import requests
import yaml


def normalize_remote_config(payload):
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    config = data.get("config", {}) if isinstance(data, dict) else {}
    spider = config.get("spiderSettings", {}) if isinstance(config, dict) else {}
    merge = spider.get("mergeResult", {}) if isinstance(spider, dict) else {}

    return {
        "spider_settings": {
            "enable": spider.get("enabled", True),
            "json_url": spider.get("jsonUrl", "https://blapi.minsp.org/api/public/friend.json"),
            "article_count": int(spider.get("articleCount", 10) or 10),
            "merge_result": {
                "enable": merge.get("enabled", False),
                "merge_json_url": merge.get("mergeJsonUrl", "https://rss.minsp.org"),
            },
        },
        "specific_RSS": config.get("specificRSS", []) if isinstance(config.get("specificRSS", []), list) else [],
    }


def load_remote_config(remote_config):
    url = os.getenv("FCL_REMOTE_CONFIG_URL") or remote_config.get("url")
    if not url:
        return None

    headers = {
        "Accept": "application/json",
        "Origin": "https://www.minsp.org",
        "Referer": "https://www.minsp.org/",
        "User-Agent": "Friend-Circle-Lite/MinSP-RemoteConfig",
    }
    token = os.getenv("FCL_REMOTE_CONFIG_TOKEN") or remote_config.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = int(os.getenv("FCL_REMOTE_CONFIG_TIMEOUT", remote_config.get("timeout", 10)) or 10)
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return normalize_remote_config(response.json())

def load_config(config_file):
    """
    加载配置文件。
    
    参数：
    config_file (str): 配置文件的路径。
    
    返回：
    dict: 加载的配置数据。
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            local_config = yaml.safe_load(file) or {}
    except FileNotFoundError:
        logging.error(f"配置文件 {config_file} 未找到")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"YAML解析错误: {str(e)}")
        return {}
    except Exception as e:
        logging.error(f"加载配置文件时发生未知错误: {str(e)}")
        return {}

    remote_config = local_config.get("remote_config", {}) or {}
    remote_enabled = str(os.getenv("FCL_REMOTE_CONFIG_ENABLED", "")).lower() in ("1", "true", "yes")
    if remote_config.get("enable", False) or remote_enabled:
        try:
            loaded = load_remote_config(remote_config)
            if loaded:
                logging.info("已从远程接口加载朋友圈配置")
                return loaded
        except Exception as e:
            logging.warning(f"远程配置加载失败，回退到本地 conf.yaml: {e}")

    return local_config
