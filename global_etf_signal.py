#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
a_share_etf_signal_v5.py

只扫描 A 股可交易 ETF；不需要填写持仓文件。
输出同时给出两套结论：
1) if_not_held_action：如果当前没持有，应该怎么做
2) if_held_action：如果当前已持有，应该怎么做

安装：
    pip install pandas numpy yfinance akshare openpyxl schedule

运行：
    python a_share_etf_signal_v5.py --mode scan
    python a_share_etf_signal_v5.py --mode intraday
    python a_share_etf_signal_v5.py --mode backtest
    python a_share_etf_signal_v5.py --mode daemon
"""

import argparse
import os
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:
    yf = None
try:
    import akshare as ak
except Exception:
    ak = None
try:
    import schedule
except Exception:
    schedule = None

CN_TICKERS = {
    "159915": "创业板ETF",
    "588000": "科创50ETF",
    "510300": "沪深300ETF",
    "510500": "中证500ETF",
    "512100": "中证1000ETF",
    "510880": "红利ETF",
    "515180": "中证红利ETF",
    "518880": "黄金ETF-华安",
    "159934": "黄金ETF-易方达",
    "513100": "纳指ETF-国泰",
    "159941": "纳指ETF-广发",
    "513520": "日经ETF",
    "513880": "日经225ETF",
    "513030": "德国ETF",
    "513130": "恒生科技ETF",
    "159920": "恒生ETF",
}

@dataclass
class Config:
    lookback_days: int = int(os.getenv("ETF_LOOKBACK_DAYS", "900"))
    scan_time: str = os.getenv("ETF_SCAN_TIME", "18:30")
    intraday_time: str = os.getenv("ETF_INTRADAY_TIME", "10:00")
    min_history: int = 220
    score_buy: int = 4
    score_sell: int = -4
    data_source: str = os.getenv("ETF_DATA_SOURCE", "auto").lower()  # auto/yf/ak
    request_sleep: float = float(os.getenv("ETF_REQUEST_SLEEP", "1.0"))
    buy_low_pct: float = float(os.getenv("ETF_BUY_LOW_PCT", "0.005"))
    buy_high_atr_mult: float = float(os.getenv("ETF_BUY_HIGH_ATR", "0.6"))
    chase_limit_pct: float = float(os.getenv("ETF_CHASE_LIMIT_PCT", "0.03"))
    stop_atr_mult: float = float(os.getenv("ETF_STOP_ATR", "2.5"))
    take_profit_atr_mult: float = float(os.getenv("ETF_TP_ATR", "3.0"))
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    mail_to: str = os.getenv("MAIL_TO", "")
CFG = Config()


def cn_to_yahoo_symbol(code: str) -> str:
    return f"{code}.SS" if code.startswith(("5", "6")) else f"{code}.SZ"


def _normalize_ohlcv(df: pd.DataFrame, ticker: str = "") -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError(f"无数据: {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        try:
            if ticker and ticker in df.columns.get_level_values(-1):
                df = df.xs(ticker, axis=1, level=-1)
            elif ticker and ticker in df.columns.get_level_values(0):
                df = df.xs(ticker, axis=1, level=0)
            else:
                df.columns = df.columns.get_level_values(0)
        except Exception:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    need = ["open", "high", "low", "close", "volume"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"缺少OHLCV字段 {missing}: {ticker}; columns={list(df.columns)}")
    out = df[need].apply(pd.to_numeric, errors="coerce").dropna()
    if out.empty:
        raise ValueError(f"OHLCV清洗后为空: {ticker}")
    return out


def fetch_cn_yfinance(code: str, days: int) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("未安装 yfinance，请先 pip install yfinance")
    symbol = cn_to_yahoo_symbol(code)
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    last_err = None
    for attempt in range(1, 4):
        try:
            df = yf.download(symbol, start=start, auto_adjust=True, progress=False, group_by="column", threads=False)
            return _normalize_ohlcv(df, symbol)
        except Exception as e:
            last_err = e
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"yfinance获取失败: {symbol}; last_error={last_err}")


def fetch_cn_akshare(code: str, days: int) -> pd.DataFrame:
    if ak is None:
        raise RuntimeError("未安装 akshare，请先 pip install akshare")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    last_err = None
    for attempt in range(1, 5):
        try:
            df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq")
            if df is None or df.empty:
                raise ValueError(f"akshare无数据: {code}")
            df = df.rename(columns={"日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "volume"})
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            return _normalize_ohlcv(df, code)
        except Exception as e:
            last_err = e
            time.sleep(2.0 * attempt)
    raise RuntimeError(f"akshare获取失败: {code}; last_error={last_err}")


def fetch_cn(code: str, days: int) -> Tuple[pd.DataFrame, str]:
    errors = []
    if CFG.data_source in ("auto", "yf", "yfinance"):
        try:
            return fetch_cn_yfinance(code, days), "yfinance"
        except Exception as e:
            errors.append(str(e))
            if CFG.data_source in ("yf", "yfinance"):
                raise RuntimeError(" | ".join(errors))
    if CFG.data_source in ("auto", "ak", "akshare"):
        try:
            return fetch_cn_akshare(code, days), "akshare"
        except Exception as e:
            errors.append(str(e))
            raise RuntimeError(" | ".join(errors))
    raise ValueError(f"未知 ETF_DATA_SOURCE={CFG.data_source}，请使用 auto/yf/ak")


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = _normalize_ohlcv(df).copy()
    c = x["close"]
    v = x["volume"].replace(0, np.nan)
    x["ret1"] = c.pct_change()
    x["ma20"] = c.rolling(20).mean()
    x["ma50"] = c.rolling(50).mean()
    x["ma120"] = c.rolling(120).mean()
    x["ma200"] = c.rolling(200).mean()
    x["vol20"] = x["ret1"].rolling(20).std() * np.sqrt(252)
    x["vol60"] = x["ret1"].rolling(60).std() * np.sqrt(252)
    x["high60"] = c.rolling(60).max()
    x["low60"] = c.rolling(60).min()
    x["mom20"] = c / c.shift(20) - 1
    x["mom60"] = c / c.shift(60) - 1
    x["vol_ratio"] = v / v.rolling(20).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    x["rsi14"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    x["macd"] = ema12 - ema26
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["macd_hist"] = x["macd"] - x["macd_signal"]
    tr = pd.concat([
        x["high"] - x["low"],
        (x["high"] - x["close"].shift()).abs(),
        (x["low"] - x["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    x["atr14"] = tr.rolling(14).mean()
    x["atr_pct"] = x["atr14"] / c
    return x.dropna()


def score_signal(row: pd.Series, prev: pd.Series) -> Tuple[int, List[str]]:
    score, reasons = 0, []
    if row.close > row.ma200 and row.ma20 > row.ma50 > row.ma120:
        score += 2; reasons.append("长期趋势多头")
    if row.close < row.ma200 and row.ma20 < row.ma50:
        score -= 2; reasons.append("跌破长期趋势")
    if row.close >= row.high60 * 0.995 and row.vol_ratio > 1.15:
        score += 2; reasons.append("60日放量突破")
    if row.close <= row.low60 * 1.005 and row.vol_ratio > 1.15:
        score -= 2; reasons.append("60日放量破位")
    if row.mom20 > 0 and row.mom60 > 0 and row.mom20 > prev.mom20:
        score += 1; reasons.append("中短期动量改善")
    if row.mom20 < 0 and row.mom60 < 0 and row.mom20 < prev.mom20:
        score -= 1; reasons.append("中短期动量恶化")
    if prev.macd_hist <= 0 and row.macd_hist > 0:
        score += 1; reasons.append("MACD转正")
    if prev.macd_hist >= 0 and row.macd_hist < 0:
        score -= 1; reasons.append("MACD转负")
    if row.rsi14 > 76 and row.close > row.ma20 * 1.10:
        score -= 1; reasons.append("短线过热，降低追涨分")
    if row.rsi14 < 28 and row.close < row.ma200:
        score -= 1; reasons.append("弱势超跌，避免接刀")
    if row.vol20 > row.vol60 * 1.25 and row.close < row.ma50:
        score -= 1; reasons.append("波动率扩张且价格弱")
    return score, reasons


def analyze_signal(df: pd.DataFrame) -> Dict:
    ind = add_indicators(df)
    if len(ind) < 3:
        return {"raw_signal": "NO_DATA", "if_not_held_action": "WAIT", "if_held_action": "UNKNOWN", "score": 0, "reasons": ["历史数据不足"]}
    row, prev = ind.iloc[-1], ind.iloc[-2]
    score, reasons = score_signal(row, prev)
    close = float(row.close)
    atr = float(row.atr14)

    raw_signal = "BUY" if score >= CFG.score_buy else "SELL_OR_HEDGE" if score <= CFG.score_sell else "HOLD"

    buy_low = close * (1 - CFG.buy_low_pct)
    buy_high = min(close + CFG.buy_high_atr_mult * atr, close * (1 + CFG.chase_limit_pct))
    chase_limit = close * (1 + CFG.chase_limit_pct)
    initial_stop = close - CFG.stop_atr_mult * atr
    hold_stop = max(float(row.ma50), close - CFG.stop_atr_mult * atr)
    take_profit_watch = close + CFG.take_profit_atr_mult * atr

    # 没持有：只在 raw BUY 时给买入计划
    if raw_signal == "BUY":
        if_not_held_action = "BUY_PLAN"
        not_held_note = "未持有：按买入参考区间观察；若高于追高上限则不追"
    else:
        if_not_held_action = "WAIT"
        not_held_note = "未持有：等待，不买"

    # 已持有：判断是否应卖出；不需要用户提供是否持有，直接给“如果持有”的处理
    sell_reasons = []
    if raw_signal == "SELL_OR_HEDGE":
        sell_reasons.append("模型出现SELL_OR_HEDGE")
    if close < row.ma50:
        sell_reasons.append("收盘跌破MA50")
    if close < row.ma200:
        sell_reasons.append("收盘跌破MA200")
    if row.macd_hist < 0 and prev.macd_hist >= 0:
        sell_reasons.append("MACD转负")
    if row.mom20 < 0 and row.mom60 < 0:
        sell_reasons.append("20/60日动量均为负")

    if sell_reasons:
        if_held_action = "SELL_PLAN"
        held_note = "若有持有：应卖出/减仓；" + "；".join(sell_reasons)
    else:
        if_held_action = "HOLD_OR_TRAIL"
        held_note = "若有持有：继续持有，按持仓止损线跟踪"

    return {
        "raw_signal": raw_signal,
        "if_not_held_action": if_not_held_action,
        "if_held_action": if_held_action,
        "score": score,
        "close": close,
        "buy_ref": close if if_not_held_action == "BUY_PLAN" else np.nan,
        "buy_low": buy_low if if_not_held_action == "BUY_PLAN" else np.nan,
        "buy_high": buy_high if if_not_held_action == "BUY_PLAN" else np.nan,
        "chase_limit": chase_limit if if_not_held_action == "BUY_PLAN" else np.nan,
        "initial_stop_after_buy": initial_stop if if_not_held_action == "BUY_PLAN" else np.nan,
        "hold_stop_if_held": hold_stop,
        "take_profit_watch_if_held": take_profit_watch,
        "ma20": float(row.ma20),
        "ma50": float(row.ma50),
        "ma200": float(row.ma200),
        "rsi14": round(float(row.rsi14), 2),
        "atr_pct": round(float(row.atr_pct) * 100, 2),
        "date": str(ind.index[-1].date()),
        "reasons": reasons + [not_held_note, held_note],
    }


def fetch_realtime_quotes() -> pd.DataFrame:
    if ak is None:
        raise RuntimeError("未安装 akshare，盘中模式需要 akshare：pip install akshare")
    last_err = None
    for attempt in range(1, 4):
        try:
            spot = ak.fund_etf_spot_em()
            if spot is None or spot.empty:
                raise ValueError("fund_etf_spot_em 返回空")
            spot = spot.rename(columns={"代码": "code", "名称": "rt_name", "最新价": "rt_price", "涨跌幅": "rt_pct"})
            spot["code"] = spot["code"].astype(str).str.zfill(6)
            spot["rt_price"] = pd.to_numeric(spot["rt_price"], errors="coerce")
            spot["rt_pct"] = pd.to_numeric(spot["rt_pct"], errors="coerce")
            return spot[["code", "rt_name", "rt_price", "rt_pct"]].dropna(subset=["rt_price"])
        except Exception as e:
            last_err = e
            time.sleep(2 * attempt)
    raise RuntimeError(f"实时行情获取失败: {last_err}")


def send_email(subject: str, body: str):
    if not all([CFG.smtp_host, CFG.smtp_user, CFG.smtp_password, CFG.mail_to]):
        print("[WARN] 邮件环境变量未配置，改为打印：")
        print(subject); print(body); return
    msg = MIMEMultipart()
    msg["From"] = CFG.smtp_user
    msg["To"] = CFG.mail_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(CFG.smtp_host, CFG.smtp_port, context=context) as server:
        server.login(CFG.smtp_user, CFG.smtp_password)
        server.sendmail(CFG.smtp_user, [CFG.mail_to], msg.as_string())


def scan_all(save=True) -> pd.DataFrame:
    rows = []
    for code, name in CN_TICKERS.items():
        try:
            time.sleep(CFG.request_sleep)
            df, source = fetch_cn(code, CFG.lookback_days)
            sig = analyze_signal(df)
            rows.append({"market": "CN", "code": code, "name": name, "source": source, **sig})
        except Exception as e:
            rows.append({"market": "CN", "code": code, "name": name, "source": "ERROR", "raw_signal": "ERROR", "if_not_held_action": "ERROR", "if_held_action": "ERROR", "score": 0, "reasons": [str(e)]})
    out = pd.DataFrame(rows)
    out["reasons"] = out["reasons"].apply(lambda x: "；".join(x) if isinstance(x, list) else x)
    order = {"SELL_PLAN": 0, "BUY_PLAN": 1, "HOLD_OR_TRAIL": 2, "WAIT": 3, "ERROR": 9}
    out["_order"] = out["if_held_action"].map(order).fillna(5) + out["if_not_held_action"].map(order).fillna(5) / 10
    out = out.sort_values(["_order", "score"], ascending=[True, False]).drop(columns=["_order"])
    if save:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out.to_excel(f"a_share_etf_scan_{ts}.xlsx", index=False)
    alerts = out[(out["if_not_held_action"] == "BUY_PLAN") | (out["if_held_action"] == "SELL_PLAN")]
    if not alerts.empty:
        send_email(f"A股ETF交易计划 {datetime.now():%Y-%m-%d}", alerts.to_string(index=False))
    return out


def intraday_check() -> pd.DataFrame:
    plan = scan_all(save=False)
    spot = fetch_realtime_quotes()
    out = plan.merge(spot, on="code", how="left")

    def judge(row):
        price = row.get("rt_price", np.nan)
        if pd.isna(price):
            return "NO_RT_PRICE"
        statuses = []
        if row["if_not_held_action"] == "BUY_PLAN":
            if price > row["chase_limit"]:
                statuses.append("未持有:SKIP_CHASE_TOO_HIGH")
            elif row["buy_low"] <= price <= row["buy_high"]:
                statuses.append("未持有:BUY_TRIGGERED")
            elif price < row["buy_low"]:
                statuses.append("未持有:WAIT_OR_WEAK")
            else:
                statuses.append("未持有:WAIT_PRICE_TOO_HIGH")
        else:
            statuses.append("未持有:WAIT")
        if row["if_held_action"] == "SELL_PLAN":
            statuses.append("已持有:SELL_TRIGGERED")
        elif pd.notna(row.get("hold_stop_if_held", np.nan)) and price <= row["hold_stop_if_held"]:
            statuses.append("已持有:STOP_TRIGGERED")
        else:
            statuses.append("已持有:HOLD_OK")
        return " | ".join(statuses)

    out["intraday_status"] = out.apply(judge, axis=1)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out.to_excel(f"a_share_etf_intraday_{ts}.xlsx", index=False)
    alerts = out[out["intraday_status"].str.contains("BUY_TRIGGERED|SELL_TRIGGERED|STOP_TRIGGERED|SKIP_CHASE_TOO_HIGH", na=False)]
    if not alerts.empty:
        send_email(f"A股ETF盘中触发提醒 {datetime.now():%Y-%m-%d %H:%M}", alerts.to_string(index=False))
    return out


def backtest_one(df: pd.DataFrame, name: str = "") -> Dict:
    ind = add_indicators(df)
    if len(ind) < CFG.min_history:
        return {"name": name, "error": "history too short"}
    position, entry, equity = 0, 0.0, 1.0
    curve, trades = [], []
    for i in range(2, len(ind)):
        row, prev = ind.iloc[i], ind.iloc[i - 1]
        score, _ = score_signal(row, prev)
        price = row.close
        if position == 0 and score >= CFG.score_buy:
            position, entry = 1, price; trades.append((ind.index[i], "BUY", price))
        elif position == 1:
            trailing_stop = max(row.ma50, price - 3.0 * row.atr14)
            if score <= CFG.score_sell or price < trailing_stop:
                equity *= price / entry; position = 0; trades.append((ind.index[i], "SELL", price))
        curve.append(equity * price / entry if position == 1 else equity)
    if position == 1:
        equity *= ind.iloc[-1].close / entry
    curve = pd.Series(curve, index=ind.index[-len(curve):])
    dd = (curve / curve.cummax() - 1).min() if len(curve) else np.nan
    years = max((ind.index[-1] - ind.index[0]).days / 365.25, 0.1)
    return {"name": name, "total_return": equity - 1, "cagr": equity ** (1 / years) - 1, "max_drawdown": dd, "buy_hold_return": ind.close.iloc[-1] / ind.close.iloc[0] - 1, "trades": len(trades)}


def run_backtest_sample() -> pd.DataFrame:
    results = []
    for code, name in CN_TICKERS.items():
        try:
            time.sleep(CFG.request_sleep)
            df, source = fetch_cn(code, 2200)
            r = backtest_one(df, f"{code}-{name}")
            r["source"] = source
            results.append(r)
        except Exception as e:
            results.append({"name": f"{code}-{name}", "source": "ERROR", "error": str(e)})
    res = pd.DataFrame(results)
    res.to_excel(f"a_share_etf_backtest_{datetime.now():%Y%m%d_%H%M}.xlsx", index=False)
    return res


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["scan", "intraday", "backtest", "daemon"], default="scan")
    args = parser.parse_args()
    if args.mode == "scan":
        print(scan_all().to_string(index=False))
    elif args.mode == "intraday":
        print(intraday_check().to_string(index=False))
    elif args.mode == "backtest":
        print(run_backtest_sample().to_string(index=False))
    elif args.mode == "daemon":
        if schedule is None:
            raise RuntimeError("未安装 schedule，请先 pip install schedule")
        schedule.every().day.at(CFG.scan_time).do(scan_all)
        schedule.every().day.at(CFG.intraday_time).do(intraday_check)
        print(f"已启动：每天 {CFG.intraday_time} 盘中检查，{CFG.scan_time} 日线扫描。Ctrl+C退出。")
        while True:
            schedule.run_pending(); time.sleep(30)

if __name__ == "__main__":
    main()
