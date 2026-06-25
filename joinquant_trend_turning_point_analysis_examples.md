# JoinQuant 趋势分析与拐点识别 Python 示例

> 说明：本文是一个面向 JoinQuant 研究环境 / Notebook 的技术分析示例集。  
> 重点包括：趋势识别、涨跌拐点、趋势延续判断、连涨/连跌统计、突破分析、量价配合、简单信号评分等。  
> 注意：这些方法只能做**概率判断和研究辅助**，不能保证未来走势，也不构成投资建议。

---

## 0. 准备工作：统一获取行情数据

下面这个函数作为后续所有分析的基础。它会获取股票日线行情，并补充常用衍生字段。

```python
from jqdata import *
import pandas as pd
import numpy as np

# 目标：获取单只股票的日线行情，并补充涨跌幅、收益率等基础字段

def load_price(code, start_date='2020-01-01', end_date='2020-12-31'):
    """
    参数：
    code: 股票代码，例如 '600519.XSHG'
    start_date: 开始日期
    end_date: 结束日期

    返回：
    一个 DataFrame，包含 open/high/low/close/volume/money 以及衍生字段
    """

    # 1) 获取日线行情
    df = get_price(
        code,
        start_date=start_date,
        end_date=end_date,
        frequency='daily',
        fields=['open', 'close', 'high', 'low', 'volume', 'money']
    )

    # 2) 把索引日期转成普通列，方便后续 merge / groupby
    df = df.reset_index().rename(columns={'index': 'date'})

    # 3) 增加股票代码列
    df['code'] = code

    # 4) 计算每日涨跌额
    df['change'] = df['close'] - df['close'].shift(1)

    # 5) 计算每日收益率
    df['return'] = df['close'].pct_change()

    # 6) 计算涨跌方向：上涨=1，下跌=-1，平盘=0
    df['direction'] = np.sign(df['change']).fillna(0)

    return df

# 示例
price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')
price.head()
```

---

# 1. 趋势分析

## 1.1 均线趋势：MA5 / MA20 / MA60

均线是最常用的趋势判断工具：

- `MA5`：短期趋势
- `MA20`：中期趋势
- `MA60`：长期趋势
- `MA5 > MA20 > MA60`：多头排列，偏强趋势
- `MA5 < MA20 < MA60`：空头排列，偏弱趋势

```python
from jqdata import *
import pandas as pd
import numpy as np

# 目标：用均线判断股票当前处于多头、空头还是震荡趋势

code = '600519.XSHG'
price = load_price(code, '2020-01-01', '2020-12-31')

# 1) 计算不同周期均线
price['ma5'] = price['close'].rolling(5).mean()
price['ma20'] = price['close'].rolling(20).mean()
price['ma60'] = price['close'].rolling(60).mean()

# 2) 定义趋势状态
# 多头排列：短期均线 > 中期均线 > 长期均线
price['trend_ma'] = np.where(
    (price['ma5'] > price['ma20']) & (price['ma20'] > price['ma60']),
    '多头趋势',
    np.where(
        (price['ma5'] < price['ma20']) & (price['ma20'] < price['ma60']),
        '空头趋势',
        '震荡/不明确'
    )
)

# 3) 查看最近20天趋势状态
result = price[['date', 'close', 'ma5', 'ma20', 'ma60', 'trend_ma']].tail(20)
result
```

---

## 1.2 均线斜率：判断趋势是在增强还是减弱

仅仅看均线高低还不够，还可以看均线斜率：

- 均线斜率向上：趋势增强
- 均线斜率向下：趋势减弱
- 斜率接近 0：趋势不明显

```python
# 目标：计算 MA20 的斜率，用来判断中期趋势方向

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算20日均线
price['ma20'] = price['close'].rolling(20).mean()

# 2) 计算 MA20 最近5天的变化，也就是近似斜率
price['ma20_slope_5d'] = price['ma20'] - price['ma20'].shift(5)

# 3) 根据斜率判断趋势
price['trend_slope'] = np.where(
    price['ma20_slope_5d'] > 0,
    '中期趋势向上',
    np.where(price['ma20_slope_5d'] < 0, '中期趋势向下', '中期趋势走平')
)

# 4) 查看最近20天
result = price[['date', 'close', 'ma20', 'ma20_slope_5d', 'trend_slope']].tail(20)
result
```

---

## 1.3 线性回归斜率：用统计方式判断趋势

移动平均是直观方法，线性回归斜率更接近统计判断。  
这里用最近 `N` 天收盘价做一条回归线，看回归线斜率。

```python
from jqdata import *
import pandas as pd
import numpy as np

# 目标：用最近 N 天收盘价的线性回归斜率判断趋势方向

def rolling_slope(series, window=20):
    """
    对滚动窗口内的数据做线性回归，返回斜率。
    斜率 > 0 表示价格整体向上，斜率 < 0 表示价格整体向下。
    """
    slopes = []
    x = np.arange(window)

    for i in range(len(series)):
        if i < window - 1:
            slopes.append(np.nan)
        else:
            y = series.iloc[i-window+1:i+1].values
            # polyfit(x, y, 1) 返回一次函数的斜率和截距
            slope = np.polyfit(x, y, 1)[0]
            slopes.append(slope)

    return pd.Series(slopes, index=series.index)

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算20日回归斜率
price['slope_20'] = rolling_slope(price['close'], window=20)

# 2) 把斜率标准化，避免高价股和低价股不可比
price['slope_20_pct'] = price['slope_20'] / price['close']

# 3) 判断趋势
price['trend_regression'] = np.where(
    price['slope_20_pct'] > 0.001,
    '趋势向上',
    np.where(price['slope_20_pct'] < -0.001, '趋势向下', '震荡')
)

result = price[['date', 'close', 'slope_20', 'slope_20_pct', 'trend_regression']].tail(30)
result
```

---

# 2. 找出涨跌拐点

## 2.1 局部高点 / 局部低点

最直接的拐点识别方式：

- 某一天的收盘价高于前后若干天：局部高点
- 某一天的收盘价低于前后若干天：局部低点

```python
# 目标：寻找局部高点和局部低点

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# window 表示前后比较的天数
window = 3

# 1) 判断局部高点：当前 close 大于前后 window 天所有 close
price['local_high'] = price['close'] == price['close'].rolling(window * 2 + 1, center=True).max()

# 2) 判断局部低点：当前 close 小于前后 window 天所有 close
price['local_low'] = price['close'] == price['close'].rolling(window * 2 + 1, center=True).min()

# 3) 标记拐点类型
price['turning_point'] = np.where(
    price['local_high'],
    '局部高点',
    np.where(price['local_low'], '局部低点', '')
)

# 4) 只查看拐点记录
turning_points = price[price['turning_point'] != ''][['date', 'close', 'turning_point']]
turning_points.tail(20)
```

---

## 2.2 用均线金叉 / 死叉找趋势拐点

均线交叉常用于判断趋势切换：

- `MA5` 上穿 `MA20`：短期转强，称为金叉
- `MA5` 下穿 `MA20`：短期转弱，称为死叉

```python
# 目标：用 MA5 和 MA20 的交叉寻找趋势拐点

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算短期和中期均线
price['ma5'] = price['close'].rolling(5).mean()
price['ma20'] = price['close'].rolling(20).mean()

# 2) 计算均线差值
price['ma_diff'] = price['ma5'] - price['ma20']

# 3) 金叉：昨天差值 <= 0，今天差值 > 0
price['golden_cross'] = (price['ma_diff'].shift(1) <= 0) & (price['ma_diff'] > 0)

# 4) 死叉：昨天差值 >= 0，今天差值 < 0
price['dead_cross'] = (price['ma_diff'].shift(1) >= 0) & (price['ma_diff'] < 0)

# 5) 标记信号
price['cross_signal'] = np.where(
    price['golden_cross'],
    '金叉：可能转强',
    np.where(price['dead_cross'], '死叉：可能转弱', '')
)

# 6) 只看出现信号的日期
signals = price[price['cross_signal'] != ''][['date', 'close', 'ma5', 'ma20', 'cross_signal']]
signals.tail(20)
```

---

## 2.3 MACD 拐点：DIF 上穿 / 下穿 DEA

MACD 是判断趋势和动能拐点的常用指标：

- DIF 上穿 DEA：偏多信号
- DIF 下穿 DEA：偏空信号
- MACD 柱由负转正：动能改善
- MACD 柱由正转负：动能转弱

```python
# 目标：计算 MACD，并找出 MACD 金叉/死叉

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算 EMA12 和 EMA26
price['ema12'] = price['close'].ewm(span=12, adjust=False).mean()
price['ema26'] = price['close'].ewm(span=26, adjust=False).mean()

# 2) DIF = EMA12 - EMA26
price['dif'] = price['ema12'] - price['ema26']

# 3) DEA = DIF 的 9日 EMA
price['dea'] = price['dif'].ewm(span=9, adjust=False).mean()

# 4) MACD 柱，一般写作 2 * (DIF - DEA)
price['macd'] = 2 * (price['dif'] - price['dea'])

# 5) DIF 上穿 DEA = MACD 金叉
price['macd_golden_cross'] = (price['dif'].shift(1) <= price['dea'].shift(1)) & (price['dif'] > price['dea'])

# 6) DIF 下穿 DEA = MACD 死叉
price['macd_dead_cross'] = (price['dif'].shift(1) >= price['dea'].shift(1)) & (price['dif'] < price['dea'])

# 7) 标记信号
price['macd_signal'] = np.where(
    price['macd_golden_cross'],
    'MACD金叉：可能转强',
    np.where(price['macd_dead_cross'], 'MACD死叉：可能转弱', '')
)

# 8) 查看信号
result = price[price['macd_signal'] != ''][['date', 'close', 'dif', 'dea', 'macd', 'macd_signal']]
result.tail(20)
```

---

## 2.4 RSI 拐点：超买超卖后的反转

RSI 常用于判断超买/超卖：

- RSI > 70：可能超买
- RSI < 30：可能超卖
- RSI 从低位上穿 30：可能反弹
- RSI 从高位下穿 70：可能回落

```python
# 目标：计算 RSI，并识别超买/超卖后的反转信号

def calc_rsi(close, window=14):
    """
    RSI = 平均上涨幅度 / (平均上涨幅度 + 平均下跌幅度) * 100
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return rsi

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算 RSI14
price['rsi14'] = calc_rsi(price['close'], 14)

# 2) RSI 从 30 以下上穿 30：可能从超卖中反弹
price['rsi_rebound'] = (price['rsi14'].shift(1) < 30) & (price['rsi14'] >= 30)

# 3) RSI 从 70 以上下穿 70：可能从超买中回落
price['rsi_fall'] = (price['rsi14'].shift(1) > 70) & (price['rsi14'] <= 70)

# 4) 标记信号
price['rsi_signal'] = np.where(
    price['rsi_rebound'],
    'RSI超卖反弹',
    np.where(price['rsi_fall'], 'RSI超买回落', '')
)

result = price[price['rsi_signal'] != ''][['date', 'close', 'rsi14', 'rsi_signal']]
result.tail(20)
```

---

# 3. 判断接下来的趋势

> 重要提醒：这里的“判断接下来趋势”不是预测未来一定上涨或下跌，而是根据已有数据做**趋势评分**，只能作为研究参考。

## 3.1 多指标趋势评分模型

可以把多个信号合成一个分数：

- 收盘价 > MA20：+1
- MA5 > MA20：+1
- MA20 斜率向上：+1
- MACD 柱为正：+1
- 成交额高于20日均值：+1

分数越高，趋势越强。

```python
# 目标：用多个指标给趋势打分，得到偏强/中性/偏弱判断

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算均线
price['ma5'] = price['close'].rolling(5).mean()
price['ma20'] = price['close'].rolling(20).mean()
price['ma60'] = price['close'].rolling(60).mean()

# 2) 计算 MA20 斜率
price['ma20_slope_5d'] = price['ma20'] - price['ma20'].shift(5)

# 3) 计算 MACD
price['ema12'] = price['close'].ewm(span=12, adjust=False).mean()
price['ema26'] = price['close'].ewm(span=26, adjust=False).mean()
price['dif'] = price['ema12'] - price['ema26']
price['dea'] = price['dif'].ewm(span=9, adjust=False).mean()
price['macd'] = 2 * (price['dif'] - price['dea'])

# 4) 计算20日平均成交额
price['money_ma20'] = price['money'].rolling(20).mean()

# 5) 给每个条件打分
price['score_close_above_ma20'] = (price['close'] > price['ma20']).astype(int)
price['score_ma5_above_ma20'] = (price['ma5'] > price['ma20']).astype(int)
price['score_ma20_slope_up'] = (price['ma20_slope_5d'] > 0).astype(int)
price['score_macd_positive'] = (price['macd'] > 0).astype(int)
price['score_volume_confirm'] = (price['money'] > price['money_ma20']).astype(int)

# 6) 合计趋势分数，满分5分
score_cols = [
    'score_close_above_ma20',
    'score_ma5_above_ma20',
    'score_ma20_slope_up',
    'score_macd_positive',
    'score_volume_confirm'
]
price['trend_score'] = price[score_cols].sum(axis=1)

# 7) 根据分数给出趋势判断
price['next_trend_view'] = np.where(
    price['trend_score'] >= 4,
    '偏强，趋势可能延续',
    np.where(price['trend_score'] <= 1, '偏弱，注意下行风险', '中性/震荡')
)

# 8) 查看最近30天评分
result = price[['date', 'close', 'trend_score', 'next_trend_view']].tail(30)
result
```

---

## 3.2 趋势延续 vs 趋势反转

一个简单判断框架：

- 价格创新高 + 成交额放大：趋势延续概率更高
- 价格创新高 + 成交额萎缩：可能背离
- 价格跌破 MA20：趋势减弱
- 价格跌破 MA60：中期趋势转弱

```python
# 目标：判断当前是趋势延续、量价背离，还是趋势转弱

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算20日最高价和20日均成交额
price['high_20'] = price['close'].rolling(20).max()
price['money_ma20'] = price['money'].rolling(20).mean()

# 2) 计算均线
price['ma20'] = price['close'].rolling(20).mean()
price['ma60'] = price['close'].rolling(60).mean()

# 3) 创20日新高
price['new_20d_high'] = price['close'] >= price['high_20']

# 4) 成交额是否放大
price['volume_expand'] = price['money'] > price['money_ma20']

# 5) 判断趋势状态
conditions = [
    price['new_20d_high'] & price['volume_expand'],
    price['new_20d_high'] & (~price['volume_expand']),
    price['close'] < price['ma60'],
    price['close'] < price['ma20']
]
choices = [
    '创新高且放量：趋势延续较强',
    '创新高但缩量：警惕量价背离',
    '跌破MA60：中期趋势转弱',
    '跌破MA20：短中期趋势减弱'
]

price['trend_continuation_view'] = np.select(conditions, choices, default='无明显信号')

result = price[['date', 'close', 'high_20', 'money', 'money_ma20', 'trend_continuation_view']].tail(30)
result
```

---

# 4. 连涨 / 连跌统计

## 4.1 统计当前连涨/连跌天数

```python
# 目标：计算每天对应的连续上涨或连续下跌天数

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 判断每日涨跌方向
# close > 昨日 close 为上涨；close < 昨日 close 为下跌
price['up'] = price['close'] > price['close'].shift(1)
price['down'] = price['close'] < price['close'].shift(1)

# 2) 计算连续上涨天数
up_streak = []
count = 0
for is_up in price['up']:
    if is_up:
        count += 1
    else:
        count = 0
    up_streak.append(count)
price['up_streak'] = up_streak

# 3) 计算连续下跌天数
down_streak = []
count = 0
for is_down in price['down']:
    if is_down:
        count += 1
    else:
        count = 0
    down_streak.append(count)
price['down_streak'] = down_streak

# 4) 查看最近30天连涨/连跌情况
result = price[['date', 'close', 'up', 'down', 'up_streak', 'down_streak']].tail(30)
result
```

---

## 4.2 找出历史最长连涨 / 连跌区间

```python
# 目标：找出最长连涨和最长连跌天数

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')
price['up'] = price['close'] > price['close'].shift(1)
price['down'] = price['close'] < price['close'].shift(1)

# 1) 定义一个函数，用来计算连续 True 的长度

def calc_streak(bool_series):
    streak = []
    count = 0
    for v in bool_series:
        if v:
            count += 1
        else:
            count = 0
        streak.append(count)
    return streak

# 2) 计算连涨/连跌天数
price['up_streak'] = calc_streak(price['up'])
price['down_streak'] = calc_streak(price['down'])

# 3) 找最长连涨记录
max_up_row = price.loc[price['up_streak'].idxmax()]

# 4) 找最长连跌记录
max_down_row = price.loc[price['down_streak'].idxmax()]

# 5) 整理结果
result = {
    'max_up_streak_days': int(max_up_row['up_streak']),
    'max_up_streak_end_date': max_up_row['date'],
    'max_down_streak_days': int(max_down_row['down_streak']),
    'max_down_streak_end_date': max_down_row['date']
}

result
```

---

## 4.3 批量统计多只股票当前连涨/连跌天数

```python
from jqdata import *
import pandas as pd

# 目标：批量统计多只股票当前连涨/连跌天数
stocks = ['000001.XSHE', '000002.XSHE', '600519.XSHG']

# 1) 获取最近60个交易日收盘价
price = get_price(
    stocks,
    end_date='2020-12-31',
    count=60,
    fields=['close'],
    panel=False
)

# 2) 定义计算某只股票当前连涨/连跌天数的函数
def current_streak(df):
    df = df.sort_values('time').copy()
    df['up'] = df['close'] > df['close'].shift(1)
    df['down'] = df['close'] < df['close'].shift(1)

    # 从最后一天往前数
    last_up_count = 0
    for v in reversed(df['up'].tolist()):
        if v:
            last_up_count += 1
        else:
            break

    last_down_count = 0
    for v in reversed(df['down'].tolist()):
        if v:
            last_down_count += 1
        else:
            break

    return pd.Series({
        'current_up_streak': last_up_count,
        'current_down_streak': last_down_count,
        'last_close': df['close'].iloc[-1]
    })

# 3) 按 code 分组计算
result = price.groupby('code').apply(current_streak).reset_index()

# 4) 按当前连涨天数排序
result.sort_values('current_up_streak', ascending=False)
```

---

# 5. 其他常用技术分析

## 5.1 布林带：判断突破和回归

布林带常用于判断价格是否偏离均值过远：

- 收盘价突破上轨：短期强势，但也可能过热
- 收盘价跌破下轨：短期弱势，但也可能超跌
- 价格回到中轨附近：均值回归

```python
# 目标：计算布林带，并识别突破上轨/跌破下轨

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算20日均线和标准差
price['mid'] = price['close'].rolling(20).mean()
price['std'] = price['close'].rolling(20).std()

# 2) 上轨和下轨
price['upper'] = price['mid'] + 2 * price['std']
price['lower'] = price['mid'] - 2 * price['std']

# 3) 判断突破
price['boll_signal'] = np.where(
    price['close'] > price['upper'],
    '突破上轨：短期强势/可能过热',
    np.where(price['close'] < price['lower'], '跌破下轨：短期弱势/可能超跌', '区间内')
)

result = price[['date', 'close', 'mid', 'upper', 'lower', 'boll_signal']].tail(30)
result
```

---

## 5.2 支撑位 / 压力位：用近期高低点近似

```python
# 目标：用最近 N 天的最高价和最低价近似压力位和支撑位

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

window = 20

# 1) 近期压力位：过去20天最高收盘价
price['resistance_20'] = price['close'].rolling(window).max()

# 2) 近期支撑位：过去20天最低收盘价
price['support_20'] = price['close'].rolling(window).min()

# 3) 判断是否突破压力位或跌破支撑位
price['break_resistance'] = price['close'] >= price['resistance_20']
price['break_support'] = price['close'] <= price['support_20']

price['support_resistance_signal'] = np.where(
    price['break_resistance'],
    '突破近期压力位',
    np.where(price['break_support'], '跌破近期支撑位', '区间震荡')
)

result = price[['date', 'close', 'support_20', 'resistance_20', 'support_resistance_signal']].tail(30)
result
```

---

## 5.3 放量上涨 / 放量下跌

量价关系常用判断：

- 放量上涨：趋势可能更可靠
- 放量下跌：下跌压力可能较强
- 缩量上涨：可能反弹力度不足
- 缩量下跌：可能抛压减弱

```python
# 目标：判断每日是放量上涨、放量下跌、缩量上涨还是缩量下跌

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 计算20日平均成交额
price['money_ma20'] = price['money'].rolling(20).mean()

# 2) 判断是否放量
price['volume_expand'] = price['money'] > price['money_ma20']

# 3) 判断涨跌
price['up_day'] = price['close'] > price['close'].shift(1)
price['down_day'] = price['close'] < price['close'].shift(1)

# 4) 组合量价信号
conditions = [
    price['up_day'] & price['volume_expand'],
    price['down_day'] & price['volume_expand'],
    price['up_day'] & (~price['volume_expand']),
    price['down_day'] & (~price['volume_expand'])
]
choices = ['放量上涨', '放量下跌', '缩量上涨', '缩量下跌']

price['volume_price_signal'] = np.select(conditions, choices, default='平盘/无明显信号')

result = price[['date', 'close', 'money', 'money_ma20', 'volume_price_signal']].tail(30)
result
```

---

## 5.4 综合信号表：把趋势、拐点、连涨连跌合并

```python
# 目标：把常用技术信号合并成一张综合表，方便每天观察

price = load_price('600519.XSHG', '2020-01-01', '2020-12-31')

# 1) 均线
price['ma5'] = price['close'].rolling(5).mean()
price['ma20'] = price['close'].rolling(20).mean()
price['ma60'] = price['close'].rolling(60).mean()

# 2) MA5/MA20 金叉死叉
price['ma_diff'] = price['ma5'] - price['ma20']
price['golden_cross'] = (price['ma_diff'].shift(1) <= 0) & (price['ma_diff'] > 0)
price['dead_cross'] = (price['ma_diff'].shift(1) >= 0) & (price['ma_diff'] < 0)

# 3) 连涨连跌
price['up'] = price['close'] > price['close'].shift(1)
price['down'] = price['close'] < price['close'].shift(1)

def calc_streak(bool_series):
    streak = []
    count = 0
    for v in bool_series:
        if v:
            count += 1
        else:
            count = 0
        streak.append(count)
    return streak

price['up_streak'] = calc_streak(price['up'])
price['down_streak'] = calc_streak(price['down'])

# 4) 趋势状态
price['trend'] = np.where(
    (price['ma5'] > price['ma20']) & (price['ma20'] > price['ma60']),
    '多头趋势',
    np.where((price['ma5'] < price['ma20']) & (price['ma20'] < price['ma60']), '空头趋势', '震荡')
)

# 5) 生成综合信号
price['signal'] = ''
price.loc[price['golden_cross'], 'signal'] += '均线金叉;'
price.loc[price['dead_cross'], 'signal'] += '均线死叉;'
price.loc[price['up_streak'] >= 5, 'signal'] += '连续上涨>=5天;'
price.loc[price['down_streak'] >= 5, 'signal'] += '连续下跌>=5天;'

# 6) 最终观察表
result = price[[
    'date', 'close', 'ma5', 'ma20', 'ma60',
    'trend', 'up_streak', 'down_streak', 'signal'
]].tail(60)

result
```
