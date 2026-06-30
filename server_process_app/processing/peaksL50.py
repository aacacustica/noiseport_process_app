import re
import os
import argparse
import logging

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from scipy.signal import find_peaks
from tqdm import tqdm

from server_process_app.common.misc.logging_config import *
from server_process_app.common.utils.utils import *
from server_process_app.common.config.settings import settings
from server_process_app.common.utils.utils_peaks import * 


logger = setup_logging('[Peaks]')
config = load_config()

def main():

    # +----------------------------------------------------------------------+ #
    #   INITIALIZATION: CONFIG , DEVICES LIST & FULL FOLDER PATHS              #
    # +----------------------------------------------------------------------+ #
    devices                         = config['devices']
    inbox_folder                    = config['paths']['inbox']


    acoustics_folder_name           = config['processing']['acoustic_folder']
    predictions_folder_name         = config['processing']['prediction_folder']
    peaks_folder_name               = config['processing']['peaks_folder']

    window_size                     = config['peaks']['window_size']
    adding_threshold                = config['peaks']['adding_threshold']
    width                           = config['peaks']['width']
    prominence                      = config['peaks']['prominence']

    devices_folder_paths = [os.path.join(inbox_folder,device['id']) for device in devices if device['enabled'] == True]
    
    for device in tqdm(devices_folder_paths, desc='Processing csv files'):

        # +------------------------------------------------------------+ #
        #   LOOP for each device:                                        #
        #        1. Get hourly queries files paths in a list             #
        #        2. LOOP for each hourly csv file                        #
        #           2.1. Peak analysis, dynamic median for LA values w=30#     
        #           2.2. Peak analysis, find peaks                       #     
        #           2.3. Peak analysis, find peak duration               #     
        #           2.4. Peak analysis, create csv                       #     
        #           2.5. Peak analysis, save csv                         #
        #                                                                #
        #   FINALLY: List peak, acoustic and prediction files            #     
        #            Merge peak,acoustic and prediction csvs             #
        # +------------------------------------------------------------+ #

        logger.info(f"Finding peaks for: {os.path.basename(device)}")
        
        
        # ------------------------- Get hourly queries files paths in a list ------------------------ #
        hourly_acoustics_folders,_,_ = list(get_hourly_folders_device(device,predictions_folder_name,peaks_folder_name,acoustics_folder_name))
        device_name = os.path.basename(device)
        
        
        # ------------------------- LOOP for each hourly csv file ------------------------ #
        for csv_file in hourly_acoustics_folders:

            df = pd.read_csv(csv_file)
            date_csv_file = extract_key_from_filename(os.path.basename(csv_file))
            output_folder = os.path.join(device,peaks_folder_name)
            
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # ------------------------- Format Timestamp column ------------------------------------- #

            df['Timestamp'] = pd.to_datetime(df['Timestamp'])

            # ------------------------- Peak analysis ------------------------------------------------ #
            try:
            
            # ------------------------- dynamic median for the LA values with a window of 30 seconds -- #
                df['LA_median'] = df['LA'].rolling(window=window_size, min_periods=1).quantile(0.5) + adding_threshold
                above_threshold = df[df['LA'] > df['LA_median']]
            
            # ------------------------- find peaks ---------------------------------------------------- #            
                if not above_threshold.empty:
                    peaks, properties   = find_peaks(above_threshold['LA'], prominence=prominence, width=width)
                    df_peaks            = above_threshold.iloc[peaks]
                    
                    logging.info(f"Detected {len(df_peaks)} peaks")

            # ------------------------- find peaks duration -------------------------------------------- #
                    start_points    = properties['left_ips'].astype(int)
                    end_points      = properties['right_ips'].astype(int)
                    durations       = end_points - start_points
                
                    
            # ------------------------- create csv -------------------------------------------------------- #
                    peak_data = []
                    for start, end in zip(start_points, end_points):
                        peak_LA_values = above_threshold['LA'].iloc[start:end+1].values
                        leq_value = leq(peak_LA_values)
                        
                        peak_data.append({
                            'filename':             above_threshold['Filename'].iloc[start],
                            'start_time':           above_threshold['Timestamp'].iloc[start],
                            'end_time':             above_threshold['Timestamp'].iloc[end],
                            'duration':             int(end - start),
                            'leq':                  round(leq_value, 1),
                            'LA_values':            peak_LA_values.tolist()
                        })

                    
            # ------------------------- save csv----------------------------------------------------------- #
                    peaks_df = pd.DataFrame(peak_data)
                    output_file_name = os.path.join(output_folder, f"peaks_detection_{device_name}_{date_csv_file}.csv") 
                    peaks_df.to_csv((output_file_name), index=False)
                    logging.info(f"Peaks saved at {output_file_name}")
                
                else:
                    
                    logging.info(f"No peaks found in {csv_file} from {device}")
                
            except Exception as e:
                logger.error(f"Error saving peak csv: {e}")
        

    try:
        # ------------------------- List peak, acoustic and prediction files---------------------------------------------------------- #
        hourly_acoustics_folders,hourly_predictions_folders,hourly_peaks_folders = list(get_hourly_folders_device(device,predictions_folder_name,peaks_folder_name,acoustics_folder_name))

        # ------------------------- Merge peak,acoustic and prediction csvs----------------------------------------------------------- #
        merge_acoustics_predictions_and_peaks(None,hourly_acoustics_folders,hourly_predictions_folders,hourly_peaks_folders,devices,logger)
    
    except Exception as e:
        logger.error(f"Error concatenating acoustics predictions and peaks: {e}")


if __name__ == "__main__":
    main()