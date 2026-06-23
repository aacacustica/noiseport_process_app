import sys
sys.path.insert(0, "/home/aac/I+D/CODIGOS/NoisePort_server/")
import argparse
import os
from logging_config import setup_logging
from config_vi import *
from utils import *
import config_vi
import sys

sys.path.insert(0, "/home/aac/I+D/CODIGOS/NoisePort_server/06_visualization")
from processing import *
import re


COEFFS_PATH = "/home/aac/I+D/CODIGOS/NoisePort_server/point_coeffs.json"

ID_MICRO, LOCATION_RECORD, LOCATION_PLACE, LOCATION_POINT, \
AUDIO_SAMPLE_RATE, AUDIO_WINDOW_SIZE, AUDIO_CALIBRATION_CONSTANT,\
STORAGE_S3_BUCKET_NAME, STORAGE_OUTPUT_WAV_FOLDER, \
STORAGE_OUTPUT_ACOUSTIC_FOLDER,DEVICES_FOLDER,INBOX_FOLDER, \
ACOUSTIC_QUERIES_FOLDER_NAME, PREDICTION_QUERIES_FOLDER_NAME = load_config_acoustic('config.yaml')

def arg_parser():
    parser = argparse.ArgumentParser(description='Plotting AudioMoth data')
    parser.add_argument('-f', '--path_general', type=str, required=True, 
                        help='Path to sonometers folder')
    parser.add_argument('-o', '--output-dir', type=str, required=False, 
                        help='Output directory, if not provided, the output directory is the same as the input directory') 
    parser.add_argument('-a', '--agg_period', type=int, required=False, default=900, 
                        help='Aggregation period in seconds')
    parser.add_argument('-p', '--percentiles', type=float, nargs='+', required=False, default=[90, 10],
                        help='Percentiles to plot [1 5 10 50 90] (L90 and L10 as default)')
    parser.add_argument('-l', '--limit_oca', type=str, required=False, default='OCA_RESIDENTIAL',
                        help='Limit OCA to plot [OCA_RESIDENTIAL, OCA_LEISURE, OCA_OFFICE, OCA_INDUSTRIAL, OCA_CULTURE]')
    parser.add_argument('--filterpoint', type=str, required=True,default='P5_TEST',
                        help='Sets the point to process')
    parser.add_argument('--audiomoth', action='store_true', 
                        help='Process audiomoth data')
    parser.add_argument('--sonometer', action='store_true', 
                        help='Process sonometer data'),
    parser.add_argument('--raspbery', action='store_true',
                        help='Process Raspberry Pi like TCT Tenerife'),
    #urban or port taxonomy
    parser.add_argument('--urban', action='store_true', 
                        help='Urban taxonomy')
    parser.add_argument('--port', action='store_true', 
                        help='Port taxonomy')
    # ask the user to change the date/time
    parser.add_argument('--change-date', action='store_true',
                        help='Change the date and the time of the csv file')

    return parser.parse_args()



def get_taxonomy(args, urban_taxonomy_map, port_taxonomy_map):
    return port_taxonomy_map if args.port else urban_taxonomy_map



def ask_date_time_changes():
    def ask(prompt, pattern):
        ans = input(prompt).lower()
        while ans not in ['y', 'n']:
            ans = input(prompt).lower()
        if ans == 'y':
            val = input("Enter value: ")
            while not re.match(pattern, val):
                val = input("Enter value: ")
            return val
        return None

    return (
        ask("Change date? (y/n): ", r"\d{4}-\d{2}-\d{2}"),
        ask("Change time? (y/n): ", r"([01]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"),
        ask("Set threshold date? (y/n): ", r"\d{4}-\d{2}-\d{2}"),
        ask("Set threshold time? (y/n): ", r"([01]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]")
    )
    

def collect_coeff(coeffs,device):

    for key,value in coeffs.items():
        if key ==  device:
            return value


def collect_folders(input_folder, change_time_flag,label_source_type, logger,point_filter):
    folders, coefficients, date_time, threshold = [], {}, {}, {}
    
    #Lectura de los coeficientes desde un JSON para no tener que escribirlos por consola
    with open(COEFFS_PATH,'r') as f:
        coeffs = json.load(f)

    if "raspberry" in label_source_type:
        logger.info("Searching for RASPBERRY")
        for root, dirs, _ in os.walk(input_folder):
            if point_filter is not None:
                if point_filter not in root:
                    continue
            if 'acoustics' in dirs:
                path = os.path.join(root,ACOUSTIC_PARAMS_FOLDER)
                if point_filter is not None:
                    coefficients[path] = coeffs[point_filter]
                else:
                    coefficients[path] = coeffs[root.split("/")[-1]]
                folder_name = path.split("/")[-3]
                #coeff = float(input(f"Correction coefficient for {folder_name}: "))
                new_date = new_time = t_date = t_time = None

                if change_time_flag:
                    new_date, new_time, t_date, t_time = ask_date_time_changes()

                folders.append(path)
                #coefficients[path] = coeff
                date_time[path] = (new_date, new_time)
                threshold[path] = (t_date, t_time)


    if label_source_type == "audiomoth":
        logger.info("Searching for RASPBERRY")
        for root, dirs, _ in os.walk(input_folder):
            if point_filter is not None:
                if point_filter not in root:
                    continue

            if "AUDIOMOTH" in dirs:
                path = os.path.join(root, "AUDIOMOTH")
                if point_filter is not None:
                    coefficients[path] = coeffs[point_filter]
                else:
                    coefficients[path] = coeffs[root.split("/")[-1]]
                folder_name = path.split("\\")[-2]
                #coeff = float(input(f"Correction coefficient for {folder_name}: "))
                new_date = new_time = t_date = t_time = None

                if change_time_flag:
                    new_date, new_time, t_date, t_time = ask_date_time_changes()

                folders.append(path)
                #coefficients[path] = coeff
                date_time[path] = (new_date, new_time)
                threshold[path] = (t_date, t_time)


    if label_source_type == "sonometer":
        logger.info("Searching for RASPBERRY")
        for root, dirs, _ in os.walk(input_folder):
            if point_filter is not None:
                if point_filter not in root:
                    continue 
            if "SONOMETER" in dirs:
                path = os.path.join(root, "SONOMETER")
                if point_filter is not None:
                    coefficients[path] = coeffs[point_filter]
                else:
                    coefficients[path] = coeffs[root.split("/")[-1]]
                folder_name = path.split("\\")[-2]
                #coeff = float(input(f"Correction coefficient for {folder_name}: "))
                new_date = new_time = t_date = t_time = None

                if change_time_flag:
                    new_date, new_time, t_date, t_time = ask_date_time_changes()

                folders.append(path)
                #coefficients[path] = coeff
                date_time[path] = (new_date, new_time)
                threshold[path] = (t_date, t_time)

    return folders, coefficients, date_time, threshold



def resolve_oca_type(oca_type):
    oca_map = {
        'OCA_RESIDENTIAL': config_vi.OCA_RESIDENTIAL,
        'OCA_LEISURE': config_vi.OCA_LEISURE,
        'OCA_OFFICE': config_vi.OCA_OFFICE,
        'OCA_INDUSTRIAL': config_vi.OCA_INDUSTRIAL,
        'OCA_CULTURE': config_vi.OCA_CULTURE,
    }
    if oca_type not in oca_map:
        raise ValueError(f"Invalid OCA type: {oca_type}")
    return oca_map[oca_type]

def load_devices(devices_folder,logger):
    """
    devices_folder: str, path to the txt file that contains the names of the devices to process, one per line.


    returns: list of str, full paths to the devices folders to process.
    """
    devices = []

    with open(devices_folder, 'r') as f:
        for line in f:
            device = line.strip()
            devices.append(os.path.join(INBOX_FOLDER, device))

    return devices



def main():
    logger = setup_logging('visualization')

    try:
        
        args = arg_parser()
        devices = load_devices(DEVICES_FOLDER,logger)
        
        taxonomy = get_taxonomy(args, *taxonomy_json())
        oca_limits = resolve_oca_type(args.limit_oca)
        yamnet_csv = yamnet_class_map_csv()
        input_folder = args.path_general

        source_types = {
            "AUDIOMOTH": args.audiomoth,
            "SONOMETRO": args.sonometer,
            "RASPBERRY": args.raspbery,
        }

        point_to_process = args.filterpoint

        
          
        """
        for label, active in source_types.items():
            logger.info(f"Active: {active}")
            logger.info(f"Trying to get label: {label}")
            if not active:
                continue
            label_source_type =label.lower()
            logger.info(f"Processing {label_source_type} data")
            # exit()

            ############################
            folders, coeffs, date_map, thresh_map = collect_folders(input_folder, args.change_date, label_source_type,logger,point_to_process)

            logger.info(f"Using percentiles {args.percentiles}")
            logger.info(f"Aggregation period {args.agg_period}")
            logger.info(f"Input folder: {input_folder}")


            logger.info("Entering the process all folder function")
            
            process_all_folders(
                input_folder,
                folders,
                args.agg_period,
                args.percentiles,
                taxonomy,
                yamnet_csv,
                label_source_type,
                coeffs,
                date_map,
                thresh_map,
                oca_limits,
                args.limit_oca,
                logger
            )
        """
        with open(COEFFS_PATH,'r') as f:
            coeffs = json.load(f)

        for device in devices:

            folders, _, date_map, thresh_map = collect_folders(input_folder, args.change_date, device,logger,point_to_process)
            
            device_coeff = collect_coeff(coeffs,device) 
            
            process_all_folders(
                input_folder,
                folders,
                args.agg_period,
                args.percentiles,
                taxonomy,
                yamnet_csv,
                os.path.basename(device),
                device_coeff,
                date_map,
                thresh_map,
                oca_limits,
                args.limit_oca,
                device,
                logger
            )

            logger.info(f"Processing received data from : {device}")

        logger.info("Finished all processing.")

    except Exception as e:
        logger.error(f"Error during executing the main program: {e}")


if __name__ == "__main__":
    main()
