#!/usr/bin/env python3
"""
DeepSeek Search & Fetch CLI Demo
基于 https://api-docs.deepseek.com/zh-cn/guides/search 实现
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests
import yaml


# ---------- 配置加载 ----------

def load_config(path: str = "config.yaml") -> dict[str, Any]:
    """加载 YAML 配置文件，缺失字段时给出明确提示。"""
    cfg_path = Path(path)
    if not cfg_path.exists():
        print(f"[错误] 配置文件不存在：{cfg_path.resolve()}", file=sys.stderr)
        print("请先在当前目录创建 config.yaml，并填入 api_key。", file=sys.stderr)
        sys.exit(1)

    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if not cfg.get("api_key") or cfg["api_key"].startswith("sk-your-"):
        print("[错误] 请先在 config.yaml 中填入真实的 api_key。", file=sys.stderr)
        sys.exit(1)

    return {
        "api_key": cfg["api_key"].strip(),
        "base_url": cfg.get("base_url", "https://api.deepseek.com").rstrip("/"),
        "timeout": int(cfg.get("timeout", 30)),
    }


# ---------- HTTP 请求封装 ----------

def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _post(cfg: dict[str, Any], endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    """向指定 endpoint 发送 POST 请求，并统一处理文档中列出的 HTTP 错误码。"""
    url = f"{cfg['base_url']}{endpoint}"
    try:
        resp = requests.post(
            url,
            headers=_headers(cfg["api_key"]),
            json=payload,
            timeout=cfg["timeout"],
        )
    except requests.RequestException as exc:
        print(f"[网络错误] 请求失败：{exc}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 200:
        return resp.json()

    # 文档第 57–63 行定义的标准错误格式
    try:
        err = resp.json().get("error", {})
    except json.JSONDecodeError:
        err = {}

    message = err.get("message", resp.text[:200])
    code = resp.status_code

    mapping = {
        400: "请求头或请求体不合法",
        401: "API Key 缺失或无效",
        402: "账号余额不足",
        403: "Fetch 请求被安全策略拒绝",
        404: "Fetch 未能获取可用网页内容",
        408: "读取请求体超时",
        413: "请求体超过大小限制",
        429: "超过 QPS 限制",
        500: "服务器内部错误",
        504: "下游请求超时",
    }
    hint = mapping.get(code, "未知错误")
    print(f"[HTTP {code}] {hint}", file=sys.stderr)
    print(f"        {message}", file=sys.stderr)

    if code in (408, 429) or 500 <= code < 600:
        print("提示：该错误可等待后重试。", file=sys.stderr)
    sys.exit(1)


# ---------- Search ----------

def cmd_search(cfg: dict[str, Any], args: argparse.Namespace) -> None:
    """调用 Search 接口并格式化输出。"""
    payload: dict[str, Any] = {
        "query": args.query,
        "count": args.count,
        "need_content": args.need_content,
    }
    if args.ori_question:
        payload["ori_question"] = args.ori_question
    if args.localization:
        payload["localization"] = args.localization

    data = _post(cfg, "/v1/tools/search", payload)
    results = data.get("results", [])

    if not results:
        print("搜索完成，但未找到匹配结果。")
        return

    print(f"共返回 {len(results)} 条结果\n")
    for idx, r in enumerate(results, 1):
        print("=" * 60)
        print(f"[{idx}] {r.get('title') or '(无标题)'}")
        print(f"    URL       : {r.get('url')}")
        print(f"    站点      : {r.get('site_name') or '-'}")
        print(f"    发布时间  : {r.get('date') or '-'}")
        print(f"    权威性    : {r.get('authority', -1)}")
        print(f"    排序分数  : {r.get('rerank_score', 0)}")
        print(f"    短摘要    : {r.get('snippet') or '-'}")
        print(f"    长摘要    : {r.get('summary') or '-'}")
        if args.need_content and r.get("content"):
            preview = r["content"][:300].replace("\n", " ")
            print(f"    正文预览  : {preview}...")


# ---------- Fetch ----------

def cmd_fetch(cfg: dict[str, Any], args: argparse.Namespace) -> None:
    """调用 Fetch 接口并输出 Markdown 正文。"""
    data = _post(cfg, "/v1/tools/fetch", {"url": args.url})
    title = data.get("title") or "(无标题)"
    content = data.get("content") or ""

    if not content:
        print("抓取成功，但未返回正文内容。")
        return

    print(f"标题：{title}\n")
    print("-" * 60)
    print(content)

    if args.save:
        out = Path(args.save)
        out.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        print(f"\n[已保存] {out.resolve()}")


# ---------- CLI 入口 ----------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deepseek-search-demo",
        description="DeepSeek Search & Fetch 命令行演示程序",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径（默认：config.yaml）",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # search 子命令
    p_search = sub.add_parser("search", help="网页搜索")
    p_search.add_argument("query", help="搜索词，1～128 字符，支持 site:、lang:、after: 等语法")
    p_search.add_argument("-n", "--count", type=int, default=10, help="返回条数 1～50（默认 10）")
    p_search.add_argument("--need-content", action="store_true", help="是否在结果中返回网页正文")
    p_search.add_argument("--ori-question", default="", help="触发搜索的用户原始问题（可选）")
    p_search.add_argument("--localization", default="", help="用于本地化结果的 IP 地址（可选）")
    p_search.set_defaults(func=cmd_search)

    # fetch 子命令
    p_fetch = sub.add_parser("fetch", help="抓取单个网页")
    p_fetch.add_argument("url", help="要抓取的 HTTP/HTTPS URL")
    p_fetch.add_argument("-s", "--save", default="", help="将 Markdown 正文保存到指定文件")
    p_fetch.set_defaults(func=cmd_fetch)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config(args.config)
    args.func(cfg, args)


if __name__ == "__main__":
    main()