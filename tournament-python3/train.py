""" An extra entry point specifically for training. Used when running locally """

import predict

train_data_path, predict_data_path, predict_output_path = predict.download_data()

model_id = predict.MODEL_ID
model_type = predict.MODEL

predict.train(train_data_path, model_id, model_type, force_training=True)
