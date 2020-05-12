import pickle

import joblib
import numerox as nx
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.svm import SVC
from sklearn import decomposition, pipeline, preprocessing


class LinearModel(nx.Model):

    # You must specify your model_id from https://numer.ai/models or submission will fail
    model_id = None

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.model = LinearRegression()

    def fit(self, dfit, tournament):
        self.model.fit(dfit.x, dfit.y[tournament])

    def fit_predict(self, dfit, dpre, tournament):
        # fit is done separately in `.fit()`

        # predict
        yhat = self.model.predict(dpre.x)

        # return predictions along with the original ids
        return dpre.ids, yhat

    def save(self, filename):
        joblib.dump(self, filename)

    @classmethod
    def load(cls, filename):
        return joblib.load(filename)

class YetAnotherLinearModel(LinearModel):

    # You must specify your model_id from https://numer.ai/models or submission will fail
    model_id = None

    def fit_predict(self, dfit, dpre, tournament):
        # fit is done separately in `.fit()`

        # predict
        yhat = self.model.predict(dpre.x)

        # return predictions along with the original ids
        return dpre.ids, yhat

# Declare your model classes to be trained and used for predictions
models = [LinearModel, YetAnotherLinearModel]
