import numerox as nx
import numerapi
import os
import model


def predict_and_submit(tournaments, data, model_class, numerai_public, numerai_secret):
    model_name = model_class.__name__
    for tournament_name in tournaments:
        saved_model_name = f'model_trained_{model_name}_{tournament_name}'
        if os.path.exists(saved_model_name):
            print("using saved model for", tournament_name)
            m = model_class.load(saved_model_name)
        else:
            print("saved model not found for", tournament_name)
            m = model_class(verbose=True)

            print("training model for", tournament_name)
            m.fit(data['train'], tournament_name)

        print("running predictions for", tournament_name)
        # fit model with train data and make predictions for tournament data
        prediction = nx.production(m, data, tournament=tournament_name)

        # save predictions to csv file
        prediction_filename = f'/tmp/prediction_{model_name}_{tournament_name}.csv'
        prediction.to_csv(prediction_filename, verbose=True)

    # submit the prediction
    for tournament_name in tournaments:
        prediction_filename = f'/tmp/prediction_{model_name}_{tournament_name}.csv'

        submission_id = nx.upload(
            prediction_filename, tournament_name, numerai_public, numerai_secret, block=False, n_tries=3)

    # staking variables
    # change block in nx.upload to block=True. This is because you can't stake until the submission has finished its checks, which take a few minutes
    # confidence = .501 # increase this number to signify your confidence in a minimum AUC. Can't go below .501
    # stake_value = .1 # the amount of NMR to stake

    # napi = numerapi.NumerAPI(numerai_public, numerai_secret)

    # for tournament_name in tournaments:
    #   napi.stake(confidence, stake_value, nx.tournament_int(tournament_name))


if __name__ == '__main__':
    tournaments = nx.tournament_names()
    print(tournaments)

    # download dataset from numerai
    data = nx.download('numerai_dataset.zip')

    predict_and_submit(tournaments, data, model.LogisticModel,
                       os.environ["NUMERAI_PUBLIC_ID_1"], os.environ["NUMERAI_SECRET_KEY_1"])
    predict_and_submit(tournaments, data, model.LogisticAndFactorAnalysisModel,
                       os.environ["NUMERAI_PUBLIC_ID_2"], os.environ["NUMERAI_SECRET_KEY_2"])
    predict_and_submit(tournaments, data, model.LogisticAndPCAModel,
                       os.environ["NUMERAI_PUBLIC_ID_3"], os.environ["NUMERAI_SECRET_KEY_3"])
