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

    taxonomy_cols = []
    base_cols                       = [ "id_micro","Filename","datetime","Timestamp","Unixtimestamp","LA","LC","LZ","LZ","LAmax","LAmin","LC-LA"]
    peak_cols                       = ["is_peak","peak_start_time","peak_end_duration","peak_leq","peak_LA_values"]

    csv_path                        = Path(csv_path)
    base_dir                        = os.path.dirname(csv_path)
    post_dir                        = os.path.join(base_dir, "postprocessing")
    filename                        = os.path.basename(csv_path)
    stem, _                         = os.path.splitext(filename)
    
    m = re.search(r"(\d{8})", stem)
    if m: day_hour = m.group(0)
    else: logger.error(f"Could not find YYYYMMDD_HH pattern in filename {filename}, using full stem")

    output_path                     = os.path.join(post_dir, f"{day_hour}_postpo.csv")
    output_path_graphics_alarms     = os.path.join(post_dir,day_hour,'GRAPHICS_ALARMS')
    output_path_ai_alarms           = os.path.join(post_dir,day_hour,'AI_Alarms')
    output_path_day                 = os.path.join(post_dir,day_hour)
    folder_output_dir_for_alarms    = folder.replace('SPL', 'Graphics_ALARMS')
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
    #        5. Generación de df_1h, datos de 1s a datos de 1h       #
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
    

    if "NoisePort_Level_1" in df.columns: taxonomy_cols = ["NoisePort_Level_1"]

    band_cols       = [c for c in df.columns if c.endswith("Hz")]
    pred_cols       = [c for c in df.columns if c.startswith("Prediction_") or c.startswith("Prob_")]
    peak_cols       = [c for c in peak_cols if c in df.columns]
    ordered_cols    = [c for c in base_cols + band_cols + pred_cols+taxonomy_cols + peak_cols if c in df.columns]

    df              = df[ordered_cols]
    df              = df.sort_values("datetime").reset_index(drop=True)
    df.to_csv(output_path, index=False)

    # ------------------------- Creación de carpetas ----------------------------------------------- #
    os.makedirs(post_dir,                   exist_ok=True)
    os.makedirs(output_path_graphics_alarms,exist_ok=True)
    os.makedirs(output_path_ai_alarms,      exist_ok=True)
    os.makedirs(folder_output_dir_1h,       exist_ok=True)
    os.makedirs(ia_visualization_folder,    exist_ok=True)

    # ------------------------- Añadir columna datetime --------------------------------------------- #
    try:
        if df is None:
            logger.Exception(f"DF from {csv_path} is none")
            return

        df = add_datetime_columns(df,logger,date_col='datetime')
        df = df.sort_values('datetime')
        df = df.set_index('datetime', drop=True)
        start_date = df.index[0]
        end_date = df.index[1]

        logger.info(f"Start date and end date are [{start_date} ,{end_date}]")

    except Exception as e: logger.Exception(f"Exception adding datetime columns {e}")

    # ------------------------- Añadir columna indicators, night y oca ------------------------------- #
    try:
        
        if df is not None: df['indicador_str'] = df.apply(lambda x: evaluation_period_str(x['hour']), axis=1)
        else:
            logger.exception(f"DF from {csv_path} is none")
            return
        
        if df is not None: df['night_str'] = df.apply(lambda x: add_night_column(x['hour'], x['weekday']), axis=1)
        else:
            logger.exception(f"DF from {csv_path} is none")
            return
        
        if df is not None: df['oca'] = df['hour'].apply(lambda h: db_limit(h, **oca_limits))
        else:
            logger.exception(f"DF from {csv_path} is none")
            return

    except Exception as e: logger.Exception(f"Exception while adding indicators, night, or oca column: {e}")
    

    # ------------------------- Procesar predicciones -------------------------------------------------- #

    try:

        if "Prediction_1" in df.columns and "Prob_1" in df.columns:
            mask = df["Prob_1"] >= probability_threshold
            cols_to_clear = ["Prediction_1","Prob_1"]
            if "Noise_Port_Level_1" in df.columns: cols_to_clear.append("Noise_Port_Level_1")
            df.loc[~mask, cols_to_clear] = pd.NA
        else:
            logger.Warning(f"Prediction_1 or Prob_1 columns not found in df from: {csv_path}")

    except Exception as e: logger.Exception(f" Exception while processing predictions file:{e}")

    # ------------------------- Transformar a datos de una hora ----------------------------------------- #

    try:
        df_1h = df.resample("1h").apply(periodo_agregacion)
        df_1h = df_1h.reset_index()
        df_1h = df_1h.round(1)

        df_1h["hour"] = df_1h["datetime"].dt.hour
        df_1h["weekday"] = df_1h["datetime"].dt.weekday
        df_1h["indicador_str"] = df_1h["hour"].apply(evaluation_period_str)
        df_1h["night_str"] = df_1h.apply(lambda x: add_night_column(x["hour"], x["weekday"]), axis=1)
        df_1h["oca"] = df_1h["hour"].apply(lambda h: db_limit(h, **oca_limits))

    except Exception as e:
        logger.Exception(f"Exception transforming one second data: {e} in file : {csv_path}")

    # ------------------------- Creación de alarmas ---------------------------------------------------- #

    try: df_alarms_1h = oca_alarm(df_alarms_1h, logger=logger)
    except Exception as e: logger.Exception(f"Exception while creating OCA alarm: {e} in file : {csv_path}")

    try: df_alarms_1h = lmax_alarm(df_alarms_1h, logger=logger, threshold=95)
    except Exception as e: logger.Exception(f"Exception while creating Lmax alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = LC_LA_alarm(df_alarms_1h, logger=logger,threshold_norma=10, threshold_dB=3)
    except Exception as e: logger.Exception(f"Exception while creating LC_LA alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = l90_alarm_dynamic(df_alarms_1h, logger=logger, threshold_dB=5)
    except Exception as e: logger.Exception(f"Exception while creating LC_LA alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = frequency_composition(df_1h,df_alarms_1h,logger=logger,threshold_comp=5)
    except Exception as e: logger.Exception(f"Exception while creating Freq_composition alarm: {e} in file: {csv_path}")

    try: df_alarms_1h = tonal_frequency(df_1h,df_alarms_1h,folder_output_dir_1h,logger,plotname=folder)
    except Exception as e: logger.Exception(f"Exception while creating Tonal_frequency alarm: {e} in file: {csv_path}")

    # ------------------------- Creación de gráficos ---------------------------------------------------- #

    try: plot_peak_distribution_heatmap(df_alarms_1h, output_path_graphics_alarms, logger, plotname="heatmap")
    except Exception as e: logger.Exception(f"Exception while plotting peak distribution heatmap: {e} in file {csv_path}")

    try: plot_peak_distribution(df_alarms_1h, output_path_graphics_alarms, logger, plotname="peak")
    except Exception as e: logger.Exception(f"Exception while plotting peak distribution: {e} in file {csv_path}")

    try: plot_density_distribution_peaks(df_alarms_1h, output_path_graphics_alarms, logger, plotname="density")
    except Exception as e: logger.Exception(f"Exception while plotting density distribution peaks: {e} in file {csv_path}")

    try: plot_predic_peak_laeq_mean(df_alarms_1h,yamnet_csv, output_path_ai_alarms, logger, plotname="predic")
    except Exception as e: logger.Exception(f"Exception while plotting prediction peak laeq mean: {e} in file {csv_path}")

    try: plot_box_plot_prediction(df_alarms_1h,yamnet_csv, output_path_ai_alarms, logger, plotname="box")
    except Exception as e: logger.Exception(f"Exception while plotting box plot prediction: {e} in file {csv_path}")

    try: plot_heat_map_prediction(df_alarms_1h,yamnet_csv, output_path_ai_alarms, logger, plotname="heat map predic")
    except Exception as e: logger.Exception(f"Exception while plotting heat map prediction: {e} in file {csv_path}")

    # ------------------------- Guardado de CSV ----------------------------------------------------------- #


    df_alarms_1h.to_csv(alarms_csv_path,mode="a" if not write_header else "w",header = write_header,index=False)




def process_all_folders(folders,day_devices,yamnet_csv,oca_limits, logger):

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
        
        print(device)
        print(device_state)
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

    # ------------------------- Comprobar si el dispositivo completo ya fue procesado ------------------------ #
        if device_state.get("processed",False): 
            logger.info(f"Skipping device {device}:all CSV files are already processed")
            continue
    
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
        for csv_state in csv_states:
    # ------------------------- Comprobar el csv ya fue procesado -------------------------------------------- # 
            if csv_state.get("processed",False):
                logger.info(f"Skipping already processed CSV: {csv_state['path']}")
                continue
            csv_path = Path(csv_state['path'])
            if not csv_path.is_absolute(): csv_path = folder / csv_path
    # ------------------------- Procesar CSV ------------------------------------------------------------------ # 
            try:
                process_single_csv(
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
    # ------------------------- device['processed] = True si todos sus csvs procesados ------------------------ #
        device_state["processed"] = (
            bool(csv_states)
            and all(
                csv_state.get("processed",False)
                for csv_state in csv_states
            )
        )
        if device_state["processed"]: logger.info(f"Device: {device} has been entirely processed until now.")
        else: logger.warning(f"Device {device} has pending processing or something failed.")

        return day_devices
