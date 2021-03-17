import predict

train_data_path, predict_data_path, predict_output_path = predict.download_data()

for model_id, model_type in predict.MODEL_CONFIGS:
    predict.train(train_data_path, model_id, model_type, force_training=True)