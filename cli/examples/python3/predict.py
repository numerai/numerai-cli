import os
import logging
import joblib
import numerapi
import pandas as pd
from sklearn.linear_model import LinearRegression


TRAINED_MODEL_PREFIX = './trained_model'
# Define models here as (ID, model instance),
# a model ID of None is submitted as your default model
MODEL_CONFIGS = [
    (None, LinearRegression()),
    # (YOUR MODEL ID, LinearRegression(n_jobs=10))
    #  etc...
]

# initialize API client
napi = numerapi.NumerAPI()


def download_data():
    logging.info('downloading tournament data files')
    # create an API client and download current data
    file_path = napi.download_current_dataset()
    file_path = file_path.split('.zip')[0]         # we only want the unzipped directory
    logging.info(f'output path: {file_path}')

    train_data_path = f'{file_path}/numerai_training_data.csv'
    predict_data_path = f'{file_path}/numerai_tournament_data.csv'
    predict_output_path = f'{file_path}/predictions.csv'

    return train_data_path, predict_data_path, predict_output_path


def train(train_data_path, model_id, model, force_training=False):
    model_name = TRAINED_MODEL_PREFIX
    if model_id:
        model_name += f"_{model_id}"

    # load a model if we have a trained model already and we aren't forcing a training session
    if os.path.exists(model_name) and not force_training:
        logging.info('loading existing trained model')
        model = joblib.load(model_name)
        return model

    logging.info(f'reading training data')
    train_data = pd.read_csv(train_data_path)

    logging.info('extracting features and targets')
    train_features = train_data.iloc[:, 3:-1]   # get all rows and all columns from 4th to last-1
    train_targets = train_data.iloc[:, -1]      # get all rows and only last column

    logging.info(f'training model')
    model.fit(X=train_features, y=train_targets)

    logging.info('saving features')
    joblib.dump(model, model_name)

    return model


def predict(model, predict_data_path):
    logging.info(f'reading prediction data')
    predict_data = pd.read_csv(predict_data_path)

    logging.info('extracting features')
    predict_ids = predict_data.iloc[:, 0]           # get all rows and only first column
    predict_features = predict_data.iloc[:, 3:-1]   # get all rows and all columns from 4th to last-1

    logging.info(f'generating predictions')
    predictions = model.predict(predict_features)
    predictions = pd.DataFrame(predictions, columns=['prediction'])
    predictions.insert(0, "id", predict_ids)

    return predictions


def submit(predictions, model_id=None):
    logging.info('writing predictions to file')
    # numerai doesn't want the index, so don't write it to our file
    predictions.to_csv(predict_output_path, index=False)

    # Numerai API uses Environment variables to find your keys: NUMERAI_PUBLIC_ID and NUMERAI_SECRET_KEY
    # these are set by docker via the numerai cli; see README for more info
    logging.info(f'submitting')
    napi.upload_predictions(predict_output_path, model_id=model_id)


if __name__ == '__main__':
    train_data_path, predict_data_path, predict_output_path = download_data()

    for model_id, model_type in MODEL_CONFIGS:
        trained_model = train(train_data_path, model_id, model_type)
        predictions = predict(trained_model, predict_data_path)
        submit(predictions, model_id)
