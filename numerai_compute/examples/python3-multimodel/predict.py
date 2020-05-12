import logging
import model
import os

import numerapi
import numerox as nx

# Init basic logger config
logger = logging.getLogger(__name__)
log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)

# Numerai API keys
NUMERAI_PUBLIC_ID = os.environ["NUMERAI_PUBLIC_ID"]
NUMERAI_SECRET_KEY = os.environ["NUMERAI_SECRET_KEY"]

# Upload retry tuning
N_TRIES = 3
SLEEP_SECONDS = 60

def predict_and_submit(data, model_class):
    model_name = model_class.__name__
    model_id = model_class.model_id
    logger = logging.getLogger(model_name)

    for tournament in nx.tournament_names():

        logger.info(f"Predict and submit for {tournament} using {model_class}")
        saved_model_name = f'model_trained_{model_name}_{tournament}'
        if os.path.exists(saved_model_name):
            logger.info(f'Using saved model {saved_model_name}')
            m = model_class.load(saved_model_name)
        else:
            logger.info(f'Saved model {saved_model_name} not found')
            m = model_class(verbose=True)

            try:
                logger.info(f'Training model against {tournament} training data')
                m.fit(data['train'], tournament)
            except Exception as e:
                logger.error(f'Failed to train {model_class} - {e}')
                return

        # fit model with train data and make predictions for tournament data
        logger.info(f'Predicting with {model_class} on {tournament} data')
        prediction = nx.production(m, data, tournament=tournament)

        # save predictions to csv file
        prediction_filename = f'/tmp/prediction_{model_name}_{tournament}.csv'
        logger.info(f"Saving predictions to {prediction_filename}")
        prediction.to_csv(prediction_filename, verbose=True)

        try:
            # submit the prediction
            logger.info(f"Submitting predictions from {prediction_filename} using {model_id}")
            submission_id, status = nx.upload(prediction_filename,
                                              tournament,
                                              NUMERAI_PUBLIC_ID,
                                              NUMERAI_SECRET_KEY,
                                              block=False,
                                              n_tries=N_TRIES,
                                              sleep_seconds=SLEEP_SECONDS,
                                              model_id=model_id)
            logger.info(status)
            logger.info(f'Successfully submitted predictions using model_id {model_id}')
        except Exception as e:
            logger.error(f'Upload failed with - {e}')


if __name__ == '__main__':
    logger.info('Downloading dataset')
    data = nx.download('numerai_dataset.zip')

    for model_class in model.models[1:]:
        predict_and_submit(data, model_class)
