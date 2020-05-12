import logging
import model
import os

import numerox as nx
import numerapi

# Init basic logger config
logger = logging.getLogger(__name__)
log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)

def train(data, model_class):
    model_name = model_class.__name__

    for tournament_name in nx.tournament_names():
        saved_model_name = f'model_trained_{model_name}_{tournament_name}'

        # create your model
        m = model_class(verbose=True)

        logger.info(f'Fitting {model_name} for {saved_model_name}')
        m.fit(data['train'], tournament_name)

        logger.info(f'Saving {model_name} for {saved_model_name}')
        m.save(saved_model_name)


if __name__ == '__main__':
    logger.info('Downloading dataset')
    data = nx.download('numerai_dataset.zip')

    # Or load dataset locally from file
    #data = nx.load_zip('numerai_datasets.zip', include_train=True, single_precision=True)

    # Train your models
    for model_class in model.models:
        try:
            train(data, model_class)
        except Exception as e:
            logger.error(f'Failed to train model {model_class} - {e}')
            raise

