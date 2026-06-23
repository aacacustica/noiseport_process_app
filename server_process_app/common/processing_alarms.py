import sys

import pandas as pd
import matplotlib.pyplot as plt
import os
plt.style.use("bmh")

from scipy.signal import find_peaks

import re


from server_process_app.common.reading_alarms import *
from server_process_app.common.utils_vi import *
from server_process_app.common.config_vi import *
from server_process_app.common.visualization_alarms import *



def process_all_folders(folders, PERIODO_AGREGACION, PERCENTILES, taxonomy, yamnet_csv, sufix_string, oca_limits, oca_type, logger):
    
    temporal_bool = True
    print()
    stable_version = get_stable_version(logger)
    home_dir = os.path.expanduser('~')

    for folder in folders:
        device = folder.split("/")[-2]
        sufix_string = device
        logger.info("")
        logger.info(f"Suffix string: {sufix_string}")

        ###################
        # PROCESSED FILE 
        ###################
        
        processed_list_path = os.path.join(folder,f"processed_csv_{device}_{stable_version}.txt")
        logger.info(f"Processed list file path: {processed_list_path}")

        with open(processed_list_path, "w+", encoding="utf-8") as f:
            processed_csvs = {line.strip() for line in f if line.strip()}






        ###################
        # YAMNET COLUMNS
        ###################
        yamnet_df = yamnet_csv[[
            # "mid",
            "display_name",
            # "iso_taxonomy",
            # "Brown_Level_2",
            # "Brown_Level_3",
            "NoisePort_Level_1",
            # "NoisePort_Level_2",
        ]]



        #############################
        ## GETTING THE DATAFRAME ###
        #############################
        try:
            logger.info("")
            logger.info(f"Processing folder {folder}") 
            logger.info(f"Getting the data from the dataframes")
            
            ############
            # RASPBERRY
            ############

            logger.info("") 
            logger.info("Processing RASPBERRY data")
            csv_files = [f for f in os.listdir(folder) if f.lower().endswith(".csv")]
            csv_paths = [os.path.join(folder, f) for f in csv_files]
            logger.info(f"Found {len(csv_paths)} CSV files in {folder}")

            for csv_path in csv_paths:
                csv_path_abs = os.path.abspath(csv_path)

                #skip processed files
                if csv_path_abs in processed_csvs:
                    logger.info(f"Skipping already processed file: {csv_path_abs}")
                    continue

                logger.info(f"Processing CSV: {csv_path_abs}")
                df=pd.read_csv(csv_path_abs)



                # [0] datetimecolumn
                df["datetime"] = pd.to_datetime(df["Timestamp"])
                df["datetime"] = df["datetime"].dt.tz_localize(None)

                # [1] rename
                if "Filename_acoustic" in df.columns:
                    df = df.rename(columns={"Filename_acoustic": "Filename"})


                if "Prediction_1" in df.columns:
                    df = df.merge(yamnet_df,how="left",left_on="Prediction_1",right_on="display_name",)
                else:
                    logger.warning("Prediction_1 column not found in df; cannot merge YAMNet taxonomy")


                # drop other filenames columns
                cols_to_drop = []
                for col in ["Filename_prediction", "peak_filename", "Prediction_2", "Prediction_3", "Prob_2", "Prob_3", "display_name"]:
                    if col in df.columns:
                        cols_to_drop.append(col)
                if cols_to_drop:
                    df = df.drop(columns=cols_to_drop)


                if "LC" in df.columns and "LA" in df.columns:
                    df["LC-LA"] = df["LC"] - df["LA"]

                # [2] desired order
                base_cols = [
                    "id_micro",
                    "Filename",
                    "datetime",
                    "Timestamp",
                    "Unixtimestamp",
                    "LA", "LC", "LZ", "LAmax", "LAmin", "LC-LA",
                ]


                # [3] 1/3 octave bands
                band_cols = [c for c in df.columns if c.endswith("Hz")]

                # [4 ] prediction columns
                pred_cols = [c for c in df.columns if c.startswith("Prediction_") or c.startswith("Prob_")]

                taxonomy_cols = []
                if "NoisePort_Level_1" in df.columns:
                    taxonomy_cols = ["NoisePort_Level_1"]

                # [5] peak columns
                peak_cols = [
                    "is_peak",
                    "peak_start_time",
                    "peak_end_time",
                    "peak_duration",
                    "peak_leq",
                    "peak_LA_values",
                ]
                peak_cols = [c for c in peak_cols if c in df.columns]

                # 6] rerange
                ordered_cols = [c for c in base_cols + band_cols + pred_cols+taxonomy_cols + peak_cols if c in df.columns]

                df = df[ordered_cols]
                df = df.sort_values("datetime").reset_index(drop=True)

                #save
                #folder to 
                prosprocessing_str = "postprocessing_csv"
                base_dir = os.path.dirname(csv_path_abs)

                post_dir = os.path.join(base_dir, "postprocessing")
                os.makedirs(post_dir, exist_ok=True)
                filename = os.path.basename(csv_path_abs)
                stem, _ = os.path.splitext(filename)
                #m = re.search(r"(\d{8}_\d{2})", stem)
                m = re.search(r"(\d{8})", stem)
                
                if m:
                    #date_hour = m.group(1)# "20250401_12"
                    day_hour = m.group(0)
                else:
                    logger.error(f"Could not find YYYYMMDD_HH pattern in filename {filename}, using full stem")
                

                output_path = os.path.join(post_dir, f"{day_hour}_postpo.csv")
                df.to_csv(output_path, index=False)
                logger.info(f"Saved corrected CSV to: {output_path}")

                
                output_path_graphics_alarms = os.path.join(post_dir,day_hour,'GRAPHICS_ALARMS')
                os.makedirs(output_path_graphics_alarms,exist_ok=True)
                output_path_ai_alarms = os.path.join(post_dir,day_hour,'AI_Alarms')
                os.makedirs(output_path_ai_alarms,exist_ok=True)
                output_path_day = os.path.join(post_dir,day_hour)
                
                # mark it
                # with open(processed_list_path, "a", encoding="utf-8") as f:
                #     f.write(csv_path_abs + "\n")
            


                ###################################################################
                ###################################################################
                logger.info("")
                try:
                    if df is not None:
                        logger.info("")
                        # add datetime columns, sort by datetime and set datetime as index
                        logger.info(f"Adding datetime columns, sorting by datetime and setting datetime as index")
                        df = add_datetime_columns(df,logger, date_col='datetime')
                        df = df.sort_values('datetime')
                        df.set_index('datetime', inplace=True, drop=True)
                        start_date = df.index[0]
                        end_date = df.index[-1]

                        logger.info(f"Start date {start_date} and end date {end_date}")
                        logger.info(f"df was sorted by datetime and datetime was set as index")
                    else:
                        logger.warning(f"df is None")
                        continue
                except Exception as e:
                    logger.error(f"An error occurred while adding datetime columns: {e}")

                



                try:
                    logger.info("")
                    # add indicators column
                    if df is not None:
                        logger.info(f"Adding indicators column")
                        df['indicador_str'] = df.apply(lambda x: evaluation_period_str(x['hour']), axis=1)
                    
                    # add nights column
                    if df is not None:
                        logger.info(f"Adding nights column")
                        df['night_str'] = df.apply(lambda x: add_night_column(x['hour'], x['weekday']), axis=1)


                    # add oca column
                    logger.info(f"Adding oca column")
                    logger.info(f"OCA Limits --> {oca_limits}")
                    if df is not None:
                        df['oca'] = df['hour'].apply(lambda h: db_limit(h, **oca_limits))

                except Exception as e:
                    logger.error(f"An error occurred while adding indicators and nights columns and oca column: {e}")


                    

                try:
                    logger.info("")
                    logger.info("FILTERING PREDICTIONS")
                    if "Prediction_1" in df.columns and "Prob_1" in df.columns:
                        mask = df["Prob_1"] >= PROBABILITY_THRESHOLD
                        cols_to_clear = ["Prediction_1", "Prob_1"]
                        if "NoisePort_Level_1" in df.columns:
                            cols_to_clear.append("NoisePort_Level_1")
                        # keep row
                        df.loc[~mask, cols_to_clear] = pd.NA
                    else:
                        logger.warning("Prediction_1 or Prob_1 column not found in df")

                except Exception as e:
                    logger.error(f"An error occurred while processing predictions in folder {folder}: {e}")



                ################################################################
                # TRANSFORMING 1 SECOND DATA TO 1 HOUR DATA
                ##################################################################
                try:
                    logger.info("")
                    logger.info(f"MAKING FOLDER FOR 1H ANALYSIS TO SAVE THE DATA")
                    # remove the last part of the folder_output_dir
                    folder_output_dir_for_alarms = folder.replace('SPL', 'Graphics_ALARMS')
                    folder_output_dir_1h = os.path.dirname(folder_output_dir_for_alarms)
                    os.makedirs(folder_output_dir_1h, exist_ok=True)

                    ia_visualization_folder = os.path.join(folder_output_dir_1h, 'AI_ALARMS')
                    os.makedirs(ia_visualization_folder, exist_ok=True)
                    logger.info(f"folder_output_dir_1h: {folder_output_dir_1h}")
                    logger.info(f"ia_visualization_folder: {ia_visualization_folder}")

                    point_name = os.path.basename(folder_output_dir_1h)
                    logger.info(f"Point name detected: {point_name}")


                    logger.info("")
                    logger.info(f"Transforming 1 second data to 1 hour data")

                    df_1h = df.resample("1h").apply(agg_hour)
                    df_1h = df_1h.reset_index()
                    df_1h = df_1h.round(1)


                    logger.info(f"")
                    logger.info(f"Adding oca column")
                    df_1h["hour"] = df_1h["datetime"].dt.hour
                    df_1h["weekday"] = df_1h["datetime"].dt.weekday
                    logger.info("Adding indicators / night / oca to 2H dataframe")

                    df_1h["indicador_str"] = df_1h["hour"].apply(evaluation_period_str)
                    df_1h["night_str"] = df_1h.apply(lambda x: add_night_column(x["hour"], x["weekday"]), axis=1)
                    df_1h["oca"] = df_1h["hour"].apply(lambda h: db_limit(h, **oca_limits))

                except Exception as e:
                    logger.error(f"An error occurred while transforming 1 second data to 1 hour data: {e}")
                    continue


                ###################################
                ###################################
                logger.info("")
                logger.info(f"CREATING THE CSV ALARMS!!!")
                df_alarms_1h = df_1h.copy()


                #OCA alarm
                logger.info("[1] Computing OCA alarm columns")
                df_alarms_1h = oca_alarm(df_alarms_1h, logger=logger)

                #LMAX alarm
                logger.info("[2] Computing LMAX alarm columns")
                df_alarms_1h = lmax_alarm(df_alarms_1h, logger=logger, threshold=95)

                #LC-LA alarm
                logger.info("[3] Computing LC-LA alarm columns")
                df_alarms_1h = LC_LA_alarm(df_alarms_1h, logger=logger,threshold_norma=10, threshold_dB=3)

                #L90 dynamic alarm
                logger.info("[4] Computing dynamic L90 alarm columns")
                df_alarms_1h = l90_alarm_dynamic(df_alarms_1h, logger=logger, threshold_dB=5)

                #freq composition
                logger.info("[5] Computing frequency composition alarms")
                df_alarms_1h = frequency_composition(df_1h,df_alarms_1h,logger=logger,threshold_comp=5)

                #tonal frequ
                logger.info("[6] Computing tonal frequency alarms")
                df_alarms_1h = tonal_frequency(df_1h,df_alarms_1h,folder_output_dir_1h,logger,plotname=folder)



                ################################################################
                # PEAK ANALYSIS
                ##################################################################
                if temporal_bool:PLOTTING_ALARMS=True
                if PLOTTING_ALARMS:
                    logger.info("")
                    logger.info(f"PLOTTING PEAKS!!!")

                    logger.info(f"[8] Plotting peak heatmap for folder {folder}")
                    plot_peak_distribution_heatmap(df_alarms_1h, output_path_graphics_alarms, logger, plotname="heatmap")


                    logger.info(f"[9] Plotting peak distribution for folder {folder}")
                    plot_peak_distribution(df_alarms_1h, output_path_graphics_alarms, logger, plotname="peak")


                    logger.info(f"[10] Plotting density distribution for folder {folder}")
                    plot_density_distribution_peaks(df_alarms_1h, output_path_graphics_alarms, logger, plotname="density")



                    #####################################################
                    # PLOTTING PREDICTION SECTION
                    #####################################################
                    logger.info("")
                    logger.info(f"PLOTTING PREDICTION !!!")

                    logger.info(f"[11] Plotting PLOT_PREDIC_LAEQ for folder {folder}")
                    plot_predic_peak_laeq_mean(df_alarms_1h,yamnet_csv, output_path_ai_alarms, logger, plotname="predic")


                    logger.info(f"[12] Plotting box plot prediction for folder {folder}")
                    plot_box_plot_prediction(df_alarms_1h,yamnet_csv, output_path_ai_alarms, logger, plotname="box")


                    logger.info(f"[13] Plotting heatmap prediction for folder {folder}")
                    plot_heat_map_prediction(df_alarms_1h,yamnet_csv, output_path_ai_alarms, logger, plotname="heat map predic")
                else:
                    logger.info("Not plotting alarms.")


                ################################
                ################################
                ################################
                # SAVING THE ALARMS CSV FILE
                logger.info("")
                logger.info(f"SAVING THE ALARMS CSV FILE")
                try:
                    
                    alarms_csv_path = os.path.join(output_path_day, f"{device}_alarms.csv")
                    write_header = not os.path.exists(alarms_csv_path)
                    df_alarms_1h.to_csv(alarms_csv_path,mode="a" if not write_header else "w",header=write_header,index=False)
                    logger.info(f"Saved or update alarms dataframe to {alarms_csv_path}")

                except Exception as e:
                    logger.error(f"An error occurred while saving the alarms dataframe: {e}")
                    continue

            """
            ###############
            # SONOMETER
            ###############
            elif sufix_string == "SONOMETER":
               logger.info(f"Processing SONOMETER data")
            
            
            ###############
            # SONOMETER
            ###############
            elif sufix_string == "AUDIOMOTH":
               logger.info(f"Processing AUDIOMOTH data")
            

            ###############
            # ERROR
            ###############
            else:
                logger.error(f"suffix is wrong {sufix_string}")  

            """

        except Exception as e:
            logger.error(f"An error occurred while processing folder {folder}: {e}")