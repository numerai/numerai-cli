import logging

import pandas as pd
import numpy as np
# a fork of yfinance that implements retries nicely, see requirements.txt
import yfinance

# read in user-maintained ticker map
TICKER_MAP = pd.read_csv(
    "https://raw.githubusercontent.com/hellno/"
    "numerai-signals-tickermap/main/ticker_map.csv"
)


def map_tickers(tickers, from_ticker, to_ticker):
    # create two maps for bbg -> yahoo and yahoo -> bbg
    ticker_map = dict(zip(
        TICKER_MAP[from_ticker],
        TICKER_MAP[to_ticker]
    ))
    new_tickers = tickers.map(ticker_map).dropna()
    logging.info(f"Number of tickers in {from_ticker} -> {to_ticker} map: {len(ticker_map)}")
    return new_tickers


def download_yahoo_data(yfinance_tickers):
    # download data
    n = 1000  # chunk row size
    chunk_df = [
        yfinance_tickers.iloc[i : i + n]
        for i in range(0, len(yfinance_tickers), n)
    ]

    concat_dfs = []
    for df in chunk_df:
        try:
            # threads=True -> faster; tickers fail, script hangs
            # threads=False -> slower; more tickers will succeed
            temp_df = yfinance.download(
                df.str.cat(sep=" "),
                start="2005-12-01",
                threads=False
            )
            temp_df = temp_df["Adj Close"].stack().reset_index()
            concat_dfs.append(temp_df)
        except:
            pass
    full_data = pd.concat(concat_dfs)

    # properly position and clean raw data, after taking adjusted close only
    full_data.columns = ["date", "ticker", "price"]
    full_data.set_index("date", inplace=True)

    return full_data


def relative_strength_index(prices, interval=10):
    """
    Computes Relative Strength Index given a price series and lookback interval
    See more here https://www.investopedia.com/terms/r/rsi.asp
    """
    delta = prices.diff()

    # copy deltas, set losses to 0, get rolling avg
    gains = delta.copy()
    gains[gains < 0] = 0
    avg_gain = gains.rolling(interval).mean()

    # copy deltas, set gains to 0, get rolling avg
    losses = delta.copy()
    losses[losses > 0] = 0
    avg_loss = losses.rolling(interval).mean().abs()

    # calculate relative strength and it's index
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def get_rsi_feature_names(num_days):
    # define column names of features, target, and prediction
    feat_quintile_lag = [f"RSI_quintile_lag_{num}" for num in range(num_days + 1)]
    feat_rsi_diff = [f"RSI_diff_{num}" for num in range(num_days)]
    feat_rsi_diff_abs = [f"RSI_abs_diff_{num}" for num in range(num_days)]
    return feat_quintile_lag, feat_rsi_diff, feat_rsi_diff_abs


def generate_rsi_features(full_data, num_days):
    # add Relative Strength Index
    logging.info('generating RSI for each price...')
    ticker_groups = full_data.groupby("ticker")
    full_data["RSI"] = ticker_groups["price"].transform(
        lambda x: relative_strength_index(x)
    )

    # group by era (date)
    logging.info('grouping by dates...')
    date_groups = full_data.groupby(full_data.index)

    # create quintile labels within each era, useful for learning relative ranking
    logging.info('generating RSI quintiles...')
    full_data["RSI_quintile"] = date_groups["RSI"].transform(
        lambda group: pd.qcut(group, 5, labels=False, duplicates="drop")
    )
    full_data.dropna(inplace=True)

    feat_quintile_lag, feat_rsi_diff, feat_rsi_diff_abs = get_rsi_feature_names(num_days)

    # create lagged features grouped by ticker
    logging.info('grouping by ticker...')
    ticker_groups = full_data.groupby("ticker")

    # lag 0 is that day's value, lag 1 is yesterday's value, etc
    logging.info('generating lagged RSI quintiles...')
    for day in range(num_days + 1):
        full_data[feat_quintile_lag[day]] = ticker_groups["RSI_quintile"].transform(
            lambda group: group.shift(day)
        )

    # create difference of the lagged features and
    # absolute difference of the lagged features (change in RSI quintile by day)
    logging.info('generating lagged RSI diffs...')
    for day in range(num_days):
        full_data[feat_rsi_diff[day]] = (
            full_data[feat_quintile_lag[day]] - full_data[feat_quintile_lag[day + 1]]
        )
        full_data[feat_rsi_diff_abs[day]] = np.abs(full_data[feat_rsi_diff[day]])

    return full_data, feat_quintile_lag + feat_rsi_diff + feat_rsi_diff_abs


def add_targets_and_split(full_data):
    logging.info('adding targets...')
    # read in Signals targets and format the date
    targets = pd.read_csv(
        "https://numerai-signals-public-data.s3-us-west-2.amazonaws.com/"
        "signals_train_val_bbg.csv"
    )
    targets["date"] = pd.to_datetime(
        targets["friday_date"],
        format="%Y%m%d"
    ).dt.strftime('%Y-%m-%d')

    # merge our feature data with Numerai targets
    logging.info('generating dataset...')
    ml_data = pd.merge(
        full_data.reset_index(), targets,
        on=["date", "bloomberg_ticker"]
    )

    # convert date to datetime and index on it
    ml_data["date"] = pd.to_datetime(targets['date'], format='%Y-%m-%d')
    ml_data = ml_data.set_index("date")

    # for training and testing we want clean, complete data only
    ml_data.dropna(inplace=True)
    # ensure we have only fridays
    ml_data = ml_data[ml_data.index.weekday == 4]
    # drop eras with under 50 observations per era
    ml_data = ml_data[ml_data.index.value_counts() > 50]

    # train test split
    train_data = ml_data[ml_data["data_type"] == "train"]
    test_data = ml_data[ml_data["data_type"] == "validation"]

    return train_data, test_data

