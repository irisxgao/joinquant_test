# -*- coding: utf-8 -*-
"""
JoinQuant strategy: CLS news rotation between CSI 300 ETF and Gold ETF.
Backtest setup in JoinQuant UI:
    start: 2025-01-01
    end:   2026-09-07
    frequency: minute
    initial cash: e.g. 1,000,000 CNY

Required private file (recommended): cls_telegraph_2025.json
JSON should be a list of CLS telegraph dicts from cls.py, each item containing at least:
    ctime (Unix timestamp), and one or more of title/brief/content/subjects.
Upload the file to JoinQuant's Strategy -> Research/Data/private-file area.

Important anti-look-ahead rule:
At 14:50 on trading day T, only records with publish time <= T 14:45 are used.
The signal window starts at previous trading day's 14:45.
"""
from jqdata import *
import json
import re
import datetime as dt


def initialize(context):
    # Products: Huatai-PB CSI 300 ETF and Huaan Gold ETF.
    g.equity = '510300.XSHG'
    g.gold = '518880.XSHG'
    g.assets = [g.equity, g.gold]

    set_benchmark(g.equity)
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    log.set_level('order', 'error')

    # Explicit ETF transaction-cost assumptions. Adjust to the broker account.
    set_order_cost(OrderCost(open_tax=0, close_tax=0,
                             open_commission=0.00025,
                             close_commission=0.00025,
                             close_today_commission=0,
                             min_commission=5), type='fund')
    set_slippage(FixedSlippage(0.001), type='fund')

    # Strategy parameters.
    g.news_file = 'cls_telegraph_2025.json'
    g.min_confidence = 2.0       # minimum score advantage to switch asset
    g.switch_buffer = 1.5        # hysteresis to reduce turnover
    g.max_news_per_window = 5000
    g.stop_loss = 0.08           # portfolio-level defensive exit
    g.reentry_days = 3
    g.cooldown_until = None
    g.high_watermark = context.portfolio.total_value

    g.news = load_cls_archive(g.news_file)
    g.last_signal = None

    run_daily(risk_check, time='14:40', reference_security=g.equity)
    run_daily(rebalance_by_cls, time='14:50', reference_security=g.equity)
    run_daily(after_close_report, time='after_close', reference_security=g.equity)


def load_cls_archive(filename):
    """Load and normalize CLS historical telegraphs from a JoinQuant private file."""
    try:
        raw = read_file(filename)
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        items = json.loads(raw)
        out = []
        seen = set()
        for x in items:
            ts = safe_int(x.get('ctime', 0))
            uid = str(x.get('id', '')) or (str(ts) + text_of(x)[:80])
            if ts <= 0 or uid in seen:
                continue
            seen.add(uid)
            out.append({'ctime': ts, 'text': text_of(x)})
        out.sort(key=lambda z: z['ctime'])
        log.info('Loaded %d deduplicated CLS telegraphs', len(out))
        return out
    except Exception as e:
        log.error('Cannot load %s: %s', filename, e)
        log.error('Historical backtest requires an archived CLS JSON file; no synthetic news will be used.')
        return []


def safe_int(x):
    try:
        return int(x)
    except Exception:
        return 0


def text_of(item):
    parts = [item.get('title', ''), item.get('brief', ''), item.get('content', '')]
    for s in item.get('subjects', []) or []:
        if isinstance(s, dict):
            parts.append(s.get('subject_name', ''))
    txt = ' '.join([str(x) for x in parts if x])
    txt = re.sub(r'<[^>]+>', ' ', txt)
    return re.sub(r'\s+', ' ', txt).strip()


# Weighted dictionaries. Positive means supportive of the corresponding asset.
EQUITY_POS = {
    '降准': 4, '降息': 4, '逆回购': 2, '流动性投放': 3, '增量资金': 2,
    '回购': 2, '增持': 2, '业绩预增': 3, '超预期': 2, '稳增长': 2,
    '财政刺激': 3, '专项债': 2, '房地产支持': 2, '外资流入': 2,
    '成交额放大': 1, '大涨': 2, '创新高': 2, '牛市': 3,
}
EQUITY_NEG = {
    '业绩预亏': -3, '爆雷': -4, '违约': -4, '立案调查': -3, '减持': -2,
    '外资流出': -2, '大跌': -3, '暴跌': -4, '跳水': -3, '跌停': -3,
    '经济衰退': -3, '通缩': -2, '关税升级': -3, '制裁': -2,
    '地缘冲突': -2, '风险偏好下降': -2,
}
GOLD_POS = {
    '黄金': 2, '金价': 2, '避险': 3, '地缘冲突': 3, '战争': 4,
    '制裁': 2, '降息': 3, '美元走弱': 2, '美元下跌': 2,
    '通胀': 2, '央行购金': 4, '黄金储备': 3, '创历史新高': 3,
    '金融风险': 3, '银行危机': 4, '债务危机': 4,
}
GOLD_NEG = {
    '金价下跌': -3, '黄金下跌': -3, '美元走强': -2, '美元上涨': -2,
    '加息': -3, '鹰派': -2, '实际利率上升': -3, '避险降温': -2,
    '黄金减持': -2,
}
NEGATIONS = ('不', '未', '否认', '辟谣', '无意', '不会')


def keyword_score(text, dictionary):
    score = 0.0
    hits = []
    for word, weight in dictionary.items():
        start = 0
        while True:
            idx = text.find(word, start)
            if idx < 0:
                break
            prefix = text[max(0, idx - 5):idx]
            w = -0.6 * weight if any(n in prefix for n in NEGATIONS) else weight
            score += w
            hits.append(word)
            start = idx + len(word)
    return score, hits


def score_window(start_dt, end_dt):
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())
    selected = [x for x in g.news if start_ts < x['ctime'] <= end_ts]
    selected = selected[-g.max_news_per_window:]

    eq = 0.0
    au = 0.0
    hit_count = 0
    for x in selected:
        text = x['text']
        a, h1 = keyword_score(text, EQUITY_POS)
        b, h2 = keyword_score(text, EQUITY_NEG)
        c, h3 = keyword_score(text, GOLD_POS)
        d, h4 = keyword_score(text, GOLD_NEG)
        if h1 or h2 or h3 or h4:
            hit_count += 1
        eq += a + b
        au += c + d

    # Normalize by sqrt(number of stories), preserving intensity while reducing volume bias.
    denom = max(1.0, len(selected) ** 0.5)
    return eq / denom, au / denom, len(selected), hit_count


def previous_trade_day(day):
    days = get_trade_days(end_date=day, count=2)
    if len(days) >= 2:
        return days[-2]
    return day - dt.timedelta(days=1)


def tradable(security):
    d = get_current_data()[security]
    return not (d.paused or d.is_st or d.last_price >= d.high_limit or d.last_price <= d.low_limit)


def current_asset(context):
    values = []
    for s in g.assets:
        p = context.portfolio.positions[s]
        values.append((p.value if p else 0, s))
    values.sort(reverse=True)
    return values[0][1] if values and values[0][0] > 0 else None


def risk_check(context):
    value = context.portfolio.total_value
    g.high_watermark = max(g.high_watermark, value)
    drawdown = 1.0 - value / max(g.high_watermark, 1.0)
    if drawdown >= g.stop_loss:
        for s in g.assets:
            order_target_value(s, 0)
        trade_days = list(get_trade_days(start_date=context.current_dt.date(),
                                         end_date=context.current_dt.date() + dt.timedelta(days=15)))
        if len(trade_days) > g.reentry_days:
            g.cooldown_until = trade_days[g.reentry_days]
        log.warn('Risk exit: drawdown %.2f%%, cooldown until %s', drawdown * 100, g.cooldown_until)


def rebalance_by_cls(context):
    if not g.news:
        return
    today = context.current_dt.date()
    if g.cooldown_until is not None and today < g.cooldown_until:
        return

    prev = previous_trade_day(today)
    start_dt = dt.datetime.combine(prev, dt.time(14, 45))
    end_dt = dt.datetime.combine(today, dt.time(14, 45))
    eq_score, gold_score, n_news, n_hits = score_window(start_dt, end_dt)
    diff = eq_score - gold_score
    held = current_asset(context)

    # Hysteresis: keep the current asset unless the alternative wins decisively.
    target = held
    if held == g.equity:
        if diff < -g.switch_buffer:
            target = g.gold
    elif held == g.gold:
        if diff > g.switch_buffer:
            target = g.equity
    else:
        if diff >= g.min_confidence:
            target = g.equity
        elif diff <= -g.min_confidence:
            target = g.gold
        else:
            target = None

    g.last_signal = (str(today), eq_score, gold_score, n_news, n_hits, target)
    if target is None or target == held or not tradable(target):
        record(cls_equity=eq_score, cls_gold=gold_score, cls_diff=diff)
        return

    # Sell first, then buy. Reserve 1% for commission/slippage.
    for s in g.assets:
        if s != target and context.portfolio.positions[s].value > 0:
            order_target_value(s, 0)
    order_target_value(target, context.portfolio.total_value * 0.99)
    log.info('CLS rotation %s -> %s | eq=%.3f gold=%.3f news=%d hits=%d',
             held, target, eq_score, gold_score, n_news, n_hits)
    record(cls_equity=eq_score, cls_gold=gold_score, cls_diff=diff)


def after_close_report(context):
    if g.last_signal:
        log.info('Daily CLS signal: %s', str(g.last_signal))
