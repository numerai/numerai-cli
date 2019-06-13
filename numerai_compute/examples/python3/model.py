import numerox as nx
import joblib

from sklearn.linear_model import LogisticRegression

# define a model that can be trained separately and saved


class LogisticModel(nx.Model):

    def __init__(self, inverse_l2=0.0001, verbose=False):
        self.verbose = verbose
        self.model = LogisticRegression(
            C=inverse_l2, solver='liblinear', verbose=verbose)

    def fit(self, dfit, tournament):
        self.model.fit(dfit.x, dfit.y[tournament])

    def fit_predict(self, dfit, dpre, tournament):
        # fit is done separately in `.fit()`

        # predict
        yhat = self.model.predict_proba(dpre.x)[:, 1]

        # return predictions along with the original ids
        return dpre.ids, yhat

    def save(self, filename):
        joblib.dump(self, filename)

    @classmethod
    def load(cls, filename):
        return joblib.load(filename)
