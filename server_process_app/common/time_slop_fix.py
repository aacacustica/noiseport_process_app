import os
import shutil
import tqdm

from pathlib import Path
import pandas as pd

from config import *
from logging_config import *




from server_process_app.common.logging_config import *
from server_process_app.common.config import *

logger = setup_logging("query_automatize")

CODE_ROOT = Path("/home/aac/I+D/CODIGOS/NoisePort_server")
INBOX_ROOT = Path("/srv/services/inbox")

TIMESTAMP_CANDIDATES = (
    "Timestamp",
    "timestamp",
    "date",
    "Date",
    "datetime",
    "Datetime",
)

SOURCE_FILE_COL = "_source_file_path"

def bucket_end_time(bucket):
    day, hour = parse_bucket(bucket)

    if day is None:
        return None

    try:
        if hour is None:
            # Bucket diario YYYYMMDD acaba al día siguiente a las 00:00
            return pd.to_datetime(day, format="%Y%m%d") + pd.Timedelta(days=1)

        # Bucket horario YYYYMMDD_HH acaba a la hora siguiente
        return pd.to_datetime(f"{day}_{hour:02d}", format="%Y%m%d_%H") + pd.Timedelta(hours=1)

    except Exception:
        return None


def is_bucket_closed(bucket, grace_minutes=30):
    end_time = bucket_end_time(bucket)

    if end_time is None:
        return False

    now = pd.Timestamp.now()

    return now >= end_time + pd.Timedelta(minutes=grace_minutes)


def resolve_output_path(path):
    path = Path(path)

    try:
        relative = path.relative_to(CODE_ROOT)
        return INBOX_ROOT / relative
    except ValueError:
        return path
    

def get_time_column(df):
    for col in TIMESTAMP_CANDIDATES:
        if col in df.columns:
            return col
    return None


def normalize_timestamp_column(df, csv_path=None, logger=None):
    if df is None or df.empty:
        return None

    time_col = get_time_column(df)

    if time_col is None:
        return None

    df = df.copy()
    df["Timestamp"] = pd.to_datetime(df[time_col], errors="coerce")

    if df["Timestamp"].dropna().empty:
        return None

    return df


def safe_read_timestamp_series(csv_path, nrows=10):
    try:
        df = pd.read_csv(csv_path, nrows=nrows)
    except Exception:
        return None

    df = normalize_timestamp_column(df, csv_path, logger)

    if df is None:
        return None

    ts = df["Timestamp"].dropna()

    if ts.empty:
        return None

    return ts


def get_csv_first_valid_timestamp(csv_path):
    ts_series = safe_read_timestamp_series(csv_path, nrows=10)

    if ts_series is None or ts_series.empty:
        return None

    return ts_series.iloc[0]


def get_csv_last_valid_timestamp(csv_path):
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return None

    df = normalize_timestamp_column(df, csv_path, logger)

    if df is None:
        return None

    ts = df["Timestamp"].dropna()

    if ts.empty:
        return None

    return ts.iloc[-1]


def sort_csvs_by_content_timestamp(folder):
    csvs = [
        f for f in os.listdir(folder)
        if f.lower().endswith(".csv")
    ]

    def _key(fname):
        ts = get_csv_first_valid_timestamp(os.path.join(folder, fname))
        return ts.timestamp() if ts is not None else float("inf")

    return sorted(csvs, key=_key)


def parse_bucket(bucket):
    parts = bucket.split("_")

    if len(parts) == 1:
        return parts[0], None

    if len(parts) == 2:
        try:
            return parts[0], int(parts[1])
        except ValueError:
            return None, None

    return None, None


def build_bucket_key_from_timestamp(ts, original_bucket):
    _, original_hour = parse_bucket(original_bucket)

    day = ts.strftime("%Y%m%d")

    if original_hour is None:
        return day

    return f"{day}_{ts.hour:02d}"


def get_next_hour_bucket(bucket):
    day, hour = parse_bucket(bucket)

    if day is None:
        return None

    if hour is None:
        next_day = (pd.to_datetime(day) + pd.Timedelta(days=1)).strftime("%Y%m%d")
        return next_day

    if hour < 23:
        return f"{day}_{hour + 1:02d}"

    next_day = (pd.to_datetime(day) + pd.Timedelta(days=1)).strftime("%Y%m%d")
    return f"{next_day}_00"


def get_bucket_list(measurement_path):
    return sorted([
        b for b in os.listdir(measurement_path)
        if os.path.isdir(os.path.join(measurement_path, b))
        and not b.startswith("fixed_")
        and "fixed" not in b
        and not b.endswith(".txt")
    ])


def copy_original_csvs(bucket_path, fixed_folder, measurement_folder):
    if measurement_folder in ("predictions", "predictions_litle"):
        csv_files = [
            f for f in os.listdir(bucket_path)
            if f.endswith("w_1.0.csv")
        ]
    else:
        csv_files = [
            f for f in os.listdir(bucket_path)
            if f.lower().endswith(".csv")
        ]

    os.makedirs(fixed_folder, exist_ok=True)

    for fname in csv_files:
        src = os.path.join(bucket_path, fname)
        dst = os.path.join(fixed_folder, fname)

        if not os.path.exists(dst):
            shutil.copy(src, dst)

    return csv_files


def detect_minute_jump_by_content(prev_path, curr_path, threshold_seconds=70):
    tprev = get_csv_last_valid_timestamp(prev_path)
    tcurr = get_csv_first_valid_timestamp(curr_path)

    if tprev is None or tcurr is None:
        return False

    return (tcurr - tprev).total_seconds() > threshold_seconds


def get_extra_seconds_indices(csv_path):
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return 0, []

    df = normalize_timestamp_column(df, csv_path, logger)

    if df is None:
        return 0, []

    df["Timestamp"] = df["Timestamp"].apply(
        lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x
    )

    timestamps_valid = df["Timestamp"].dropna()

    if timestamps_valid.empty:
        return 0, []

    official_minute = timestamps_valid.iloc[0].minute

    idxs = df[
        df["Timestamp"].notna()
        & (df["Timestamp"].dt.minute != official_minute)
    ].index.tolist()

    return len(idxs), idxs


def drop_internal_columns(df):
    if SOURCE_FILE_COL in df.columns:
        return df.drop(columns=[SOURCE_FILE_COL])
    return df


def log_row_move(n_rows, src_path, dst_path):
    logger.info(f"Moving {n_rows} rows from {src_path} to {dst_path}")


def append_extra_seconds(fixed_folder_path, prev_name, curr_name, row_indices):
    if not row_indices:
        return

    prev_path = os.path.join(fixed_folder_path, prev_name)
    curr_path = os.path.join(fixed_folder_path, curr_name)

    try:
        df_prev = pd.read_csv(prev_path)
        df_curr = pd.read_csv(curr_path)
    except Exception:
        return

    df_prev = normalize_timestamp_column(df_prev, prev_path, logger)
    df_curr = normalize_timestamp_column(df_curr, curr_path, logger)

    if df_prev is None or df_curr is None:
        return

    rows_to_move = df_prev.loc[row_indices].copy()

    if rows_to_move.empty:
        return

    df_prev = df_prev.drop(index=row_indices).reset_index(drop=True)

    df_curr = (
        pd.concat([df_curr, rows_to_move], ignore_index=True)
        .sort_values("Timestamp")
        .reset_index(drop=True)
    )

    drop_internal_columns(df_prev).to_csv(prev_path, index=False)
    drop_internal_columns(df_curr).to_csv(curr_path, index=False)

    log_row_move(len(rows_to_move), prev_path, curr_path)


def build_bucket_key_from_df_rows(rows_df, original_bucket=None):
    if rows_df.empty:
        return None, None

    rows_df = normalize_timestamp_column(rows_df, logger=logger)

    if rows_df is None:
        return None, None

    ts_valid = rows_df["Timestamp"].dropna()

    if ts_valid.empty:
        return None, None

    ts0 = ts_valid.iloc[0]
    bucket_day = ts0.strftime("%Y%m%d")

    if original_bucket is not None:
        _, original_hour = parse_bucket(original_bucket)

        # Si la carpeta original era diaria, mantener salida diaria.
        if original_hour is None:
            return bucket_day, ts0

    # Si la carpeta original era horaria, mantener salida horaria.
    bucket_hour = ts0.hour
    return f"{bucket_day}_{bucket_hour:02d}", ts0


def append_rows_to_bucket_store(leftover_buckets, key, rows, source_path):
    if rows is None or rows.empty:
        return

    rows = rows.copy()
    rows[SOURCE_FILE_COL] = source_path

    leftover_buckets.setdefault(key, pd.DataFrame())
    leftover_buckets[key] = (
        pd.concat([leftover_buckets[key], rows], ignore_index=True)
        .sort_values("Timestamp")
        .reset_index(drop=True)
    )


def append_leftover_rows_to_next_bucket(leftover_df, next_fixed_folder_path):
    if leftover_df is None or leftover_df.empty:
        return

    # Carpeta lógica que recibes
    original_folder_path = Path(next_fixed_folder_path)

    # Carpeta real donde quieres escribir
    output_folder_path = resolve_output_path(original_folder_path)

    output_folder_path.mkdir(parents=True, exist_ok=True)

    bucket_name = output_folder_path.name

    if bucket_name.startswith("fixed_"):
        bucket = bucket_name.replace("fixed_", "", 1)
    else:
        bucket = bucket_name

    bucket_day, bucket_hour = parse_bucket(bucket)

    if bucket_day is None:
        return

    leftover_df = normalize_timestamp_column(
        leftover_df,
        str(output_folder_path),
        logger
    )

    if leftover_df is None:
        return

    if bucket_hour is None:
        rows_for_bucket = leftover_df[
            leftover_df["Timestamp"].dt.strftime("%Y%m%d") == bucket_day
        ].copy()
    else:
        rows_for_bucket = leftover_df[
            (leftover_df["Timestamp"].dt.strftime("%Y%m%d") == bucket_day)
            & (leftover_df["Timestamp"].dt.hour == bucket_hour)
        ].copy()

    if rows_for_bucket.empty:
        return

    csvs = sort_csvs_by_content_timestamp(str(output_folder_path))

    if not csvs:
        fname = (
            f"generated_"
            f"{rows_for_bucket.iloc[0]['Timestamp'].strftime('%Y%m%d_%H%M%S')}"
            f"_tflt_w_1.0.csv"
        )

        dst_path = output_folder_path / fname

        rows_to_write = (
            drop_internal_columns(rows_for_bucket)
            .sort_values("Timestamp")
            .reset_index(drop=True)
        )

        rows_to_write.to_csv(dst_path, index=False)

        if SOURCE_FILE_COL in rows_for_bucket.columns:
            for src_path, src_rows in rows_for_bucket.groupby(SOURCE_FILE_COL):
                log_row_move(len(src_rows), src_path, str(dst_path))
        else:
            log_row_move(len(rows_for_bucket), "unknown", str(dst_path))

        return

    first_csv_path = output_folder_path / csvs[0]

    try:
        df_next = pd.read_csv(first_csv_path)
    except Exception as e:
        logger.warning(f"Could not read CSV {first_csv_path}: {e}")
        return

    df_next = normalize_timestamp_column(df_next, str(first_csv_path), logger)

    if df_next is None:
        return

    rows_to_merge = drop_internal_columns(rows_for_bucket)
    df_next = drop_internal_columns(df_next)

    merged = (
        pd.concat([rows_to_merge, df_next], ignore_index=True)
        .sort_values("Timestamp")
        .reset_index(drop=True)
    )

    merged.to_csv(first_csv_path, index=False)

    if SOURCE_FILE_COL in rows_for_bucket.columns:
        for src_path, src_rows in rows_for_bucket.groupby(SOURCE_FILE_COL):
            log_row_move(len(src_rows), src_path, str(first_csv_path))
    else:
        log_row_move(len(rows_for_bucket), "unknown", str(first_csv_path))

def handle_minute_jumps(prev_path, curr_path, leftover_buckets, measurement_folder, bucket):
    if not detect_minute_jump_by_content(prev_path, curr_path):
        return

    try:
        df_prev = pd.read_csv(prev_path)
    except Exception:
        return

    df_prev = normalize_timestamp_column(df_prev, prev_path, logger)

    if df_prev is None:
        return

    prev_hour = df_prev["Timestamp"].dropna().iloc[0].hour

    leftover_rows = df_prev[
        df_prev["Timestamp"].notna()
        & (df_prev["Timestamp"].dt.hour != prev_hour)
    ].copy()

    if leftover_rows.empty:
        return

    df_prev = df_prev.drop(index=leftover_rows.index).reset_index(drop=True)
    drop_internal_columns(df_prev).to_csv(prev_path, index=False)

    bucket_key, _ = build_bucket_key_from_df_rows(leftover_rows, original_bucket=bucket)

    if bucket_key is None:
        return

    key = (bucket_key, measurement_folder)
    append_rows_to_bucket_store(leftover_buckets, key, leftover_rows, prev_path)


def handle_last_csv_leftovers(fixed_folder, bucket, leftover_buckets, measurement_folder):
    fixed_csvs = sort_csvs_by_content_timestamp(fixed_folder)

    if not fixed_csvs:
        return

    last_path = os.path.join(fixed_folder, fixed_csvs[-1])

    try:
        df_last = pd.read_csv(last_path)
    except Exception:
        return

    df_last = normalize_timestamp_column(df_last, last_path, logger)

    if df_last is None:
        return

    bucket_day, bucket_hour = parse_bucket(bucket)

    if bucket_day is None:
        return

    if bucket_hour is None:
        overflow_mask = (
            df_last["Timestamp"].dt.strftime("%Y%m%d") != bucket_day
        )
    else:
        overflow_mask = (
            (df_last["Timestamp"].dt.strftime("%Y%m%d") != bucket_day)
            | (df_last["Timestamp"].dt.hour != bucket_hour)
        )

    overflow_rows = df_last[overflow_mask].copy()

    if overflow_rows.empty:
        return

    df_last = df_last[~overflow_mask].reset_index(drop=True)
    drop_internal_columns(df_last).to_csv(last_path, index=False)

    first_valid_ts = overflow_rows["Timestamp"].dropna()

    if first_valid_ts.empty:
        return

    next_bucket = build_bucket_key_from_timestamp(first_valid_ts.iloc[0], bucket)

    key = (next_bucket, measurement_folder)
    append_rows_to_bucket_store(leftover_buckets, key, overflow_rows, last_path)


def handle_already_fixed_pairs(processed_folder_txt, day_csv):
    current_csv = os.path.basename(day_csv)

    if not os.path.exists(processed_folder_txt):
        open(processed_folder_txt, "w").close()

    with open(processed_folder_txt, "r+") as myfile:
        content = myfile.read()
        complete_paths = [path for path in content.split("\n")]

        if current_csv in complete_paths:
            return False

        return True


def mark_fix_done(fixed_folder):
    os.makedirs(fixed_folder, exist_ok=True)
    open(os.path.join(fixed_folder, ".fix_done"), "w").close()


def is_fix_done(fixed_folder):
    return os.path.exists(os.path.join(fixed_folder, ".fix_done"))


def load_fingerprint(fixed_folder):
    path = os.path.join(fixed_folder, ".fingerprint")

    if not os.path.exists(path):
        return None

    with open(path) as f:
        content = f.read().strip()

    if not content:
        return None

    return tuple(content.split("|"))


def save_fingerprint(fixed_folder, fingerprint):
    os.makedirs(fixed_folder, exist_ok=True)

    path = os.path.join(fixed_folder, ".fingerprint")

    with open(path, "w") as f:
        f.write("|".join(map(str, fingerprint)))


def remove_fingerprint(fixed_folder):
    path = os.path.join(fixed_folder, ".fingerprint")

    if os.path.exists(path):
        os.remove(path)


def bucket_fingerprint(fixed_folder):
    total_rows = 0
    min_ts = None
    max_ts = None

    for fname in os.listdir(fixed_folder):
        if not fname.lower().endswith(".csv"):
            continue

        path = os.path.join(fixed_folder, fname)

        try:
            df = pd.read_csv(path)
        except Exception:
            continue

        if df.empty:
            continue

        df = normalize_timestamp_column(df, path, logger)

        if df is None:
            continue

        ts = df["Timestamp"].dropna()

        if ts.empty:
            continue

        total_rows += len(ts)

        cur_min = ts.min()
        cur_max = ts.max()

        min_ts = cur_min if min_ts is None else min(min_ts, cur_min)
        max_ts = cur_max if max_ts is None else max(max_ts, cur_max)

    return total_rows, str(min_ts), str(max_ts)


def last_file_trim_overflow(last_csv_path):
    try:
        df = pd.read_csv(last_csv_path)
    except Exception:
        return pd.DataFrame()

    df = normalize_timestamp_column(df, last_csv_path, logger)

    if df is None:
        return pd.DataFrame()

    first_hour = df["Timestamp"].dropna().iloc[0].hour
    overflow_mask = df["Timestamp"].dt.hour != first_hour

    extra_rows = df[overflow_mask].copy()

    drop_internal_columns(df[~overflow_mask]).to_csv(last_csv_path, index=False)

    return extra_rows


def get_last_minute_leftovers(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = normalize_timestamp_column(df, logger=logger)

    if df is None:
        return pd.DataFrame()

    timestamps_valid = df["Timestamp"].dropna()

    if timestamps_valid.empty:
        return pd.DataFrame()

    last_minute = timestamps_valid.iloc[-1].minute

    return df[df["Timestamp"].dt.minute == last_minute].copy()


def get_measurement_folders(point):
    point = point.replace("3-Medidas", "5-Resultados")

    point_AI = os.path.join(point, "AI_MODEL")

    acoustic_path = os.path.join(point, "acoustic_params")
    prediction_path = os.path.join(point_AI, "predictions_litle")

    return acoustic_path, prediction_path


def time_slop_fix(point, acoustic_folder, pred_litle_folder, logger):
    measurement_folders = [acoustic_folder, pred_litle_folder]

    for measurement_folder in measurement_folders:

        if os.path.isabs(measurement_folder):
            measurement_path = measurement_folder
        else:
            measurement_path = os.path.join(point, measurement_folder)

        measurement_name = os.path.basename(os.path.normpath(measurement_path))

        if measurement_name == "acoustics":
            processed_folders_txt_path = os.path.join(
                measurement_path,
                "processed_acoustic.txt"
            )

        elif measurement_name in ("predictions", "predictions_litle"):
            processed_folders_txt_path = os.path.join(
                measurement_path,
                "processed_predictions.txt"
            )

        else:
            continue

        leftover_buckets = {}

        try:
            buckets = get_bucket_list(measurement_path)
        except Exception:
            continue

        for bucket in tqdm.tqdm(
            buckets,
            desc=f"Fixing time slops {measurement_name}"
        ):

            bucket_path = os.path.join(measurement_path, bucket)
            fixed_folder = os.path.join(measurement_path, f"fixed_{bucket}")

            if is_fix_done(fixed_folder):
                continue

            csv_files = copy_original_csvs(
                bucket_path,
                fixed_folder,
                measurement_name
            )

            if not csv_files:
                continue

            fixed_csvs = sort_csvs_by_content_timestamp(fixed_folder)

            for prev_name, curr_name in zip(fixed_csvs, fixed_csvs[1:]):

                prev_path = os.path.join(fixed_folder, prev_name)
                curr_path = os.path.join(fixed_folder, curr_name)

                if not handle_already_fixed_pairs(
                    processed_folders_txt_path,
                    prev_path
                ):
                    continue

                handle_minute_jumps(
                    prev_path,
                    curr_path,
                    leftover_buckets,
                    measurement_name,
                    bucket,
                )

                _, extra_idx = get_extra_seconds_indices(prev_path)

                if extra_idx:
                    append_extra_seconds(
                        fixed_folder,
                        prev_name,
                        curr_name,
                        extra_idx
                    )

            handle_last_csv_leftovers(
                fixed_folder,
                bucket,
                leftover_buckets,
                measurement_name
            )

            fp_now = bucket_fingerprint(fixed_folder)
            fp_prev = load_fingerprint(fixed_folder)

            if fp_now[0] == 0:
                remove_fingerprint(fixed_folder)
                continue

            if fp_prev == tuple(map(str, fp_now)):
                if is_bucket_closed(bucket, grace_minutes=30):
                    mark_fix_done(fixed_folder)
                    logger.info(f"Marked fix done: {fixed_folder}")
                else:
                    logger.info(f"Bucket still open, not marking .fix_done: {bucket}")
            else:
                save_fingerprint(fixed_folder, fp_now)


        measurement_paths = {
            os.path.basename(os.path.normpath(acoustic_folder)): acoustic_folder,
            os.path.basename(os.path.normpath(pred_litle_folder)): pred_litle_folder,
        }
        
        measurement_paths = {
            os.path.basename(os.path.normpath(acoustic_folder)): acoustic_folder,
            os.path.basename(os.path.normpath(pred_litle_folder)): pred_litle_folder,
        }

        for (bucket_key, m_folder), leftover_df in leftover_buckets.items():
            base_path = measurement_paths.get(m_folder)

            if base_path is None:
                logger.warning(
                    "Unknown measurement folder for leftovers: m_folder=%s, bucket_key=%s",
                    m_folder,
                    bucket_key,
                )
                continue

            next_folder = os.path.join(base_path, f"fixed_{bucket_key}")
            os.makedirs(next_folder, exist_ok=True)

            logger.info(
                "Appending leftover rows to absolute folder: %s",
                next_folder,
            )

            append_leftover_rows_to_next_bucket(leftover_df, next_folder)