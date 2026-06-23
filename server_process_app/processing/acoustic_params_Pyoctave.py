import os
import pandas as pd
import datetime
import time
import numpy as np
import pandas as pd
import argparse
import time
from tqdm import tqdm
import json


import soundfile as sf
from pyfilterbank.splweighting import a_weighting_coeffs_design, c_weighting_coeffs_design
from utils import *
from config import *
from scipy.signal import lfilter

from logging_config import setup_logging
from PyOctaveBand import *


def twenty_db_fix(levels):
    levels_fix = []
    """"
    for row in levels:
        row_fix = []
        for octave_level in row:
            row_fix.append(octave_level + 20)
        levels_fix.append(row_fix)
    """
    for level in levels:
        levels_fix.append(level + 20)

    return levels_fix

class LeqLevelOct:
    def __init__(self, id_micro, fs, calibration_constant, window_size, audio_path, wav_files, acoustic_params, s3_bucket_name, upload_s3, logging):
        """
        Set up the LeqLevelOct object with the necessary parameters
        :param fs:
            Sample rate of the audio
        :param calibration_constant:
            Calibration constant for the microphone
        :param window_size:
            Size of the window for calculating SPL levels
        :param audio_path:
            Path to the audio files
        """
        
        
        self.id_micro = id_micro
        self.fs = fs
        self.C = calibration_constant
        self.window_size = window_size
        self.audio_path = audio_path
        self.acoustic_params = acoustic_params
        self.wav_files = wav_files
        self.s3_bucket_name = s3_bucket_name
        self.upload_s3 = upload_s3
        
        # A and C weighting filters
        self.bA, self.aA = a_weighting_coeffs_design(fs)
        self.bC, self.aC = c_weighting_coeffs_design(fs)
        
        #logging
        self.logging = logging
        logging.info("Initializing LeqLevelOct")
        logging.info(f"with fs={fs}, C={calibration_constant}, window_size={window_size}, audio_path={audio_path}, wav_files={wav_files}, acoustic_params={acoustic_params}")
    
    

    def get_oct_levels(self, frame):
        """
        Calculate 1/3-octave levels for a frame of audio data.
        Returns a list of 1/3-octave levels.
        """
        
        
        y_oct, _ = self.third_oct.filter(frame)
        oct_level_temp = [get_db_level(y_band, self.C) for y_band in y_oct.T]
        return oct_level_temp

    
    def process_audio_files(self, path):
        """
        Process each WAV file in audio_files, compute SPL metrics,
        and write a CSV per file with frame-by-frame data.
        
        :param audio_files: List of .wav filenames in self.audio_path
        :return: all_data, a list of lists (one sub-list per file).
        """
        
        
        
        # ---------------------------
        # INIZIALATIN PROCESSING FILE
        # ---------------------------
        processed_files_txt = os.path.join(path, "processed_acoustic.txt")
        processed_files_txt = processed_files_txt.replace("wav_files", "acoustic_params")
        os.makedirs(os.path.dirname(processed_files_txt), exist_ok=True)
        self.logging.info(f"Saving the processed file txt here --> {processed_files_txt}")
        
        
        processed_files = load_processed_files(processed_files_txt)


        # ----------------------------------
        # COLLECTING AUDIO FILES TO PROCESS
        # ----------------------------------
        self.logging.info("")
        full_paths= []
        wav_folder_strs= []
        diff_list= []


        try:
            # get all sub-folders in 'path'
            wav_folders = [os.path.join(path, f)for f in os.listdir(path) if os.path.isdir(os.path.join(path, f)) ]
            len_folders = len(wav_folders)
            self.logging.info(f"Found {len_folders} folders in {path}")
            
            
            self.logging.info("")
            for wav_folder in wav_folders:
                self.logging.info(f"Processing folder: {wav_folder}")
                wav_folder_strs.append(os.path.basename(wav_folder))

                #The processed files filter is applied here
                wav_files = [f for f in os.listdir(wav_folder)if f.lower().endswith('.wav')]
                full_paths.extend(os.path.join(wav_folder, f) for f in wav_files if os.path.join(wav_folder, f) not in processed_files)

                found = len(full_paths)
                if found == 60:
                    self.logging.info(f"Found {found} audio files. Folder complete.")
                else:
                    missing = 60 - found
                    self.logging.info(f"Found {found} audio files. "
                        f"Missing {missing} files.")

                    diff_list.append({
                        "folder": wav_folder,
                        "files_missing": missing
                    })


        except Exception as e:
            self.logging.error(f"Error getting the audio files: {e}")



        # ----------------------------------
        expect_wav_files = len_folders * 60
        total_audio_files = len(full_paths)
        total_missing = expect_wav_files - total_audio_files


        #convert into to hours, minutes and seconds, 60x60 3600
        # 1 audio files = 60 seconds
        # 1 folder = 60 audio files
        # 1 folder = 60 minutes
        # 1 folder = 1 hour
        total_audio_files_in_hours = total_audio_files / 3600
        total_audio_files_in_minutes = total_audio_files / 60
        total_audio_files_in_seconds = total_audio_files

        #missing files
        total_missing_in_hours = total_missing / 3600
        total_missing_in_minutes = total_missing / 60
        total_missing_in_seconds = total_missing


        self.logging.info("")
        self.logging.info(f"Expecting {expect_wav_files} wav files in total")
        self.logging.info(f"There are {total_audio_files} total audio files to process")
        self.logging.info(f"Missing {total_missing} wav files")
        self.logging.info("")


        self.logging.info(f"Total audio files in hours: {total_audio_files_in_hours:.2f} hours")
        self.logging.info(f"Total audio files in minutes: {total_audio_files_in_minutes:.2f} minutes")
        self.logging.info(f"Total audio files in seconds: {total_audio_files_in_seconds:.2f} seconds")
        self.logging.info("")


        self.logging.info(f"Total missing files in hours: {total_missing_in_hours:.2f} hours")
        self.logging.info(f"Total missing files in minutes: {total_missing_in_minutes:.2f} minutes")
        self.logging.info(f"Total missing files in seconds: {total_missing_in_seconds:.2f} seconds")
        self.logging.info("")


        # ----------------------------------
        # saving the missing files information to the previous json file
        # ----------------------------------
        
        report = {
            "expected_wav_files": expect_wav_files,
            "total_audio_files": total_audio_files,
            "total_missing_files": total_missing,

            "total_audio_duration": {
                "hours": total_audio_files_in_hours,
                "minutes": total_audio_files_in_minutes,
                "seconds": total_audio_files_in_seconds
            },
            "missing_audio_duration": {
                "hours": total_missing_in_hours,
                "minutes": total_missing_in_minutes,
                "seconds": total_missing_in_seconds
            },
            "folders_with_missing": diff_list
        }

        out_path = os.path.join(path, "wav_folder_report.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        self.logging.info(f"Saved full report to {out_path}")


        # ----------------------------------
        # HEADERS
        # ----------------------------------
        col_names = ['id_micro', 'Filename', 'Timestamp', 'Unixtimestamp', 'LA', 'LC', 'LZ', 'LAmax', 'LAmin']
        freq_labels = None
        
        
        # ----------------------------------
        # PROCESSING
        # ----------------------------------
        
        all_data = []
        # for audio_file in tqdm(full_paths[:1], desc="Processing audio files", unit="file"):
        for audio_file in tqdm(full_paths, desc="Processing audio files", unit="file"):

            self.logging.info(f"Processing file: {audio_file}")
            try:
                if audio_file in processed_files:
                    self.logging.info(f"Skipping {audio_file}, already processed.")
                    continue
                
                self.logging.info(f"Processing audio file: {audio_file}")
                db = []
                # reading audio data
                x, _ = sf.read(audio_file)
                
                #naming
                name_split = audio_file.split("/")[-1]  # '20250107_130000'
                name_split = name_split.split(".")[0]  # '20250107_130000'
                self.logging.info(f"Name split: {name_split}")
                
                #CET
                local_tz = datetime.datetime.now().astimezone().tzinfo
                start_timestamp = datetime.datetime.strptime(name_split, '%Y%m%d_%H%M%S')
                start_timestamp = start_timestamp.replace(tzinfo=local_tz)
                self.logging.info(start_timestamp)                

                # build a list of frame start timestamps
                # each frame has length self.window_size samples, so:
                # fstart is 0, window_size, 2*window_size, ...
                # timestamps will be used in each row
                
                timestamps = [
                    start_timestamp + datetime.timedelta(seconds=fstart/self.fs) 
                    for fstart in range(0, len(x) - self.window_size + 1, self.window_size)
                ]
                
                self.logging.info("A and C weighting filters to the signal")
                # A and C weighting filters to the signal
                y_A_weighted = lfilter(self.bA, self.aA, x)
                y_C_weighted = lfilter(self.bC, self.aC, x)
                

                
                self.logging.info("Processing frame!!!")
                #process frame
                for fstart, timestamp in zip(
                    range(0, len(x) - self.window_size + 1, self.window_size),
                    timestamps):
                    # getting and weighting the frame
                    frame = x[fstart:fstart + self.window_size]
                    yA = y_A_weighted[fstart:fstart + self.window_size]
                    yC = y_C_weighted[fstart:fstart + self.window_size]

                    #weighted SPL levels
                    LA = round(get_db_level(yA, self.C), 2)
                    LC = round(get_db_level(yC, self.C), 2)
                    LZ = round(get_db_level(frame, self.C), 2)

                    # LAmax and LAmin (over "fast" sub-intervals)
                    # like splitting the frame into 8 smaller chunks
                    # for a "Fast" time weighting approach
                    fast_chunk_size = self.window_size // 8
                    fast_levels = [
                        get_db_level(yA[i:i + fast_chunk_size], self.C)
                        for i in range(0, len(frame) - fast_chunk_size + 1, fast_chunk_size)
                    ]
                    Lmax = round(np.max(fast_levels), 2)
                    Lmin = round(np.min(fast_levels), 2)
                    

                    #----------------------------
                    # CALCULATE 1/3 OCTAVE LEVELS
                    #----------------------------
                    levels, freqs =third_octave_filter(frame, self.fs, order=6, limits=[12, 20000])
                    # eound the levels to 2 decimal places
                    levels = [round(level, 2) for level in levels]
                    #20db fix
                    levels = twenty_db_fix(levels)
                    
                    if freq_labels is None:
                        freq_labels = [f"{round(freq, 1)}Hz" for freq in freqs]
                        col_names.extend(freq_labels)  # 1/3-oct columns
                    
                    
                    #unixtimestamp
                    unix_ts = int(timestamp.timestamp())

                    #building a single row
                    level_temp = [
                        self.id_micro,
                        audio_file,
                        timestamp,
                        unix_ts,
                        LA,
                        LC,
                        LZ,
                        Lmax,
                        Lmin,
                        # *oct_level_temp_rounded # expanding the list, not a pointer
                        *levels # expanding the list, not a pointer
                    ]
                    db.append(level_temp)
                # append to all_data
                all_data.append(db)


                # --------------------------------------------------
                # csv for !THIS! audio file
                # --------------------------------------------------
                self.logging.info("")
                csv_filename = audio_file.replace(".wav", ".csv")
                self.logging.info(f"/wav_file/ replaced: {csv_filename}")

                # change thie wav folder for the acoustic one
                csv_acoustic_path = csv_filename.replace(self.wav_files, self.acoustic_params)
                self.logging.info(f"csv_acoustic_path: {csv_acoustic_path}")

                # remove the last element
                csv_full_path = os.path.dirname(csv_acoustic_path)
                # self.logging.info(f"csv_full_path: {csv_full_path}")
                os.makedirs(csv_full_path, exist_ok=True)


                # saving results
                df = pd.DataFrame(db, columns=col_names)
                df.to_csv(csv_acoustic_path, index=False, encoding='utf-8')
                self.logging.info(f"Processed and wrote CSV for file: {audio_file}")
                self.logging.info(f"CSV file saved at: {csv_full_path}")

                #debugging
                # df = pd.read_csv(csv_acoustic_path)
                # print(df)
                # exit()

                # --------------------------------------------------
                # UPLOAD TO BUCKET S3
                # --------------------------------------------------
                
                if self.upload_s3 is not None:
                    try:
                        self.logging.info("Uploading the csv file to bucket S3")
                        upload_file_to_s3(csv_acoustic_path, self.s3_bucket_name, self.logging)
                    except Exception as e:
                        self.logging.error(f"Failed to upload {csv_acoustic_path} to S3: {e}")
                else:
                    self.logging.info("Not Uploading the csv file to bucket S3")
            

                # ----------------------------
                # MARKING FILE AS PROICESSED
                # ----------------------------
                update_processed_files(processed_files_txt, audio_file)
                processed_files.add(audio_file)
                logging.info(f"Final CSV file added to the processed file. {audio_file}")
                self.logging.info("")


            # -------------
            # END
            # ---------------
            except Exception as e:
                self.logging.error(f"Error processing file {audio_file}: {e}")
                continue

        return all_data



def load_processed_files(processed_file_path):
    
      
    """Load the set of processed filenames from a text file."""
    
    
 
    if os.path.exists(processed_file_path):
        with open(processed_file_path, "r") as f:
            return {line.strip() for line in f if line.strip() and os.path.basename(line.strip()).lower().endswith('.wav')}
    return set()



def update_processed_files(processed_file_path, filename):
    
    
    
    """Append a processed filename to the text file."""
    
    
    with open(processed_file_path, "a") as f:
        f.write(filename + "\n")


def point_iteration_acoustics(point, root, storage_output_wav_folder,audio_sample_rate, audio_window_size,
                              storage_s3_bucket_name, storage_output_acoust_folder, upload_s3, logging):

    """
    Creates leq_processor object for given params in order to process given wav_file_folder    
    """

    # ------------------------------
    # POINT PARAMS
    # ------------------------------
    if point in CALIBRATION_CONSTANTS:
        calib = CALIBRATION_CONSTANTS[point]
        logging.info(f"Calibration constant: {calib}")
    else:
        raise ValueError(f"Calibration constant for {point} not found in CALIBRATION_CONSTANTS.")

    if point in ID_MICROPHONE:
        id_micro = ID_MICROPHONE[point]
        logging.info(f"ID Microphone: {id_micro}")
    else:
        raise ValueError(f"ID Microphone for {point} not found in ID_MICROPHONE.")

    # ------------------------------
    # WAV FILES FOLDER
    # ------------------------------
    wav_files_folder = os.path.join(root, storage_output_wav_folder)
    logging.info(f"WAV files folder: {wav_files_folder}")

    logging.info("Creating the leq_processor")
    
    # ------------------------------
    # LEQ PROCESSOR IMPLEMENTATION
    # ------------------------------
    leq_processor = LeqLevelOct(
            audio_path=wav_files_folder,

            id_micro=id_micro,
            fs=audio_sample_rate,
            window_size=audio_window_size,
            calibration_constant=calib,
            
            acoustic_params=storage_output_acoust_folder,
            wav_files=storage_output_wav_folder,
            s3_bucket_name=storage_s3_bucket_name,
            
            upload_s3=upload_s3,
            logging=logging
        )
    
    # ------------------------------
    # END
    # ------------------------------
    return leq_processor,wav_files_folder

def parse_arguments():
    parser = argparse.ArgumentParser(description='Make prediction with YAMNet model for audio files')
    parser.add_argument('-f', '--path', type=str, required=False,
                        help='Folder containing WAV files to process')
    parser.add_argument('-p','--point', type=str, required=True,
                        help='Point to process')
    parser.add_argument('-c', '--calib-const', type=str, required=False, default=0,
                        help='Calibration constant to setup for each audio device.')
    parser.add_argument('-u', '--upload-S3', action='store_true',default=False,
                        help='If provided, upload the final CSV to S3.')
    return parser.parse_args()



def main():
    """
    usage: python.exe -m 02_acoustic_params.acoustic_params_test -p '\\192.168.205.122\Contenedores' 
    """
    try:
        
        args = parse_arguments()

        logging.info("Staarting process!!")
        logging.info("")
        
        
        try:
            
            #-------------------------------
            #   1- Get acoustic config from config.yaml local file
            #-------------------------------
               
            logging.info("Getting the element form the yamnl file")
            id_micro, location_record, location_place, location_point, \
            audio_sample_rate, audio_window_size, audio_calibration_constant,\
            storage_s3_bucket_name, storage_output_wav_folder, \
            storage_output_acoust_folder = load_config_acoustic('config.yaml')
            logging.info("Config loaded successfully")    
       
       
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            
            return

        try:

            #-------------------------------
            #   2- Upload to bucket S3
            #-------------------------------
            
            if args.upload_S3:
                upload_s3 = args.upload_S3
            else:
                upload_s3 = None
        
        except Exception as e:
            logging.error(f"Error setting upload_s3: {e}")
            
            return



        try:

            #-------------------------------
            #   3- Set base path from arguments or config
            #-------------------------------

            if args.path: path = args.path  
            else:

                if os.name == 'posix':
                    path = SANDISK_PATH_LINUX_NEW
                    logging.info(f"Using path: {path}")
                elif os.name == 'nt':
                    path = SANDISK_PATH_WINDOWS
                    logging.info(f"Using path: {path}")
                

            if os.path.isdir(path): logging.info(f"Path exists --> {path}")
            else: raise ValueError(f'Path ({path}) doesnt exist.')
               
        except Exception as e:
            logging.error(f"Error setting path: {e}")
            
            return
            
            #-------------------------------
            #   4- Iterate through points in "3- Medidas" folder and:
            #-------------------------------

        for root, dirs, files in os.walk(path):
            
            if storage_output_wav_folder in dirs:


            #-------------------------------
            #   5- When wav_folder found in point folder, create leq_processor and leq_process wav_folder
            #-------------------------------
                logging.info(f"Found folder: {storage_output_wav_folder} in {root}")
                point = os.path.basename(root)
                logging.info(f"Point: {point}")


                if point == str(args.point):

                    leq_processor, wav_files_folder = point_iteration_acoustics(
                        point,
                        root,
                        storage_output_wav_folder,
                        audio_sample_rate,
                        audio_window_size,
                        storage_s3_bucket_name,
                        storage_output_acoust_folder,
                        upload_s3,
                        logging
                    )

                    logging.info("Processing audio files...")
                    leq_processor.process_audio_files(wav_files_folder)
                
                
                else:
                    
                    
                    logging.info(f"Skipping point: {point}")
                    
                    
                    continue

    except KeyboardInterrupt:
        logging.error("Recording interrupted by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")



            #-------------------------------
            #   6- End !
            #-------------------------------
    logging.info("")
    logging.info("Done!")


if __name__ == "__main__":
    main()