"""
Download the dataset used by this project and rebuild the exact CSV the code reads.

1. The complete original dataset from the UCI Machine Learning Repository
   (ElectricityLoadDiagrams20112014, ID 321): 370 clients, 15-minute readings, 2011-2014.
   Saved as LD2011_2014_raw.txt.zip and extracted to LD2011_2014.txt (about 711 MB).
2. The standard hourly packaging of the same data (LSTNet release: 2012-2014, 321 clients,
   15-minute readings summed to hourly). Saved as electricity_hourly_LSTNet.txt.gz.
3. electricity_hourly_2012_2014.csv: the LSTNet matrix with a date column and MT_001..MT_321
   headers. This is the file the code uses (code/data_pipeline.py). It is also committed to the
   repository, so step 3 only matters if you want to rebuild it yourself.

Note: the hourly packaging renumbers the 321 retained clients as MT_001..MT_321, so its IDs do
not match the raw UCI file's MT_001..MT_370 numbering.

Usage (from the project root):  python Dataset/download_dataset.py [--skip-raw] [--rebuild-only]
"""
import argparse, gzip, io, os, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
UCI_ZIP = "https://archive.ics.uci.edu/static/public/321/electricityloaddiagrams20112014.zip"
LSTNET_GZ = "https://raw.githubusercontent.com/laiguokun/multivariate-time-series-data/master/electricity/electricity.txt.gz"
RAW_ZIP = os.path.join(HERE, "LD2011_2014_raw.txt.zip")
RAW_TXT = os.path.join(HERE, "LD2011_2014.txt")
HOURLY_GZ = os.path.join(HERE, "electricity_hourly_LSTNet.txt.gz")
HOURLY_CSV = os.path.join(HERE, "electricity_hourly_2012_2014.csv")


def fetch(url, dest):
    if os.path.exists(dest):
        print(f"  already have {os.path.basename(dest)}")
        return
    print(f"  downloading {url}")
    tmp = dest + ".part"
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length", 0)); done = 0
        while chunk := r.read(1 << 20):
            f.write(chunk); done += len(chunk)
            if total:
                print(f"\r  {done / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    os.replace(tmp, dest)


def extract_raw():
    if os.path.exists(RAW_TXT):
        print("  already have LD2011_2014.txt"); return
    with zipfile.ZipFile(RAW_ZIP) as z:
        name = next(n for n in z.namelist() if n.endswith("LD2011_2014.txt"))
        with z.open(name) as src, open(RAW_TXT, "wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)
    print("  extracted LD2011_2014.txt")


def build_csv():
    import numpy as np, pandas as pd
    with gzip.open(HOURLY_GZ, "rt") as f:
        X = np.loadtxt(f, delimiter=",")
    assert X.shape == (26304, 321), X.shape
    df = pd.DataFrame(X, columns=[f"MT_{i:03d}" for i in range(1, 322)])
    df.insert(0, "date", pd.date_range("2012-01-01 00:00:00", periods=len(df), freq="h"))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-raw", action="store_true", help="skip the 261 MB original UCI download")
    ap.add_argument("--rebuild-only", action="store_true", help="only rebuild the CSV from the local .gz")
    a = ap.parse_args()
    if not a.rebuild_only:
        if not a.skip_raw:
            print("[1/3] original UCI dataset"); fetch(UCI_ZIP, RAW_ZIP); extract_raw()
        print("[2/3] hourly packaging (LSTNet)"); fetch(LSTNET_GZ, HOURLY_GZ)
    print("[3/3] building electricity_hourly_2012_2014.csv")
    df = build_csv()
    df.to_csv(HOURLY_CSV, index=False, float_format="%.10g")
    print(f"  wrote {HOURLY_CSV}: {df.shape[0]} rows x {df.shape[1] - 1} clients")


if __name__ == "__main__":
    main()
