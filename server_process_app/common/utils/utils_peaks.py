import pandas as pd
import os
import re
from pathlib import Path

def merge_peaks(df_pk: pd.DataFrame, df_final: pd.DataFrame) -> pd.DataFrame:
    # Ordenar por tiempo
    df_final = df_final.sort_values("Timestamp").reset_index(drop=True)
    df_pk = df_pk.sort_values("start_time").reset_index(drop=True)

    # Crear IntervalIndex
    intervals = pd.IntervalIndex.from_arrays(df_pk["start_time"], df_pk["end_time"], closed="both")
    
    intervals = pd.IntervalIndex.from_arrays(
        intervals.left.tz_localize(None),
        intervals.right.tz_localize(None),
        closed=intervals.closed
    )
    # Inicializar DataFrame con NaNs para los picos
    df_picos_matched = pd.DataFrame(pd.NA, index=df_final.index, columns=df_pk.columns)

    # Iterar sobre cada timestamp y asignar pico correspondiente

    for i, ts in enumerate(df_final["Timestamp"]):
        ts = ts.tz_localize(None)
        matches = df_pk[intervals.contains(ts)]
        if not matches.empty:
            # Tomamos solo la primera coincidencia
            df_picos_matched.iloc[i] = matches.iloc[0]
            df_final.at[i,'is_peak'] = True

    # Concatenar resultados con prefijo
    df_final = pd.concat([df_final, df_picos_matched.add_prefix("peak_")], axis=1)

    return df_final

def _to_datetime_no_tz(series: pd.Series):
    """
    Convierte a datetime y elimina timezone si existe.
    """
    series = pd.to_datetime(series, errors='coerce')
    # si es tz-aware, convertir a naive
    if pd.api.types.is_datetime64tz_dtype(series.dtype):
        series = series.dt.tz_convert(None)
    return series

def extract_key_from_filename(path: str):
    """
    Extrae una clave temporal del nombre de fichero.

    Prioridad:
    1. YYYYMMDD_HH
    2. YYYYMMDD

    Ejemplos:
    - fixed_20260519_10.csv                  -> 20260519_10
    - fixed_20260519.csv                     -> 20260519
    - peaks_detection_fixed_20260519.csv.csv -> 20260519
    """

    name = os.path.basename(path)
    
    m = re.search(r'(?<!\d)(\d{8}_\d{2})(?!\d)', name)
    
    if m:
        return m.group(1)
    
    m = re.search(r'(?<!\d)(\d{8})(?!\d)', name)

    if m:
        return m.group(1)
    
    return None

def merge_acoustics_predictions_and_peaks(acoustics_paths,predictions_paths,peaks_paths,output_folder_name,logger):
      
    """
    Refactor de la función para emparejar archivos por clave horaria (YYYYMMDD_HH),
    procesar todas las horas donde existan ACÚSTICA y PREDICCIÓN, y aplicar peaks
    cuando existan para esa hora.

    Devuelve la lista de archivos generados (paths).
    """
    

    # Filtrado inicial (el tag de fixed se propaga en toda la cadena y llega hasta peaks también)
    peaks_paths = [f for f in peaks_paths if 'fixed' in f]
    predictions_paths = [f for f in predictions_paths if 'fixed' in f ]
    acoustics_paths = [f for f in acoustics_paths if 'fixed' in f]


    # Indexar por clave YYYYMMDD_HH
    ac_dict = {}
    for f in acoustics_paths:
        date_key = extract_key_from_filename(f)

        if date_key:
            p = Path(f)
            device = p.parts[p.parts.index("inbox") + 1]

            key = (device,date_key)
            ac_dict[key] = f
        else:
            logger.warning(f"Unable to extract key from acoustic file: {f}")

    pr_dict = {}
    for f in predictions_paths:
        date_key = extract_key_from_filename(f)
        if date_key:
            p = Path(f)
            device = p.parts[p.parts.index("inbox") + 1]

            key = (device,date_key)
            pr_dict[key] = f
        else:
            logger.warning(f"Unable to extract key from prediction file: {f}")

    pk_dict = {}
    
    for f in peaks_paths:
        date_key = extract_key_from_filename(f)
        if date_key:
            p = Path(f)
            device = p.parts[p.parts.index("inbox") + 1]

            key = (device,date_key)
            pk_dict.setdefault(key, []).append(f)
        else:
            logger.warning(f"Unable to extract key from peaks file: {f}")

    # Aseguramos salida
    
    # Iterar sobre las horas donde existan acoustics Y predictions
    all_keys = sorted(set(ac_dict.keys()) & set(pr_dict.keys()))
    logger.info(f"Processing {len(all_keys)} hours (acoustic+prediction pairs). "
                f"{len(pk_dict)} keys with peaks available.")

    generated_files = []

    for key in all_keys:

        acoustic_path = ac_dict[key]
        pred_path = pr_dict[key]
        peak_files_for_key = pk_dict.get(key, [])  # lista (posiblemente vacía)

        output_path = "/" + os.path.join(*acoustic_path.split('/')[:5],output_folder_name)
        if not os.path.exists(output_path): os.makedirs(output_path)
        
        
        try:
            # Lectura
            df_ac = pd.read_csv(acoustic_path)
            df_pr = pd.read_csv(pred_path)
        except Exception as e:
            logger.exception(f"Failed reading acoustic/prediction files for key {key}: {e}")
            continue

        if '20251212' in acoustic_path:
            logger.debug(f"Read files for {key}: acoustics={acoustic_path}, predictions={pred_path}, peaks={peak_files_for_key or 'NONE'}")
        
        # Normalizar Timestamp en ambos DF
        if 'Timestamp' not in df_ac.columns or 'Timestamp' not in df_pr.columns:
            logger.error(f"Missing 'Timestamp' column for key {key}. Skipping.")
            continue

        df_ac['Timestamp'] = _to_datetime_no_tz(df_ac['Timestamp'])
        df_pr['Timestamp'] = _to_datetime_no_tz(df_pr['Timestamp'])

        # Drop NaT timestamps
        n_ac_nat = df_ac['Timestamp'].isna().sum()
        n_pr_nat = df_pr['Timestamp'].isna().sum()
        if n_ac_nat > 0 or n_pr_nat > 0:
            logger.warning(f"{key}: Dropping {n_ac_nat} NaT rows from acoustics and {n_pr_nat} from predictions.")
            df_ac = df_ac.dropna(subset=['Timestamp'])
            df_pr = df_pr.dropna(subset=['Timestamp'])

        # Merge acústica + predicción por Timestamp (inner)
        try:
            df_merged = pd.merge(df_ac, df_pr, on='Timestamp', how='left', suffixes=('_acoustic', '_prediction'))
        except Exception as e:
            logger.exception(f"Merge failed for key {key}: {e}")
            continue

        if df_merged.empty:
            logger.info(f"{key}: merged acoustics+predictions is empty. Will still write file (empty) to keep traceability.")
        else:
            logger.debug(f"{key}: merged shape {df_merged.shape}")

        # Preparar columna is_peak
        df_final = df_merged.copy()
        df_final['is_peak'] = False

        # Si hay ficheros de peaks para esta clave, concatenarlos y normalizarlos
        if peak_files_for_key:
            try:
                # leer y concatenar todos los peaks del mismo key (si hay varios)
                list_pk = []
                for pk_file in peak_files_for_key:
                    df_pk_tmp = pd.read_csv(pk_file)
                    # estandarizar nombres de columnas y parseo de tiempos
                    df_pk_tmp.rename(columns={'start time': 'start_time', 'end time': 'end_time'}, inplace=True)
                    if 'start_time' not in df_pk_tmp.columns or 'end_time' not in df_pk_tmp.columns:
                        logger.warning(f"{pk_file} missing start_time/end_time columns. Skipping this peaks file.")
                        continue
                    df_pk_tmp['start_time'] = pd.to_datetime(df_pk_tmp['start_time'], errors='coerce')
                    df_pk_tmp['end_time'] = pd.to_datetime(df_pk_tmp['end_time'], errors='coerce')
                    # descartamos filas inválidas
                    df_pk_tmp = df_pk_tmp.dropna(subset=['start_time', 'end_time'])
                    list_pk.append(df_pk_tmp)
                if list_pk:
                    df_pk = pd.concat(list_pk, ignore_index=True)
                    # Opcional: ordenar por start_time
                    df_pk = df_pk.sort_values('start_time').reset_index(drop=True)
                else:
                    df_pk = None
            except Exception as e:
                logger.exception(f"{key}: failed reading/concat peaks: {e}")
                df_pk = None
        else:
            df_pk = None

        # Aplicar merge_peaks sólo si tenemos df_pk
        if df_pk is not None and not df_pk.empty:
            try:
                df_with_peaks = merge_peaks(df_pk, df_final)
            except Exception as e:
                logger.exception(f"{key}: merge_peaks failed: {e}. Continuing with is_peak=False.")
                df_with_peaks = df_final
        else:
            df_with_peaks = df_final

        # Guardar CSV 
        merged_filename = os.path.join(output_path, f"merged_{key[0]}_{key[1]}.csv")

        try:
            print("Saving merged in:",merged_filename)
            df_with_peaks.to_csv(merged_filename, index=False)
            generated_files.append(merged_filename)
            logger.info(f"Saved merged file for {key} -> {merged_filename}")
        except Exception as e:
            logger.exception(f"Failed saving merged file for {key}: {e}")

    logger.info(f"Processing finished. Generated {len(generated_files)} files in {output_path}")
    
    return generated_files


