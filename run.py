import logging

from friend_circle_lite.all_friends import (
    deal_with_large_data,
    fetch_and_process_data,
    marge_data_from_json_url,
    marge_errors_from_json_url,
)
from friend_circle_lite.utils.config import load_config
from friend_circle_lite.utils.json import write_json


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)


def main() -> None:
    config = load_config("./conf.yaml")
    spider_settings = config.get("spider_settings", {})

    if not spider_settings.get("enable", False):
        logging.info("Spider is disabled.")
        return

    json_url = spider_settings["json_url"]
    article_count = spider_settings["article_count"]
    specific_rss = config.get("specific_RSS", [])

    logging.info("Fetching friend links from %s", json_url)
    result, lost_friends = fetch_and_process_data(
        json_url=json_url,
        specific_RSS=specific_rss,
        count=article_count,
        cache_file="./temp/cache.json",
    )

    merge_settings = spider_settings.get("merge_result", {})
    if merge_settings.get("enable", False):
        merge_url = merge_settings["merge_json_url"].rstrip("/")
        logging.info("Merging external data from %s", merge_url)
        result = marge_data_from_json_url(result, f"{merge_url}/all.json")
        lost_friends = marge_errors_from_json_url(lost_friends, f"{merge_url}/errors.json")

    result = deal_with_large_data(result)

    write_json("./all.json", result)
    write_json("./errors.json", lost_friends)
    logging.info("Generated all.json and errors.json")


if __name__ == "__main__":
    main()
