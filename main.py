import numerox as nx
import numerapi
import os

from sklearn.linear_model import LogisticRegression

tournaments = nx.tournament_names()
print(tournaments)


class logistic(nx.Model):
    # define your model

    def __init__(self, inverse_l2=0.0001, verbose=False):
        self.p = {'inverse_l2': inverse_l2}
        self.verbose = verbose

    def fit_predict(self, dfit, dpre, tournament):
        # create a sklearn.LogisticRegression model
        model = LogisticRegression(
            C=self.p['inverse_l2'], solver='liblinear', verbose=self.verbose)

        # fit the data
        model.fit(dfit.x, dfit.y[tournament])

        # predict
        yhat = model.predict_proba(dpre.x)[:, 1]

        # return predictions along with the original ids
        return dpre.ids, yhat


# download dataset from numerai
data = nx.download('numerai_dataset.zip')

for tournament_name in tournaments:
    # create your model
    model = logistic(verbose=True)

    # fit model with train data and make predictions for tournament data
    prediction = nx.production(model, data, tournament=tournament_name)

    # save predictions to csv file
    prediction_filename = 'prediction_' + tournament_name + '.csv'
    prediction.to_csv(prediction_filename, verbose=True)

# submit the prediction

# Numerai API key
# You will need to create an API key by going to https://numer.ai/account and clicking "Add" under the "Your API keys" section.
# Select the following permissions for the key: "Upload submissions", "Make stakes", "View historical submission info", "View user info"
public_id = os.environ["NUMERAI_PUBLIC_ID"]
secret_key = os.environ["NUMERAI_SECRET_KEY"]

for tournament_name in tournaments:
    prediction_filename = 'prediction_' + tournament_name + '.csv'

    submission_id = nx.upload(
        prediction_filename, tournament_name, public_id, secret_key)

# staking variables
# confidence = .501 # increase this number to signify your confidence in a minimum AUC. Can't go below .501
# stake_value = .1 # the amount of NMR to stake

# napi = numerapi.NumerAPI(public_id, secret_key)

# for tournament_name in tournaments:
#   napi.stake(confidence, stake_value, nx.tournament_int(tournament_name))
