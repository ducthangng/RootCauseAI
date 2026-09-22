import glob
import pandas as pd

path = glob.glob("/opt/ml/processing/input/data/*.csv")[0]
df = pd.read_csv(path)
print("rows:", len(df))
df["processed"] = True           # TODO: logic thật
df.to_csv("/opt/ml/processing/output/processed.csv", index=False)