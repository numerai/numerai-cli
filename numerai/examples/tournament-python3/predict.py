""" Sample tournament model in python 3 """

import os
import json
import logging
import joblib
import numerapi
import pandas as pd
import lightgbm as lgbm

logging.basicConfig(filename="log.txt", filemode="a")

TOURNAMENT = 8
DATA_VERSION = "v6.0"
TARGET_COL = "target"
TRAINED_MODEL_PREFIX = f"./trained_model_{DATA_VERSION}"

DEFAULT_MODEL_ID = None
DEFAULT_PUBLIC_ID = None
DEFAULT_SECRET_KEY = None

# Read model id and initialize API client with api keys
# these are set by the docker image that you deploy after training,
# but you can also set them manually above for local testing
MODEL_ID = os.getenv("MODEL_ID", DEFAULT_MODEL_ID)
napi = numerapi.NumerAPI(
    public_id=os.getenv("NUMERAI_PUBLIC_ID", DEFAULT_PUBLIC_ID),
    secret_key=os.getenv("NUMERAI_SECRET_KEY", DEFAULT_SECRET_KEY),
)


def get_features(napi):
    napi.download_dataset(f"{DATA_VERSION}/features.json")
    with open(f"{DATA_VERSION}/features.json", "r") as f:
        feature_metadata = json.load(f)
    return feature_metadata["feature_sets"]["small"]


def train(napi, model_id, force_training=False):
    model_name = TRAINED_MODEL_PREFIX
    if model_id:
        model_name += f"_{model_id}"

    # load a model if we have a trained model already and we aren't forcing a training session
    if os.path.exists(model_name) and not force_training:
        logging.info("loading existing trained model")
        model = joblib.load(model_name)
        return model

    logging.info("reading training data")
    napi.download_dataset(f"{DATA_VERSION}/train.parquet")
    train_data = pd.read_parquet(
        f"{DATA_VERSION}/train.parquet",
        columns=get_features(napi) + [TARGET_COL],
    )
    features = train_data.filter(like="feature_", axis="columns").select_dtypes(include="number")
    assert len(features.columns), "No numeric training features found"

    # This will take a few minutes 🍵
    logging.info("training model")
    model = lgbm.LGBMRegressor(
        n_estimators=2000,
        learning_rate=0.01,
        max_depth=5,
        num_leaves=2**5 - 1,
        colsample_bytree=0.1,
    )
    model.fit(
        features,
        train_data[TARGET_COL],
    )

    logging.info("saving model")
    joblib.dump(model, model_name)
    return model


def predict(napi, model):
    logging.info("reading prediction data")
    napi.download_dataset(f"{DATA_VERSION}/live.parquet")
    predict_data = pd.read_parquet(
        f"{DATA_VERSION}/live.parquet", columns=["numerai_ticker"] + model.feature_name_
    ).set_index("numerai_ticker")

    logging.info("generating predictions")
    predictions = model.predict(predict_data[model.feature_name_])
    predictions = pd.DataFrame(
        predictions, columns=["prediction"], index=predict_data.index
    )
    return predictions.rank(pct=True)


def submit(predictions, predict_output_path="predictions.csv", model_id=None):
    logging.info("writing predictions to file and submitting")
    include_index = predictions.index.name is not None
    predictions.to_csv(predict_output_path, index=include_index)
    napi.upload_predictions(predict_output_path, model_id=model_id)


if __name__ == "__main__":
    trained_model = train(napi, MODEL_ID)
    predictions = predict(napi, trained_model)
    submit(predictions, model_id=MODEL_ID)
