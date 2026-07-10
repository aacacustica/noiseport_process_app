import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

plt.style.use("bmh")


from tqdm import tqdm
from pathlib import Path
import json
from scipy.signal import find_peaks


from server_process_app.common.config.config_vi import *
from server_process_app.common.utils.utils_vi import *
from server_process_app.common.utils.utils import *
from server_process_app.common.reading.reading_visualizations import *
from server_process_app.common.graphics.visualization_visualization import *

config = load_config()
RELATIVE_PATH_SHIPS_1H = config['paths']['ships_1h']

def load_data(file_path, logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    logger.info("")
    slm_type_function_mapping = {
        'tenerife_TCT': (get_data_tenerife_TCT, tenerife_tct_dict),
        "audiomoth": (get_data_audiomoth, audiopost_dict),
        # "SV307": (get_data_SV307, sv307_dict),
        "SV307": (get_data_SV307_new, sv307_dict),
        "814": (get_data_814, larson814_dict),
        "824": (get_data_824, larson824_dict),
        "lx_ES": (get_data_lx_ES, larsonlx_dict),
        "lx_EN": (get_data_lx_EN, larsonlx_dict),
        "cesva": (get_data_cesva, cesva_dict),
        "sono-bilbo": (get_data_bilbo, sonometer_bilbo_dict),
        "bruel&kjaer": (get_data_bruel_kjaer, bruel_kjaer_dict),
    } # SLM stands for Sound Level Meter
    # load the data for each SLM type until one works |  for each slm_type, (func, slm_dict) in slm_type_function_mapping.items(): means that for each key and value in the dictionary, the key is slm_type and the value is a tuple with the function and the dictionary | the function is the function to load the data and the dictionary is the dictionary with the column names for the SLM type


    for slm_type, (func, slm_dict) in slm_type_function_mapping.items():
        try:
            logger.info(f"Loading file {file_path} for SLM type {slm_type}")

            # this is the actual invocation of the function
            df = func(file_path, logger, new_date=new_date, new_time=new_time, new_threshold_date=new_threshold_date, new_threshold_time=new_threshold_time, selected_folder=selected_folder)
            

            logger.info("")
            logger.info(f"Data loaded for SLM type {slm_type}")
            return df, slm_type, slm_dict
        


        except Exception as e:
            clean_message = str(e).replace('\n', ' ')
            logger.warning(f"Failed to load data for SLM type {slm_type}: {clean_message}. Trying next SLM type")
            continue
    
    raise ValueError("SLM type not found or file could not be loaded")



def process_folder(folder_path, folder_date_time, folder_threshold, logger, selected_folder):
    logger.info("")

    # folder contains a CESVA folder
    cesva_path = os.path.join(folder_path, 'CESVA')
    if os.path.isdir(cesva_path):
        # load the data from the CESVA folder
        subfolders = [f for f in os.listdir(cesva_path) if os.path.isdir(os.path.join(cesva_path, f))]
        new_date, new_time = folder_date_time.get(folder_path, (None, None))
        new_threshold_date, new_threshold_time  = folder_threshold.get(folder_path, (None, None))
        
        # CESVA folder contains subfolders
        for subfolder in subfolders:
            #load the data from the first subfolder
            subfolder_path = os.path.join(cesva_path, subfolder)
            
            # subfolder contains measurement files
            files = [os.path.join(subfolder_path, f) for f in os.listdir(subfolder_path) if f.endswith(('.csv', '.xlsx', '.CSV', 'XLSX'))]
            if files:
                # logger.info(f"Files found: {files}")
                return load_data(files[0], logger, new_date=new_date, new_time=new_time, new_threshold_date=new_threshold_date, new_threshold_time=new_threshold_time)
            else:
                logger.warning(f"No measurement files found in {subfolder_path}")


    else:
        new_date, new_time = folder_date_time.get(folder_path, (None, None))
        new_threshold_date, new_threshold_time  = folder_threshold.get(folder_path, (None, None))

        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(('.csv', '.xlsx', '.CSV'))]
        len_files = len(files)
        logger.info(f"Files found: {len_files} at {folder_path}")
        logger.info(f"Processing folder: {folder_path}")



        if len_files > 1:
            logger.info("Processing more than one file, so concatenating them")
            first_file = files[0]
            return load_data(first_file, logger, new_date=new_date, new_time=new_time, new_threshold_date=new_threshold_date, new_threshold_time=new_threshold_time,selected_folder=selected_folder)
        
        elif len_files == 1:
            logger.info("Processing only one file, so loading it directly")
            # this is the case where there is only one file
            return load_data(files[0], logger, new_date=new_date, new_time=new_time, new_threshold_date=new_threshold_date, new_threshold_time=new_threshold_time,selected_folder=selected_folder)
        

        if not files:
            logger.info(f"No measurement files found in {folder_path}")
            try:
                logger.info(f"Trying to load data")
                # load_data regular files
                return load_data(folder_path, logger, new_date=new_date, new_time=new_time, new_threshold_date=new_threshold_date, new_threshold_time=new_threshold_time, selected_folder=selected_folder)
            except Exception as e:
                logger.error(f"Error loading data: {e}")
            # if no files found, return None
            logger.error(f"No measurement files found in {folder_path}")
            return None, None, None
        
    return None, None, None 



def process_all_folders(input_folder, device_folders, PERIODO_AGREGACION, PERCENTILES, taxonomy, yamnet_csv, sufix_string, device_coeff, folder_date_time, folder_threshold, oca_limits, oca_type,device, logger):

    stable_version = get_stable_version(logger)
    home_dir = os.path.expanduser('~')
    temporal_bool = False


    for folder in tqdm(device_folders, desc="Processing folders"): # \\192.168.205.117\AAC_Server\OCIO\24052_ZARAUTZ\CAMPAÑA_1\3-Medidas\ZARAUTZ_C1_P1\AUDIOMOTH
        logger.info("")
        logger.info(f"Suffix string: {sufix_string}")


        #####################################
        # SETTING UP THE FOLDER PATHS
        #####################################
        try:
            reg_folder = os.path.join(input_folder, folder) # \\192.168.205.117\AAC_Server\INDUSTRIA\23132-IRUÑA_OCA_CANTERA\5-Resultados\FAA205-P1_CAMPAÑA1\SPL
            folder = folder.split("/")[-1]
            logger.info(f"Entering folder: {folder}")
            actual_folder_name = folder[-1]
            #folder = folder.split("\\")[:-1]
            #folder = os.path.join('\\\\', *folder)
            #actual_folder_name = folder.split("\\")[-1]
            logger.info(f"Processing folder: {actual_folder_name}")
            


            spl_string = "SPL"
            graphics_string = f"Graphics_{sufix_string}"
            result_dir_name = "5-Resultados"


            # 5-Resultados directory
            resultados_dir = os.path.join("/",Path(*reg_folder.split("/")[:-2]),sufix_string)
            #resultados_dir = os.path.join(*resultados_dir,sufix_string,result_dir_name)
            logger.info(f"Resultados directory: {resultados_dir}")
            #if not os.path.exists(resultados_dir):
            #    os.makedirs(resultados_dir)
            #    logger.info(f"Created output folder: {resultados_dir}")
            


            # CREATING THE FOLDER OUTPUT DIR --> /5-RESULTAODS/P1/SPL/GRAPHICS_SUFFIX/
            folder_output_dir = os.path.join(resultados_dir,spl_string, graphics_string)
            
            logger.info(f"folder_output_dir: {folder_output_dir}")
            if '3-Medidas' in folder_output_dir:
                folder_output_dir = folder_output_dir.replace('3-Medidas', '5-Resultados')
            if not os.path.exists(folder_output_dir):
                os.makedirs(folder_output_dir)
                logger.info(f"Created output folder: {folder_output_dir}")
            

            # CREATIONG THE FOLDER OUTPUT DIR FOR WEEK 
            folder_output_dir_week = os.path.join(folder_output_dir, f"Graphics_week")
            logger.info(f"folder_output_dir_week: {folder_output_dir_week}")
            if not os.path.exists(folder_output_dir_week):
                os.makedirs(folder_output_dir_week)
                logger.info(f"Created output folder: {folder_output_dir_week}")



            # PREDICTION FOLDERS
            # CREATING THE PREDICTION FOLDER --> /5-RESULTAODS/P1/AI_MODEL/Predictions/
            ai_prediction_folder = os.path.join(resultados_dir,"predictions")
            os.makedirs(ai_prediction_folder, exist_ok=True)
            logger.info(f"Created AI prediction folder: {ai_prediction_folder}")
            
            
            # CREATING THE PREDICTION VISUALIZATION FOLDER--> /5-RESULTAODS/P1/AI_MODEL/Visualizations/
            ia_visualization_folder = os.path.join(folder_output_dir,'AI_Visualizations')
            os.makedirs(ia_visualization_folder, exist_ok=True)
            logger.info(f"Created AI visualization folder: {ia_visualization_folder}")
            

        except Exception as e:
            logger.error(f"An error occurred while setting up the folder paths: {e}")
            continue
        ########################################################



        #############################
        ## GETTING THE DATAFRAME ###
        #############################
        try:
            logger.info("")
            logger.info(f"Processing folder {folder}") 
            logger.info(f"Getting the data from the dataframes")
            
            """
            if sufix_string == "SONOMETRO":
                logger.info(f"Processing SONOMETRO data")
                reg_folder = reg_folder.replace(ACOUSTIC_PARAMS_FOLDER, SONOMETER_FOLDER)
                df, slm_type, slm_dict = process_folder(reg_folder, folder_date_time, folder_threshold, logger,selected_folder=SONOMETER_FOLDER)
                if df is None:
                    logger.warning(f"df is None")
                    continue
            
            else:
                logger.info(f"Getting the acoustic data from the dataframes")
                df, slm_type, slm_dict = process_folder(reg_folder, folder_date_time, folder_threshold, logger, ACOUSTIC_PARAMS_FOLDER)
                if df is None:
                    logger.warning(f"df is None")
                    continue
            """

            dfs_acoustics,dfs_predictions,dfs_peaks,dfs_merged = collect_df_server(resultados_dir)

            # taking just 1 day, which are the first 86400 rows
            # df = df.iloc[:86400] # 1 day of data, 24 hours * 60 minutes * 60 seconds = 86400 seconds
            # df = df.iloc[:43200] # 1/2 day of data


            #############################
            ### GETTING PREDICTION DF ###
            #############################
            """
            logger.info("")
            logger.info(f"Getting the prediction data from the dataframes")
            reg_folder_prediction = reg_folder.replace(ACOUSTIC_PARAMS_FOLDER, PREDICTION_LITTLE_FOLDER)
            logger.info(f"Prediction folder: {reg_folder_prediction}")
            
            
            df_prediction, slm_type, slm_dict = process_folder(reg_folder_prediction, folder_date_time, folder_threshold, logger, PREDICTION_LITTLE_FOLDER)
            if df_prediction is None:
                logger.warning(f"df prediction is None")
                continue
            ###################################################################
            """
            for df_path,df_prediction_path,df_peaks_path,df_all_path in zip(dfs_acoustics,dfs_predictions,dfs_peaks,dfs_merged):
                
                df = pd.read_csv(df_path)
                df_prediction = pd.read_csv(df_prediction_path)
                df_peaks = pd.read_csv(df_peaks_path)
                df_all = pd.read_csv(df_all_path)

                csv_acoustics_basename = os.path.basename(df_path)
                csv_predictions_basename = os.path.basename(df_prediction_path)
                csv_peaks_basename = os.path.basename(df_peaks_path)
                csv_merged_basename = os.path.basename(df_all_path)

                if temporal_bool:
                    if csv_predictions_basename not in ["fixed_20260609.csv","fixed_20260610.csv","fixed_20260611.csv","fixed_202606012.csv"]: continue
                    
                    logger.info(f"Predictions with info")

                logger.info(f"Processing visualizations using the following csvs: ")

                logger.info(f"Acoustics: {csv_acoustics_basename}")
                logger.info(f"Predictions: {csv_predictions_basename}")
                logger.info(f"Peaks: {csv_peaks_basename}")
                logger.info(f"Merged : {csv_merged_basename}")
                
                logger.info("")
                if TENERIFE_TIMEZONE:
                    df['Timestamp'] = pd.to_datetime(df['Timestamp']) - pd.Timedelta(hours=1)
                    logger.info(f"Time zone was set to Tenerife")

                #take data from 06/05/2025  16:00:00
                # df = df.loc[df['datetime'] >= '2025-05-06 16:00:00']

                try:
                    if df is not None:
                        logger.info("")
                        # add datetime columns, sort by datetime and set datetime as index
                        logger.info(f"FOR SPL FILE: Adding datetime columns, sorting by datetime and setting datetime as index")
                        df = add_datetime_columns(df,logger, date_col='datetime')
                        df = df.sort_values('Timestamp')
                        df.set_index('Timestamp', inplace=True, drop=False)
                        start_date = df.index[0]
                        end_date = df.index[-1]

                        logger.info(f"Start date {start_date} and end date {end_date}")
                        logger.info(f"df was sorted by datetime and datetime was set as index")
                    else:
                        logger.warning(f"df is None")
                        continue
                        

                    # the same for the prediction file
                    if df_prediction is not None:
                        logger.info("")
                        logger.info(f"FOR PREDICTION FILE: Adding datetime columns, sorting by datetime and setting datetime as index")
                        
                        df_prediction = add_datetime_columns(df_prediction, logger, date_col='Timestamp')
                        df_prediction = df_prediction.sort_values('Timestamp')
                        df_prediction.set_index('Timestamp', inplace=True, drop=False)
                        pred_start_date = df_prediction.index[0]
                        pred_end_date = df_prediction.index[-1]

                        logger.info(f"Start date {pred_start_date} and end date {pred_end_date}")
                        logger.info(f"df was sorted by datetime and datetime was set as index")
                    else:
                        logger.warning(f"df_prediction is None")
                
                except Exception as e:
                    logger.error(f"An error occurred while adding datetime columns: {e}")


                try:
                    logger.info("")
                    if df is not None:
                        # drop the beginning and ending of the measurement (15min)
                        df = df.loc[start_date + pd.Timedelta(REMOVE_START_TIME, unit='seconds'):end_date - pd.Timedelta(REMOVE_END_TIME, unit='seconds')]
                        logger.info(f"SPL df was trimmed, {REMOVE_START_TIME} secs from the beggining and {REMOVE_END_TIME} secs from the end")
                    
                    if df_prediction is not None:
                        df_prediction = df_prediction.loc[pred_start_date + pd.Timedelta(REMOVE_START_TIME, unit='seconds'):pred_end_date - pd.Timedelta(REMOVE_END_TIME, unit='seconds')]
                        logger.info(f"Prediction df was trimmed, {REMOVE_START_TIME} secs from the beggining and {REMOVE_END_TIME} secs from the end")


                    # add indicators column
                    if df is not None:
                        logger.info(f"Adding indicators column")
                        df['indicador_str'] = df.apply(lambda x: evaluation_period_str(x['hour']), axis=1)
                    if df_prediction is not None:
                        df_prediction['indicador_str'] = df_prediction.apply(lambda x: evaluation_period_str(x['hour']), axis=1)

                    
                    # add nights column
                    if df is not None:
                        logger.info(f"Adding nights column")
                        df['night_str'] = df.apply(lambda x: add_night_column(x['hour'], x['day_name']), axis=1)
                    if df_prediction is not None:
                        df_prediction['night_str'] = df_prediction.apply(lambda x: add_night_column(x['hour'], x['day_name']), axis=1)

                except Exception as e:
                    logger.error(f"An error occurred while adding indicators and nights columns: {e}")



                try:
                    # add oca column
                    logger.info(f"Adding oca column")
                    logger.info(f"OCA Limits --> {oca_limits}")

                    if df is not None:
                        df['oca'] = df['hour'].apply(
                                lambda h: db_limit(h, **oca_limits)
                        )
                    if df.isnull().values.any():
                    # check if there is nan values
                        logger.warning(f"There are nan values in the dataframe")
                        # removing nan values
                        df = df.dropna()
                        logger.info(f"Removing nan values from the dataframe")

                    # removing nan values
                    
                    if df_prediction is not None:
                        if temporal_bool: 
                            
                            df_prediction = df_prediction.dropna(axis=1,how='all')
                            
                            if 'Prediction_1' in df_prediction.columns: df_prediction['Prediction_1'] = df_prediction['Prediction_1'].fillna("\'Silence\'")
                            if 'Prediction_2' in df_prediction.columns: df_prediction['Prediction_2'] = df_prediction['Prediction_2'].fillna("\'Silence\'")
                            if 'Prediction_3' in df_prediction.columns: df_prediction['Prediction_3'] = df_prediction['Prediction_3'].fillna("\'Silence\'")
                            
                        else: df_prediction = df_prediction.dropna()
                        logger.info(f"Removing nan values")

                except Exception as e:
                    logger.error(f"An error occurred while adding oca column: {e}")
                    


                try:
                    #####################################################
                    ########## APPLYING DB CORRECTION TO THE DATA #########
                    #####################################################
                    logger.info("")
                    tuple_folder_coeff = []
                    logger.info(f"Applying db correction")
                    """
                    for key, value in folder_coefficients.items():
                        key = key.split("\\")[:-1]
                        folder_name = key[-1]

                        # save tupples folder name, coefficient value
                        folder_name_coeff_value = (folder_name, value)
                        tuple_folder_coeff.append(folder_name_coeff_value)
                        key = os.path.join('\\\\', *key)

                        # assign the value to the folder
                        if folder == key:
                            df = apply_db_correction(df, value, sufix_string, logger)
                            logger.info(f"Apply {value} correction coefficient to the folder {folder}")
                    """
                    df = apply_db_correction(df, device_coeff, sufix_string, logger)
                    logger.info(f"Apply {device_coeff} correction coefficient to the folder {device}")
                except Exception as e:
                    logger.error(f"An error occurred while processing folder {folder}: {e}")
                    

                try:
                    logger.info("")    
                    logger.info(f"Creating slm_dict")
                    slm_dict = {}    
                    #folder = folder.split("\\")[-1]
                    
                    # add slm_dict column LAEQ_COLUMN_COEFF: with the value of LA_corrected
                    slm_dict["LAEQ_COLUMN_COEFF"] = 'LA_corrected'
                    slm_dict["LAMAX_COLUMN_COEFF"] = 'LAmax_corrected'
                    slm_dict["LAMIN_COLUMN_COEFF"] = 'LAmin_corrected'
                    #### NEW ONES ####
                    slm_dict["LC-LA_COLUMN_COEFF"] = 'LCeq-LAeq_corrected'
                    # slm_dict["L90_COLUMN_COEFF"] = '90percentile'


                    # SAVE THE INFO IN A JSON FILE
                    info_dict = {
                        "PERIODO_AGREGACION": PERIODO_AGREGACION,
                        "PERCENTILES": PERCENTILES,
                        "folder_coeff": tuple_folder_coeff,
                        "stable_version": stable_version,
                        "slm_type": device,
                        "oca_limits": oca_limits,
                        "oca_type": oca_type,
                    }

                    # save the info in a json file
                    with open(os.path.join(folder_output_dir, "processing_parameters.json"), 'w') as f:
                        json.dump(info_dict, f)
                    logger.info(f"Saved processing_parameters.json in {folder_output_dir}")
                except Exception as e:
                    logger.error(f"An error occurred while creating slm_dict: {e}")
                    continue

                
                try:
                    logger.info("")
                    logger.info(f"Adding the ships on dock to the general dataframe")


                    logger.info(f"Ship dock 1h")
                    ship_dock_1h_path = RELATIVE_PATH_SHIPS_1H
                    #check if the file exists
                    if not os.path.exists(ship_dock_1h_path):
                        logger.error(f"File {ship_dock_1h_path} does not exist. Please check the path.")
                    else:
                        logger.info(f"File {ship_dock_1h_path} exist!")
                    df_ship_dock_1h = pd.read_csv(ship_dock_1h_path, parse_dates=['date_time'])
                    


                    # logger.info(f"Ship dock 15min")
                    # ship_dock_15min_path = os.path.join(home_dir, RELATIVE_PATH_SHIPS_15MIN)
                    # #check if the file exists
                    # if not os.path.exists(ship_dock_15min_path):
                    #     logger.error(f"File {ship_dock_15min_path} does not exist. Please check the path.")
                    # else:
                    #     logger.info(f"File {ship_dock_15min_path} exist!")
                    # df_ship_dock_15min = pd.read_csv(ship_dock_15min_path, parse_dates=['datetime'])
                    

                    # df_ship_1s_csv_path = os.path.join(folder_output_dir, f"{actual_folder_name}_ship_1s.csv")
                    # if os.path.exists(df_ship_1s_csv_path):
                    #     logger.info(f"File {df_ship_1s_csv_path} already exists, skipping ship dock 1s analysis")
                    #     df = pd.read_csv(df_ship_1s_csv_path)
                    #     logger.info(f"Loaded ships on dock 1s dataframe from {df_ship_1s_csv_path}")
                    #     # continue
                    
                    # else:
                    #     logger.info(f"Ship dock 1s")
                    #     ship_dock_1s_path = os.path.join(home_dir, RELATIVE_PATH_SHIPS_1S)
                    #     #check if the file exists
                    #     if not os.path.exists(ship_dock_1s_path):
                    #         logger.error(f"File {ship_dock_1s_path} does not exist. Please check the path.")
                    #     else:
                    #         logger.info(f"File {ship_dock_1s_path} exist!")
                    #     df_ship_dock_1s = pd.read_csv(ship_dock_1s_path, parse_dates=['date_time'])
                    #     df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

                    #     # df = Timestamp
                    #     # df_ship_dock_1s = date_time

                    #     # merging
                    #     logger.info(f"Merging the ships on dock dataframes with the main dataframe")
                    #     df = df.merge(
                    #         df_ship_dock_1s[['date_time', 'nships']],
                    #         left_on='Timestamp',
                    #         right_on='date_time',
                    #         how='left'
                    #     )
                    #     # remove the date_time column from the df_ship_dock_1s
                    #     df.drop(columns=['date_time'], inplace=True, errors='ignore')

                    #     df.to_csv(df_ship_1s_csv_path, index=False)
                    #     logger.info(f"Saved ships on dock 1s dataframe to {df_ship_1s_csv_path}")
                        # if the values inside the nships is 1 or more, then 1, else 0
                        # df_alarms_1h['ships_alarm'] = df_alarms_1h['ships_alarm'].apply(lambda x: 1 if x > 0 else 0)
                except Exception as e:
                    logger.error(f"An error occurred while adding the ships on dock to the alarms dataframe: {e}")
                    continue



                try:
                    logger.info("")
                    logger.info("FILTERING THE PREDICTION DF. TAKING JUST THE FIRST ONE AND IF IT OVERCOME THE THRESHOLD")

                    # getting just the first class and their oribability
                    df_prediction_alarms = df_prediction

                    if temporal_bool:
                        df_prediction_alarms["class_list"] = df_prediction_alarms["Prediction_1"].apply(parse_prediction_class)
                        df_prediction_alarms["probability_list"] = df_prediction_alarms["Prob_1"].apply(parse_probability)

                        df_prediction_alarms["class"] = df_prediction_alarms["class_list"].apply(lambda x: x[0] if len(x) > 0 else "Silence")
                        df_prediction_alarms["probability"] = df_prediction_alarms["probability_list"].apply(lambda x: float(x[0]) if len(x) > 0 and pd.notna(x[0]) else 0.0)
                    else:
                        df_prediction_alarms["class_list"] = df_prediction_alarms["Prediction_1"].apply(parse_prediction_class)
                        df_prediction_alarms["probability_list"] = df_prediction_alarms["Prob_1"].apply(parse_probability)

                        df_prediction_alarms["class"] = df_prediction_alarms["class_list"].apply(lambda x: x[0] if len(x) > 0 else "Silence")
                        df_prediction_alarms["probability"] = df_prediction_alarms["probability_list"].apply(lambda x: float(x[0]) if len(x) > 0 and pd.notna(x[0]) else 0.0)

                    #now, just taking the first class when its probability is greater than the threshold
                    df_prediction_alarms = df_prediction_alarms[df_prediction_alarms['probability'] >= PROBABILITY_THRESHOLD]


                    #adding the prediction to the df
                    yamnet_csv_renamed = yamnet_csv.rename(columns={"display_name": "class"})
                    df_prediction_alarms_mapped = df_prediction_alarms.merge(
                        yamnet_csv_renamed,
                        on="class",
                        how="left"
                    )


                    if df is not None: df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    else: continue
                    df_prediction_alarms_mapped['Timestamp'] = pd.to_datetime(df_prediction_alarms_mapped['Timestamp'])
                    if df is not None:
                        if temporal_bool:
                            if df_prediction_alarms.index.name == "Timestamp":
                                df_prediction_alarms_mapped = df_prediction_alarms_mapped.reset_index(drop=True)
                                df_prediction_alarms_mapped["Timestamp"] = pd.to_datetime(df_prediction_alarms_mapped["Timestamp"],utc=True)

                                df = df.reset_index(drop=True)
                                df["Timestamp"] = pd.to_datetime(df["Timestamp"],utc=True)
                        df = df.merge(
                            df_prediction_alarms_mapped[['Timestamp', 'class', 'probability', 'NoisePort_Level_1']],
                            left_on='Timestamp',
                            right_on='Timestamp',
                            how='left'
                        )
                    df.drop(columns=['Timestamp_y'], inplace=True, errors='ignore')
                    df.rename(columns={'Timestamp_x': 'Timestamp'}, inplace=True, errors='ignore')
                    logger.info("Added the prediction data to the main dataframe")

                except Exception as e:
                    logger.error(f"An error occurred while processing folder {folder}: {e}")





                try:
                    ##################################
                    ##################################
                    ##################################
                    # PEAK + ROLLING ANALYSIS
                    ##################################
                    ##################################
                    ##################################
                    logger.info("")
                    logger.info(f"Applying find_peaks function to the whole dataframe")
                    df_peaks_csv_path = os.path.join(folder_output_dir, f"{actual_folder_name}_peaks_filtered.csv")
                    
                    # if os.path.exists(df_peaks_csv_path):
                    #     logger.info(f"File {df_peaks_csv_path} already exists, skipping peaks analysis")
                    #     df_peaks = pd.read_csv(df_peaks_csv_path)
                    #     logger.info(f"Loaded peaks dataframe from {df_peaks_csv_path}")
                    
                    # else:


                    #peaks, properties=find_peaks(df['LA_corrected'], prominence=PROMINENCE, width=WIDTH)
                    #df_peaks = df.iloc[peaks].copy()
                    if not temporal_bool:
                        logger.info("")
                        logger.info(f"Rolling the data with a window of {WINDOW_SIZE} seconds")
                        # rolling median for the LA values with a window of 30 seconds
                        df_peaks['LA_cor_median'] = df_peaks['LA_corrected'].rolling(window=WINDOW_SIZE, min_periods=1).quantile(0.5) + ADDING_THRESHOLD
                        df_peaks['Peak'] = 1

                        #above threshold
                        logger.info(f"Calculating peaks above threshold")
                        df_peaks = df_peaks[df_peaks['LA_corrected'] > df_peaks['LA_cor_median']]
                        logger.info(f"There are {len(df_peaks)} peaks in the dataframe after filtering")
                        # 

                        df_peaks.to_csv(df_peaks_csv_path, index=False)
                        logger.info(f"Saved peaks filtered dataframe to {df_peaks_csv_path}, with a lenght of {len(df_peaks)}")

                    #Timestamp to datetime
                    if temporal_bool : df_peaks['Timestamp'] = df_peaks['start_time']
                    df_peaks['Peak'] = 1
                    df_peaks['Timestamp'] = pd.to_datetime(df_peaks['Timestamp'])
                    df_peaks["Timestamp"] = pd.to_datetime(df_peaks["Timestamp"],utc=True)
                except Exception as e:
                    logger.error(f"An error occurred while trimming the dataframe {e}")
                    continue


                
                try:
                    logger.info("")
                    
                    print(df_peaks)

                    #merging
                    logger.info("Merging the peaks dataframe with the acoustic dataframe")
                    df_all = df.merge(
                        df_peaks[['Peak']],
                        left_index=True,
                        right_index=True,
                        how='left'
                    )
                    logger.info("Merge successful for the peaks and acoustic dataframes")
                    print(df_all)
                    print(df_all["Peak"].value_counts())
                    print(df_all["Peak"].unique())
                    #exit()


                except Exception as e:
                    logger.error(f"An error occurred while merging the peak df and the acoustic dataframe {e}")
                    continue

                

                ################################################################
                ################################################################
                try:
                    ################################################################
                    # TRANSFORMING 1 SECOND DATA TO 1 HOUR DATA
                    ##################################################################
                    logger.info("")
                    logger.info(f"Transforming 1 second data to 1 hour data")
                    
                    logger.info(f"MAKING FOLDER FOR 1H ANALYSIS TO SAVE THE DATA")
                    # remove the last part of the folder_output_dir
                    folder_output_dir_for_alarms = os.path.dirname(folder_output_dir)
                    folder_output_dir_1h = os.path.join(folder_output_dir_for_alarms, 'Graphics_ALARMS')
                    os.makedirs(folder_output_dir_1h, exist_ok=True)

                    logger.info(f"Making the folder for week analysis for 1 hour data")
                    folder_output_dir_1h_week = os.path.join(folder_output_dir_1h, 'Graphics_week')
                    os.makedirs(folder_output_dir_1h_week, exist_ok=True)


                    # check if the file exists
                    df_1h_csv_path = os.path.join(folder_output_dir_1h, f"{actual_folder_name}_1h.csv")
                    # if os.path.exists(df_1h_csv_path):
                    #     logger.info(f"File {df_1h_csv_path} already exists, skipping transformation")
                    #     df_1h = pd.read_csv(df_1h_csv_path)
                    #     logger.info(f"Loaded 1 hour dataframe from {df_1h_csv_path}")
                    #     # continue
                    
                    # else:
                    # df_1h = transform_1h(df, slm_dict, logger, agg_period=3600)

                    # print(len(df_1h))
                    df_1h = transform_1h_pred(df, logger, agg_period=3600)
                    df_1h = df_1h.round(2)
                    logger.info(f"Transformed 1 second data to 1 hour data")
                    print(df_1h)
                    #exit()



                    logger.info("")
                    logger.info("")
                    logger.info(f"TRANSFORMATION SECTION")
                    logger.info(f"Adding oca column")
                    logger.info(f"OCA Limits --> {oca_limits}")
                    # set index (which is datetime) as column
                    df_1h.reset_index(inplace=True)
                    
                    df_1h = transformation(df_1h, logger, oca_limits)

                    #####
                    #ssave
                    #removeing datetime column and rename datetime_y to datetime
                    # df.drop(columns=['datetime'], inplace=True, errors='ignore')
                    # df.rename(columns={'datetime_y': 'datetime'}, inplace=True, errors='ignore')
                    # print(df_1h)
                    # print(df_1h.columns)
                    # print(df)
                    # print(df.columns)
                    df_1h.to_csv(df_1h_csv_path, index=False)
                    logger.info(f"Saved 1 hour dataframe to {df_1h_csv_path}")

                except Exception as e:
                    logger.error(f"An error occurred while transforming 1 second data to 1 hour data: {e}")
                    continue



                ###################################
                ###################################
                ###################################
                # MERGING SECTION
                ####################################
                logger.info("")
                logger.info(f"MERGING SECTION")
                

                try:
                        ############# MERGING PEAKS WITH ACOUSTIC PREDICTION DATAFRAME ##################
                    acoustic_pred_peak_csv_path = os.path.join(ai_prediction_folder, f"{actual_folder_name}_acoustic_pred_peak_test.csv")
                    # if os.path.exists(acoustic_pred_peak_csv_path):
                    #     logger.info(f"[2] File {acoustic_pred_peak_csv_path} already exists, skipping merge")
                    #     df_all = pd.read_csv(acoustic_pred_peak_csv_path)

                    # else:
                    logger.info("")
                    logger.info("[2] Merging the peaks dataframe with the acoustic dataframe")
                    df_all = df_1h.merge(
                        df_peaks[['Peak']],
                        left_index=True,
                        right_index=True,
                        how='left'
                    )
                    logger.info("Merge successful for the peaks and acoustic dataframes")

                    logger.info(f"Saving the merged dataframe to the prediction folder")
                    df_all.to_csv(acoustic_pred_peak_csv_path, index=False)
                    logger.info(f"Saved merged dataframe to {acoustic_pred_peak_csv_path}")

                except Exception as e:
                    logger.error(f"An error occurred while merging the ACOUSTIC PREDICT PEAKS dataframE: {e}")

                print(df_all)
                print(df_all["Peak"].value_counts())
                print(df_all["Peak"].unique())
                #exit()
                



                ###################################
                ###################################
                logger.info("")
                logger.info(f"PLOTTING SECTION")

                # Plotting night evolution
                if PLOT_NIGHT_EVOLUTION:
                    logger.info(f"[1.1] Plotting night evolution for folder {folder}")
                    plot_night_evolution(df, folder_output_dir, logger, laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname=folder, indicador_noche="Ln")
                
                if PLOT_NIGHT_EVOLUTION_WEEK:
                    logger.info(f"[1.2] Plotting night WEEK evolution for folder {folder}")
                    plot_night_evolution_week(df, folder_output_dir_week, logger, laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname='night_evolution_week', indicador_noche="Ln")



                # Plotting night evolution 15 min
                if PLOT_NIGHT_EVOLUTION_15_MIN:
                    logger.info(f"[2.1] Plotting night evolution 15 min for folder {folder}")
                    plot_night_evolution_15_min(df, folder_output_dir, logger, name_extension="15_min", laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname='night_evolution_15min', indicador_noche="Ln")

                # Plotting night evolution 15 min
                if PLOT_NIGHT_EVOLUTION_15_MIN_WEEK:
                    logger.info(f"[2.2] Plotting night WEEK evolution 15 min for folder {folder}")
                    plot_night_evolution_15_min_week(df, folder_output_dir_week, logger, name_extension="15_min", laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname='night_evolution_15min_week', indicador_noche="Ln")





                ############################ PREDICTION PLOTTING SECTION ####################################################################################
                # Plotting LEq power average with predictions
                if PLOT_PREDIC_LAEQ_MEAN:
                    logger.info(f"[3.1] Plotting PLOT_PREDIC_LAEQ_MEAN for folder {folder}")
                    plot_predic_laeq_mean(df, taxonomy, ia_visualization_folder, logger, plotname='predictions')

                if PLOT_PREDIC_LAEQ_MEAN_WEEK:
                    logger.info(f"[3.2] Plotting PLOT_PREDIC_LAEQ_MEAN WEEK for folder {folder}")
                    plot_predic_laeq_mean_week(df, taxonomy, ia_visualization_folder, logger, plotname='predictions')


                # TODO
                # if PLOT_PREDIC_LAEQ_15_MIN_PERIOD:
                #     logger.info(f"[4.1] Plotting PLOT_PREDIC_LAEQ_15_MIN_PERIOD for folder {folder}")
                #     plot_predic_laeq_15_min_period(df, yamnet_csv, taxonomy, ia_visualization_folder, logger, columns_dict=slm_dict, agg_period=PERIODO_AGREGACION, plotname=folder)

                if PLOT_PREDIC_LAEQ_MEAN_4H:
                    logger.info(f"[4.1] Plotting PLOT_PREDIC_LAEQ_MEAN_4H for folder {folder}")
                    plot_predic_laeq_mean_4h(df, df_ship_dock_1h, taxonomy, ia_visualization_folder, logger, plotname='predictions')    
                    #exit()
                
                if PLOT_PREDIC_LAEQ_DAY:
                    logger.info(f"[4.1] Plotting PLOT_PREDIC_LAEQ_MEAN_4H for folder {folder}")
                    plot_predic_laeq_mean_day(df, df_ship_dock_1h, taxonomy, ia_visualization_folder, logger, plotname='predictions')
                    #exit()


                # TODO
                # if PLOT_PREDIC_LAEQ_15_MIN_4H:
                #     logger.info(f"[5] Plotting PLOT_PREDIC_LAEQ_4H for folder {folder}")
                #     plot_predic_laeq_15_min_4h(df, yamnet_csv,taxonomy, df_prediction, ia_visualization_folder, logger, columns_dict=slm_dict, agg_period=PERIODO_AGREGACION, plotname=folder)


                # TODO
                # # Plotting stack bar with predictions class
                # if PLOT_PREDICTION_STACK_BAR:
                #     logger.info(f"[6] Plotting PLOT_PREDICTION_STACK_BAR for folder {folder}")
                #     plot_prediction_stack_bar(df_prediction, yamnet_csv, taxonomy, ia_visualization_folder, logger, plotname=folder)
                


                # TODO
                #if PLOT_PREDICTION_MAP:
                #    logger.info(f"[7.1] Plotting PLOT_PREDICTION_MAP WEEK for folder {folder}")
                #    df_all_yamnet_1h = plot_prediction_map_new(df_all_yamnet, df_ship_dock_1h, ia_visualization_folder, logger, plotname=folder)
                #    print(df_all_yamnet_1h)
                #    print(df_all_yamnet_1h.columns)
                #    # print(df_all_yamnet_1h['NoisePort_Level_1'].value_counts())
                #    # exit()

                # TODO
                #if PLOT_PREDICTION_MAP_WEEK:
                #    logger.info(f"[7.2] Plotting PLOT_PREDICTION_MAP WEEK for folder {folder}")
                #    plot_prediction_map_new_week(df_all_yamnet, taxonomy, ia_visualization_folder, logger, plotname=folder)



                # TODO
                # # Plotting tree map
                # if PLOT_TREE_MAP:
                #     logger.info(f"[8] Plotting PLOT_TREE_MAP for folder {folder}")
                #     plot_tree_map(df_prediction,taxonomy,ia_visualization_folder, logger, plotname=folder)
                ##############################################################################################################################################

    
                
                # Plotting time plot
                if PLOT_MAKE_TIME_PLOT:
                    logger.info(f"[9.1] Plotting time plot for folder {folder}")
                    make_time_plot(df, folder_output_dir, logger, columns_dict=slm_dict, agg_period=PERIODO_AGREGACION, plotname='time_plot', percentiles=PERCENTILES)


                # Plotting time plot
                if PLOT_MAKE_TIME_PLOT_WEEK:
                    logger.info(f"[9.2] Plotting time WEEK plot for folder {folder}")
                    make_time_plot_week(df, folder_output_dir_week, logger, columns_dict=slm_dict, agg_period=PERIODO_AGREGACION, plotname='time_plot_week', percentiles=PERCENTILES)


                # Plotting heatmap evolution hour
                if PLOT_HEATMAP_EVOLUTION_HOUR:
                    logger.info(f"[10.1] Plotting heatmap for folder {folder}")
                    plot_heatmap_evolution_hour(df, folder_output_dir, logger, values_column=slm_dict['LAEQ_COLUMN_COEFF'], agg_func=leq,plotname='heatmap_hour')


                # Plotting heatmap evolution hour
                if PLOT_HEATMAP_EVOLUTION_HOUR_WEEK:
                    logger.info(f"[10.2] Plotting heatmap WEEK for folder {folder}")
                    plot_heatmap_evolution_hour_week(df, folder_output_dir_week, logger, values_column=slm_dict['LAEQ_COLUMN_COEFF'], agg_func=leq,plotname='heatmap_hour_week')
                
                
                # Plotting heatmap evolution 15 min
                if PLOT_HEATMAP_EVOLUTION_15_MIN:
                    logger.info(f"[11] Plotting heatmap 15 min for folder {folder}")
                    plot_heatmap_evolution_15_min(df, folder_output_dir, logger, values_column=slm_dict['LAEQ_COLUMN_COEFF'], agg_func=leq,plotname='heatmap_evolution')

                
                # Plotting heatmap evolution 15 min
                if PLOT_HEATMAP_EVOLUTION_15_MIN_WEEK:
                    logger.info(f"[11.2] Plotting heatmap 15 min WEEK for folder {folder}")
                    plot_heatmap_evolution_15_min_week(df, folder_output_dir_week, logger, values_column=slm_dict['LAEQ_COLUMN_COEFF'], agg_func=leq,plotname='heatmap_evolution_week')
                

                # Plotting individual heatmap
                if PLOT_INDICADORES_HEATMAP:
                    logger.info(f"[12] Plotting indicadores heatmap for folder {folder}")
                    plot_indicadores_heatmap(df, folder_output_dir, logger, plotname='indicadores_heatmap', ind_column=slm_dict["LAEQ_COLUMN_COEFF"])

                
                # Plotting individual heatmap
                if PLOT_INDICADORES_HEATMAP_WEEK:
                    logger.info(f"[12.2] Plotting indicadores heatmap WEEK for folder {folder}")
                    plot_indicadores_heatmap_week(df, folder_output_dir_week, logger, plotname='indicadores_heatmap_week', ind_column=slm_dict["LAEQ_COLUMN_COEFF"])


                # Plotting day evolution
                if PLOT_DAY_EVOLUTION:
                    logger.info(f"[13] Plotting day evolution for folder {folder}")
                    plot_day_evolution(df, folder_output_dir, logger, laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname='day_evolution')


                if PLOT_DAY_EVOLUTION_WEEK:
                    logger.info(f"[13.2] Plotting day evolution WEEK for folder {folder}")
                    plot_day_evolution_week(df, folder_output_dir_week, logger, laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname='day_evolution_week')
                

                # Plotting period evolution
                if PLOT_PERIOD_EVOLUTION:
                    logger.info(f"[14] Plotting period evolution (1) Ld (2) Le for folder {folder}")
                    plot_period_evolution(df, folder_output_dir, logger, laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname='period_evolution')


                # Plotting period evolution
                if PLOT_PERIOD_EVOLUTION_WEEK:
                    logger.info(f"[14.2] Plotting period evolution (1) Ld (2) Le WEEK for folder {folder}")
                    plot_period_evolution_week(df, folder_output_dir_week, logger, laeq_column=slm_dict["LAEQ_COLUMN_COEFF"], plotname='period_evolution_week')
                

                # TODO
                # I dont know why I commented this out
                # if PLOT_SPECTROGRAM_1_3:
                #     logger.info(f"[15] Plotting spectrogram for folder {folder}")
                #     # plt_spectrogram(df_oct, folder_output_dir, logger, plotname=folder)
                #     plt_spectrogram(df, folder_output_dir, sufix_string, logger, plotname=folder)




                #############################
                ######### PLOTING ALARMS
                ################################
                logger.info("")
                logger.info(f"PLOTTING ALARMS!!!")

                if OCA_ALARM:
                    logger.info(f"[1.1] Plotting OCA alarm for folder {folder}")
                    df_alarms_1h = oca_alarm(df_1h, folder_output_dir_1h, logger, plotname='oca_alarm')
                    print(df_alarms_1h)

                if OCA_ALARM_WEEK:
                    logger.info(f"[1.2] Plotting OCA alarm WEEK for folder {folder}")
                    oca_alarm_week(df_1h, folder_output_dir_1h_week, logger, plotname='oca_alarm_week')
                
                if LMAX_ALARM:
                    logger.info(f"[2.1] Plotting LMAX alarm for folder {folder}")
                    df_alarms_1h=lmax_alarm(df_1h, folder_output_dir_1h, logger, plotname='lmax_alarm', threshold=95) # OCA +10
                    print(df_alarms_1h)

                if LMAX_ALARM_WEEK:
                    logger.info(f"[2.2] Plotting LMAX alarm WEEK for folder {folder}")
                    lmax_alarm_week(df_1h, folder_output_dir_1h_week, logger, plotname='lmax_alarm_week', threshold=95)

                if LC_LA_ALARM:
                    logger.info(f"[3.1] Plotting LC-LA alarm for folder {folder}")
                    df_alarms_1h=LC_LA_alarm(df_1h, folder_output_dir_1h, logger, plotname='LC_LA_alarm', threshold_norma=10, threshold_dB=3)
                    print(df_alarms_1h)

                if LC_LA_ALARM_WEEK:
                    logger.info(f"[3.2] Plotting LC-LA alarm WEEK for folder {folder}")
                    LC_LA_alarm_week(df_1h, folder_output_dir_1h_week, logger, plotname='LC_LA_alarm_week', threshold_norma=10, threshold_dB=3)

                if L90_ALARM:
                    logger.info(f"[4.1] Plotting L90 alarm for folder {folder}")
                    l90_alarm(df_1h, folder_output_dir_1h, logger, plotname='190_alarm', threshold_dB=5)

                if L90_ALARM_WEEK:
                    logger.info(f"[4.2] Plotting L90 alarm WEEK for folder {folder}")
                    l90_alarm_week(df_1h, folder_output_dir_1h_week, logger, plotname='190_alarm_week', threshold_dB=5)

                if L90_ALARM_DYNAMIC:
                    logger.info(f"[5.1] Plotting L90 alarm dynamic for folder {folder}")
                    df_alarms_1h=l90_alarm_dynamic(df_1h, folder_output_dir_1h, logger, plotname='190_alarm_dynamic', threshold_dB=5)
                    print(df_alarms_1h)

                if L90_ALARM_DYNAMIC_WEEK:
                    logger.info(f"[5.2] Plotting L90 alarm dynamic WEEK for folder {folder}")
                    l90_alarm_dynamic_week(df_1h, folder_output_dir_1h_week, logger, plotname='190_alarm_dynamic_week', threshold_dB=5)

                if FREQUENCY_COMPOSITION:
                    logger.info(f"[6.1] Plotting frequency composition for folder {folder}")            
                    df_alarms_1h =frequency_composition(df, df_alarms_1h, folder_output_dir_1h, logger, plotname='freq_composition', threshold_comp=5)
                    print(df_alarms_1h)
                    # exit()

                if FREQUENCY_COMPOSITION_WEEK:
                    logger.info(f"[6.2] Plotting frequency composition WEEK for folder {folder}")            
                    frequency_composition_week(df, folder_output_dir_1h_week, logger, plotname='freq_composition_week', threshold_comp=5)

                if TONAL_FREQUENCY:
                    logger.info(f"[7.1] Plotting tonal frequency for folder {folder}")
                    df_alarms_1h = tonal_frequency(df, df_alarms_1h, folder_output_dir_1h, logger, plotname='tonal_freq')
                    print(df_alarms_1h)
                # TODO
                #if TONAL_FREQUENCY_WEEK:
                #    logger.info(f"[7.2] Plotting tonal frequency WEEK for folder {folder}")
                #    tonal_frequency_week(df, folder_output_dir_1h_week, logger, plotname='tonal_freq_week')





                ################################################################
                # PEAK ANALYSIS
                ##################################################################
                logger.info("")
                logger.info(f"PEAKS PLOTTING!!!")
                

                if PLOT_PEAK_DISTRIBUTION_HEATMAP:
                    logger.info(f"[8.1] Plotting peak heatmap for folder {folder}")
                    df_alarms_1h=plot_peak_distribution_heatmap(df_peaks, df_alarms_1h, folder_output_dir_1h, logger, plotname='peak_distribution_heatmap')

                if PLOT_PEAK_DISTRIBUTION_HEATMAP_WEEK:
                    logger.info(f"[8.2] Plotting peak heatmap WEEK for folder {folder}")
                    plot_peak_distribution_heatmap_week(df_peaks, folder_output_dir_1h_week, logger, plotname='peak_distribution_heatmap_week')



                if PLOT_PEAK_DISTRIBUTION:
                    logger.info(f"[9.1] Plotting peak distribution for folder {folder}")
                    plot_peak_distribution(df_peaks, folder_output_dir_1h, logger, plotname='peak_distribution')

                if PLOT_PEAK_DISTRIBUTION_WEEK:
                    logger.info(f"[9.2] Plotting peak distribution WEEK for folder {folder}")
                    plot_peak_distribution_week(df_peaks, folder_output_dir_1h_week, logger, plotname='peak_distribution_week')



                if PLOT_PEAK_DENSITY_DISTRIBUTION:
                    logger.info(f"[10.1] Plotting density distribution for folder {folder}")
                    plot_density_distribution_peaks(df_peaks, folder_output_dir_1h, logger, plotname='peak_density_distribution')

                if PLOT_PEAK_DENSITY_DISTRIBUTION_WEEK:
                    logger.info(f"[10.2] Plotting density distribution WEEK for folder {folder}")
                    plot_density_distribution_peaks_week(df_peaks, folder_output_dir_1h_week, logger, plotname='peak_density_distribution_week')




                # #####################################################
                # PLOTTING PREDICTION SECTION
                # #####################################################
                if PLOT_PEAK_PREDIC_LAEQ_MEAN:
                    logger.info(f"[11.1] Plotting PLOT_PREDIC_LAEQ for folder {folder}")
                    plot_predic_peak_laeq_mean(df_all_yamnet, taxonomy, ia_visualization_folder, logger, plotname='prediction')

                if PLOT_PEAK_PREDIC_LAEQ_MEAN_WEEK:
                    logger.info(f"[11.2] Plotting PLOT_PREDIC_LAEQ WEEK for folder {folder}")
                    plot_predic_peak_laeq_mean_week(df_all_yamnet, taxonomy, ia_visualization_folder, logger, plotname='prediction')

                


                if PLOT_PEAK_BOX_PLOT_PREDICTION:
                    logger.info(f"[12] Plotting box plot prediction for folder {folder}")
                    plot_box_plot_prediction(df_all_yamnet, taxonomy, ia_visualization_folder, logger, plotname='prediction')

                if PLOT_PEAK_BOX_PLOT_PREDICTION_WEEK:
                    logger.info(f"[12.2] Plotting box plot prediction WEEK for folder {folder}")
                    plot_box_plot_prediction_week(df_all_yamnet, taxonomy, ia_visualization_folder, logger, plotname='prediction')




                if PLOT_PEAK_HEATMAT_PREDICTION:
                    logger.info(f"[13] Plotting heatmap prediction for folder {folder}")
                    plot_heat_map_prediction(df_all_yamnet, taxonomy, ia_visualization_folder, logger, plotname='peak_heatman_prediction')

                if PLOT_PEAK_HEATMAT_PREDICTION_WEEK:
                    logger.info(f"[13.2] Plotting heatmap prediction WEEK for folder {folder}")
                    plot_heat_map_prediction_week(df_all_yamnet, taxonomy, ia_visualization_folder, logger, plotname='peak_heatmap_prediction')




                ################################
                ################################
                ################################
                # # ADDING THE NEW ALARMS CALCULATED
                logger.info("")
                logger.info(f"Adding the yamnet taxonomy to the alarms dataframe")
                columns_to_merge = ["Timestamp", "mid", "iso_taxonomy", "Brown_Level_2", "Brown_Level_3", "NoisePort_Level_1", "NoisePort_Level_2"]
                df_subset = df_all_yamnet_1h[columns_to_merge]


                df_alarms_1h = df_alarms_1h.merge(
                    df_subset,
                    left_on="date_time",
                    right_on="Timestamp",
                    how="left"
                )
                df_alarms_1h.drop(columns=["Timestamp"], inplace=True)
                logger.info(f"Adding the yamnet taxonomy to the alarms dataframe successful")


                ################################
                ################################
                ################################
                # SAVING THE ALARMS CSV FILE
                logger.info("")
                logger.info(f"SAVING THE ALARMS CSV FILE")

                try:
                    alarms_csv_path = os.path.join(folder_output_dir_1h, f"{actual_folder_name}_full_alarms.csv")
                    df_alarms_1h.to_csv(alarms_csv_path, index=False)
                    logger.info(f"Saved alarms dataframe to {alarms_csv_path}")

                except Exception as e:
                    logger.error(f"An error occurred while saving the alarms dataframe: {e}")
                    continue
                ################################
                ################################
                ################################



        except Exception as e:
            logger.error(f"An error occurred while processing folder {folder}: {e}")