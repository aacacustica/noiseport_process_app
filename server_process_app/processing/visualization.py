import sys
import argparse
import os
import sys
import re

from server_process_app.common.misc.logging_config import *
from server_process_app.common.config.config_vi import *
from server_process_app.common.utils.utils import *
from server_process_app.common.processing.processing_visualizations import *

logger = setup_logging('[Visualization]')
config = load_config()


def get_taxonomy(taxonomy_selection, urban_taxonomy_map, port_taxonomy_map):
    return port_taxonomy_map if taxonomy_selection == 'port' else urban_taxonomy_map

def collect_coeff(coeffs,device):

    for key,value in coeffs.items():
        if key ==  device:
            return value



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
    #   INITIALIZATION: CONFIG , DEVICES LIST & VALUES LOAD                    #
    # +----------------------------------------------------------------------+ #    

    # ------------------------- config ---------------------------------------- #

    audiomoth           = config['visualization']['audiomoth']
    sonometer           = config['visualization']['sonometer']
    raspberry           = config['visualization']['raspberry']

    filter_point        = config['visualization']['filter_point']
    agg_period          = config['visualization']['agg_period']
    percentiles         = config['visualization']['percentiles']
    limit_oca           = config['visualization']['limit_oca']
    taxonomy            = config['visualization']['taxonomy']
    change_date         = config['visualization']['change_date']

    coeffs_path         = config['paths']['point_coeffs']

    devices                         = config['devices']

    # ------------------------- devices ---------------------------------------- #
    devices_ids = [device['id'] for device in devices if device['enabled'] == True]
    devices_folder_paths = [os.path.join(inbox_folder,device['id']) for device in devices if device['enabled'] == True]
    
    try:   
    # ------------------------- values load --------------------------------------#    

        taxonomy = get_taxonomy(taxonomy, *taxonomy_json())
        oca_limits = resolve_oca_type(limit_oca)
        yamnet_csv = yamnet_class_map_csv()

        source_types = {
            "AUDIOMOTH": audiomoth,
            "SONOMETRO": sonometer,
            "RASPBERRY": raspberry,
        }

        point_to_process = filter_point

        with open(coeffs_path,'r') as f:
            coeffs = json.load(f)

        for device_folder_path in devices_folder_paths:

            device_name = os.path.basename(device_folder_path)
            folders, _, date_map, thresh_map = collect_folders(device_folder_path, change_date, device_folder_path,logger,point_to_process)
            
            device_coeff = collect_coeff(coeffs,device_name) 
            
            process_all_folders(
                device_folder_path,
                folders,
                agg_period,
                percentiles,
                taxonomy,
                yamnet_csv,
                device_name,
                device_coeff,
                date_map,
                thresh_map,
                oca_limits,
                limit_oca,
                device_folder_path,
                logger
            )

            logger.info(f"Processing received data from : {device_name}")

        logger.info("Finished all processing.")

    except Exception as e:
        logger.error(f"Error during executing the main program: {e}")


if __name__ == "__main__":
    main()
