import importlib.util
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd


EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "numerai/examples/tournament-python3/predict.py"
)
spec = importlib.util.spec_from_file_location("classic_example", EXAMPLE)
classic = importlib.util.module_from_spec(spec)
with patch("logging.basicConfig"):
    spec.loader.exec_module(classic)


class ClassicExampleTest(unittest.TestCase):
    def test_training_entry_point(self):
        with (
            patch.dict(sys.modules, {"predict": classic}),
            patch.object(classic, "train") as train,
        ):
            runpy.run_path(str(EXAMPLE.parent / "train.py"), run_name="__main__")
        train.assert_called_once_with(
            classic.napi, classic.MODEL_ID, force_training=True
        )

    def test_train_predict_and_submit_v6(self):
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
                "numerai_ticker": ["B US", "A US"],
                "date": ["2026-01-02"] * 2,
                "feature_beta": [0.5, 0.6],
                "feature_alpha": [0.7, 0.8],
                "feature_country": ["US", "GB"],
            }
        )
        api = Mock()
        model = Mock()
        model.feature_name_ = ["feature_alpha", "feature_beta"]
        model.predict.return_value = [-2.0, 3.0]

        def read_parquet(path, columns=None):
            data = train_data if path.endswith("train.parquet") else live_data
            return data if columns is None else data[columns]

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(
                    classic, "TRAINED_MODEL_PREFIX", f"{directory}/trained_model_v6.0"
                ),
                patch.object(classic.pd, "read_parquet", side_effect=read_parquet),
                patch.object(
                    classic,
                    "get_features",
                    return_value=["feature_alpha", "feature_country", "feature_beta"],
                ),
                patch.object(classic.lgbm, "LGBMRegressor", return_value=model),
                patch.object(classic.joblib, "dump"),
                patch.object(classic, "napi", api),
            ):
                trained_model = classic.train(api, "model-id")
                predictions = classic.predict(api, trained_model)
                filename = str(Path(directory) / "predictions.csv")
                classic.submit(predictions, filename, "model-id")
                output = pd.read_csv(filename)

        self.assertEqual(
            [call.args[0] for call in api.download_dataset.call_args_list],
            ["v6.0/train.parquet", "v6.0/live.parquet"],
        )
        self.assertEqual(list(model.fit.call_args.args[0].columns), model.feature_name_)
        self.assertEqual(
            list(model.predict.call_args.args[0].columns), model.feature_name_
        )
        self.assertEqual(
            output.to_dict("list"),
            {"numerai_ticker": ["B US", "A US"], "prediction": [0.5, 1.0]},
        )
        api.upload_predictions.assert_called_once_with(filename, model_id="model-id")


if __name__ == "__main__":
    unittest.main()
