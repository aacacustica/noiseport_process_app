import sys

import argparse
import os
import re

 


from server_process_app.common.utils.utils import *
from server_process_app.common.utils.utils_vi import *
from server_process_app.common.processing.processing_alarms import *
from server_process_app.common.misc.logging_config import *
from server_process_app.common.config.config_vi import *


def collect_folders(input_folder,label_source_type, logger,point_filter=None):
    folders = []

    if label_source_type == "raspberry":
        logger.info("Searching for RASPBERRY merged folders")
        for root, dirs, _ in os.walk(input_folder):
            if point_filter is not None:
                parts = root.split(os.sep)
                if point_filter not in root:
                    continue

            if config_vi.MERGED_FOLDER in dirs:
                path = os.path.join(root, config_vi.MERGED_FOLDER)
                folders.append(path)
                logger.info(f"Found raspberry merged folder: {path}")

    elif label_source_type == "audiomoth":
        logger.info("Searching for AUDIOMOTH folders")
        for root, dirs, _ in os.walk(input_folder):
            if point_filter is not None:
                parts = root.split(os.sep)
                if point_filter not in parts:
                    continue

            if "AUDIOMOTH" in dirs:
                path = os.path.join(root, "AUDIOMOTH")
                folders.append(path)
                logger.info(f"Found audiomoth folder: {path}")

    elif label_source_type == "sonometro":
        logger.info("Searching for SONOMETER folders")
        for root, dirs, _ in os.walk(input_folder):
            if point_filter is not None:
                parts = root.split(os.sep)
                if point_filter not in parts:
                    continue

            if "SONOMETER" in dirs:
                path = os.path.join(root, "SONOMETER")
                folders.append(path)
                logger.info(f"Found sonometer folder: {path}")

    return folders

def collect_folders_server(devices):
    folders = []

    for device in devices:
        subfolders_device = os.listdir(device)
        for f in os.listdir(device): 
            if MERGED_FOLDER in f:
                folders.append(os.path.join(device,f))

    return folders

def collect_folders_server_device(folders,device):
    folders = []

    for folder in folders:
        None

    return None

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


def collect_folders_days_devices(folders, devices):
    dict_days = {device: [] for device in devices}
    for device in devices:
        for folder in folders:
            if os.path.basename(os.path.dirname(folder)) == os.path.basename(device):
                dict_days[device].append(folder)
    return dict_days


def main():
    """
    execution
        python3 -m 06_alarms_processing.main -f "\192.168.205.120\Contenedores\5-Resultados\" --raspbery --port (--point P5_TEST)
    """
    try:
        logger = setup_logging("Alarms")
        args = arg_parser()
        logger.info(f"Starting alarm processing!!")
        yamnet_csv = yamnet_class_map_csv()
        urban_taxonomy_map, port_taxonomy_map = taxonomy_json()
        taxonomy = "port" if args.port else "urban"

        devices = load_devices()
        oca_limits = resolve_oca_type(args.limit_oca)

        #input_folder = args.path_general
        
        """
        source_types = {
            "AUDIOMOTH": args.audiomoth,
            "SONOMETRO": args.sonometer,
            "RASPBERRY": args.raspbery,
        }
        """





        ############################
        #folders = collect_folders(input_folder, label_source_type,logger,point_filter=args.point)
        folders = collect_folders_server(devices)
        days_devices = collect_folders_days_devices(folders,devices)
        logger.info(f"Taxonomy: {taxonomy}")
        #logger.info(f"Input folder: {input_folder}")


        logger.info("Entering the process all folder function")
        
        process_all_folders(
            folders,
            args.agg_period,
            args.percentiles,
            taxonomy,
            yamnet_csv,
            "",
            oca_limits,
            args.limit_oca,
            logger)

        logger.info("Finished all processing.")

    except Exception as e:
        logger.error(f"Error during executing the main program: {e}")


if __name__ == "__main__":
    main()
