#!/usr/bin/env python3
"""
财联社（CLS）电报 API 抓取工具

逆向了财联社网站的 API 签名机制，可直接通过 HTTP 请求获取电报数据。
签名算法：MD5(SHA1(sorted_query_string))
  1. 参数按 key 字母升序排序
  2. 拼接为 key=value&key2=value2 格式
  3. 对拼接字符串做 SHA1 → 40位 hex
  4. 对 SHA1 结果再做 MD5 → 32位 hex（即最终 sign）

主要接口：
  - /api/cache?name=telegraph       获取最新电报列表（首页20条）
  - /v1/roll/get_roll_list          翻页获取历史电报
  - /api/cache?name=refreshTenTelegraph  增量刷新（获取新消息）
"""

import hashlib
import time
import json
import argparse
from datetime import datetime
from typing import Optional

import requests


class CLSTelegraph:
    """财联社电报 API 客户端"""

    BASE_URL = "https://www.cls.cn"
    DEFAULT_PARAMS = {
        "app": "CailianpressWeb",
        "os": "web",
        "sv": "8.7.9",
    }
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.cls.cn/telegraph",
        "Accept": "application/json, text/plain, */*",
    }

    @staticmethod
    def _sign(params: dict) -> str:
        """
        计算财联社 API 签名

        算法: MD5(SHA1(sorted_query_string))
        """
        if not params:
            sha1 = hashlib.sha1(b"").hexdigest()
            return hashlib.md5(sha1.encode()).hexdigest()

        # 参数按 key 字母升序排序，拼接为 key=value&...
        sorted_keys = sorted(params.keys())
        sign_str = "&".join(f"{k}={params[k]}" for k in sorted_keys)

        # 先 SHA1，再 MD5
        sha1 = hashlib.sha1(sign_str.encode()).hexdigest()
        md5 = hashlib.md5(sha1.encode()).hexdigest()
        return md5

    def _request(self, path: str, extra_params: Optional[dict] = None) -> dict:
        """发送带签名的 GET 请求"""
        params = dict(self.DEFAULT_PARAMS)
        if extra_params:
            params.update(extra_params)

        # 计算 sign 并追加到参数中
        params["sign"] = self._sign(params)

        url = f"{self.BASE_URL}{path}"
        resp = requests.get(url, params=params, headers=self.HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_latest(self) -> list[dict]:
        """
        获取最新电报列表（首页，约20条）

        Returns:
            电报列表，每条包含 id, title, brief, content, ctime, subjects 等字段
        """
        data = self._request("/api/cache", {"name": "telegraph"})
        if data.get("errno") != 0:
            raise RuntimeError(f"API 返回错误: {data.get('errno')} - {data.get('msg')}")
        return data.get("data", {}).get("roll_data", [])

    def get_history(self, last_time: int, rn: int = 20) -> list[dict]:
        """
        翻页获取历史电报（向过去翻页）

        Args:
            last_time: 上一次获取的最后一条电报的 ctime（Unix 时间戳）
            rn: 每页条数，默认20

        Returns:
            历史电报列表
        """
        data = self._request(
            "/v1/roll/get_roll_list",
            {"refresh_type": 1, "rn": rn, "last_time": last_time},
        )
        if data.get("errno") != 0:
            raise RuntimeError(f"API 返回错误: {data.get('errno')} - {data.get('msg')}")
        return data.get("data", {}).get("roll_data", [])

    def get_refresh(self, last_time: int) -> list[dict]:
        """
        增量刷新：获取指定时间之后的新电报

        Args:
            last_time: 当前已获取的最新一条电报的 ctime

        Returns:
            新增的电报列表
        """
        data = self._request(
            "/api/cache",
            {"name": "refreshTenTelegraph", "lastTime": last_time},
        )
        if data.get("errno") != 0:
            raise RuntimeError(f"API 返回错误: {data.get('errno')} - {data.get('msg')}")

        # refreshTenTelegraph 返回格式不同，新消息在 data["l"] 字典中
        result = data.get("data", {})
        if isinstance(result, dict) and "l" in result:
            return list(result["l"].values())
        return []

    def fetch_all(
        self,
        pages: int = 5,
        rn: int = 20,
    ) -> list[dict]:
        """
        批量抓取多页电报

        Args:
            pages: 抓取页数（首页 + pages-1 页历史）
            rn: 每页条数

        Returns:
            全部电报列表（按时间倒序）
        """
        all_items = self.get_latest()
        print(f"[第1页] 获取 {len(all_items)} 条")

        for page in range(2, pages + 1):
            if not all_items:
                break
            last_time = all_items[-1]["ctime"]
            time.sleep(0.5)  # 礼貌性延迟
            history = self.get_history(last_time, rn=rn)
            if not history:
                print(f"[第{page}页] 已无更多数据")
                break
            all_items.extend(history)
            print(f"[第{page}页] 获取 {len(history)} 条，累计 {len(all_items)} 条")

        return all_items


def format_telegraph(item: dict) -> str:
    """格式化单条电报为可读文本"""
    ts = item.get("ctime", 0)
    time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    title = item.get("title", "").strip()
    brief = item.get("brief", "").strip()
    content = item.get("content", "").strip()

    # 优先级: title > brief > content
    main_text = title or brief or content

    # 话题标签
    subjects = item.get("subjects", [])
    tags = " ".join(f"#{s['subject_name']}" for s in subjects if s.get("subject_name"))

    # 阅读数 / 评论数
    reading_num = item.get("reading_num", 0)
    comment_num = item.get("comment_num", 0)
    share_num = item.get("share_num", 0)

    line = f"[{time_str}] {main_text}"
    if tags:
        line += f"\n  📎 {tags}"
    line += f"\n  👁 {reading_num}  💬 {comment_num}  🔗 {share_num}"
    return line


def save_to_json(items: list[dict], filepath: str):
    """保存为 JSON 文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n已保存 {len(items)} 条到 {filepath}")


def main():
    parser = argparse.ArgumentParser(description="财联社电报 API 抓取工具")
    parser.add_argument(
        "-n", "--pages",
        type=int,
        default=3,
        help="抓取页数，每页约20条（默认: 3）",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="",
        help="保存到 JSON 文件（不指定则只打印）",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="只获取最新一页（不翻页）",
    )
    args = parser.parse_args()

    client = CLSTelegraph()

    print("=" * 60)
    print("  财联社电报 API 抓取工具")
    print("=" * 60)

    if args.latest_only:
        items = client.get_latest()
        print(f"\n获取最新 {len(items)} 条电报:\n")
    else:
        items = client.fetch_all(pages=args.pages)
        print(f"\n共获取 {len(items)} 条电报\n")

    print("-" * 60)
    for item in items:
        print(format_telegraph(item))
        print("-" * 60)

    if args.output:
        save_to_json(items, args.output)


if __name__ == "__main__":
    main()