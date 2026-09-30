""" An extra entry point specifically for training. Used when running locally """

import predict

predict.train(predict.napi, predict.MODEL_ID, force_training=True)
