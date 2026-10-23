#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily public-RSS updater for AI Law Radar. Python standard library only."""
import hashlib, html, json, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT
DATA = SITE / "data.json"
USER_AGENT = "Mozilla/5.0 (compatible; AILawRadar/2.0; educational project)"
QUERIES = [
    ("中国网信网", "site:cac.gov.cn (人工智能 OR 生成式人工智能 OR 算法推荐 OR 深度合成 OR 内容标识)"),
    ("最高人民法院", "site:court.gov.cn 人工智能 (意见 OR 司法 OR 案例 OR 侵权 OR 知识产权)"),
    ("中国政府网", "site:gov.cn 人工智能 (法律 OR 政策 OR 监管 OR 办法 OR 规定)"),
    ("工业和信息化部", "site:miit.gov.cn 人工智能 (监管 OR 规范 OR 标识 OR 政策)"),
    ("国家发展改革委", "site:ndrc.gov.cn 人工智能 (法规 OR 规范 OR 招标投标 OR 政策)"),
]
AI_TERMS = ["人工智能", "生成式人工智能", "算法推荐", "深度合成", "大模型", "AI生成", "AI换脸", "人工智能生成合成", "智能算法"]
LEGAL_TERMS = ["法律", "法规", "办法", "规定", "意见", "通知", "政策", "监管", "司法", "法院", "审理", "判决", "案例", "备案", "标识", "执法", "处罚", "合规", "侵权", "著作权", "知识产权", "个人信息", "数据安全", "行政", "国家标准", "标准", "招标投标", "登记"]

class Strip(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        if data and data.strip():
            self.parts.append(data.strip())

def clean(value):
    parser = Strip()
    try:
        parser.feed(value or "")
    except Exception:
        pass
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()

def ident(url, title, source):
    raw = (url.strip() + "|" + title.strip() + "|" + source.strip()).encode("utf-8", "ignore")
    return hashlib.sha256(raw).hexdigest()[:20]

def parse_date(value):
    if not value:
        return "日期未提供"
    try:
        return parsedate_to_datetime(value).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value.strip()

def classify(title, snippet):
    text = title + " " + snippet
    if any(k in text for k in ("备案", "登记")):
        category, focus = "备案与合规", "核对备案/登记对象、适用范围、信息公示和持续合规要求。"
    elif any(k in text for k in ("著作权", "知识产权", "训练数据", "专利")):
        category, focus = "知识产权", "关注训练数据来源、生成内容权利归属及开发者、服务者与使用者责任。"
    elif any(k in text for k in ("个人信息", "隐私", "数据安全")):
        category, focus = "数据与个人信息", "关注个人信息处理依据、权益保护、数据安全及相关主体责任。"
    elif any(k in text for k in ("标识", "深度合成", "生成合成内容")):
        category, focus = "生成内容标识", "关注显式/隐式标识、平台核验义务与用户声明责任。"
    elif any(k in text for k in ("法院", "司法", "审理", "判决", "案例", "侵权")):
        category, focus = "司法规则与案例", "关注裁判规则、责任分配、适用法律以及对企业和用户行为的影响。"
    elif "算法" in text:
        category, focus = "算法治理", "关注算法透明度、用户权益、平台义务与监管机制。"
    elif any(k in text for k in ("招标投标", "行政", "执法", "处罚")):
        category, focus = "行政监管与执法", "关注监管权限、程序要求、责任承担及对行政相对人的影响。"
    else:
        category, focus = "AI政策动态", "进一步核对文件效力层级、适用对象、生效时间与配套规则。"
    score = sum(1 for k in LEGAL_TERMS if k in text)
    priority = "高" if score >= 3 or any(k in text for k in ("办法", "规定", "意见", "司法解释", "处罚", "裁判规则")) else "中"
    return category, focus, priority

def fetch(label, query):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"})
    last_error = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=18) as response:
                payload = response.read()
            root = ET.fromstring(payload)
            entries = []
            for node in root.findall(".//item"):
                title = clean(node.findtext("title", ""))
                link = node.findtext("link", "").strip()
                description = clean(node.findtext("description", ""))
                source_node = node.find("source")
                source = (source_node.text or label).strip() if source_node is not None else label
                joined = title + " " + description
                if not any(k.lower() in joined.lower() for k in AI_TERMS):
                    continue
                if not any(k in joined for k in LEGAL_TERMS):
                    continue
                category, focus, priority = classify(title, description)
                entries.append({
                    "id": ident(link, title, source), "title": title or "（无标题）", "url": link,
                    "date": parse_date(node.findtext("pubDate", "")), "source": source,
                    "description": description, "category": category, "focus": focus,
                    "priority": priority, "query_group": label, "is_new": False, "is_sample": False,
                })
            return entries
        except Exception as error:
            last_error = error
            if attempt == 0:
                time.sleep(1)
    raise RuntimeError(type(last_error).__name__ + ": " + str(last_error))

def read_previous():
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception:
        return {}

def sample_items():
    samples = [
        {"date":"2026-09-07","source":"中华人民共和国最高人民法院","title":"最高法发布《关于依法审理涉人工智能纠纷案件的意见》","url":"https://www.court.gov.cn/zixun/xiangqing/511101.html","category":"司法规则与案例","priority":"高","description":"最高人民法院发布涉人工智能纠纷案件审理意见，涉及人工智能侵权责任、人格权益与个人信息保护、知识产权、模型训练数据以及 AI 换脸拟声等问题。请打开原文核验具体条文。","focus":"这是司法裁判规则指引，需结合民法典、个人信息保护法、著作权法等现行规范理解适用。"},
        {"date":"2026-09-14","source":"中央网络安全和信息化委员会办公室（中国网信网）","title":"关于发布生成式人工智能服务已备案信息的公告（2026年7月至8月）","url":"https://www.cac.gov.cn/2026-09/14/c_1791136833136332.htm","category":"备案与合规","priority":"高","description":"公告涉及生成式人工智能服务备案及应用、功能登记动态，可继续关注服务主体边界和信息公示要求。请打开官方原文核验具体数据及要求。","focus":"关注生成式人工智能服务备案/登记的主体边界、信息公示义务，以及应用调用模型能力时的登记要求。"},
    ]
    for item in samples:
        item.update({"id":ident(item["url"], item["title"], item["source"]), "is_new":False, "is_sample":True, "query_group":"预置官方来源样例（非实时）"})
    return samples

def main():
    SITE.mkdir(parents=True, exist_ok=True)
    previous = read_previous()
    seen = set(previous.get("seen_ids", []))
    previous_items = previous.get("items", []) if isinstance(previous.get("items", []), list) else []
    errors, source_stats, fresh = [], [], {}
    print("AI 法规雷达：开始每日抓取")
    for label, query in QUERIES:
        try:
            entries = fetch(label, query)
            source_stats.append({"label":label, "status":"ok", "count":len(entries), "error":""})
            print("[OK] " + label + ": " + str(len(entries)) + " 条")
            for item in entries:
                fresh.setdefault(item["id"], item)
        except Exception as error:
            message = label + ": " + str(error)
            errors.append(message)
            source_stats.append({"label":label, "status":"error", "count":0, "error":str(error)})
            print("[WARN] " + message)

    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S UTC+08:00")
    ok_count = sum(1 for item in source_stats if item["status"] == "ok")
    if fresh:
        status = "live" if not errors else "partial"
        combined = {x.get("id"):x for x in previous_items if x.get("id") and not x.get("is_sample")}
        combined.update(fresh)
        cutoff = datetime.now(timezone.utc) - timedelta(days=45)
        items = []
        for item in combined.values():
            raw_date = item.get("date", "")
            parsed = None
            try:
                parsed = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                try:
                    parsed = parsedate_to_datetime(raw_date)
                except Exception:
                    pass
            if parsed is not None:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed < cutoff:
                    continue
            item["is_new"] = item["id"] not in seen
            item["is_sample"] = False
            items.append(item)
        items.sort(key=lambda x:x.get("date", ""), reverse=True)
        seen.update(fresh.keys())
    elif any(not x.get("is_sample") for x in previous_items):
        status = "stale" if ok_count == 0 else "partial"
        items = [dict(x, is_new=False) for x in previous_items if not x.get("is_sample")]
    else:
        status = "offline_demo"
        items = sample_items()

    data = {
        "project":"AI 法规雷达", "generated_at":now, "status":status,
        "source_method":"Google News RSS search with queries restricted to official Chinese government and judicial domains",
        "schedule":"Daily refresh at 09:17 Asia/Singapore/Beijing time, with backup refreshes at 09:47 and 10:17",
        "source_errors":errors, "sources":source_stats, "item_count":len(items),
        "new_count":sum(1 for x in items if x.get("is_new")) if status in ("live", "partial") else 0,
        "seen_ids":list(seen)[-5000:], "items":items,
    }
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Finished: status=" + status + "; items=" + str(len(items)) + "; newly seen=" + str(data["new_count"]) + "; source errors=" + str(len(errors)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
