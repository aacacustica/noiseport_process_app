import mysql.connector
import json
import os
import tqdm 
import time
import sys
import argparse

from server_process_app.common.utils.utils_queries import *
from server_process_app.common.misc.time_slop_fix import *
from server_process_app.common.misc.logging_config import *
from server_process_app.common.utils.utils import *
from server_process_app.common.processing.processing_queries import *

config = load_config()


# -----------------------------------
# CONFIG GLOBAL VARIABLES
# -----------------------------------

logger = setup_logging('[Queries]')

def arg_parser():

    parser = argparse.ArgumentParser(description='Generating acoustics/wav/predictions/sonometer queries')

    parser.add_argument('-m', '--send_mqtt', action='store_true',
                        help='To send or not the data to mqtt')
    parser.add_argument('-w', '--window', type=int, required=False, default=3600, 
                        help='Window for sonometer (1 for 1 sec, 3600 for hour)')
    parser.add_argument('-t', '--time_slop', action='store_true', 
                        help='Add a time slop fix to the process')
    parser.add_argument('-s', '--sonometer', action='store_true',
                        help='To process sonometer data')
    

    return parser.parse_args()


def acoustic_processing(folder_days,db,logger, query_acoustic_folder, processed_acoustics, processed_folder_acoustic_txt,header,device):
    
    start_time = time.time()                 
    process_acoustic_folder(db,logger,folder_days, query_acoustic_folder, processed_acoustics, processed_folder_acoustic_txt,header,device)                   
    end_time =  round(time.time() - start_time,2)
    return end_time


def prediction_processing(folder_days,db,logger, query_pred_folder, processed_predictions, processed_folder_predictions_txt,device):
    
    start_time = time.time()
    process_pred_folder(db,logger,folder_days,query_pred_folder, processed_predictions, processed_folder_predictions_txt,device)                 
    end_time =  round(time.time() - start_time,2)
    return end_time




def main():
    
    # +----------------------------------------------------------------------+ #
    #   INITIALIZATION: CONFIG , DATABASE , DEVICES LIST & FULL FOLDER PATHS   #
    # +----------------------------------------------------------------------+ #



    # ------------------------- config ---------------------------------------- #

    db_host                         = config['mysql']['host']
    db_user                         = config['mysql']['user']
    db_password                     = config['mysql']['password']
    db_name                         = config['mysql']['database']
    db_local_infile                 = config['mysql']['local_infile']
    db_local_infile_path            = config['paths']['inbox']
    db_init_value                   = config['mysql']['active_switch']

    devices                         = config['devices']

    acoustic_query_switch           = config['queries']['acoustic_query']
    prediction_query_switch         = config['queries']['prediction_query']
    sonometer_query_switch          = config['queries']['sonometer_query']
    wav_query_switch                = config['queries']['wav_query']
    acoustic_table_name             = config['queries']['acoustic_table_name']
    prediction_table_name           = config['queries']['predictions_table_name']
    sonometer_table_name            = config['queries']['sonometer_table_name']
    wav_table_name                  = config['queries']['wav_table_name']
    time_slop_apply                 = config['queries']['time_slop_fix']
    send_mqtt                       = config['queries']['send_mqtt']

    inbox_folder                    = config['paths']['inbox']

    acoustics_folder_name           = config['processing']['acoustic_folder']
    predictions_folder_name         = config['processing']['prediction_folder']
    
    # ------------------------- devices ---------------------------------------- #

    devices_ids = [device['id'] for device in devices if device['enabled'] == True]
    devices_folder_paths = [os.path.join(inbox_folder,device['id']) for device in devices if device['enabled'] == True]

    # ------------------------- database ---------------------------------------- #
    
    db = mysql.connector.connect(
        host                            = db_host,
        user                            = db_user,
        password                        = db_password,
        database                        = db_name,
        allow_local_infile              = db_local_infile,
        allow_local_infile_in_path      = db_local_infile_path,
    )
    
    if db_init_value: initialize_database(db, logger)
    
    
    # ------------------------- folders ---------------------------------------- #

    acoustic_folders                    = load_folders(devices_folder_paths,acoustics_folder_name)
    prediction_folders                  = load_folders(devices_folder_paths,predictions_folder_name)

    


    logger.info(f"[Queries] Devices to query: {devices}")
    logger.info(f"[Queries] Info located in {acoustic_folders} , {prediction_folders}")

    

    for device in tqdm.tqdm(devices_ids, desc="Processing devices", unit="device"):
        
        # +------------------------------------------------------------+ #
        #   LOOP for each device:                                        #
        #        1. List folders,create queries folders,intialize .txts  #
        #        2. List files                                           #
        #        3. Apply time slop fix to filtered files                #
        #        4. Re-list files with the fixed version                 #
        #        5. Make queries!                                        #
        #        6. Save all_info to JSON                                #
        #        7. Add processed folder to all_info                     #
        #        8. Close DB                                             #
        # +------------------------------------------------------------+ #
        try:
            logger.info(f"Processing queries for : {device}")

            # ------------------------- list folders ------------------------ #

            device_folder_path              = os.path.join(inbox_folder,device)
            acoustic_folder_device          = [f for f in acoustic_folders if device in f.split('/')]
            prediction_folder_device        = [f for f in prediction_folders if device in f.split('/')]
            
            # ------------------------- create queries folders --------------- #
            (
                
                query_acoustic_folder,
                query_pred_folder,

            ) = create_query_folders_server(device_folder_path,logger)

            # ------------------------- initialize .txts --------------------- #
            (   
                processed_folder_acoustic_txt_path,
                processed_folder_predictions_txt_path,
                processed_mqtt_data_txt_path,
                processed_acoustics_list,
                processed_predictions_list,
                processed_mqtt_list

            )  = initialize_process_files_server(query_acoustic_folder,query_pred_folder,logger)

            logger.info(f"Saving the processed list of predictions files txt here   -->             {processed_folder_predictions_txt_path}" )
            logger.info(f"Saving the processed list of acoustics files txt here     -->             {processed_folder_acoustic_txt_path}"    )

            # ------------------------- list files ----------------------------- #
            (
                acoustics_params_folder_path,
                predictions_litle_folder_path,
                days_folders_acoustics,
                days_folders_predictions,

            ) =  get_sonometer_rasp_acoustics_preds_days_and_paths_server_version(logger,device) 

            # ------------------------- Apply time slops ------------------------- #
            if time_slop_apply:  time_slop_fix(device,acoustics_params_folder_path,predictions_litle_folder_path,logger)
                
            # ------------------------- Re-list files ----------------------------- #
            (
                acoustics_params_folder_path,
                predictions_litle_folder_path,
                days_folders_acoustics,
                days_folders_predictions,
                
            ) =  get_sonometer_rasp_acoustics_preds_days_and_paths_server_version(logger,device) 
                
            # ------------------------- Make queries ----------------------------- #
                
            if acoustic_query_switch:
                    if 'ccmp' in device:
                        HEADER = config['mysql']['headers']
                        header = HEADER['THIRD_OCTAVES_SENSOR_FORMAT']
                    else:
                        HEADER = config['mysql']['headers']
                        header = HEADER['THIRD_OCTAVES_SENSOR_FORMAT']
                        
                    acoustic_processing(days_folders_acoustics,db,logger,query_acoustic_folder,processed_acoustics_list,processed_folder_acoustic_txt_path,header,device)    
                    if send_mqtt:
                        power_avg_results = power_laeq_avg(db,logger,device,acoustic_table_name)
                        send_mqtt_data(power_avg_results,logger,processed_mqtt_data_txt_path)              
                    
            if prediction_query_switch: prediction_processing(days_folders_predictions,db,logger,query_pred_folder,processed_predictions_list,processed_folder_acoustic_txt_path,device)
            if sonometer_query_switch: None
            if wav_query_switch: None

           
       
        except Exception as e:
            logger.info(f"Error processing:{device} , {e}")

        
    # ------------------------- Add processed folder to all_info ----------- #
    """
    for device in devices:

        if not device['enabled']: continue
        
        logger.info("")
        logger.info("Saving all_info to JSON")
        logger.info("all_info: %s", all_info)
        json.dump(all_info, sys.stdout, indent=4, default=decimal_to_native)

        query_acoustic_folder = os.path.join(device['id'],acoustics_folder_name) 
        all_info_path = os.path.join(query_acoustic_folder, f"{device['id']}_all.json")
        
        with open(all_info_path, "a+") as f:
            json.dump(all_info, f, indent=4, default=decimal_to_native)
        
        logger.info("Saved all_info to: %s", all_info_path)
        
    """
    # ------------------------- Close DB ------------------------------------- #
    

    logger.info("")
    db.close()
    logger.info("Database connection closed")



if __name__ == "__main__":
    main()