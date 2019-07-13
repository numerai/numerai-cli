import numerox as nx
import numerapi
import os
import model

tournaments = nx.tournament_names()
print(tournaments)

# download dataset from numerai
data = nx.download('numerai_dataset.zip')

for tournament_name in tournaments:
    # create your model
    m = model.LinearModel(verbose=True)

    print("fitting model for", tournament_name)
    m.fit(data['train'], tournament_name)

    print("saving model for", tournament_name)
    m.save('model_trained_' + tournament_name)
