"""
Import the Intel Berkeley Lab data into the readings table.

Usage:
    python import_intel.py data.txt.gz            # auto-picks the mote with the most data
    python import_intel.py data.txt.gz --mote 7   # use a specific mote

Run it from the folder that contains config.py and DatabaseModel.py.
It creates one AppSession for the imported history and inserts one reading
per minute (mean of the raw 31-second readings) for the chosen mote.
"""
import argparse
import uuid

import pandas as pd

COLS = ["date", "time", "epoch", "moteid", "temperature", "humidity", "light", "voltage"]



def load_clean(path: str, mote: int | None = None) -> tuple[pd.DataFrame, int]:
    """Return (1-minute DataFrame indexed by time with temperature/humidity, mote id)."""
    df = pd.read_csv(
        path, sep=" ", names=COLS, compression="infer",
        usecols=["date", "time", "moteid", "temperature", "humidity"],
        dtype=str, on_bad_lines="skip",
    )
    total = len(df)

    df["ts"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
    for c in ["moteid", "temperature", "humidity"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["ts", "moteid", "temperature", "humidity"])

    # Drop glitchy values (outside a plausible indoor range)
    df = df[df["temperature"].between(0, 50) & df["humidity"].between(0, 100)]
    print(f"Kept {len(df):,} of {total:,} rows after cleaning")

    if mote is None:
        mote = int(df["moteid"].value_counts().idxmax())
        print(f"Auto-selected mote {mote} (most rows)")
    df = df[df["moteid"] == mote]
    if df.empty:
        raise SystemExit(f"No usable rows for mote {mote}")

    # One reading per minute; fill gaps of up to 5 minutes, drop the rest
    minute = (
        df.set_index("ts")[["temperature", "humidity"]]
        .sort_index()
        .resample("1min")
        .mean()
        .interpolate(limit=5, limit_area="inside")
        .dropna()
    )
    return minute, mote


def insert_session(minute: pd.DataFrame, batch_size: int = 10_000) -> None:
    # Imported here so load_clean can be used without a database
    from config import SessionLocal
    from DatabaseModel import AppSession, Readings

    start = minute.index[0].to_pydatetime()
    end = minute.index[-1].to_pydatetime()

    db = SessionLocal()
    try:
        exists = db.query(AppSession).filter(AppSession.created_at == start).first()
        if exists:
            raise SystemExit("A session starting at that time already exists; already imported?")

        session = AppSession(created_at=start, disconected_at=end)
        db.add(session)
        db.flush()  # makes session.id usable for the foreign key

        rows = [
            {
                "id": uuid.uuid4(),
                "temperature": round(float(r.temperature), 2),
                "humidity": round(float(r.humidity), 2),
                "recieved_at": ts.to_pydatetime(),
                "session_id": session.id,
            }
            for ts, r in minute.iterrows()
        ]
        for i in range(0, len(rows), batch_size):
            db.bulk_insert_mappings(Readings, rows[i:i + batch_size])

        db.commit()
        print(f"Inserted {len(rows):,} readings ({start} to {end}) into session {session.id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="path to data.txt.gz (or the unzipped data.txt)")
    ap.add_argument("--mote", type=int, default=None, help="mote id to import (default: most data)")
    args = ap.parse_args()

    minute, mote = load_clean(args.path, args.mote)
    print(f"Mote {mote}: {len(minute):,} one-minute readings "
          f"from {minute.index[0]} to {minute.index[-1]}")
    insert_session(minute)
