#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
国内场外基金数据抓取 + 手动量化扫描

功能：
1. 获取全部基金代码列表
2. 获取单只基金实时估值 / 最新净值
3. 获取单只基金历史净值
4. 自动按板块挑选基金，并输出建议买入/建议卖出或回避的基金

示例：
python fund_fetcher.py
python fund_fetcher.py --mode scan
python fund_fetcher.py --mode scan --sector 黄金
python fund_fetcher.py --code 000001
python fund_fetcher.py --code 000001 --history --pages 5
python fund_fetcher.py --list
"""

import argparse
import os
import json
import random
import re
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://fund.eastmoney.com/",
}


@dataclass
class QuantConfig:
    history_pages: int = int(os.getenv("FUND_HISTORY_PAGES", "8"))
    history_per_page: int = int(os.getenv("FUND_HISTORY_PER_PAGE", "49"))
    min_history: int = int(os.getenv("FUND_MIN_HISTORY", "120"))
    score_buy: int = int(os.getenv("FUND_SCORE_BUY", "4"))
    score_sell: int = int(os.getenv("FUND_SCORE_SELL", "-4"))
    request_sleep_min: float = float(os.getenv("FUND_SLEEP_MIN", "0.5"))
    request_sleep_max: float = float(os.getenv("FUND_SLEEP_MAX", "1.2"))
    candidates_per_sector: int = int(os.getenv("FUND_CANDIDATES_PER_SECTOR", "2"))
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    mail_to: str = os.getenv("MAIL_TO", "")


CFG = QuantConfig()

SECTOR_KEYWORDS = {
    "黄金": ["黄金"],
    "医药": ["医疗", "医药", "生物医药"],
    "新能源": ["新能源", "光伏", "电池", "新能源汽车"],
    "半导体": ["半导体", "芯片", "集成电路"],
    "消费": ["消费", "白酒", "食品饮料"],
    "红利": ["红利", "高股息"],
    "军工": ["军工", "国防"],
    "港股科技": ["恒生科技", "互联网", "港股通科技", "中概互联网"],
    "人工智能": ["人工智能", "AI人工智能", "机器人", "算力"],
    "券商": ["证券", "券商", "证券公司"],
    "银行": ["银行"],
    "煤炭": ["煤炭"],
    "有色": ["有色", "有色金属", "稀有金属"],
    "稀土": ["稀土"],
    "沪深300": ["沪深300"],
    "上证50": ["上证50", "50ETF", "上证50ETF"],
    "中证500": ["中证500"],
    "中证1000": ["中证1000"],
    "创业板": ["创业板", "创业板指"],
    "科创": ["科创", "科创50"],
    "纳指": ["纳指", "纳斯达克", "纳斯达克100"],
    "标普500": ["标普500", "标普"],
    "恒生": ["恒生", "恒生指数"],
    "港股红利": ["港股红利", "恒生红利"],
    "通信": ["通信", "5G"],
    "计算机": ["计算机", "软件", "信创"],
    "传媒": ["传媒", "影视", "文娱"],
    "游戏": ["游戏", "动漫"],
    "家电": ["家电"],
    "地产": ["地产", "房地产"],
    "基建": ["基建", "建筑", "建材"],
    "农业": ["农业", "农牧", "种业"],
    "环保": ["环保", "绿色电力", "碳中和"],
    "电力": ["电力", "公用事业"],
    "化工": ["化工"],
    "汽车": ["汽车", "整车", "汽车零部件"],
    "央企国企": ["央企", "国企", "国企改革"],
    "美股科技": ["全球互联", "美国科技", "海外科技"],
    "日经": ["日经", "日本"],
    "德国": ["德国", "德国DAX"],
}


def request_text(url: str, timeout: int = 10, retries: int = 3) -> str:
    """
    带重试的 GET 请求
    """
    last_error = None

    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except Exception as e:
            last_error = e
            sleep_seconds = 1 + i + random.random()
            time.sleep(sleep_seconds)

    raise RuntimeError(f"请求失败：{url}, error={last_error}")


def get_fund_list() -> pd.DataFrame:
    """
    获取基金代码列表

    接口返回格式大致为：
    var r = [
      ["000001","HXCZHH","华夏成长混合","混合型-灵活","HUAXIACHENGZHANGHUNHE"],
      ...
    ];
    """
    url = "https://fund.eastmoney.com/js/fundcode_search.js"
    text = request_text(url)

    match = re.search(r"var\s+r\s*=\s*(\[.*\]);?", text, re.S)
    if not match:
        raise ValueError("无法解析基金列表返回内容")

    data = json.loads(match.group(1))

    df = pd.DataFrame(
        data,
        columns=["基金代码", "拼音简称", "基金名称", "基金类型", "拼音全称"],
    )
    df["基金代码"] = df["基金代码"].astype(str).str.zfill(6)
    return df


def get_fund_name_map() -> Dict[str, str]:
    df = get_fund_list()
    return dict(zip(df["基金代码"], df["基金名称"]))


def _class_preference_score(name: str) -> int:
    if re.search(r"(联接)?A(类)?$", name):
        return 0
    if re.search(r"(联接)?C(类)?$", name):
        return 3
    if re.search(r"(联接)?E(类)?$", name):
        return 4
    if re.search(r"(联接)?[FIY]$", name):
        return 5
    return 1


def auto_select_sector_funds(fund_list: pd.DataFrame, sector: Optional[str] = None) -> pd.DataFrame:
    if sector and sector not in SECTOR_KEYWORDS:
        raise ValueError(f"未知板块: {sector}；可选板块: {', '.join(SECTOR_KEYWORDS)}")

    target_sectors = {sector: SECTOR_KEYWORDS[sector]} if sector else SECTOR_KEYWORDS
    selections = []

    for sector_name, keywords in target_sectors.items():
        pattern = "|".join(re.escape(keyword) for keyword in keywords)
        sector_df = fund_list[fund_list["基金名称"].str.contains(pattern, regex=True, na=False)].copy()
        if sector_df.empty:
            continue

        sector_df["sector"] = sector_name
        sector_df["class_score"] = sector_df["基金名称"].apply(_class_preference_score)
        sector_df["index_score"] = (~sector_df["基金名称"].str.contains("指数|ETF|LOF|联接", regex=True, na=False)).astype(int)
        sector_df["keyword_order"] = sector_df["基金名称"].apply(
            lambda name: min((idx for idx, keyword in enumerate(keywords) if keyword in name), default=99)
        )
        sector_df = sector_df.sort_values(
            ["index_score", "class_score", "keyword_order", "基金代码"],
            ascending=[True, True, True, True],
        )
        sector_df = sector_df.drop_duplicates(subset=["基金名称"], keep="first")
        sector_df = sector_df.head(CFG.candidates_per_sector)
        selections.append(sector_df[["sector", "基金代码", "基金名称", "基金类型"]])

    if not selections:
        raise ValueError("没有筛选到任何板块基金，请检查关键词配置")

    out = pd.concat(selections, ignore_index=True)
    out = out.drop_duplicates(subset=["基金代码"], keep="first")
    return out


def get_realtime_fund(code: str) -> Dict:
    """
    获取单只基金实时估值 / 最新净值

    返回字段示例：
    {
        "fundcode": "000001",
        "name": "华夏成长混合",
        "jzrq": "2026-xx-xx",
        "dwjz": "x.xxxx",
        "gsz": "x.xxxx",
        "gszzl": "x.xx",
        "gztime": "2026-xx-xx 15:00"
    }
    """
    code = str(code).zfill(6)
    ts = int(time.time() * 1000)
    url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"

    text = request_text(url)

    # 返回形如：jsonpgz({...});
    match = re.search(r"jsonpgz\((\{.*?\})\);?", text, re.S)
    if not match:
        raise ValueError(f"无法解析实时基金数据，基金代码：{code}，返回内容：{text[:100]}")

    return json.loads(match.group(1))


def get_history_nav(code: str, page: int = 1, per: int = 20) -> pd.DataFrame:
    """
    获取单只基金历史净值，单页

    接口返回 HTML 片段，表格字段通常包括：
    净值日期、单位净值、累计净值、日增长率、申购状态、赎回状态、分红送配
    """
    code = str(code).zfill(6)

    url = (
        "https://fundf10.eastmoney.com/F10DataApi.aspx"
        f"?type=lsjz&code={code}&page={page}&per={per}"
    )

    text = request_text(url)

    soup = BeautifulSoup(text, "lxml")
    rows = soup.select("tbody tr")

    records = []
    for row in rows:
        cols = [c.get_text(strip=True) for c in row.select("td")]
        if len(cols) >= 7:
            records.append(
                {
                    "净值日期": cols[0],
                    "单位净值": cols[1],
                    "累计净值": cols[2],
                    "日增长率": cols[3],
                    "申购状态": cols[4],
                    "赎回状态": cols[5],
                    "分红送配": cols[6],
                }
            )

    df = pd.DataFrame(records)

    if not df.empty:
        df["基金代码"] = code

        # 尝试转换数值
        for col in ["单位净值", "累计净值"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["日增长率"] = (
            df["日增长率"]
            .astype(str)
            .str.replace("%", "", regex=False)
        )
        df["日增长率"] = pd.to_numeric(df["日增长率"], errors="coerce")

    return df


def get_history_nav_multi_pages(
    code: str,
    pages: int = 5,
    per: int = 20,
    sleep_min: float = 0.5,
    sleep_max: float = 1.5,
) -> pd.DataFrame:
    """
    获取多页历史净值
    """
    all_df = []

    for page in range(1, pages + 1):
        print(f"正在抓取 {code} 第 {page}/{pages} 页历史净值...")
        df = get_history_nav(code, page=page, per=per)

        if df.empty:
            print(f"第 {page} 页为空，停止。")
            break

        all_df.append(df)
        time.sleep(random.uniform(sleep_min, sleep_max))

    if not all_df:
        return pd.DataFrame()

    result = pd.concat(all_df, ignore_index=True)
    return result


def normalize_nav_history(df: pd.DataFrame, code: str = "") -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError(f"基金历史净值为空: {code}")

    out = df.copy()
    out["净值日期"] = pd.to_datetime(out["净值日期"], errors="coerce")
    out["单位净值"] = pd.to_numeric(out["单位净值"], errors="coerce")
    out = out.dropna(subset=["净值日期", "单位净值"])
    out = out.drop_duplicates(subset=["净值日期"], keep="first")
    out = out.sort_values("净值日期")
    out = out.rename(columns={"净值日期": "date", "单位净值": "nav"})
    out = out.set_index("date")

    if out.empty:
        raise ValueError(f"基金历史净值清洗后为空: {code}")

    return out[["nav"]]


def add_nav_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = normalize_nav_history(df).copy()
    nav = x["nav"]
    x["ret1"] = nav.pct_change()
    x["ma5"] = nav.rolling(5).mean()
    x["ma10"] = nav.rolling(10).mean()
    x["ma20"] = nav.rolling(20).mean()
    x["ma60"] = nav.rolling(60).mean()
    x["ma120"] = nav.rolling(120).mean()
    x["high20"] = nav.rolling(20).max()
    x["high60"] = nav.rolling(60).max()
    x["low60"] = nav.rolling(60).min()
    x["mom10"] = nav / nav.shift(10) - 1
    x["mom20"] = nav / nav.shift(20) - 1
    x["mom60"] = nav / nav.shift(60) - 1
    x["vol20"] = x["ret1"].rolling(20).std() * np.sqrt(252)
    x["vol60"] = x["ret1"].rolling(60).std() * np.sqrt(252)
    x["drawdown20"] = nav / x["high20"] - 1

    delta = nav.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    x["rsi14"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    ema12 = nav.ewm(span=12, adjust=False).mean()
    ema26 = nav.ewm(span=26, adjust=False).mean()
    x["macd"] = ema12 - ema26
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["macd_hist"] = x["macd"] - x["macd_signal"]

    return x.dropna()


def score_fund_signal(row: pd.Series, prev: pd.Series) -> tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    if row.nav > row.ma120 and row.ma20 > row.ma60 > row.ma120:
        score += 2
        reasons.append("长期趋势向上")
    if row.nav < row.ma120 and row.ma20 < row.ma60:
        score -= 2
        reasons.append("跌破长期趋势")

    if row.nav >= row.high60 * 0.995:
        score += 2
        reasons.append("逼近60日新高")
    if row.nav <= row.low60 * 1.005:
        score -= 2
        reasons.append("逼近60日低点")

    if row.mom20 > 0 and row.mom60 > 0 and row.mom20 > prev.mom20:
        score += 1
        reasons.append("中期动量改善")
    if row.mom20 < 0 and row.mom60 < 0 and row.mom20 < prev.mom20:
        score -= 1
        reasons.append("中期动量恶化")

    if prev.macd_hist <= 0 and row.macd_hist > 0:
        score += 1
        reasons.append("MACD转正")
    if prev.macd_hist >= 0 and row.macd_hist < 0:
        score -= 1
        reasons.append("MACD转负")

    if row.rsi14 > 76 and row.nav > row.ma20 * 1.06:
        score -= 1
        reasons.append("短线偏热")
    if row.drawdown20 < -0.08 and row.nav < row.ma60:
        score -= 1
        reasons.append("回撤偏深且弱于中期均线")
    if row.vol20 > row.vol60 * 1.2 and row.nav < row.ma20:
        score -= 1
        reasons.append("波动放大且净值偏弱")

    return score, reasons


def analyze_fund_signal(df: pd.DataFrame) -> Dict:
    ind = add_nav_indicators(df)
    if len(ind) < 3:
        return {
            "raw_signal": "NO_DATA",
            "tomorrow_action": "WAIT",
            "if_held_action": "REVIEW",
            "score": 0,
            "reasons": ["历史净值不足，无法判断明日买点"],
        }

    row, prev = ind.iloc[-1], ind.iloc[-2]
    score, reasons = score_fund_signal(row, prev)
    nav = float(row.nav)

    raw_signal = "BUY" if score >= CFG.score_buy else "SELL_OR_AVOID" if score <= CFG.score_sell else "HOLD"

    if raw_signal == "BUY":
        tomorrow_action = "BUY_TOMORROW"
        tomorrow_note = "今晚可加入明日申购观察，优先在趋势延续时买入"
    else:
        tomorrow_action = "WAIT"
        tomorrow_note = "今晚不建议为明天主动申购加仓"

    redeem_reasons = []
    if raw_signal == "SELL_OR_AVOID":
        redeem_reasons.append("模型进入SELL_OR_AVOID")
    if nav < row.ma20:
        redeem_reasons.append("净值跌破MA20")
    if nav < row.ma60:
        redeem_reasons.append("净值跌破MA60")
    if row.macd_hist < 0 and prev.macd_hist >= 0:
        redeem_reasons.append("MACD转负")
    if row.mom20 < 0 and row.mom60 < 0:
        redeem_reasons.append("20/60日动量均为负")

    if redeem_reasons:
        if_held_action = "REDEEM_OR_REVIEW"
        held_note = "若已持有，明天优先考虑减仓或复核持仓逻辑"
    else:
        if_held_action = "HOLD_OR_WATCH"
        held_note = "若已持有，可继续持有并观察趋势是否延续"

    return {
        "raw_signal": raw_signal,
        "tomorrow_action": tomorrow_action,
        "if_held_action": if_held_action,
        "score": score,
        "latest_nav": round(nav, 4),
        "ma20": round(float(row.ma20), 4),
        "ma60": round(float(row.ma60), 4),
        "ma120": round(float(row.ma120), 4),
        "mom20_pct": round(float(row.mom20) * 100, 2),
        "mom60_pct": round(float(row.mom60) * 100, 2),
        "rsi14": round(float(row.rsi14), 2),
        "vol20_pct": round(float(row.vol20) * 100, 2),
        "date": str(ind.index[-1].date()),
        "reasons": reasons + [tomorrow_note, held_note] + redeem_reasons,
    }


def fetch_signal_history(code: str, pages: Optional[int] = None, per: Optional[int] = None) -> pd.DataFrame:
    return get_history_nav_multi_pages(
        code,
        pages=pages or CFG.history_pages,
        per=per or CFG.history_per_page,
        sleep_min=CFG.request_sleep_min,
        sleep_max=CFG.request_sleep_max,
    )


def send_email(subject: str, body: str):
    if not all([CFG.smtp_host, CFG.smtp_user, CFG.smtp_password, CFG.mail_to]):
        print(f"[WARN] 邮件环境变量未配置，跳过邮件发送：{subject}")
        return

    msg = MIMEMultipart()
    msg["From"] = CFG.smtp_user
    msg["To"] = CFG.mail_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(CFG.smtp_host, CFG.smtp_port, context=context) as server:
        server.login(CFG.smtp_user, CFG.smtp_password)
        server.sendmail(CFG.smtp_user, [CFG.mail_to], msg.as_string())


def scan_fund_pool(sector: Optional[str] = None, save: bool = True) -> pd.DataFrame:
    fund_list = get_fund_list()
    candidate_funds = auto_select_sector_funds(fund_list, sector=sector)

    rows = []
    for item in candidate_funds.itertuples(index=False):
        code = item.基金代码
        try:
            history = fetch_signal_history(code)
            nav_history = normalize_nav_history(history, code)
            if len(nav_history) < CFG.min_history:
                raise ValueError(f"历史净值不足 {CFG.min_history} 条")

            signal = analyze_fund_signal(history)
            rows.append(
                {
                    "sector": item.sector,
                    "code": code,
                    "name": item.基金名称,
                    "fund_type": item.基金类型,
                    **signal,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "sector": item.sector,
                    "code": code,
                    "name": item.基金名称,
                    "fund_type": item.基金类型,
                    "raw_signal": "ERROR",
                    "tomorrow_action": "ERROR",
                    "if_held_action": "ERROR",
                    "score": 0,
                    "reasons": [str(exc)],
                }
            )

    out = pd.DataFrame(rows)
    out["reasons"] = out["reasons"].apply(lambda x: "；".join(x) if isinstance(x, list) else x)

    buy_order = {"BUY_TOMORROW": 0, "WAIT": 1, "ERROR": 9}
    sell_order = {"REDEEM_OR_REVIEW": 0, "HOLD_OR_WATCH": 1, "ERROR": 9}
    out["_buy_order"] = out["tomorrow_action"].map(buy_order).fillna(5)
    out["_sell_order"] = out["if_held_action"].map(sell_order).fillna(5)
    out = out.sort_values(["sector", "_buy_order", "_sell_order", "score"], ascending=[True, True, True, False])
    out = out.drop(columns=["_buy_order", "_sell_order"])

    if save:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out.to_csv(f"fund_signal_scan_{ts}.csv", index=False, encoding="utf-8-sig")

    alerts = out[
        (out["tomorrow_action"] == "BUY_TOMORROW")
        | (out["if_held_action"] == "REDEEM_OR_REVIEW")
    ]
    if not alerts.empty:
        send_email(
            f"基金板块扫描建议 {datetime.now():%Y-%m-%d}",
            alerts.to_string(index=False),
        )

    return out


def build_recommendation_view(df: pd.DataFrame) -> str:
    def _format_section(title: str, part: pd.DataFrame) -> List[str]:
        lines = [title]
        if part.empty:
            lines.append("无")
            return lines

        display = part.copy()
        display["reasons"] = display["reasons"].astype(str).apply(
            lambda text: "；".join(text.split("；")[:3])
        )
        for sector_name, sector_df in display.groupby("sector", sort=False):
            lines.append(f"[{sector_name}]")
            lines.append(
                sector_df[["code", "name", "score", "latest_nav", "date", "reasons"]].to_string(index=False)
            )
        return lines

    buy_df = df[df["tomorrow_action"] == "BUY_TOMORROW"]
    sell_df = df[df["if_held_action"] == "REDEEM_OR_REVIEW"]
    wait_df = df[(df["tomorrow_action"] != "BUY_TOMORROW") & (df["if_held_action"] != "REDEEM_OR_REVIEW")]

    lines = []
    lines.extend(_format_section("建议明天买入的基金", buy_df))
    lines.append("")
    lines.extend(_format_section("建议卖出或回避的基金", sell_df))
    lines.append("")
    lines.extend(_format_section("其余观察基金", wait_df))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="国内场外基金数据抓取脚本")
    parser.add_argument("--mode", choices=["realtime", "history", "scan"], default=None, help="运行模式")
    parser.add_argument("--code", type=str, help="基金代码，例如 000001")
    parser.add_argument("--sector", choices=list(SECTOR_KEYWORDS.keys()), help="只扫描指定板块")
    parser.add_argument("--list", action="store_true", help="获取基金列表")
    parser.add_argument("--history", action="store_true", help="获取历史净值")
    parser.add_argument("--pages", type=int, default=3, help="历史净值抓取页数，默认 3")
    parser.add_argument("--per", type=int, default=20, help="每页条数，默认 20")
    parser.add_argument("--out", type=str, default=None, help="输出 CSV 文件名")

    args = parser.parse_args()

    if args.list:
        df = get_fund_list()
        out = args.out or "fund_list.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"基金列表已保存：{out}")
        print(df.head())
        return

    mode = args.mode
    if mode is None:
        if args.history:
            mode = "history"
        elif args.code:
            mode = "realtime"
        else:
            mode = "scan"

    if mode in {"realtime", "history"} and not args.code:
        parser.error("请指定 --code 或使用 --list")

    if mode == "scan":
        result = scan_fund_pool(sector=args.sector, save=True)
        print(build_recommendation_view(result))
        return

    code = args.code.zfill(6)

    if mode == "history":
        df = get_history_nav_multi_pages(code, pages=args.pages, per=args.per)
        out = args.out or f"{code}_history_nav.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"历史净值已保存：{out}")
        print(df.head())
    else:
        data = get_realtime_fund(code)
        df = pd.DataFrame([data])
        out = args.out or f"{code}_realtime.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"实时基金数据已保存：{out}")
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()