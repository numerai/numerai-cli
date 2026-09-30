"""Checks for the deployable Signals example without downloading full datasets."""

import importlib.util
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd


EXAMPLE = Path(__file__).resolve().parents[1] / "numerai/examples/signals-python3/predict.py"
spec = importlib.util.spec_from_file_location("signals_example", EXAMPLE)
signals = importlib.util.module_from_spec(spec)
with patch("logging.basicConfig"):
    spec.loader.exec_module(signals)


class SignalsExampleTest(unittest.TestCase):
    def test_training_entry_point(self):
        example_dir = EXAMPLE.parent
        with patch.dict(sys.modules, {"predict": signals}), patch.object(signals, "train") as train:
            runpy.run_path(str(example_dir / "train.py"), run_name="__main__")
        train.assert_called_once_with(signals.napi, signals.MODEL_ID, force_training=True)

    def test_train_and_predict_with_v3_data(self):
        train_data = pd.DataFrame(
            {
                "feature_alpha": [0.1, 0.2],
                "feature_beta": [0.3, 0.4],
                "feature_country": ["US", "GB"],
                "target": [0.2, 0.8],
            }
        )
        live_data = pd.DataFrame(
            {
                "numerai_ticker": ["A", "B"],
                "feature_beta": [0.5, 0.6],
                "feature_alpha": [0.7, 0.8],
                "feature_country": ["US", "GB"],
            }
        )
        api = Mock()
        model = Mock()
        model.feature_name_ = ["feature_alpha", "feature_beta"]
        model.predict.return_value = [0.1, 0.9]

        def read_parquet(path):
            return train_data if path.endswith("train.parquet") else live_data

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(signals, "TRAINED_MODEL_PREFIX", f"{directory}/trained_model_signals_v3.0"),
                patch.object(signals.pd, "read_parquet", side_effect=read_parquet),
                patch.object(signals.lgbm, "LGBMRegressor", return_value=model),
                patch.object(signals.joblib, "dump"),
            ):
                trained_model = signals.train(api, "model-id")
                predictions = signals.predict(api, trained_model)

        self.assertEqual(
            [call.args[0] for call in api.download_dataset.call_args_list],
            ["signals/v3.0/train.parquet", "signals/v3.0/live.parquet"],
        )
        self.assertEqual(list(model.fit.call_args.args[0].columns), model.feature_name_)
        self.assertEqual(list(model.predict.call_args.args[0].columns), model.feature_name_)
        self.assertEqual(predictions.index.name, "numerai_ticker")
        self.assertEqual(predictions["prediction"].tolist(), [0.1, 0.9])


if __name__ == "__main__":
    unittest.main()
