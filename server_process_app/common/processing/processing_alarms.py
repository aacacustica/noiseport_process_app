import sys

import pandas as pd
import matplotlib.pyplot as plt
import os
plt.style.use("bmh")

from scipy.signal import find_peaks
from pathlib import Path
import re


from server_process_app.common.reading.reading_alarms import *
from server_process_app.common.utils.utils_vi import *
from server_process_app.common.config.config_vi import *
from server_process_app.common.graphics.visualization_alarms import *
from server_process_app.common.utils.utils import *

config = load_config()

probability_threshold = config['alarms']['probability_threshold']
periodo_agregacion = config['alarms'] ['agg_period']

def process_single_csv( csv_path,device,folder,yamnet_df,yamnet_csv,oca_limits,logger):

    taxonomy_cols                   = []
    base_cols                       = ["id_micro","Filename","datetime","Timestamp","Unixtimestamp","LA","LA_corrected","LC","LZ","LAmax","LAmin","LC-LA"]
    peak_cols                       = ["is_peak","peak_start_time","peak_end_time","peak_duration_seconds","peak_sample_count","peak_leq","peak_LA_values"]

    csv_path                        = Path(csv_path)
    base_dir                        = os.path.dirname(csv_path)
    post_dir                        = os.path.join(base_dir, "postprocessing")
    filename                        = os.path.basename(csv_path)
    stem, _                         = os.path.splitext(filename)
    
    m = re.search(r"(\d{8})", stem)
    if m: day_hour = m.group(0)
    else: logger.error(f"Could not find YYYYMMDD_HH pattern in filename {filename}, using full stem")

    
    output_path_graphics_alarms     = os.path.join(post_dir,day_hour,'GRAPHICS_ALARMS')
    output_path_ai_alarms           = os.path.join(post_dir,day_hour,'AI_Alarms')
    output_path_day                 = os.path.join(post_dir,day_hour)
    folder_output_dir_for_alarms    = Path(str(folder).replace("SPL", "Graphics_ALARMS"))
    folder_output_dir_1h            = os.path.dirname(folder_output_dir_for_alarms)
    ia_visualization_folder         = os.path.join(folder_output_dir_1h, 'AI_ALARMS')
    alarms_csv_path                 = os.path.join(output_path_day, f"{device}_alarms.csv")

    write_header                    = not os.path.exists(alarms_csv_path)
    if not csv_path.is_file(): raise FileNotFoundError(f"CSV file does not exist { csv_path}")

    logger.info(f"Processing CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    # +------------------------------------------------------------+ #
    #                                                                #
    #        1. Ordenación de columnas,                              #
    #        2. Creación de carpetas                                 #
    #        3. Añadir columna datetime                              #
    #        4. Añadir columna indicadores, oca y noche              #
    #        5. Procesar predicciones                                #
    #        5. Generación de df_agg, datos de 1s a datos de 1h       #
    #        6. Cálculo de alarmas                                   #
    #        7. Gráficos                                             #
    #        8. Guardado                                             #
    #                                                                #
    # +------------------------------------------------------------+ #


    # ------------------------- Ordenación de columnas ---------------------------------------- #
    df["datetime"] = pd.to_datetime(df["Timestamp"])
    df["datetime"] = df["datetime"].dt.tz_localize(None)

    if "Filename_acoustic" in df.columns: df = df.rename(columns={"Filename_acoustic": "Filename"})
    if "Prediction_1" in df.columns: df = df.merge(yamnet_df,how="left",left_on="Prediction_1",right_on="display_name",)
    else: logger.warning("Prediction_1 column not found in df; cannot merge YAMNet taxonomy")

    cols_to_drop = []
    for col in ["Filename_prediction", "peak_filename", "Prediction_2", "Prediction_3", "Prob_2", "Prob_3", "display_name"]:
        if col in df.columns:
            cols_to_drop.append(col)
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
    
    if "LC" in df.columns and "LA" in df.columns: df["LC-LA"] = df["LC"] - df["LA"]
    if 'LA_corrected' not in df.columns and 'LA' in df.columns: df['LA_corrected'] = pd.to_numeric(df['LA'],errors='coerce')
    else: df['LA_corrected'] = pd.to_numeric(df['LA_corrected'],errors='coerce')

    if "NoisePort_Level_1" in df.columns: taxonomy_cols = ["NoisePort_Level_1"]

    band_cols       = [c for c in df.columns if c.endswith("Hz")]
    pred_cols       = [c for c in df.columns if c.startswith("Prediction_") or c.startswith("Prob_")]
    peak_cols       = [c for c in peak_cols if c in df.columns]
    ordered_cols    = list(dict.fromkeys(column for column in (base_cols + band_cols + pred_cols + taxonomy_cols + peak_cols) if column in df.columns))

    df              = df[ordered_cols]
    df              = df.sort_values("datetime").reset_index(drop=True)
    

    # ------------------------- Creación de carpetas ----------------------------------------------- #
    os.makedirs(post_dir,                   exist_ok=True)
    os.makedirs(output_path_graphics_alarms,exist_ok=True)
    os.makedirs(output_path_ai_alarms,      exist_ok=True)
    os.makedirs(folder_output_dir_1h,       exist_ok=True)
    os.makedirs(ia_visualization_folder,    exist_ok=True)

    # ------------------------- Añadir columna datetime --------------------------------------------- #

    
    try:
        if df is None:
            logger.exception(f"DF from {csv_path} is none")
            return

        df = add_datetime_columns(df,logger,date_col='datetime')
        df = df.sort_values('datetime')
        df = df.set_index('datetime', drop=True)
        start_date = df.index.min()
        end_date = df.index.max()

        logger.info(f"Start date and end date are [{start_date} ,{end_date}]")

    except Exception as e: logger.exception(f"Exception adding datetime columns {e}")

    # ------------------------- Añadir columna indicators, night y oca ------------------------------- #
    try:
        
        if df is not None: df['indicador_str'] = df.apply(lambda x: evaluation_period_str(x['hour']), axis=1)
        else:
            logger.exception(f"DF from {csv_path} is none")
            return
        
        if df is not None: df['night_str'] = df.apply(lambda x: add_night_column(x['hour'], x['day_name']), axis=1)
        else:
            logger.exception(f"DF from {csv_path} is none")
            return
        
        if df is not None: df['oca'] = df['hour'].apply(lambda h: db_limit(h, **oca_limits))
        else:
            logger.exception(f"DF from {csv_path} is none")
            return

    except Exception as e: logger.exception(f"Exception while adding indicators, night, or oca column: {e}")
    

    # ------------------------- Procesar predicciones -------------------------------------------------- #

    try:

        if "Prediction_1" in df.columns and "Prob_1" in df.columns:
            duplicated_columns = (df.columns[df.columns.duplicated()].tolist())

            if duplicated_columns: 
                logger.warning(f"Removing duplicated columns: {duplicated_columns}")
                df = df.loc[:, ~df.columns.duplicated()].copy()
            
            df['Prob_1'] = pd.to_numeric(df['Prob_1'],errors='coerce')
            mask = df['Prob_1'] >= probability_threshold
            df['class'] = df['Prediction_1']
            cols_to_clear = [column for column in ('Prediction_1','Prob_1','class','NoisePort_Level_1')]
            df.loc[~mask, cols_to_clear] = pd.NA

        else:
            logger.warning(f"Prediction_1 or Prob_1 columns not found in {csv_path} ")

    except Exception as e: logger.exception(f" Exception while processing predictions file:{e}")

    # ------------------------- Dataframe para AI_ALARMS ----------------------------------------- #

    df_predictions_plot = df.copy()

    df_predictions_plot = ensure_timestamp_column(df,logger)
    
    if (df_predictions_plot is None or df_predictions_plot.empty):
        logger.warning(f"Canot prepare prediction plot dataframe for {csv_path}")
        return
    
    
    df_predictions_plot['LA_corrected'] = pd.to_numeric(df_predictions_plot['LA_corrected'],errors='coerce')

    # ------------------------- Transformar a datos de una hora ----------------------------------------- #

    try:
        logger.info(
            "periodo_agregacion=%r, type=%s, callable=%s",
            periodo_agregacion,
            type(periodo_agregacion).__name__,
            callable(periodo_agregacion),
        )
        agg_rule = f"{int(periodo_agregacion)}s"
        weekday_translation = {"Monday": "Lunes","Tuesday": "Martes","Wednesday": "Miércoles","Thursday": "Jueves","Friday": "Viernes","Saturday": "Sábado","Sunday": "Domingo"}

        is_peak_agg = df['is_peak'].fillna(False).astype(bool).resample(agg_rule).max()
        df_agg = df.resample(agg_rule).apply(agg_hour)
        df_agg['is_peak'] = is_peak_agg
        df_agg = df_agg.reset_index().round(1)
        

        df_agg["hour"] = df_agg["datetime"].dt.hour
        df_agg["day_name"] = df_agg["datetime"].dt.day_name().map(weekday_translation)
        df_agg["indicador_str"] = df_agg["hour"].apply(evaluation_period_str)
        df_agg["night_str"] = df_agg.apply(lambda x: add_night_column(x["hour"], x["day_name"]), axis=1)
        df_agg["oca"] = df_agg["hour"].apply(lambda h: db_limit(h, **oca_limits))

    except Exception as e:
        logger.exception(f"Exception transforming one second data: {e} in file : {csv_path}")
        return

    # ------------------------- Creación de alarmas ---------------------------------------------------- #

    try: df_alarms_1h = oca_alarm(df_agg, logger=logger)
    except Exception as e: logger.exception(f"Exception while creating OCA alarm: {e} in file : {csv_path}")

    try: df_alarms_1h = lmax_alarm(df_alarms_1h, logger=logger, threshold=95)
    except Exception as e: logger.exception(f"Exception while creating Lmax alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = LC_LA_alarm(df_alarms_1h, logger=logger,threshold_norma=10, threshold_dB=3)
    except Exception as e: logger.exception(f"Exception while creating LC_LA alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = l90_alarm_dynamic(df_alarms_1h, logger=logger, threshold_dB=5)
    except Exception as e: logger.exception(f"Exception while creating LC_LA alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = frequency_composition(df_agg,df_alarms_1h,logger=logger,threshold_comp=5)
    except Exception as e: logger.exception(f"Exception while creating Freq_composition alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = tonal_frequency(df_agg,df_alarms_1h,folder_output_dir_1h,logger,plotname=folder)
    except Exception as e: logger.exception(f"Exception while creating Tonal_frequency alarm: {e} in file: {csv_path}")

    # ------------------------- Creación de gráficos ---------------------------------------------------- #

    try: plot_peak_distribution_heatmap(df_alarms_1h, output_path_graphics_alarms, logger, plotname="heatmap")
    except Exception as e: logger.exception(f"Exception while plotting peak distribution heatmap: {e} in file {csv_path}")

    try: plot_peak_distribution(df_alarms_1h, output_path_graphics_alarms, logger, plotname="peak")
    except Exception as e: logger.exception(f"Exception while plotting peak distribution: {e} in file {csv_path}")

    try: plot_density_distribution_peaks(df_alarms_1h, output_path_graphics_alarms, logger, plotname="density")
    except Exception as e: logger.exception(f"Exception while plotting density distribution peaks: {e} in file {csv_path}")

    try: plot_predic_peak_laeq_mean(df_predictions_plot,yamnet_csv, output_path_ai_alarms, logger, plotname="predic")
    except Exception as e: logger.exception(f"Exception while plotting prediction peak laeq mean: {e} in file {csv_path}")

    try: plot_box_plot_prediction(df_predictions_plot,yamnet_csv, output_path_ai_alarms, logger, plotname="box")
    except Exception as e: logger.exception(f"Exception while plotting box plot prediction: {e} in file {csv_path}")

    try: plot_heat_map_prediction(df_predictions_plot,yamnet_csv, output_path_ai_alarms, logger, plotname="heat map predic")
    except Exception as e: logger.exception(f"Exception while plotting heat map prediction: {e} in file {csv_path}")

    # ------------------------- Guardado de CSV ----------------------------------------------------------- #

    daily_output_path                     = os.path.join(post_dir, f"{day_hour}_postpo.csv")
    
    daily_output_df = df_predictions_plot.copy()

    daily_output_df.to_csv(daily_output_path,index=False)

    logger.info(f"Saved daily postprocessed file {daily_output_path}")
    
    df_alarms_1h.to_csv(alarms_csv_path,mode="w",header = True,index=False)


def process_weekly(daily_results,device,output_dir,taxonomy_map,logger,require_complete_week = False):

    daily_results = [str(path) for path in daily_results]

    if not daily_results: 
        logger.info(f"No daily results available for weekly processing: {device}")
        return []
    
    weekly_groups = group_daily_results_by_week(daily_results,logger)

    generated_weekly_dirs = []

    for week_start, week_paths in sorted(weekly_groups.items()):

        week_end = week_start + pd.Timedelta(days=6)
        frames = []
        loaded_dates =set()

        for path in sorted(week_paths):
            
            try:
                frame = pd.read_csv(path)
            except Exception:
                logger.exception(f"Failed reading daily result for weekly report {path}")
                continue

            frame = ensure_timestamp_column(frame,logger)

            if frame is None or frame.empty:
                logger.warning(f"Daily result has no valid timestamps {path}")
                continue

            frame['Timestamp'] = pd.to_datetime(frame['Timestamp'],errors='coerce',utc=True).dt.tz_localize(None)

            frame = frame.dropna(subset=['Timestamp']).copy()

            if frame.empty:continue 

            frame_dates = (frame['Timestamp'].dt.normalize().dt.date.unique()) 

            loaded_dates.update(frame_dates)

            frame['source_daily_file'] = Path(path).name
            frames.append(frame)

        if not frames:
            logger.warning(f"No valid daily frames for a week starting {week_start.date()}")
            continue
        if require_complete_week and len(loaded_dates) < 7:
            logger.warning(f"Skipping incomplete week {week_start.date()} for {device}: {len(loaded_dates)}/7 days")
            continue

        weekly_df = pd.concat(frames,ignore_index=True,sort=False)
        weekly_df = ensure_timestamp_column(weekly_df,logger)

        

        if weekly_df is None or weekly_df.empty:
            continue

        weekly_df['Timestamp'] = pd.to_datetime(weekly_df['Timestamp'],errors='coerce',utc=True).dt.tz_localize(None)    
        
        next_week_start = week_start + pd.Timedelta(days=7)

        weekly_df = weekly_df[(weekly_df['Timestamp'] >= week_start) & (weekly_df['Timestamp'] < next_week_start)].copy()

        if weekly_df.empty:
            logger.warning(f"Weekly dataframe became empty for {week_start.date()}")
            continue

        duplicate_keys = [column for column in ('Timestamp','Filename') if column in weekly_df.columns]

        if duplicate_keys: weekly_df = (weekly_df.sort_values('Timestamp').drop_duplicates(subset=duplicate_keys,keep='last'))

        weekly_output_dir = Path(output_dir)/'weekly'/(f"{week_start:%Y%m%d}_{week_end:%Y%m%d}")
        weekly_graphics_dir = weekly_output_dir / 'GRAPHICS_ALARMS'
        weekly_ai_dir = weekly_output_dir / 'AI_ALARMS'

        weekly_output_dir.mkdir(parents=True,exist_ok=True)
        weekly_graphics_dir.mkdir(parents=True,exist_ok=True)
        weekly_ai_dir.mkdir(parents=True,exist_ok=True)

        weekly_csv_path = weekly_output_dir / f"{device}_weekly_data.csv"

        weekly_df.to_csv(weekly_csv_path,index=False)

        logger.info(f"Generating weekly report for {device}: {week_start.date()} -> {week_end.date()} \n {len(weekly_df)} rows from {len(loaded_dates)} days.")

        weekly_time_df = weekly_df.copy()
        weekly_time_df['Timestamp'] = pd.to_datetime(weekly_time_df['Timestamp'],errors='coerce')
        weekly_time_df = weekly_time_df.dropna(subset=['Timestamp'])
        weekly_time_df = weekly_time_df.set_index('Timestamp',drop=False)

        plot_name = (f"{device}_{week_start:%Y%m%d}_{week_end:%Y%m%d}")

        try:
            plot_night_evolution_week(weekly_df.copy(),str(weekly_graphics_dir),logger,laeq_column='LA_corrected',plotname=plot_name,indicador_noche='Ln')
        except Exception:
            logger.exception("Failed weekly night evolution for %s, week %s",device,week_start.date())

        try:
            plot_night_evolution_15_min_week(weekly_time_df.copy(),str(weekly_graphics_dir),logger,name_extension='15min',laeq_column='LA_corrected',plotname=plot_name,indicador_noche='Ln')
        except Exception:
            logger.exception("Failed weekly 15-minute week evolution for %s, week %s",device,week_start.date())

        try:
            plot_predic_peak_laeq_mean_week(weekly_df.copy(),taxonomy_map,str(weekly_ai_dir),logger,plotname=plot_name)
        except Exception:
            logger.exception("Failed weekly prediction report for %s, week %s",device,week_start.date())

        generated_weekly_dirs.append(str(weekly_output_dir))

    return generated_weekly_dirs

        


def process_all_folders(folders,day_devices,yamnet_csv,taxonomy_map,oca_limits, logger):

    folders_by_device = {Path(folder).parent.name: Path(folder) for folder in folders}
    yamnet_df = yamnet_csv[["display_name","NoisePort_Level_1"]]
    
    #yamnet_df = yamnet_csv[[
    #        # "mid",
    #        "display_name",
    #        # "iso_taxonomy",
    #        # "Brown_Level_2",
    #        # "Brown_Level_3",
    #        "NoisePort_Level_1",
    #        # "NoisePort_Level_2",
    #    ]]
    for device,device_state in day_devices.items():
        
    # +------------------------------------------------------------+ #
    #   LOOP for each device in day_devices:                         #
    #        1. Comprobar si el dispositivo completo ya fue procesado#
    #        2. Comprobar si hay una carpeta creada para el disp.    #
    #        3. Comprobar si existen csvs en el dispositivo          #
    #        3. LOOP device[csv_files]                               #
    #           3.1 Comprobar el csv ya fue procesado                #
    #           3.2 Llamada a process single_file_csv                #   
    #           3.3 Si da error no se marca como procesado y retry   #
    #           3.4 Si no da error se marca como procesado           #
    #        3. device['processed] = True si todos sus csvs procesados#
    #                                                                #
    # +------------------------------------------------------------+ #

    
    # ------------------------- Comprobar si hay una carpeta creada para el disp ----------------------------- #
        folder = folders_by_device.get(device)
        
        if folder is None:
            logger.error(f"Folder not found for device: {device}")
            continue
    # ------------------------- Comprobar si existen csvs en el dispositivo ---------------------------------- #    
        csv_states = device_state.get("files",[])

        if not csv_states:
            logger.warning(f"No CSV files registered for device: {device}")
            continue
    # ------------------------- LOOP device[csv_files] ------------------------------------------------------- #
        daily_results = []        
        for csv_state in csv_states:
            csv_path = Path(csv_state['path'])

            if not csv_path.is_absolute():
                csv_path = folder / csv_path
    # ------------------------- Comprobar el csv ya fue procesado -------------------------------------------- # 
            if csv_state.get("processed",False):
                existing_result = find_daily_output_for_csv(csv_path)
                if existing_result is not None:
                    daily_results.append(existing_result)

                logger.info(f"Skipping already processed CSV: {csv_state['path']}")
                continue
            csv_path = Path(csv_state['path'])
            if not csv_path.is_absolute(): csv_path = folder / csv_path
    # ------------------------- Procesar CSV ------------------------------------------------------------------ # 
            try:
                daily_result = process_single_csv(
                    csv_path    = csv_path,
                    device      = device,
                    folder      = folder,
                    yamnet_df   = yamnet_df,
                    yamnet_csv  = yamnet_csv,
                    oca_limits  = oca_limits,
                    logger      = logger
                )
            except Exception as e:
    # ------------------------- Si da error no se marca como procesado y se volverá a intentar ---------------- # 
                logger.exception(f"CSV processing failed: {csv_path} with exception: {e}")
            else:
    # ------------------------- Si no da error se marca como procesado  --------------------------------------- #
                csv_state['processed']  =   True
                if daily_result: daily_results.append(daily_result)
    # ------------------------- device['processed] = True si todos sus csvs procesados ------------------------ #
        device_state["processed"] = (
            bool(csv_states)
            and all(
                csv_state.get("processed",False)
                for csv_state in csv_states
            )
        )
        postprocessing_dir = folder / "postprocessing"
        stored_daily_results = sorted(postprocessing_dir.glob("*_postpo.csv"))

        all_daily_results = sorted({str(path) for path in (list(stored_daily_results) + [Path(path) for path in daily_results])})

        try:
            process_weekly(
                daily_results           = all_daily_results,
                device                  = device,
                output_dir              = folder / 'postprocessing',
                taxonomy_map            = taxonomy_map,
                logger                  = logger,
                require_complete_week   = False
                )
        except Exception:
            logger.exception("Weekly processing failed for device %s",device)

        if device_state["processed"]: logger.info(f"Device: {device} has been entirely processed until now.")
        else: logger.warning(f"Device {device} has pending processing or something failed.")

    return day_devices
