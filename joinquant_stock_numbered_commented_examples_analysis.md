# JoinQuant Stock：编号版字段字典 + Python注释例子 + 连接查询/分析例子

> 每个 API / 表都有编号、字段表格、带注释的 Python 例子。最后提供连接查询，以及股价分析、选股、分红、科创板等常用分析例子。

# 1. API 函数

## 1.1 `get_security_info(code)`

**用途**：查询单只证券基础信息

### 1.1.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `display_name` | 中文名称 | `平安银行` |
| `name` | 名称/简称 | `平安银行` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `type` | 类型 | `示例值` |
| `parent` | 字段含义按列名理解 | `示例值` |

### 1.1.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查看单只股票的基本信息
# 示例股票：000001.XSHE = 平安银行
code = '000001.XSHE'

# get_security_info 返回的是一个对象，不是 DataFrame
info = get_security_info(code)

# 把对象属性整理成字典，方便查看
result = {
    'code': code,
    'display_name': info.display_name,  # 中文名称
    'name': info.name,                  # 拼音/简称
    'start_date': info.start_date,      # 上市日期
    'end_date': info.end_date,          # 退市日期；未退市通常是 2200-01-01
    'type': info.type                   # 类型：stock/index/etf等
}

# 在研究环境 Notebook 中，最后一行写变量名即可显示
result
```

## 1.2 `get_all_securities(types, date)`

**用途**：查询所有证券列表

### 1.2.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `display_name` | 中文名称 | `平安银行` |
| `name` | 名称/简称 | `平安银行` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `type` | 类型 | `示例值` |

### 1.2.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询某一天仍在上市的全部A股
# date 参数很重要，可以避免未来函数
all_stock = get_all_securities(types=['stock'], date='2020-01-02')

# get_all_securities 的股票代码在 index 里，不在普通列里
# 为了后续 merge 方便，把 index 转成 code 列
all_stock = all_stock.reset_index().rename(columns={'index': 'code'})

# 示例：找上市最早的前20只股票
result = all_stock.sort_values('start_date').head(20)

result
```

## 1.3 `get_extras(info, security_list, start_date, end_date)`

**用途**：查询ST等扩展信息

### 1.3.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `date` | 日期 | `2020-01-01` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `is_st` | 是否ST/*ST | `示例值` |

### 1.3.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：统计多只股票在一段时间内有多少个交易日是 ST
stocks = ['000001.XSHE', '000002.XSHE', '600519.XSHG']

# get_extras 返回 DataFrame：行是日期，列是股票代码，值是 True/False
st_df = get_extras('is_st', stocks, start_date='2020-01-01', end_date='2020-03-31')

# True 会被当作 1，False 会被当作 0，所以 sum 可以统计 ST 天数
st_days = st_df.sum().sort_values(ascending=False)

st_days
```

## 1.4 `get_mtss(security_list, start_date, end_date, fields)`

**用途**：查询融资融券明细

### 1.4.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `date` | 日期 | `2020-01-01` |
| `sec_code` | 股票代码 | `000001.XSHE` |
| `fin_value` | 金额/数值字段 | `12345678.90` |
| `fin_buy_value` | 金额/数值字段 | `12345678.90` |
| `fin_refund_value` | 金额/数值字段 | `12345678.90` |
| `sec_value` | 金额/数值字段 | `12345678.90` |
| `sec_sell_value` | 金额/数值字段 | `12345678.90` |
| `sec_refund_value` | 金额/数值字段 | `12345678.90` |
| `fin_sec_value` | 金额/数值字段 | `12345678.90` |

### 1.4.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询多只股票的融资融券数据，并统计均值
stocks = ['000001.XSHE', '000002.XSHE']

# 只取分析需要的字段，避免返回太宽的数据
mtss = get_mtss(
    stocks,
    '2020-01-01',
    '2020-03-31',
    fields=['date', 'sec_code', 'fin_value', 'fin_buy_value', 'fin_sec_value']
)

# 按股票分组，计算融资余额、融资买入额、融资融券余额的平均值
result = mtss.groupby('sec_code')[['fin_value', 'fin_buy_value', 'fin_sec_value']].mean()

result
```

## 1.5 `get_index_stocks(index_symbol, date)`

**用途**：查询指数成分股

### 1.5.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `index_code` | 编码 | `示例值` |
| `date` | 日期 | `2020-01-01` |
| `stock_code` | 编码 | `示例值` |

### 1.5.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：获取沪深300成分股，并补充股票名称和上市日期
index_code = '000300.XSHG'
stocks = get_index_stocks(index_code, date='2020-01-02')

# 查询同一天仍上市的股票主数据
base = get_all_securities(['stock'], date='2020-01-02')

# 用成分股代码筛选主数据
result = base.loc[stocks, ['display_name', 'start_date', 'end_date']].head(20)

result
```

## 1.6 `get_industry_stocks(industry_code, date)`

**用途**：查询行业成分股

### 1.6.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `industry_code` | 编码 | `示例值` |
| `date` | 日期 | `2020-01-01` |
| `stock_code` | 编码 | `示例值` |

### 1.6.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询 I64 行业成分股，并按上市时间排序
industry_code = 'I64'
stocks = get_industry_stocks(industry_code, date='2020-01-02')

# 补充股票名称
base = get_all_securities(['stock'], date='2020-01-02')

# 只看该行业中上市最早的20只股票
result = base.loc[stocks, ['display_name', 'start_date']].sort_values('start_date').head(20)

result
```

## 1.7 `get_concept_stocks(concept_code, date)`

**用途**：查询概念成分股

### 1.7.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `concept_code` | 编码 | `示例值` |
| `date` | 日期 | `2020-01-01` |
| `stock_code` | 编码 | `示例值` |

### 1.7.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询某个概念板块的成分股
concept_code = 'GN036'
stocks = get_concept_stocks(concept_code, date='2020-01-02')

# 查询股票名称和上市日期
base = get_all_securities(['stock'], date='2020-01-02')
result = base.loc[stocks, ['display_name', 'start_date']].head(20)

result
```

## 1.8 `get_industry(security, date)`

**用途**：查询股票所属行业

### 1.8.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `date` | 日期 | `2020-01-01` |
| `sw_l1_industry_code` | 编码 | `示例值` |
| `sw_l1_industry_name` | 名称 | `示例值` |
| `sw_l2_industry_code` | 编码 | `示例值` |
| `sw_l2_industry_name` | 名称 | `示例值` |
| `zjw_industry_code` | 编码 | `示例值` |
| `zjw_industry_name` | 名称 | `示例值` |

### 1.8.2 Python复杂例子（带注释）

```python
from jqdata import *
import pandas as pd

# 目标：查询多只股票所属行业，并转成表格
stocks = ['000001.XSHE', '000002.XSHE', '600519.XSHG']
industry_dict = get_industry(stocks, date='2018-06-01')

# get_industry 返回 dict，不是 DataFrame，所以需要手动整理
rows = []
for code, item in industry_dict.items():
    rows.append({
        'code': code,
        'sw_l1': item.get('sw_l1', {}).get('industry_name'),  # 申万一级行业
        'sw_l2': item.get('sw_l2', {}).get('industry_name'),  # 申万二级行业
        'zjw': item.get('zjw', {}).get('industry_name')       # 证监会行业
    })

result = pd.DataFrame(rows)
result
```

## 1.9 `get_price/history/attribute_history/get_bars`

**用途**：查询历史行情/K线

### 1.9.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `time` | 时间 | `2020-01-01` |
| `open` | 开盘价 | `示例值` |
| `close` | 收盘价 | `示例值` |
| `high` | 最高价 | `示例值` |
| `low` | 最低价 | `示例值` |
| `volume` | 成交量 | `12345678.90` |
| `money` | 成交金额 | `12345678.90` |
| `factor` | 字段含义按列名理解 | `示例值` |
| `high_limit` | 字段含义按列名理解 | `示例值` |
| `low_limit` | 字段含义按列名理解 | `示例值` |
| `avg` | 字段含义按列名理解 | `示例值` |
| `pre_close` | 字段含义按列名理解 | `示例值` |
| `paused` | 字段含义按列名理解 | `示例值` |

### 1.9.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：计算多只股票在一段时间内的收益率和日均成交额
stocks = ['000001.XSHE', '000002.XSHE', '600519.XSHG']

# panel=False 时，多股票结果会返回普通 DataFrame，包含 code 和 time 两列
price = get_price(
    stocks,
    start_date='2020-01-01',
    end_date='2020-03-31',
    fields=['open', 'close', 'volume', 'money'],
    panel=False
)

# 先按股票和时间排序，再按股票分组计算首尾收盘价
result = price.sort_values(['code', 'time']).groupby('code').agg(
    first_close=('close', 'first'),
    last_close=('close', 'last'),
    avg_money=('money', 'mean')
)

# 计算区间收益率，单位：百分比
result['return_pct'] = (result['last_close'] / result['first_close'] - 1) * 100

# 按收益率从高到低排序
result.sort_values('return_pct', ascending=False)
```

## 1.10 `get_current_data()`

**用途**：策略当前逻辑时间快照

### 1.10.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `paused` | 字段含义按列名理解 | `示例值` |
| `is_st` | 是否ST/*ST | `示例值` |
| `day_open` | 字段含义按列名理解 | `示例值` |
| `last_price` | 字段含义按列名理解 | `示例值` |
| `high_limit` | 字段含义按列名理解 | `示例值` |
| `low_limit` | 字段含义按列名理解 | `示例值` |

### 1.10.2 Python复杂例子（带注释）

```python
from jqdata import *
import pandas as pd

# 目标：在策略当前时点，批量查看股票是否停牌、是否ST、最新价
stocks = ['000001.XSHE', '000002.XSHE', '600519.XSHG']
current = get_current_data()

rows = []
for code in stocks:
    item = current[code]
    rows.append({
        'code': code,
        'name': item.name,
        'paused': item.paused,      # 是否停牌
        'is_st': item.is_st,        # 是否ST
        'last_price': item.last_price,
        'high_limit': item.high_limit,
        'low_limit': item.low_limit
    })

result = pd.DataFrame(rows)
result
```

## 1.11 `get_ticks/get_current_tick/get_call_auction`

**用途**：查询tick/当前tick/集合竞价tick

### 1.11.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `time` | 时间 | `2020-01-01` |
| `current` | 字段含义按列名理解 | `示例值` |
| `high` | 最高价 | `示例值` |
| `low` | 最低价 | `示例值` |
| `volume` | 成交量 | `12345678.90` |
| `money` | 成交金额 | `12345678.90` |
| `a1_p` | 字段含义按列名理解 | `示例值` |
| `a1_v` | 字段含义按列名理解 | `示例值` |
| `b1_p` | 字段含义按列名理解 | `示例值` |
| `b1_v` | 字段含义按列名理解 | `示例值` |

### 1.11.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询某只股票开盘后5分钟的tick数据
# tick 数据量很大，务必限制很短的时间窗口
ticks = get_ticks(
    '000001.XSHE',
    start_dt='2020-01-02 09:30:00',
    end_dt='2020-01-02 09:35:00'
)

# 查看前20条tick记录
result = ticks.head(20)
result
```

## 1.12 `get_money_flow(security_list, start_date, end_date, fields)`

**用途**：查询资金流向

### 1.12.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `date` | 日期 | `2020-01-01` |
| `sec_code` | 股票代码 | `000001.XSHE` |
| `change_pct` | 字段含义按列名理解 | `示例值` |
| `net_amount_main` | 主力净额 | `12345678.90` |
| `net_pct_main` | 主力净占比 | `示例值` |
| `net_amount_xl` | 金额/数值字段 | `12345678.90` |
| `net_pct_xl` | 字段含义按列名理解 | `示例值` |
| `net_amount_l` | 金额/数值字段 | `12345678.90` |
| `net_pct_l` | 字段含义按列名理解 | `示例值` |
| `net_amount_m` | 金额/数值字段 | `12345678.90` |
| `net_pct_m` | 字段含义按列名理解 | `示例值` |
| `net_amount_s` | 金额/数值字段 | `12345678.90` |
| `net_pct_s` | 字段含义按列名理解 | `示例值` |

### 1.12.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：统计多只股票区间内主力净流入情况
stocks = ['000001.XSHE', '000002.XSHE', '600519.XSHG']

flow = get_money_flow(
    stocks,
    '2020-01-01',
    '2020-03-31',
    fields=['date', 'sec_code', 'change_pct', 'net_amount_main', 'net_pct_main']
)

# 按股票聚合：主力净额求和，主力净占比取平均，涨跌幅取平均
result = flow.groupby('sec_code').agg({
    'net_amount_main': 'sum',
    'net_pct_main': 'mean',
    'change_pct': 'mean'
}).sort_values('net_amount_main', ascending=False)

result
```

## 1.13 `get_billboard_list(stock_list, start_date, end_date, count)`

**用途**：查询龙虎榜

### 1.13.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `day` | 日期 | `2020-01-01` |
| `direction` | 字段含义按列名理解 | `示例值` |
| `abnormal_code` | 编码 | `示例值` |
| `abnormal_name` | 名称 | `示例值` |
| `sales_depart_name` | 名称 | `示例值` |
| `rank` | 字段含义按列名理解 | `示例值` |
| `buy_value` | 金额/数值字段 | `12345678.90` |
| `buy_rate` | 比例/比率 | `12.34` |
| `sell_value` | 金额/数值字段 | `12345678.90` |
| `sell_rate` | 比例/比率 | `12.34` |
| `total_value` | 金额/数值字段 | `12345678.90` |
| `net_value` | 金额/数值字段 | `12345678.90` |
| `amount` | 金额/数值字段 | `12345678.90` |

### 1.13.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询某一天龙虎榜，并找净买入额最高的记录
billboard = get_billboard_list(stock_list=None, end_date='2018-08-01', count=1)

# net_value = buy_value - sell_value
result = billboard.sort_values('net_value', ascending=False).head(10)

result
```

# 2. 数据表

## 2.1 `STK_MT_TOTAL`

**用途**：融资融券汇总

### 2.1.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `date` | 日期 | `2020-01-01` |
| `exchange_code` | 编码 | `示例值` |
| `fin_value` | 金额/数值字段 | `12345678.90` |
| `fin_buy_value` | 金额/数值字段 | `12345678.90` |
| `sec_volume` | 字段含义按列名理解 | `12345678.90` |
| `sec_value` | 金额/数值字段 | `12345678.90` |
| `sec_sell_volume` | 字段含义按列名理解 | `12345678.90` |
| `fin_sec_value` | 金额/数值字段 | `12345678.90` |

### 2.1.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_MT_TOTAL 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_MT_TOTAL).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.2 `STK_XR_XD`

**用途**：分红送股/除权除息

### 2.2.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `report_date` | 报告期 | `2020-01-01` |
| `bonus_type` | 字段含义按列名理解 | `示例值` |
| `board_plan_pub_date` | 日期 | `2020-01-01` |
| `implementation_pub_date` | 日期 | `2020-01-01` |
| `dividend_ratio` | 送股比例 | `12.34` |
| `transfer_ratio` | 转增比例 | `12.34` |
| `bonus_ratio_rmb` | 每10股派息金额（人民币） | `12.34` |
| `a_registration_date` | 日期 | `2020-01-01` |
| `a_xr_date` | 日期 | `2020-01-01` |
| `a_bonus_date` | 日期 | `2020-01-01` |
| `plan_progress` | 方案进度 | `示例值` |

### 2.2.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_XR_XD 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_XR_XD).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.3 `STK_EXCHANGE_TRADE_INFO`

**用途**：沪深市场每日成交概况

### 2.3.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `exchange_code` | 编码 | `示例值` |
| `exchange_name` | 名称 | `示例值` |
| `date` | 日期 | `2020-01-01` |
| `total_market_cap` | 字段含义按列名理解 | `12345678.90` |
| `circulating_market_cap` | 字段含义按列名理解 | `12345678.90` |
| `volume` | 成交量 | `12345678.90` |
| `money` | 成交金额 | `12345678.90` |
| `deal_number` | 字段含义按列名理解 | `12345678.90` |
| `pe_average` | 字段含义按列名理解 | `示例值` |
| `turnover_ratio` | 换手率 | `12.34` |

### 2.3.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_EXCHANGE_TRADE_INFO 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_EXCHANGE_TRADE_INFO).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.4 `STK_EL_CONST_CHANGE`

**用途**：市场通合格证券变动

### 2.4.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `link_id` | 市场通编码 | `310001` |
| `link_name` | 市场通名称 | `示例值` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name_ch` | 字段含义按列名理解 | `示例值` |
| `name_en` | 字段含义按列名理解 | `示例值` |
| `exchange` | 交易所 | `示例值` |
| `change_date` | 日期 | `2020-01-01` |
| `direction` | 字段含义按列名理解 | `示例值` |

### 2.4.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_EL_CONST_CHANGE 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_EL_CONST_CHANGE).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.5 `STK_EXCHANGE_LINK_CALENDAR`

**用途**：市场通交易日历

### 2.5.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `day` | 日期 | `2020-01-01` |
| `link_id` | 市场通编码 | `310001` |
| `link_name` | 市场通名称 | `示例值` |
| `type_id` | 编码/ID | `310001` |
| `type` | 类型 | `示例值` |

### 2.5.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_EXCHANGE_LINK_CALENDAR 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_EXCHANGE_LINK_CALENDAR).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.6 `STK_EL_TOP_ACTIVATE`

**用途**：市场通十大成交活跃股

### 2.6.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `day` | 日期 | `2020-01-01` |
| `link_id` | 市场通编码 | `310001` |
| `link_name` | 市场通名称 | `示例值` |
| `rank` | 字段含义按列名理解 | `示例值` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `exchange` | 交易所 | `示例值` |
| `buy` | 字段含义按列名理解 | `示例值` |
| `sell` | 字段含义按列名理解 | `示例值` |
| `total` | 字段含义按列名理解 | `示例值` |

### 2.6.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_EL_TOP_ACTIVATE 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_EL_TOP_ACTIVATE).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.7 `STK_ML_QUOTA`

**用途**：市场通成交与额度

### 2.7.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `day` | 日期 | `2020-01-01` |
| `link_id` | 市场通编码 | `310001` |
| `link_name` | 市场通名称 | `示例值` |
| `currency_id` | 编码/ID | `310001` |
| `currency` | 字段含义按列名理解 | `示例值` |
| `buy_amount` | 金额/数值字段 | `12345678.90` |
| `buy_volume` | 字段含义按列名理解 | `12345678.90` |
| `sell_amount` | 金额/数值字段 | `12345678.90` |
| `sell_volume` | 字段含义按列名理解 | `12345678.90` |
| `sum_amount` | 金额/数值字段 | `12345678.90` |
| `sum_volume` | 字段含义按列名理解 | `12345678.90` |
| `quota` | 字段含义按列名理解 | `示例值` |
| `quota_balance` | 字段含义按列名理解 | `示例值` |
| `quota_daily` | 字段含义按列名理解 | `示例值` |
| `quota_daily_balance` | 字段含义按列名理解 | `示例值` |

### 2.7.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_ML_QUOTA 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_ML_QUOTA).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.8 `STK_EXCHANGE_LINK_RATE`

**用途**：市场通汇率

### 2.8.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `day` | 日期 | `2020-01-01` |
| `link_id` | 市场通编码 | `310001` |
| `link_name` | 市场通名称 | `示例值` |
| `domestic_currency` | 字段含义按列名理解 | `示例值` |
| `foreign_currency` | 字段含义按列名理解 | `示例值` |
| `refer_bid_rate` | 比例/比率 | `12.34` |
| `refer_ask_rate` | 比例/比率 | `12.34` |
| `settle_bid_rate` | 比例/比率 | `12.34` |
| `settle_ask_rate` | 比例/比率 | `12.34` |

### 2.8.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_EXCHANGE_LINK_RATE 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_EXCHANGE_LINK_RATE).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.9 `STK_HK_HOLD_INFO`

**用途**：沪深港通持股

### 2.9.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `day` | 日期 | `2020-01-01` |
| `link_id` | 市场通编码 | `310001` |
| `link_name` | 市场通名称 | `示例值` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `share_number` | 持股数量 | `12345678.90` |
| `share_ratio` | 持股比例 | `12.34` |

### 2.9.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_HK_HOLD_INFO 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_HK_HOLD_INFO).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.10 `STK_COMPANY_INFO`

**用途**：上市公司基本信息

### 2.10.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `full_name` | 公司全称 | `江苏恒瑞医药股份有限公司` |
| `short_name` | 简称 | `平安银行` |
| `a_code` | 编码 | `示例值` |
| `b_code` | 编码 | `示例值` |
| `h_code` | 编码 | `示例值` |
| `legal_representative` | 字段含义按列名理解 | `示例值` |
| `register_location` | 字段含义按列名理解 | `示例值` |
| `office_address` | 字段含义按列名理解 | `示例值` |
| `register_capital` | 字段含义按列名理解 | `12345678.90` |
| `establish_date` | 日期 | `2020-01-01` |
| `website` | 字段含义按列名理解 | `示例值` |
| `email` | 字段含义按列名理解 | `示例值` |
| `main_business` | 字段含义按列名理解 | `示例值` |
| `business_scope` | 字段含义按列名理解 | `示例值` |
| `province` | 字段含义按列名理解 | `示例值` |
| `city` | 字段含义按列名理解 | `示例值` |
| `industry_id` | 编码/ID | `310001` |
| `industry_1` | 一级行业 | `示例值` |
| `industry_2` | 二级行业 | `示例值` |
| `ceo` | 字段含义按列名理解 | `示例值` |
| `comments` | 字段含义按列名理解 | `示例值` |

### 2.10.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_COMPANY_INFO 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_COMPANY_INFO).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.11 `STK_STATUS_CHANGE`

**用途**：上市公司状态变动

### 2.11.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `change_date` | 日期 | `2020-01-01` |
| `public_status_id` | 编码/ID | `310001` |
| `public_status` | 字段含义按列名理解 | `示例值` |
| `change_reason` | 字段含义按列名理解 | `示例值` |
| `change_type_id` | 编码/ID | `310001` |
| `change_type` | 字段含义按列名理解 | `示例值` |
| `comments` | 字段含义按列名理解 | `示例值` |

### 2.11.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_STATUS_CHANGE 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_STATUS_CHANGE).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.12 `STK_LIST`

**用途**：股票上市信息

### 2.12.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `short_name` | 简称 | `平安银行` |
| `category` | 字段含义按列名理解 | `示例值` |
| `exchange` | 交易所 | `示例值` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `ipo_shares` | 股份/持股相关字段 | `示例值` |
| `book_price` | 字段含义按列名理解 | `示例值` |
| `par_value` | 金额/数值字段 | `12345678.90` |
| `state_id` | 编码/ID | `310001` |
| `state` | 上市状态 | `示例值` |

### 2.12.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_LIST 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_LIST).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.13 `STK_NAME_HISTORY`

**用途**：股票简称变更

### 2.13.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `company_id` | 公司ID | `310001` |
| `new_name` | 名称 | `示例值` |
| `new_spelling` | 字段含义按列名理解 | `示例值` |
| `org_name` | 名称 | `示例值` |
| `org_spelling` | 字段含义按列名理解 | `示例值` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `reason` | 字段含义按列名理解 | `示例值` |

### 2.13.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_NAME_HISTORY 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_NAME_HISTORY).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.14 `STK_EMPLOYEE_INFO`

**用途**：上市公司员工情况

### 2.14.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `employee` | 员工总数 | `12345678.90` |
| `retirement` | 字段含义按列名理解 | `示例值` |
| `graduate_rate` | 比例/比率 | `12.34` |
| `college_rate` | 比例/比率 | `12.34` |
| `middle_rate` | 比例/比率 | `12.34` |

### 2.14.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_EMPLOYEE_INFO 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_EMPLOYEE_INFO).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.15 `STK_SHAREHOLDER_TOP10`

**用途**：十大股东

### 2.15.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `change_reason_id` | 编码/ID | `310001` |
| `change_reason` | 字段含义按列名理解 | `示例值` |
| `shareholder_rank` | 股东排名 | `示例值` |
| `shareholder_name` | 股东名称 | `示例值` |
| `shareholder_class` | 股东类别 | `示例值` |
| `share_number` | 持股数量 | `12345678.90` |
| `share_ratio` | 持股比例 | `12.34` |
| `sharesnature` | 股份/持股相关字段 | `示例值` |
| `share_pledge` | 股份/持股相关字段 | `示例值` |
| `share_freeze` | 股份/持股相关字段 | `示例值` |

### 2.15.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_SHAREHOLDER_TOP10 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_SHAREHOLDER_TOP10).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.16 `STK_SHAREHOLDER_FLOATING_TOP10`

**用途**：十大流通股东

### 2.16.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `change_reason_id` | 编码/ID | `310001` |
| `change_reason` | 字段含义按列名理解 | `示例值` |
| `shareholder_rank` | 股东排名 | `示例值` |
| `shareholder_name` | 股东名称 | `示例值` |
| `shareholder_class` | 股东类别 | `示例值` |
| `share_number` | 持股数量 | `12345678.90` |
| `share_ratio` | 持股比例 | `12.34` |
| `sharesnature` | 股份/持股相关字段 | `示例值` |

### 2.16.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_SHAREHOLDER_FLOATING_TOP10 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_SHAREHOLDER_FLOATING_TOP10).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.17 `STK_SHARES_PLEDGE`

**用途**：股东股份质押

### 2.17.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `pledgor` | 字段含义按列名理解 | `示例值` |
| `pledgee` | 字段含义按列名理解 | `示例值` |
| `pledge_item` | 字段含义按列名理解 | `示例值` |
| `pledge_nature` | 字段含义按列名理解 | `示例值` |
| `pledge_number` | 质押数量 | `12345678.90` |
| `pledge_total_ratio` | 比例/比率 | `12.34` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `unpledged_date` | 日期 | `2020-01-01` |
| `unpledged_number` | 字段含义按列名理解 | `12345678.90` |
| `is_buy_back` | 字段含义按列名理解 | `示例值` |

### 2.17.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_SHARES_PLEDGE 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_SHARES_PLEDGE).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.18 `STK_SHARES_FROZEN`

**用途**：股东股份冻结

### 2.18.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `frozen_person` | 字段含义按列名理解 | `示例值` |
| `frozen_reason` | 字段含义按列名理解 | `示例值` |
| `frozen_share_nature` | 股份/持股相关字段 | `示例值` |
| `frozen_number` | 冻结数量 | `12345678.90` |
| `frozen_total_ratio` | 比例/比率 | `12.34` |
| `freeze_applicant` | 字段含义按列名理解 | `示例值` |
| `freeze_executor` | 字段含义按列名理解 | `示例值` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `unfrozen_date` | 日期 | `2020-01-01` |
| `unfrozen_number` | 字段含义按列名理解 | `12345678.90` |

### 2.18.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_SHARES_FROZEN 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_SHARES_FROZEN).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.19 `STK_HOLDER_NUM`

**用途**：股东户数

### 2.19.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `share_holders` | 股份/持股相关字段 | `示例值` |
| `a_share_holders` | 股份/持股相关字段 | `示例值` |
| `b_share_holders` | 股份/持股相关字段 | `示例值` |
| `h_share_holders` | 股份/持股相关字段 | `示例值` |

### 2.19.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_HOLDER_NUM 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_HOLDER_NUM).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.20 `STK_CAPITAL_CHANGE`

**用途**：股本变动

### 2.20.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `change_date` | 日期 | `2020-01-01` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `change_reason_id` | 编码/ID | `310001` |
| `change_reason` | 字段含义按列名理解 | `示例值` |
| `share_total` | 股份/持股相关字段 | `示例值` |
| `share_non_trade` | 股份/持股相关字段 | `示例值` |
| `share_limited` | 股份/持股相关字段 | `示例值` |
| `share_trade_total` | 股份/持股相关字段 | `示例值` |
| `share_rmb` | 股份/持股相关字段 | `示例值` |
| `share_b` | 股份/持股相关字段 | `示例值` |
| `share_h` | 股份/持股相关字段 | `示例值` |
| `share_management` | 股份/持股相关字段 | `示例值` |

### 2.20.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_CAPITAL_CHANGE 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_CAPITAL_CHANGE).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.21 `valuation`

**用途**：估值表

### 2.21.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `day` | 日期 | `2020-01-01` |
| `capitalization` | 总股本 | `12345678.90` |
| `circulating_cap` | 流通股本 | `12345678.90` |
| `market_cap` | 总市值 | `12345678.90` |
| `circulating_market_cap` | 字段含义按列名理解 | `12345678.90` |
| `turnover_ratio` | 换手率 | `12.34` |
| `pe_ratio` | 市盈率 | `12.34` |
| `pe_ratio_lyr` | 比例/比率 | `12.34` |
| `pb_ratio` | 市净率 | `12.34` |
| `ps_ratio` | 市销率 | `12.34` |
| `pcf_ratio` | 市现率 | `12.34` |

### 2.21.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询 valuation 表，并查看目标股票的前10条记录
q = query(valuation).filter(valuation.code == '600519.XSHG')

# get_fundamentals 用于 valuation/income/cash_flow/indicator 这类基本面旧接口表
df = get_fundamentals(q)

# 展示前10条，研究环境中最后一行会自动显示
result = df.head(10)
result
```

## 2.22 `income`

**用途**：利润表旧接口

### 2.22.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pubDate` | 财报发布日期 | `2020-01-01` |
| `statDate` | 财报统计日期 | `2020-01-01` |
| `total_operating_revenue` | 收入/收益相关字段 | `12345678.90` |
| `operating_revenue` | 收入/收益相关字段 | `12345678.90` |
| `total_operating_cost` | 字段含义按列名理解 | `示例值` |
| `operating_cost` | 字段含义按列名理解 | `示例值` |
| `operating_profit` | 利润相关字段 | `12345678.90` |
| `total_profit` | 利润相关字段 | `12345678.90` |
| `net_profit` | 净利润 | `12345678.90` |
| `np_parent_company_owners` | 字段含义按列名理解 | `示例值` |
| `basic_eps` | 基本每股收益 | `示例值` |
| `diluted_eps` | 字段含义按列名理解 | `示例值` |

### 2.22.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询 income 表，并查看目标股票的前10条记录
q = query(income).filter(income.code == '600519.XSHG')

# get_fundamentals 用于 valuation/income/cash_flow/indicator 这类基本面旧接口表
df = get_fundamentals(q)

# 展示前10条，研究环境中最后一行会自动显示
result = df.head(10)
result
```

## 2.23 `cash_flow`

**用途**：现金流量表旧接口

### 2.23.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pubDate` | 财报发布日期 | `2020-01-01` |
| `statDate` | 财报统计日期 | `2020-01-01` |
| `goods_sale_and_service_render_cash` | 现金/现金流相关字段 | `12345678.90` |
| `subtotal_operate_cash_inflow` | 比例/比率 | `12.34` |
| `subtotal_operate_cash_outflow` | 比例/比率 | `12.34` |
| `net_operate_cash_flow` | 经营活动现金流量净额 | `12.34` |
| `subtotal_invest_cash_inflow` | 现金/现金流相关字段 | `12345678.90` |
| `subtotal_invest_cash_outflow` | 现金/现金流相关字段 | `12345678.90` |
| `net_invest_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `subtotal_finance_cash_inflow` | 现金/现金流相关字段 | `12345678.90` |
| `subtotal_finance_cash_outflow` | 现金/现金流相关字段 | `12345678.90` |
| `net_finance_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `cash_equivalent_increase` | 现金/现金流相关字段 | `12345678.90` |

### 2.23.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询 cash_flow 表，并查看目标股票的前10条记录
q = query(cash_flow).filter(cash_flow.code == '600519.XSHG')

# get_fundamentals 用于 valuation/income/cash_flow/indicator 这类基本面旧接口表
df = get_fundamentals(q)

# 展示前10条，研究环境中最后一行会自动显示
result = df.head(10)
result
```

## 2.24 `indicator`

**用途**：财务指标旧接口

### 2.24.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pubDate` | 财报发布日期 | `2020-01-01` |
| `statDate` | 财报统计日期 | `2020-01-01` |
| `eps` | 每股收益 | `示例值` |
| `roe` | 净资产收益率 | `示例值` |
| `roa` | 总资产收益率 | `示例值` |
| `net_profit_margin` | 利润相关字段 | `12345678.90` |
| `gross_profit_margin` | 利润相关字段 | `12345678.90` |
| `inc_total_revenue_year_on_year` | 收入/收益相关字段 | `12345678.90` |
| `inc_net_profit_year_on_year` | 利润相关字段 | `12345678.90` |

### 2.24.2 Python复杂例子（带注释）

```python
from jqdata import *

# 目标：查询 indicator 表，并查看目标股票的前10条记录
q = query(indicator).filter(indicator.code == '600519.XSHG')

# get_fundamentals 用于 valuation/income/cash_flow/indicator 这类基本面旧接口表
df = get_fundamentals(q)

# 展示前10条，研究环境中最后一行会自动显示
result = df.head(10)
result
```

## 2.25 `STK_AUDIT_OPINION`

**用途**：审计意见

### 2.25.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `accounting_firm` | 字段含义按列名理解 | `示例值` |
| `accountant` | 字段含义按列名理解 | `示例值` |
| `opinion_type_id` | 编码/ID | `310001` |
| `opinion_type` | 字段含义按列名理解 | `示例值` |

### 2.25.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_AUDIT_OPINION 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_AUDIT_OPINION).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.26 `STK_REPORT_DISCLOSURE`

**用途**：定期报告披露

### 2.26.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `code` | 证券/股票代码 | `000001.XSHE` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `appoint_date` | 日期 | `2020-01-01` |
| `first_date` | 日期 | `2020-01-01` |
| `second_date` | 日期 | `2020-01-01` |
| `third_date` | 日期 | `2020-01-01` |
| `pub_date` | 公告日期 | `2020-01-01` |

### 2.26.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_REPORT_DISCLOSURE 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_REPORT_DISCLOSURE).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.27 `STK_FIN_FORCAST`

**用途**：业绩预告

### 2.27.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_type_id` | 编码/ID | `310001` |
| `report_type` | 报告类型 | `示例值` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `type_id` | 编码/ID | `310001` |
| `type` | 类型 | `示例值` |
| `profit_min` | 利润相关字段 | `12345678.90` |
| `profit_max` | 利润相关字段 | `12345678.90` |
| `profit_last` | 利润相关字段 | `12345678.90` |
| `profit_ratio_min` | 比例/比率 | `12.34` |
| `profit_ratio_max` | 比例/比率 | `12.34` |
| `content` | 字段含义按列名理解 | `示例值` |

### 2.27.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_FIN_FORCAST 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_FIN_FORCAST).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.28 `STK_PERFORMANCE_LETTERS`

**用途**：业绩快报

### 2.28.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `name` | 名称/简称 | `平安银行` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_date` | 报告期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `total_operating_revenue` | 收入/收益相关字段 | `12345678.90` |
| `operating_revenue` | 收入/收益相关字段 | `12345678.90` |
| `operating_profit` | 利润相关字段 | `12345678.90` |
| `total_profit` | 利润相关字段 | `12345678.90` |
| `np_parent_company_owners` | 字段含义按列名理解 | `示例值` |
| `total_assets` | 资产总计 | `12345678.90` |
| `equities_parent_company_owners` | 字段含义按列名理解 | `示例值` |
| `basic_eps` | 基本每股收益 | `示例值` |
| `weight_roe` | 字段含义按列名理解 | `示例值` |

### 2.28.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_PERFORMANCE_LETTERS 表，并尽量按日期倒序查看最近记录
q = query(finance.STK_PERFORMANCE_LETTERS).limit(4000)

# 执行查询，返回 DataFrame
raw = finance.run_query(q)

# 自动寻找常见日期字段，用于排序
candidate_date_cols = ['pub_date', 'date', 'day', 'change_date', 'report_date', 'end_date']
date_cols = [c for c in candidate_date_cols if c in raw.columns]

# 如果有日期字段，就按日期倒序；否则只展示前10条
result = raw.sort_values(date_cols[0], ascending=False).head(10) if date_cols else raw.head(10)
result
```

## 2.29 `STK_INCOME_STATEMENT / STK_INCOME_STATEMENT_PARENT`

**用途**：非金融类利润表

### 2.29.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_date` | 报告期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `total_operating_revenue` | 收入/收益相关字段 | `12345678.90` |
| `operating_revenue` | 收入/收益相关字段 | `12345678.90` |
| `total_operating_cost` | 字段含义按列名理解 | `示例值` |
| `operating_cost` | 字段含义按列名理解 | `示例值` |
| `operating_profit` | 利润相关字段 | `12345678.90` |
| `total_profit` | 利润相关字段 | `12345678.90` |
| `net_profit` | 净利润 | `12345678.90` |
| `np_parent_company_owners` | 字段含义按列名理解 | `示例值` |
| `basic_eps` | 基本每股收益 | `示例值` |
| `diluted_eps` | 字段含义按列名理解 | `示例值` |

### 2.29.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_INCOME_STATEMENT 财务报表，并取最近公告的10期
q = query(finance.STK_INCOME_STATEMENT).filter(
    finance.STK_INCOME_STATEMENT.code == '600519.XSHG',
    finance.STK_INCOME_STATEMENT.report_type == 0
).limit(4000)

# finance.run_query 返回 DataFrame
finance_df = finance.run_query(q)

# 按公告日期倒序排列，查看最近10条
result = finance_df.sort_values('pub_date', ascending=False).head(10)
result
```

## 2.30 `STK_CASHFLOW_STATEMENT / STK_CASHFLOW_STATEMENT_PARENT`

**用途**：非金融类现金流量表

### 2.30.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_date` | 报告期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `subtotal_operate_cash_inflow` | 比例/比率 | `12.34` |
| `subtotal_operate_cash_outflow` | 比例/比率 | `12.34` |
| `net_operate_cash_flow` | 经营活动现金流量净额 | `12.34` |
| `subtotal_invest_cash_inflow` | 现金/现金流相关字段 | `12345678.90` |
| `subtotal_invest_cash_outflow` | 现金/现金流相关字段 | `12345678.90` |
| `net_invest_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `subtotal_finance_cash_inflow` | 现金/现金流相关字段 | `12345678.90` |
| `subtotal_finance_cash_outflow` | 现金/现金流相关字段 | `12345678.90` |
| `net_finance_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `cash_equivalent_increase` | 现金/现金流相关字段 | `12345678.90` |

### 2.30.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_CASHFLOW_STATEMENT 财务报表，并取最近公告的10期
q = query(finance.STK_CASHFLOW_STATEMENT).filter(
    finance.STK_CASHFLOW_STATEMENT.code == '600519.XSHG',
    finance.STK_CASHFLOW_STATEMENT.report_type == 0
).limit(4000)

# finance.run_query 返回 DataFrame
finance_df = finance.run_query(q)

# 按公告日期倒序排列，查看最近10条
result = finance_df.sort_values('pub_date', ascending=False).head(10)
result
```

## 2.31 `STK_BALANCE_SHEET / STK_BALANCE_SHEET_PARENT`

**用途**：非金融类资产负债表

### 2.31.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_date` | 报告期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `cash_equivalents` | 现金/现金流相关字段 | `12345678.90` |
| `total_current_assets` | 资产相关字段 | `12345678.90` |
| `fixed_assets` | 资产相关字段 | `12345678.90` |
| `intangible_assets` | 资产相关字段 | `12345678.90` |
| `good_will` | 字段含义按列名理解 | `示例值` |
| `total_non_current_assets` | 资产相关字段 | `12345678.90` |
| `total_assets` | 资产总计 | `12345678.90` |
| `shortterm_loan` | 字段含义按列名理解 | `示例值` |
| `accounts_payable` | 字段含义按列名理解 | `示例值` |
| `total_current_liability` | 负债相关字段 | `12345678.90` |
| `longterm_loan` | 字段含义按列名理解 | `示例值` |
| `total_non_current_liability` | 负债相关字段 | `12345678.90` |
| `total_liability` | 负债合计 | `12345678.90` |
| `paidin_capital` | 字段含义按列名理解 | `12345678.90` |
| `capital_reserve_fund` | 字段含义按列名理解 | `12345678.90` |
| `retained_profit` | 利润相关字段 | `12345678.90` |
| `total_owner_equities` | 字段含义按列名理解 | `示例值` |

### 2.31.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 STK_BALANCE_SHEET 财务报表，并取最近公告的10期
q = query(finance.STK_BALANCE_SHEET).filter(
    finance.STK_BALANCE_SHEET.code == '600519.XSHG',
    finance.STK_BALANCE_SHEET.report_type == 0
).limit(4000)

# finance.run_query 返回 DataFrame
finance_df = finance.run_query(q)

# 按公告日期倒序排列，查看最近10条
result = finance_df.sort_values('pub_date', ascending=False).head(10)
result
```

## 2.32 `FINANCE_INCOME_STATEMENT / FINANCE_INCOME_STATEMENT_PARENT`

**用途**：金融类利润表

### 2.32.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_date` | 报告期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `operating_revenue` | 收入/收益相关字段 | `12345678.90` |
| `interest_net_revenue` | 收入/收益相关字段 | `12345678.90` |
| `interest_income` | 收入/收益相关字段 | `12345678.90` |
| `interest_expense` | 字段含义按列名理解 | `示例值` |
| `commission_net_income` | 收入/收益相关字段 | `12345678.90` |
| `commission_income` | 收入/收益相关字段 | `12345678.90` |
| `commission_expense` | 字段含义按列名理解 | `示例值` |
| `operating_profit` | 利润相关字段 | `12345678.90` |
| `total_profit` | 利润相关字段 | `12345678.90` |
| `net_profit` | 净利润 | `12345678.90` |
| `np_parent_company_owners` | 字段含义按列名理解 | `示例值` |
| `basic_eps` | 基本每股收益 | `示例值` |

### 2.32.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 FINANCE_INCOME_STATEMENT 财务报表，并取最近公告的10期
q = query(finance.FINANCE_INCOME_STATEMENT).filter(
    finance.FINANCE_INCOME_STATEMENT.code == '600519.XSHG',
    finance.FINANCE_INCOME_STATEMENT.report_type == 0
).limit(4000)

# finance.run_query 返回 DataFrame
finance_df = finance.run_query(q)

# 按公告日期倒序排列，查看最近10条
result = finance_df.sort_values('pub_date', ascending=False).head(10)
result
```

## 2.33 `FINANCE_CASHFLOW_STATEMENT / FINANCE_CASHFLOW_STATEMENT_PARENT`

**用途**：金融类现金流量表

### 2.33.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_date` | 报告期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `operate_cash_flow` | 比例/比率 | `12.34` |
| `subtotal_operate_cash_inflow` | 比例/比率 | `12.34` |
| `subtotal_operate_cash_outflow` | 比例/比率 | `12.34` |
| `net_operate_cash_flow` | 经营活动现金流量净额 | `12.34` |
| `invest_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `net_invest_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `finance_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `net_finance_cash_flow` | 现金/现金流相关字段 | `12345678.90` |
| `cash_equivalent_increase` | 现金/现金流相关字段 | `12345678.90` |

### 2.33.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 FINANCE_CASHFLOW_STATEMENT 财务报表，并取最近公告的10期
q = query(finance.FINANCE_CASHFLOW_STATEMENT).filter(
    finance.FINANCE_CASHFLOW_STATEMENT.code == '600519.XSHG',
    finance.FINANCE_CASHFLOW_STATEMENT.report_type == 0
).limit(4000)

# finance.run_query 返回 DataFrame
finance_df = finance.run_query(q)

# 按公告日期倒序排列，查看最近10条
result = finance_df.sort_values('pub_date', ascending=False).head(10)
result
```

## 2.34 `FINANCE_BALANCE_SHEET / FINANCE_BALANCE_SHEET_PARENT`

**用途**：金融类资产负债表

### 2.34.1 字段表

| 列名 | 列名含义 | 实例数据 |
|---|---|---|
| `company_id` | 公司ID | `310001` |
| `company_name` | 公司名称 | `江苏恒瑞医药股份有限公司` |
| `code` | 证券/股票代码 | `000001.XSHE` |
| `pub_date` | 公告日期 | `2020-01-01` |
| `start_date` | 上市/开始日期 | `2020-01-01` |
| `end_date` | 退市/截止日期 | `2020-01-01` |
| `report_date` | 报告期 | `2020-01-01` |
| `report_type` | 报告类型 | `示例值` |
| `cash_equivalents` | 现金/现金流相关字段 | `12345678.90` |
| `deposit_client` | 字段含义按列名理解 | `示例值` |
| `loan_and_advance` | 字段含义按列名理解 | `示例值` |
| `fixed_assets` | 资产相关字段 | `12345678.90` |
| `total_assets` | 资产总计 | `12345678.90` |
| `borrowing_from_centralbank` | 字段含义按列名理解 | `示例值` |
| `deposit_absorb` | 字段含义按列名理解 | `示例值` |
| `accounts_payable` | 字段含义按列名理解 | `示例值` |
| `longterm_loan` | 字段含义按列名理解 | `示例值` |
| `bonds_payable` | 字段含义按列名理解 | `示例值` |
| `total_liability` | 负债合计 | `12345678.90` |
| `paidin_capital` | 字段含义按列名理解 | `12345678.90` |
| `capital_reserve_fund` | 字段含义按列名理解 | `12345678.90` |
| `retained_profit` | 利润相关字段 | `12345678.90` |
| `total_owner_equities` | 字段含义按列名理解 | `示例值` |
| `total_liability_equity` | 负债相关字段 | `12345678.90` |

### 2.34.2 Python复杂例子（带注释）

```python
from jqdata import finance

# 目标：查询 FINANCE_BALANCE_SHEET 财务报表，并取最近公告的10期
q = query(finance.FINANCE_BALANCE_SHEET).filter(
    finance.FINANCE_BALANCE_SHEET.code == '600519.XSHG',
    finance.FINANCE_BALANCE_SHEET.report_type == 0
).limit(4000)

# finance.run_query 返回 DataFrame
finance_df = finance.run_query(q)

# 按公告日期倒序排列，查看最近10条
result = finance_df.sort_values('pub_date', ascending=False).head(10)
result
```

# 3. 连接查询复杂例子

> JoinQuant 的 `finance.run_query` 不直接做 SQL JOIN。复杂连接一般是先分别查询，再用 pandas 的 `merge`。

## 3.1 基础信息 + 上市信息 + 估值

```python
from jqdata import *
from jqdata import finance

# 目标：连接公司基础信息、上市信息和估值数据
# 类似 Oracle 中的三表 JOIN：company JOIN list_info JOIN valuation

# 1) 查询公司基础信息
company = finance.run_query(query(
    finance.STK_COMPANY_INFO.code,
    finance.STK_COMPANY_INFO.full_name,
    finance.STK_COMPANY_INFO.industry_1,
    finance.STK_COMPANY_INFO.industry_2
).limit(4000))

# 2) 查询上市信息
list_info = finance.run_query(query(
    finance.STK_LIST.code,
    finance.STK_LIST.start_date,
    finance.STK_LIST.exchange,
    finance.STK_LIST.state
).limit(4000))

# 3) 查询估值信息，筛选市值大于500亿、PE在0到30之间的股票
val = get_fundamentals(query(
    valuation.code,
    valuation.market_cap,
    valuation.pe_ratio,
    valuation.pb_ratio
).filter(
    valuation.market_cap > 500,
    valuation.pe_ratio > 0,
    valuation.pe_ratio < 30
))

# 4) 用 pandas merge 实现连接查询
result = val.merge(company, on='code', how='left').merge(list_info, on='code', how='left')

# 5) 按行业汇总：股票数量、市值中位数、PE中位数
summary = result.groupby('industry_1').agg(
    stock_count=('code','count'),
    median_market_cap=('market_cap','median'),
    median_pe=('pe_ratio','median')
).sort_values('median_market_cap', ascending=False)

summary.head(20)
```

## 3.2 十大股东 + 公司信息

```python
from jqdata import finance

# 目标：连接十大股东和公司信息，分析机构股东集中度

# 1) 查询十大股东数据
holder = finance.run_query(query(
    finance.STK_SHAREHOLDER_TOP10.code,
    finance.STK_SHAREHOLDER_TOP10.pub_date,
    finance.STK_SHAREHOLDER_TOP10.shareholder_name,
    finance.STK_SHAREHOLDER_TOP10.shareholder_class,
    finance.STK_SHAREHOLDER_TOP10.share_ratio
).filter(finance.STK_SHAREHOLDER_TOP10.pub_date >= '2020-01-01').limit(4000))

# 2) 查询公司行业信息
company = finance.run_query(query(
    finance.STK_COMPANY_INFO.code,
    finance.STK_COMPANY_INFO.full_name,
    finance.STK_COMPANY_INFO.industry_1
).limit(4000))

# 3) 按股票代码连接
joined = holder.merge(company, on='code', how='left')

# 4) 筛选典型机构股东
institution = joined[joined['shareholder_class'].isin(['证券投资基金','保险投资组合','社保基金','QFII'])]

# 5) 汇总每只股票机构股东持股比例
summary = institution.groupby(['industry_1','code','full_name']).agg(
    institution_share_ratio=('share_ratio','sum'),
    institution_count=('shareholder_name','nunique')
).reset_index()

summary.sort_values('institution_share_ratio', ascending=False).head(30)
```

## 3.3 利润表 + 资产负债表 + 现金流量表

```python
from jqdata import finance

# 目标：连接三张财务报表，计算ROA和经营现金流质量
code = '600519.XSHG'

# 1) 利润表：取净利润和营业收入
income_df = finance.run_query(query(
    finance.STK_INCOME_STATEMENT.code,
    finance.STK_INCOME_STATEMENT.end_date,
    finance.STK_INCOME_STATEMENT.net_profit,
    finance.STK_INCOME_STATEMENT.total_operating_revenue
).filter(finance.STK_INCOME_STATEMENT.code == code, finance.STK_INCOME_STATEMENT.report_type == 0).limit(4000))

# 2) 资产负债表：取总资产和总负债
balance_df = finance.run_query(query(
    finance.STK_BALANCE_SHEET.code,
    finance.STK_BALANCE_SHEET.end_date,
    finance.STK_BALANCE_SHEET.total_assets,
    finance.STK_BALANCE_SHEET.total_liability
).filter(finance.STK_BALANCE_SHEET.code == code, finance.STK_BALANCE_SHEET.report_type == 0).limit(4000))

# 3) 现金流量表：取经营现金流净额
cash_df = finance.run_query(query(
    finance.STK_CASHFLOW_STATEMENT.code,
    finance.STK_CASHFLOW_STATEMENT.end_date,
    finance.STK_CASHFLOW_STATEMENT.net_operate_cash_flow
).filter(finance.STK_CASHFLOW_STATEMENT.code == code, finance.STK_CASHFLOW_STATEMENT.report_type == 0).limit(4000))

# 4) 用 code + end_date 连接三张表
result = income_df.merge(balance_df, on=['code','end_date'], how='inner').merge(cash_df, on=['code','end_date'], how='inner')

# 5) 计算 ROA 和经营现金流质量
result['roa'] = result['net_profit'] / result['total_assets']
result['ocf_to_net_profit'] = result['net_operate_cash_flow'] / result['net_profit']

result.sort_values('end_date').tail(12)
```

## 3.4 沪深港通持股 + 行业 + 行情

```python
from jqdata import *
from jqdata import finance

# 目标：连接沪深港通持股、行业信息、区间收益率

# 1) 查询沪股通持股数据
hold = finance.run_query(query(
    finance.STK_HK_HOLD_INFO.day,
    finance.STK_HK_HOLD_INFO.link_id,
    finance.STK_HK_HOLD_INFO.code,
    finance.STK_HK_HOLD_INFO.name,
    finance.STK_HK_HOLD_INFO.share_number,
    finance.STK_HK_HOLD_INFO.share_ratio
).filter(finance.STK_HK_HOLD_INFO.link_id == 310001, finance.STK_HK_HOLD_INFO.day >= '2020-01-01').limit(4000))

# 2) 查询行业信息
company = finance.run_query(query(
    finance.STK_COMPANY_INFO.code,
    finance.STK_COMPANY_INFO.industry_1,
    finance.STK_COMPANY_INFO.industry_2
).limit(4000))

# 3) 对持股表中出现的股票查询行情
stocks = list(hold['code'].dropna().unique())[:50]
price = get_price(stocks, start_date='2020-01-01', end_date='2020-03-31', fields=['close','money'], panel=False)

# 4) 计算每只股票区间收益率和日均成交额
returns = price.sort_values(['code','time']).groupby('code').agg(
    first_close=('close','first'),
    last_close=('close','last'),
    avg_money=('money','mean')
).reset_index()
returns['return_pct'] = (returns['last_close'] / returns['first_close'] - 1) * 100

# 5) 取每只股票最新持股记录，再连接行业和收益
latest_hold = hold.sort_values('day').groupby('code').tail(1)
result = latest_hold.merge(company, on='code', how='left').merge(returns, on='code', how='left')

result.sort_values('share_ratio', ascending=False).head(30)
```

# 4. 数据分析常用 Python 例子

> 按你的要求，这部分放在连接查询之后，专门补充常用分析场景：股价、选股、分红、科创板、行业轮动、资金流。

## 4.1 股价分析：收益率、波动率、最大回撤

```python
from jqdata import *

# 目标：分析单只股票一段时间内的收益、波动和最大回撤
code = '600519.XSHG'

# 1) 获取日线收盘价
price = get_price(code, start_date='2020-01-01', end_date='2020-12-31', fields=['close'])

# 2) 计算每日收益率
price['daily_return'] = price['close'].pct_change()

# 3) 计算累计收益曲线
price['cum_return'] = (1 + price['daily_return']).cumprod()

# 4) 计算历史最高累计收益
price['cum_max'] = price['cum_return'].cummax()

# 5) 最大回撤 = 当前累计收益 / 历史最高累计收益 - 1
price['drawdown'] = price['cum_return'] / price['cum_max'] - 1

# 6) 汇总结果
result = {
    'total_return': price['cum_return'].iloc[-1] - 1,
    'annualized_volatility': price['daily_return'].std() * (252 ** 0.5),
    'max_drawdown': price['drawdown'].min()
}
result
```

## 4.2 选股分析：低PE + 高ROE + 非ST + 成交额过滤

```python
from jqdata import *

# 目标：构造一个简单选股池：低PE、高ROE、非ST、成交额充足

# 1) 查询估值和财务指标
fund = get_fundamentals(query(
    valuation.code,
    valuation.market_cap,
    valuation.pe_ratio,
    valuation.pb_ratio,
    indicator.roe
).filter(
    valuation.pe_ratio > 0,
    valuation.pe_ratio < 30,
    valuation.market_cap > 100,
    indicator.roe > 10
))

# 2) 去掉 ST 股票
codes = list(fund['code'])
st_df = get_extras('is_st', codes, start_date='2020-01-02', end_date='2020-01-02')
not_st_codes = list(st_df.columns[~st_df.iloc[0]])
fund = fund[fund['code'].isin(not_st_codes)]

# 3) 查询最近20个交易日日均成交额
price = get_price(list(fund['code']), end_date='2020-01-02', count=20, fields=['money'], panel=False)
liquidity = price.groupby('code')['money'].mean().reset_index(name='avg_money_20d')

# 4) 合并基本面和成交额，并过滤流动性不足的股票
result = fund.merge(liquidity, on='code', how='left')
result = result[result['avg_money_20d'] > 50000000]

# 5) 按 ROE 从高到低排序
result.sort_values('roe', ascending=False).head(30)
```

## 4.3 分红分析：筛选高现金分红公司

```python
from jqdata import finance

# 目标：筛选近几年现金分红较高、分红次数较多的公司

# 1) 查询分红除权除息表
xr = finance.run_query(query(
    finance.STK_XR_XD.code,
    finance.STK_XR_XD.company_name,
    finance.STK_XR_XD.report_date,
    finance.STK_XR_XD.bonus_ratio_rmb,
    finance.STK_XR_XD.dividend_ratio,
    finance.STK_XR_XD.transfer_ratio,
    finance.STK_XR_XD.plan_progress
).filter(finance.STK_XR_XD.report_date >= '2018-01-01').limit(4000))

# 2) 去掉没有现金派息的数据
cash_dividend = xr[xr['bonus_ratio_rmb'].notna()]

# 3) 按股票汇总平均派息、最大派息、派息次数
summary = cash_dividend.groupby(['code','company_name']).agg(
    avg_bonus_ratio=('bonus_ratio_rmb','mean'),
    max_bonus_ratio=('bonus_ratio_rmb','max'),
    dividend_count=('report_date','count')
).reset_index()

# 4) 筛选派息次数>=3的公司，并按平均派息排序
result = summary[summary['dividend_count'] >= 3].sort_values('avg_bonus_ratio', ascending=False)
result.head(30)
```

## 4.4 科创板分析：688开头股票的估值和市值

```python
from jqdata import *

# 目标：筛选科创板股票，并分析市值和估值
# A股科创板股票通常以 688 开头，交易所后缀为 XSHG

# 1) 查询当前仍上市股票
base = get_all_securities(['stock'], date='2020-01-02')
base = base.reset_index().rename(columns={'index':'code'})

# 2) 筛选科创板股票
kcb = base[base['code'].str.startswith('688')]

# 3) 查询科创板股票估值
val = get_fundamentals(query(
    valuation.code,
    valuation.market_cap,
    valuation.pe_ratio,
    valuation.pb_ratio,
    valuation.turnover_ratio
).filter(valuation.code.in_(list(kcb['code']))))

# 4) 合并股票名称和上市日期
result = val.merge(kcb[['code','display_name','start_date']], on='code', how='left')

# 5) 按市值排序
result.sort_values('market_cap', ascending=False).head(30)
```

## 4.5 行业轮动分析：行业平均收益率排名

```python
from jqdata import *
from jqdata import finance

# 目标：计算各行业在某一段时间内的平均收益率

# 1) 查询公司行业信息
company = finance.run_query(query(
    finance.STK_COMPANY_INFO.code,
    finance.STK_COMPANY_INFO.industry_1
).limit(4000))

# 2) 示例只取前300只股票，实际可以扩大范围
stocks = list(company['code'].dropna().unique())[:300]

# 3) 查询区间行情
price = get_price(stocks, start_date='2020-01-01', end_date='2020-03-31', fields=['close'], panel=False)

# 4) 计算每只股票区间收益率
ret = price.sort_values(['code','time']).groupby('code').agg(
    first_close=('close','first'),
    last_close=('close','last')
).reset_index()
ret['return_pct'] = (ret['last_close'] / ret['first_close'] - 1) * 100

# 5) 连接行业信息
joined = ret.merge(company, on='code', how='left')

# 6) 按行业统计平均收益率和股票数量
result = joined.groupby('industry_1').agg(
    avg_return=('return_pct','mean'),
    stock_count=('code','count')
).sort_values('avg_return', ascending=False)

result.head(30)
```

## 4.6 资金流分析：主力净流入和涨跌幅

```python
from jqdata import *

# 目标：分析主力净流入与涨跌幅之间的关系
stocks = ['000001.XSHE', '000002.XSHE', '600519.XSHG']

# 1) 查询资金流数据
flow = get_money_flow(
    stocks,
    '2020-01-01',
    '2020-03-31',
    fields=['date','sec_code','change_pct','net_amount_main','net_pct_main']
)

# 2) 按股票汇总主力净额和平均涨跌幅
summary = flow.groupby('sec_code').agg(
    total_main_inflow=('net_amount_main','sum'),
    avg_change_pct=('change_pct','mean'),
    avg_main_pct=('net_pct_main','mean')
).reset_index()

# 3) 按主力净流入从高到低排序
result = summary.sort_values('total_main_inflow', ascending=False)
result
```
