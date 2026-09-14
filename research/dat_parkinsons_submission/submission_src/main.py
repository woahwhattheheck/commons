from pathlib import Path
import pandas as pd
from datpark.inference import load_predictor, predict_one

DATA_ROOT = Path("/code_execution/data")
NIFTI_DIR = DATA_ROOT / "niftis"
SUBMISSION_FORMAT_PATH = DATA_ROOT / "submission_format.csv"
WRITE_SUBMISSION_PATH = Path("submission.csv")
BUNDLE_DIR = Path(__file__).resolve().parent / "model_bundle"


def main():
    frame = pd.read_csv(SUBMISSION_FORMAT_PATH, dtype={"uid": str})
    if list(frame.columns) != ["uid", "is_pathologic"]: raise ValueError(f"unexpected submission columns: {list(frame.columns)!r}")
    if frame["uid"].isna().any() or frame["uid"].duplicated().any(): raise ValueError("submission template contains null or duplicate uid")
    device, models, temperatures, config = load_predictor(BUNDLE_DIR); predictions = []
    for uid in frame["uid"].tolist():
        if not uid or Path(uid).name != uid: raise ValueError("unsafe uid in submission template")
        path = NIFTI_DIR / f"{uid}.nii.gz"
        if not path.is_file(): raise FileNotFoundError(path)
        predictions.append(predict_one(path, models=models, temperatures=temperatures, config=config, device=device))
    output = frame.copy(); output["is_pathologic"] = predictions; output.to_csv(WRITE_SUBMISSION_PATH, index=False)


if __name__ == "__main__": main()
