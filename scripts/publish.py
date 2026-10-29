#!/usr/bin/env python3
"""Publish due posts from posts/queue/*.json to Instagram (@filomarbella).

A post is due when publish_date <= today (Europe/Madrid) and it has not been
published yet. Published posts are moved to posts/published/ with the result.
The access token is read from the META_TOKEN environment variable (GitHub Secret).
"""
import datetime
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

GRAPH = "https://graph.facebook.com/v21.0"
IG_USER_ID = os.environ["IG_USER_ID"]
TOKEN = os.environ["META_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
DRY = os.environ.get("DRY_RUN") == "1"


def call(method, path, params=None):
    params = dict(params or {})
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        url += "?" + data.decode()
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # never print the token
        print(f"HTTP {e.code} on {path}: {body}", file=sys.stderr)
        raise


def wait_ready(container_id):
    for _ in range(30):
        st = call("GET", container_id, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} status {st}")
        time.sleep(5)
    raise RuntimeError(f"container {container_id} not ready in time")


def publish(post):
    urls = [RAW + urllib.parse.quote(p) for p in post["images"]]
    caption = post["caption"]
    if len(urls) == 1:
        c = call("POST", f"{IG_USER_ID}/media", {"image_url": urls[0], "caption": caption})
        wait_ready(c["id"])
        return call("POST", f"{IG_USER_ID}/media_publish", {"creation_id": c["id"]})
    children = []
    for u in urls:
        c = call("POST", f"{IG_USER_ID}/media", {"image_url": u, "is_carousel_item": "true"})
        wait_ready(c["id"])
        children.append(c["id"])
    car = call(
        "POST",
        f"{IG_USER_ID}/media",
        {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption},
    )
    wait_ready(car["id"])
    return call("POST", f"{IG_USER_ID}/media_publish", {"creation_id": car["id"]})


def main():
    today = datetime.datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    os.makedirs("posts/published", exist_ok=True)
    due = sorted(f for f in os.listdir("posts/queue") if f.endswith(".json"))
    done = 0
    for name in due:
        path = os.path.join("posts/queue", name)
        post = json.load(open(path, encoding="utf-8"))
        if post["publish_date"] > today:
            continue
        for img in post["images"]:
            if not os.path.exists(img):
                raise SystemExit(f"missing image {img} for {name}")
        print(f"Publishing {name} ...")
        if DRY:
            print("DRY RUN: skipped")
            continue
        res = publish(post)
        post["published_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        post["instagram_media_id"] = res.get("id")
        json.dump(post, open(os.path.join("posts/published", name), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        os.remove(path)
        done += 1
        print(f"Published {name}: {res.get('id')}")
    print(f"Done, {done} post(s) published.")


if __name__ == "__main__":
    main()
