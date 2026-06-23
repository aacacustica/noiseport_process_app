import mysql.connector
import json
import os
import tqdm 
import time
import sys
import argparse

from server_process_app.common.utils_queries import *
from server_process_app.common.time_slop_fix import *
from server_process_app.common.logging_config import *
from server_process_app.common.utils import *
from server_process_app.common.processing_queries import *
from server_process_app.common.settings import settings

PATH = settings.paths.measurements
ISDIR = os.path.isdir(PATH)

config = load_config()

logger = setup_logging('query_automatize')

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


def acoustic_processing(folder_days,db,logger, all_info, query_acoustic_folder, processed_acoustics, processed_folder_acoustic_txt,device):
    
    start_time = time.time()                 
    process_acoustic_folder(db,logger,folder_days, all_info, query_acoustic_folder, processed_acoustics, processed_folder_acoustic_txt,device)                   
    end_time =  round(time.time() - start_time,2)
    return end_time


def prediction_processing(folder_days,db,logger, all_info, query_pred_folder, processed_predictions, processed_folder_predictions_txt,device):
    
    start_time = time.time()
    process_pred_folder(db,logger,folder_days, all_info, query_pred_folder, processed_predictions, processed_folder_predictions_txt,device)                 
    end_time =  round(time.time() - start_time,2)
    return end_time




def main():
    
    # ------------------------------------
    # INITIALIZATION
    # ------------------------------------
    
    args = arg_parser()
    
    sonometer_window    = args.window
    time_slop           = args.time_slop
    send_mqtt           = args.send_mqtt
    process_sonometer   = args.sonometer
    
    db = mysql.connector.connect(
        host=settings.mysql.host,
        user=settings.mysql.user,
        password=settings.mysql.password,
        database=settings.mysql.database,
        allow_local_infile=True,
        allow_local_infile_in_path=settings.paths.inbox,
    )
    
    if DB_INIT_SWITCH: initialize_database(db, logger)
    
    logger.info("[Queries] Initializing database!")
    
    logger.info("[Queries] Starting!!")
     
    if ISDIR:
        logger.info(f"PATH exists --> {PATH}")
    else:
        raise ValueError(f'PATH ({PATH}) doesnt exist.')
    
    
    

    all_info = []

    # ---------------------------
    # 1. LOAD DEVICE NAMES AND FULL FOLDER PATHS
    # ---------------------------

    devices                                     = load_devices(DEVICES_TXT,logger)
    acoustic_folders,prediction_folders         = load_folders(devices)

    logger.info(f"[Queries] Devices to query: {devices}")
    logger.info(f"[Queries] Info located in {acoustic_folders} , {prediction_folders}")

    for device in tqdm.tqdm(devices, desc="Processing devices", unit="device"):
        
        try:
            print("Processing: ", device)
            device_folder_path = device
            
            if os.path.isdir(device):
                device = os.path.basename(device)
            else:
                raise ValueError(f"Device path is not a folder: {device}")
            logger.info(f"Processing queries for : {device}")
            # ---------------------------
            # 2. LIST ACOUSTIC AND PREDICTION FOLDERS FOR A SPECIFIC DEVICE
            # ---------------------------

            acoustic_folder_device = [f for f in acoustic_folders if device in f.split('\\')]
            prediction_folder_device = [f for f in prediction_folders if device in f.split('\\')]
            
            # ---------------------------
            # 3. CREATE QUERIES FOLDERS FOR EACH SPECIFIC DEVICE
            # ---------------------------
        
            (
                query_acoustic_folder,
                query_pred_folder,

            ) = create_query_folders_server(device_folder_path,logger)

            # ---------------------------
            # INITIALIZING PROCESSING FILES
            # ---------------------------
            
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

        except Exception as e:
            logger.error(f"Error setting up folders: {e}")
            continue



        try:

            # ------------------------------------
            #   Filter the FILES, JUST THE FOLDERS
            # ------------------------------------


            (
                acoustics_params_folder_path,
                predictions_litle_folder_path,
                days_folders_acoustics,
                days_folders_predictions,

            ) =  get_sonometer_rasp_acoustics_preds_days_and_paths_server_version(logger,device) 
            #No queremos aún el resto de rutas porque recoge los archivos fixed y aun no se han generado
        except Exception as e:
            logger.error(f"Error listing folder days: {e}")
            continue



        try:

            # --------------------------------------------------
            #   FIX OF THE EXTRA SECONDS IN MINUTE PROBLEM     
            # --------------------------------------------------
            
            if time_slop: 
                time_slop_fix(device,acoustics_params_folder_path,predictions_litle_folder_path,logger)
            #Recall to this function as now it gives us the updated folder with the time slop fix for day records

            (
                acoustics_params_folder_path,
                predictions_litle_folder_path,
                days_folders_acoustics,
                days_folders_predictions,
                
            ) =  get_sonometer_rasp_acoustics_preds_days_and_paths_server_version(logger,device) 
            
        except Exception as e:

            logger.error(f"Error while applying the time slop fix to csv records: {e}")
            continue

            # -.--------------------
            # PROCESSING
            # ----------------------
        
        try:

            whole_start_time = time.time()
                
            if ACOUSTIC_QUERY_SWITCH:

                logger.info("[Acoustics] Quering")
                try:
                    logger.info(f"[Acoustics] days_folder_acoustics : {days_folders_acoustics}")
                    end_time = acoustic_processing(
                                                    folder_days=                        days_folders_acoustics,
                                                    db=                                 db,
                                                    logger=                             logger,
                                                    all_info=                           all_info,
                                                    query_acoustic_folder=              query_acoustic_folder,
                                                    processed_acoustics=                processed_acoustics_list,
                                                    processed_folder_acoustic_txt=      processed_folder_acoustic_txt_path,
                                                    device=                             device)
                    
                    
                    if send_mqtt:
                        power_avg_results = power_laeq_avg(db,logger,device,table_name=ACOUSTIC_TABLE_NAME) 
                        send_mqtt_data(power_avg_results,logger,processed_mqtt_data_txt_path)
                    logger.info(f"[Acoustics] Finished quering")
                    print("[Acoustics] --- %s seconds in execution ---" %end_time)
                except Exception as e:
                    logger.exception(f"Error quering acoustics")                      
            print("Quering device: ",device)
            print("Days folders predictions:",  days_folders_predictions)
            print("Days folders acoustics: ",   days_folders_acoustics)
            print("Query pred folder: ",query_pred_folder)
            print("Query acoust folder: ",query_acoustic_folder)
            if PREDICT_QUERY_SWITCH:
                
                logger.info("[Preditions] Quering")
                try:
                    end_time = prediction_processing(
                                                    folder_days =                       days_folders_predictions,
                                                    db =                                db,
                                                    logger =                            logger,
                                                    all_info =                          all_info,
                                                    query_pred_folder=                  query_pred_folder,
                                                    processed_predictions=              processed_predictions_list,
                                                    processed_folder_predictions_txt=   processed_folder_predictions_txt_path,
                                                    device=                             device)
                    
                    logger.info(f"[Predictions] Finished quering")
                    print("[Predictions] --- %s seconds in execution ---" %end_time)  
                except:
                    logger.exception(f"Error quering predictions")
            
            print(  "\n"
                    "\n"
                    " --- %s seconds in total execution ---" "\n"
                        % round(time.time() - whole_start_time,2))
    
        except Exception as e:
            logger.exception(f"Error while processing folders")
        
        


    # ------------------------------------
    #   Save all_info to json
    # ------------------------------------
    



    # ------------------------------------
    #   Adding the folder processed to the all_info
    # ------------------------------------
    for device in devices:

        logger.info("")
        logger.info("Saving all_info to JSON")
        logger.info("all_info: %s", all_info)
        json.dump(all_info, sys.stdout, indent=4, default=decimal_to_native)

        query_acoustic_folder = os.path.join(device,ACOUSTICS_FOLDER_NAME) 
        all_info_path = os.path.join(query_acoustic_folder, f"{device}_all.json")
        
        with open(all_info_path, "w") as f:
            json.dump(all_info, f, indent=4, default=decimal_to_native)
        
        logger.info("Saved all_info to: %s", all_info_path)
        

    # ------------------------------------
    #   Closing DB
    # ------------------------------------
    
    try:
        logger.info("")
        db.close()
        logger.info("Database connection closed")
    except mysql.connector.Error as err:
        logger.error("Error closing database connection: %s", err)


if __name__ == "__main__":
    main()