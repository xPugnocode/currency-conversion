import datetime
import json

import numpy as np
import pandas as pd
import yfinance as yf


def best_fit_slope(y: np.array) -> float:
    '''
    Determine the slope for the linear regression line

    Parameters
    ----------
    y : TYPE
        The time-series to find the linear regression line for

    Returns
    -------
    m : float
        The gradient (slope) of the linear regression line
    '''

    x = np.arange(0, y.shape[0])

    x_bar = np.mean(x)
    y_bar = np.mean(y)

    return np.sum((x - x_bar) * (y - y_bar)) / np.sum((x - x_bar)**2)


def getRsi(prices, n=14):
    """Compute the RSI given prices

    :param prices: pandas.Series
    :return: rsi
    """

    # Calculate the difference between the current and previous close price
    delta = prices.diff()

    # Calculate the sum of all positive changes
    gain = delta.where(delta > 0, 0)

    # Calculate the sum of all negative changes
    loss = -delta.where(delta < 0, 0)

    # Calculate the average gain over the last n periods
    avg_gain = gain.rolling(n).mean()

    # Calculate the average loss over the last n periods
    avg_loss = loss.rolling(n).mean()

    # Calculate the relative strength
    rs = avg_gain / avg_loss

    # Calculate the RSI
    rsi = 100 - (100 / (1 + rs))

    return rsi


def apply_trend_template(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Apply Mark Minervini's trend criteria and obtain a new boolean column
    to indicate where the criteria is applied

    Parameters
    ----------
    df : pd.DataFrame
        The stock price dataframe

    Returns
    -------
    df : pd.DataFrame
        The stock price dataframe with the new trend boolean column
    '''

    # Find the moving averages
    df['200_ma'] = df['Adj Close'].rolling(200).mean()
    df['150_ma'] = df['Adj Close'].rolling(150).mean()
    df['50_ma'] = df['Adj Close'].rolling(50).mean()

    # Determine the 52 week high and low
    df['52_week_low'] = df['Adj Close'].rolling(52 * 5).min()
    df['52_week_high'] = df['Adj Close'].rolling(52 * 5).max()

    # Get the linear regression slope of the 200 day SMA
    df['slope'] = df['200_ma'].rolling(40).apply(best_fit_slope)
    df['RSI'] = getRsi(df['Adj Close'])

    # Constraints for the trend template
    df['trend_template'] = (
        (df['Adj Close'] > df['200_ma'])
        & (df['Adj Close'] > df['150_ma'])
        & (df['150_ma'] > df['200_ma'])
        & (df['slope'] > 0)
        & (df['50_ma'] > df['150_ma'])
        & (df['50_ma'] > df['200_ma'])
        & (df['Adj Close'] > df['50_ma'])
        & (df['Adj Close'] / df['52_week_low'] > 1.3)
        & (df['Adj Close'] / df['52_week_high'] > 0.8)) & (df['RSI'] >= 70)

    return df


def getMinervini():
    with open("data/nasdaq.txt") as f:
        TICKERS = list(map(str.strip, f.readlines()))
    data = yf.download(
        tickers=TICKERS,
        start=datetime.datetime.now() - datetime.timedelta(weeks=55),
        # threads=False,
        group_by='ticker',
        # progress=False,
    )
    data = data.T
    trending_tickers = []
    for ticker in TICKERS:
        df = apply_trend_template(data.loc[ticker, :].T)
        if df['trend_template'].values[-1]:
            trending_tickers.append((ticker, df['RSI'].values[-1]))
    trending_tickers.sort(key=lambda tup: tup[1], reverse=True)
    with open("data/stocks.json", 'w') as f:
        json.dump(trending_tickers, f)
