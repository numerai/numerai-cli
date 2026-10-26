""" An extra entry point specifically for training. Used when running locally """

import predict

assert predict.MODEL_ID, "Set MODEL_ID to the model ID configured for your deployed node"

predict.train(predict.napi, predict.MODEL_ID, force_training=True)
