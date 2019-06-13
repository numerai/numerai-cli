import numerox as nx
import numerapi
import os
import model


def train(tournaments, data, model_class):
    model_name = model_class.__name__

    for tournament_name in tournaments:
        saved_model_name = f'model_trained_{model_name}_{tournament_name}'
        # create your model
        m = model_class(verbose=True)

        print("fitting model for", saved_model_name)
        m.fit(data['train'], tournament_name)

        print("saving model for", saved_model_name)
        m.save(saved_model_name)


if __name__ == '__main__':

    tournaments = nx.tournament_names()
    print(tournaments)

    # download dataset from numerai
    data = nx.download('numerai_dataset.zip')

    train(tournaments, data, model.LogisticModel)
    train(tournaments, data, model.LogisticAndFactorAnalysisModel)
    train(tournaments, data, model.LogisticAndPCAModel)
