""" Sample tournament model in python 3 """

import os
import json
import logging
import joblib
import numerapi
import pandas as pd
from sklearn.linear_model import LinearRegression

logging.basicConfig(filename="log.txt", filemode="a")

DATA_VERSION = "v4.1"
ERA_COL = "era"
DATA_TYPE_COL = "data_type"
TARGET_COL = "target_nomi_v4_20"
TRAINED_MODEL_PREFIX = "./trained_model"

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
    return feature_metadata["feature_sets"]["small"] + [
        ERA_COL,
        DATA_TYPE_COL,
        TARGET_COL,
    ]


def train(napi, model_id, force_training=False):
    model_name = TRAINED_MODEL_PREFIX
    if model_id:
        model_name += f"_{model_id}"

    # load a model if we have a trained model already and we aren't forcing a training session
    if os.path.exists(model_name) and not force_training:
        logging.info("loading existing trained model")
        model = joblib.load(model_name)
        return model

    model = LinearRegression()

    logging.info("reading training data")
    napi.download_dataset(f"{DATA_VERSION}/train.parquet")
    train_data = pd.read_parquet(
        f"{DATA_VERSION}/train.parquet", columns=get_features(napi)
    )

    logging.info("training model")
    model.fit(
        X=train_data.filter(like="feature_", axis="columns"),
        y=train_data[TARGET_COL],
    )

    logging.info("saving model")
    joblib.dump(model, model_name)
    return model


def predict(napi, model):
    logging.info("reading prediction data")
    napi.download_dataset(f"{DATA_VERSION}/live.parquet")
    predict_data = pd.read_parquet(
        f"{DATA_VERSION}/live.parquet", columns=get_features(napi)
    )

    logging.info("generating predictions")
    predictions = model.predict(predict_data.filter(like="feature_", axis="columns"))
    predictions = pd.DataFrame(
        predictions, columns=["prediction"], index=predict_data.index
    )
    return predictions


def submit(predictions, predict_output_path="predictions.csv", model_id=None):
    logging.info("writing predictions to file and submitting")
    predictions.to_csv(predict_output_path)
    napi.upload_predictions(predict_output_path, model_id=model_id)


if __name__ == "__main__":
    trained_model = train(napi, MODEL_ID)
    predictions = predict(napi, trained_model)
    submit(predictions, model_id=MODEL_ID)
