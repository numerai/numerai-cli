import os
import logging
from datetime import datetime, timedelta
import configparser

from data import \
    download_yahoo_data,\
    map_tickers,\
    generate_rsi_features,\
    add_targets_and_split, \
    get_rsi_feature_names

import joblib
import numerapi
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from dateutil.relativedelta import relativedelta, FR


TARGET_NAME = "target"
PREDICTION_NAME = "signal"
TRAINED_MODEL_PREFIX = './trained_model'

# Define models here as (ID, model instance),
# a model ID of None is submitted as your default model
MODEL_CONFIGS = [
    (None, GradientBoostingRegressor(subsample=0.1)),
    # (YOUR MODEL ID, LinearRegression(n_jobs=10))
    #  etc...
]

if os.getenv('NUMERAI_PUBLIC_ID') and os.getenv('NUMERAI_SECRET_KEY'):
    napi = numerapi.SignalsAPI()

else:
    config = configparser.ConfigParser()
    config.read('../.numerai/.keys')
    # initialize API client
    napi = numerapi.SignalsAPI(
        public_id=config['numerai']['NUMERAI_PUBLIC_ID'],
        secret_key=config['numerai']['NUMERAI_SECRET_KEY']
    )


def download_data(live_data_date):
    eligible_tickers = pd.Series(napi.ticker_universe(), name="bloomberg_ticker")
    logging.info(f"Number of eligible tickers: {len(eligible_tickers)}")

    yfinance_tickers = map_tickers(eligible_tickers, "bloomberg_ticker", "yahoo")
    logging.info(f"Number of yahoo tickers: {len(yfinance_tickers)}")

    num_days_lag = 5
    if os.path.exists('full_data.csv'):
        full_data = pd.read_csv('full_data.csv')
        quintile_lag, rsi_diff, rsi_diff_abs = get_rsi_feature_names(num_days_lag)
        feature_names = quintile_lag + rsi_diff + rsi_diff_abs

    else:
        full_data = download_yahoo_data(yfinance_tickers)

        full_data["bloomberg_ticker"] = map_tickers(
            full_data.ticker, "yahoo", "bloomberg_ticker")
        logging.info(
            f"Num tickers with data: {len(full_data.bloomberg_ticker.unique())}")
        logging.info(f"data size: {full_data.shape}")

        full_data, feature_names = generate_rsi_features(full_data, num_days=num_days_lag)
        logging.info(f"Features for training:\n {feature_names}")

    # add numerai targets and do train/test split
    train_data, test_data = add_targets_and_split(full_data)
    logging.info(f"{len(train_data)} train examples and {len(test_data)} test examples")

    # generate live data
    date_string = live_data_date.strftime("%Y-%m-%d")
    try:
        live_data = full_data[full_data.date == date_string].copy()
    except KeyError as e:
        logging.error(f"No ticker on {e}")
        live_data = full_data.iloc[:0].copy()
    live_data.dropna(subset=feature_names, inplace=True)

    # get data from the day before, for markets that were closed
    last_thursday = live_data_date - timedelta(days=1)
    thursday_date_string = last_thursday.strftime("%Y-%m-%d")
    thursday_data = full_data[full_data.date == thursday_date_string]

    # Only select tickers than aren't already present in live_data
    thursday_data = thursday_data[
        ~thursday_data.ticker.isin(live_data.ticker.values)
    ].copy()
    thursday_data.dropna(subset=feature_names, inplace=True)

    live_data = pd.concat([live_data, thursday_data])
    live_data = live_data.set_index("date")

    return feature_names, train_data, test_data, live_data


def train(train_data, feature_names, model_id, model, force_training=False):
    model_name = TRAINED_MODEL_PREFIX
    if model_id:
        model_name += f"_{model_id}"

    # load a model if we have a trained model already and we aren't forcing a training session
    if os.path.exists(model_name) and not force_training:
        logging.info('loading existing trained model')
        model = joblib.load(model_name)
        return model

    logging.info('training model')
    model.fit(train_data[feature_names], train_data[TARGET_NAME])

    logging.info('saving model')
    joblib.dump(model, model_name)

    return model


def predict(test_data, live_data, live_data_date, feature_names, model):
    # predict test data
    test_data[PREDICTION_NAME] = model.predict(test_data[feature_names])

    logging.info(f"Number of live tickers to submit: {len(live_data)}")
    live_data[PREDICTION_NAME] = model.predict(live_data[feature_names])

    # prepare and writeout example file
    diagnostic_df = pd.concat([test_data, live_data])
    diagnostic_df["friday_date"] = diagnostic_df.friday_date.fillna(
        live_data_date.strftime("%Y%m%d")
    ).astype(int)
    diagnostic_df["data_type"] = diagnostic_df.data_type.fillna("live")

    return diagnostic_df[[
        "bloomberg_ticker",
        "friday_date",
        "data_type",
        "signal"
    ]].reset_index(drop=True)


def submit(predictions, predict_output_path, model_id=None):
    logging.info('writing predictions to file')
    # numerai doesn't want the index, so don't write it to our file
    predictions.to_csv(predict_output_path, index=False)

    # Numerai API uses Environment variables NUMERAI_PUBLIC_ID and NUMERAI_SECRET_KEY
    # these are set by docker via the numerai cli; see README for more info
    logging.info(f'submitting for {model_id}')
    napi.upload_predictions(predict_output_path, model_id=model_id)


def main():
    """
    Creates example_signal_upload.csv to upload for validation and live data submission
    """
    # choose data as of most recent friday
    last_friday = datetime.now() + relativedelta(weekday=FR(-1))
    feature_names, train_data, test_data, live_data = download_data(last_friday)

    for model_id, model_obj in MODEL_CONFIGS:
        model = train(train_data, feature_names, model_id, model_obj)
        predictions = predict(test_data, live_data, last_friday, feature_names, model)
        submit(predictions, "example_signals.csv", model_id)


if __name__ == "__main__":
    main()
