import predict

train_data_path, predict_data_path, predict_output_path = predict.download_data()
predict.train(train_data_path, force_training=True)
