""" Sample tournament model in python 3 """

import os
import logging
import joblib
import numerapi
import pandas as pd
from sklearn.linear_model import LinearRegression

TRAINED_MODEL_PREFIX = './trained_model'

# Pull model id from "MODEL_ID" environment variable
# defaults to None, change to a model id from
MODEL_ID = os.getenv('MODEL_ID', None)
MODEL = LinearRegression()

# initialize API client
napi = numerapi.NumerAPI()


def download_data():
    """ Download the data files """

    logging.info('downloading tournament data files')
    # create an API client and download current data
    file_path = napi.download_current_dataset()
    # we only want the unzipped directory
    file_path = file_path.split('.zip')[0]
    logging.info('output path: %s', file_path)

    train_data_path = f'{file_path}/numerai_training_data.csv'
    predict_data_path = f'{file_path}/numerai_tournament_data.csv'
    predict_output_path = f'{file_path}/predictions.csv'

    return train_data_path, predict_data_path, predict_output_path


def train(train_data_path, model_id, model, force_training=False):
    """ Train the model """

    model_name = TRAINED_MODEL_PREFIX
    if model_id:
        model_name += f"_{model_id}"

    # load a model if we have a trained model already and we aren't forcing a training session
    if os.path.exists(model_name) and not force_training:
        logging.info('loading existing trained model')
        model = joblib.load(model_name)
        return model

    logging.info('reading training data')
    train_data = pd.read_csv(train_data_path)

    logging.info('extracting features and targets')
    # get all rows and all columns from 4th to last-1
    train_features = train_data.iloc[:, 3:-1]
    # get all rows and only last column
    train_targets = train_data.iloc[:, -1]
    del train_data

    logging.info('training model')
    model.fit(X=train_features, y=train_targets)

    logging.info('saving model')
    joblib.dump(model, model_name)

    return model


def predict(model, predict_data_path):
    """ Predict the results based on the previously trained model """

    logging.info('reading prediction data')
    predict_data = pd.read_csv(predict_data_path)

    logging.info('extracting features')
    # get all rows and only first column
    predict_ids = predict_data.iloc[:, 0]
    # get all rows and all columns from 4th to last-1
    predict_features = predict_data.iloc[:, 3:-1]
    del predict_data

    logging.info('generating predictions')
    predictions = model.predict(predict_features)
    predictions = pd.DataFrame(predictions, columns=['prediction'])
    predictions.insert(0, "id", predict_ids)

    return predictions


def submit(predictions, predict_output_path, model_id=None):
    """ Submit a prediction """

    logging.info('writing predictions to file')
    # numerai doesn't want the index, so don't write it to our file
    predictions.to_csv(predict_output_path, index=False)

    # Numerai API uses Environment variables to find your keys:
    # NUMERAI_PUBLIC_ID and NUMERAI_SECRET_KEY
    # these are set by docker via the numerai cli; see README for more info
    logging.info('submitting')
    napi.upload_predictions(predict_output_path, model_id=model_id)


def main():
    """ Download, train, predict and submit for this model """

    train_data_path, predict_data_path, predict_output_path = download_data()
    trained_model = train(train_data_path, MODEL_ID, MODEL)
    predictions = predict(trained_model, predict_data_path)
    submit(predictions, predict_output_path, MODEL_ID)


if __name__ == '__main__':
    main()
