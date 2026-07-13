import sys

import argparse
import os
import re

 


from server_process_app.common.utils.utils import *
from server_process_app.common.utils.utils_vi import *
from server_process_app.common.processing.processing_alarms import *
from server_process_app.common.misc.logging_config import *
from server_process_app.common.config.config_vi import *


config = load_config()
logger = setup_logging("Alarms")


def collect_folders_server(devices,merged_folder):
    folders = []

    for device in devices:
        subfolders_device = os.listdir(device)
        for f in os.listdir(device): 
            if merged_folder in f:
                folders.append(os.path.join(device,f))

    return folders


def resolve_oca_type(oca_type):
    oca_map = {
        'OCA_RESIDENTIAL': OCA_RESIDENTIAL,
        'OCA_LEISURE': OCA_LEISURE,
        'OCA_OFFICE': OCA_OFFICE,
        'OCA_INDUSTRIAL': OCA_INDUSTRIAL,
        'OCA_CULTURE': OCA_CULTURE,
    }
    if oca_type not in oca_map:
        raise ValueError(f"Invalid OCA type: {oca_type}")
    return oca_map[oca_type]


def main():

    # +----------------------------------------------------------------------+ #
    #   INITIALIZATION: CONFIG , DEVICES LIST & FULL FOLDER PATHS              #
    # +----------------------------------------------------------------------+ #

    mode                = config['alarms']['mode']
    limit_oca           = config['alarms']['oca_limit']
    agg_period          = config['alarms']['agg_period']
    percentiles         = config['alarms']['percentiles']
    devices             = config['devices']
    merged_folder_name  = config['processing']['merged_folder']


    devices_ids                         = [device['id'] for device in devices if device['enabled'] == True]
    enabled_devices_paths               = [os.path.join(inbox_folder,device['id']) for device in devices if device['enabled'] == True]
    enabled_devices_names               = [device['id'] for device in devices if device['enabled'] == True]
    taxonomy                            = mode
    folders                             = collect_folders_server(devices,merged_folder_name)
    
    try:
        
        yamnet_csv                              = yamnet_class_map_csv()
        urban_taxonomy_map, port_taxonomy_map   = taxonomy_json()
        devices                                 = load_devices()
        oca_limits                              = resolve_oca_type(limit_oca)
        days_devices                            = collect_folders_days_devices(folders,enabled_devices_names)

        
        process_all_folders(
            folders             = folders,
            day_devices         = days_devices,
            yamnet_csv          = yamnet_csv,
            oca_limits          = oca_limits,
            logger              = logger
        )
            
    except Exception as e:
        logger.error(f"Error during alarms: {e}")


if __name__ == "__main__":
    main()
