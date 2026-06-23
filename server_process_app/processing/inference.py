from __future__ import division, print_function

import os
import argparse
import numpy as np
import datetime
import csv
import tqdm

import resampy
import soundfile as sf
import tensorflow as tf
import pandas as pd

from . import params as yamnet_params
from . import yamnet as yamnet_model

import warnings

from utils import *
from logging_config import setup_logging
from collections import defaultdict

warnings.filterwarnings("ignore", 
                        message="FNV hashing is not implemented in Numba",
                        category=UserWarning)

print(f"Current GPU: {tf.config.list_physical_devices('GPU')}")

(
    ID_MICRO,
    S3_BUCKET_NAME,
    PLACE,
    POINT,
    OUTPUT_PARENT_FOLDER,
    OUTPUT_WAV_FOLDER,
    OUTPUT_ACOUST_FOLDER,
    OUTPUT_PREDICT_FOLDER,
    _,
    YAMNET_CLASS_MAP_CSV,
    SAMPLE_RATE,
    CHUNK_SIZE,
    MODEL_TF,
    _,
    

) = load_config_inference('config.yaml', os.getcwd())
"id_micro, location_record, location_place, location_point, storage_s3_bucket_name, storage_output_wav_folder, storage_output_acoust_folder, storage_output_predict_folder, storage_output_predict_lt_folder, prediction_yamnet_class_map_csv, prediction_sample_rate, prediction_chunk_size, prediction_model_tf, prediction_model_tflt"

def concatenate_prediction_csvs_to_daily(prediction_folder,logging):

    hour_folders = os.listdir(prediction_folder)
    folders_by_day = defaultdict(list)
    
    for hour_folder in hour_folders:
        hour_name = os.path.basename(hour_folder)
        day = hour_name.split("_")[0]
        folders_by_day[day].append(hour_folder)
        
        for day, folders in folders_by_day.items():
            all_minutes = []
            
            for folder in folders:
                for csv_file in os.listdir(folder):
                    if csv_file.endswith('.csv'):
                        file_path = os.path.join(folder, csv_file)
                        df = pd.read_csv(file_path)
                        all_minutes.append(df)
            
            if all_minutes:
                df_day = pd.concat(all_minutes, axis=0, ignore_index=True)
                output_file = os.path.join(prediction_folder, f"{day}_concatenated.csv")
                df_day.to_csv(output_file, index=False)
    
def get_audio_files(path):
    
    
    predictions_done_txt = path.replace('wav_files',f'AI_MODEL/prediction_files/predictions_done.txt')
    predictions_done_txt = predictions_done_txt.replace('3-Medidas',f'5-Resultados')

    day_files = [os.path.join(path,f) for f in os.listdir(path) if os.path.isdir(os.path.join(path,f))]


    predictions_done = load_predictions_done(predictions_done_txt)

    audio_files = [
        f for day in day_files
        for f in os.listdir(day)
        if f.lower().endswith('.wav') and os.path.basename(f) not in predictions_done
    ]

    full_paths = [
        os.path.join(day, f) for day in day_files
        for f in os.listdir(day)
        if f.lower().endswith('.wav') and f not in predictions_done
    ]

    return predictions_done_txt,audio_files,full_paths

def inference(path,model_path, sample_rate, chunk_size, window_size, threshold, upload_s3, logging, output_wav_folder, output_predict_folder, s3_bucket_name, cwd, yamnet_class_map_csv):
    """Perform inference on one or more audio files.
    Args:
        file_list (list[str]): List of file paths to process.
        window_size (float, optional): Window size in seconds. If None, process the entire file at once.
        threshold (float, optional): Threshold for classification.
    """
    logging.info("")
    logging.info("Making inference")

    # ----------------------------
    # 1) Create the TF object
    # ----------------------------
    logging.info("Setting the TF Model and loading the classes")
    params = yamnet_params.Params()
    yamnet = yamnet_model.yamnet_frames_model(params)
    yamnet.load_weights(model_path)
    yamnet_classes = yamnet_model.class_names(yamnet_class_map_csv)

    logging.info("Model and Classes map loaded")

    # -------------------------------------
    # 2 - GETTING NOT PROCESSED AUDIO FILES
    # -------------------------------------

    (
        predictions_done_txt,
        audio_files,
        full_paths

    ) = get_audio_files(path)


    
    logging.info(f"Found {len(audio_files)} audio files: {audio_files}")
    # --------------------
    # 3 - Processing audio files
    # --------------------
    for audio_file in tqdm.tqdm(full_paths,desc="Inferencing on audio files..."):
        logging.info("")
        logging.info(f"Processing --> {audio_file}")
        
        # -----------------------------------------------------------
        # CSV file name and folder
        # -----------------------------------------------------------
        wav_filename = os.path.basename(audio_file)  # e.g. 20250108_142606.wav
        logging.info(f"WAV file name --> {wav_filename}")

        wav_file_raw = os.path.splitext(wav_filename)[0]
        start_timestamp = datetime.datetime.strptime(wav_file_raw, '%Y%m%d_%H%M%S')
        if window_size is None:
            csv_filename = wav_filename.replace(".wav", "_tf.csv")  # e.g. 20250108_142606_tf.csv
        else:
            csv_filename = wav_filename.replace(".wav", f"_tf_w_{window_size}.csv")  # e.g. 20250108_142606_tf_w_1.0.csv
            
        logging.info(f"CSV filename --> {csv_filename}")

        prediction_folder = os.path.dirname(audio_file).replace(output_wav_folder, output_predict_folder)
        prediction_folder = prediction_folder.replace("3-Medidas","5-Resultados")
        prediction_folder = prediction_folder.replace("prediction_files","AI_MODEL/prediction_files")
        os.makedirs(prediction_folder, exist_ok=True)
        logging.info(f"Making TF prediction folder --> {prediction_folder}")

        csv_full_path = os.path.join(prediction_folder, csv_filename)
        logging.info(f"CSV FULL PATH --> {csv_full_path}")



        # -----------------------------------------------------------
        # Decode the WAV file
        # -----------------------------------------------------------
        logging.info("")
        logging.info("Decoding WAV file")
        wav_data, sr = sf.read(audio_file, dtype=np.int16)
        assert wav_data.dtype == np.int16, f'Bad sample type: {wav_data.dtype}'

        waveform = wav_data / 32768.0  # Convert to [-1.0, +1.0]
        waveform = waveform.astype('float32')

        # Convert to mono and the sample rate expected by YAMNet
        if len(waveform.shape) > 1:
            waveform = np.mean(waveform, axis=1)
            logging.info("Audio file converted to mono")
        if sr != params.sample_rate:
            waveform = resampy.resample(waveform, sr, params.sample_rate)
            logging.info("Audio file resampled to 16KHz")


        # -----------------------------------------------------------
        # Perform inference
        # -----------------------------------------------------------
        csv_data = [["filename", "date", "class", "probability"]]

        if window_size is None:
            #single chunk inference
            scores, embeddings, spectrogram = yamnet(waveform)
            prediction = np.mean(scores, axis=0)

            # top 3
            top3_i = np.argsort(prediction)[::-1][:3]
            top3_classes = [str(yamnet_classes[i]) for i in top3_i]
            top3_probs = [f"{prediction[i]:.4f}" for i in top3_i]

            csv_data.append([
                wav_filename,
                str(start_timestamp),
                str(top3_classes),
                str(top3_probs)
            ])


        # -----------------------------------------------------------
        # Windowed inference
        # -----------------------------------------------------------
        else:
            window_size_samples = int(window_size * params.sample_rate)
            start_idx = 0
            while start_idx < len(waveform):
                end_idx = min(start_idx + window_size_samples, len(waveform))
                waveform_window = waveform[start_idx:end_idx]

                scores, embeddings, spectrogram = yamnet(waveform_window)
                prediction = np.mean(scores, axis=0)

                # top 3
                top3_i = np.argsort(prediction)[::-1][:3]
                top3_classes = [str(yamnet_classes[i]) for i in top3_i]
                top3_probs = [f"{prediction[i]:.4f}" for i in top3_i]

                # timestamp for this window
                start_time_s = start_idx / params.sample_rate
                window_timestamp_actual = start_timestamp + datetime.timedelta(seconds=int(start_time_s))
                formatted_time = window_timestamp_actual.strftime("%H:%M:%S")

                csv_data.append([
                    wav_filename,
                    formatted_time,
                    str(top3_classes),
                    str(top3_probs)
                ])

                start_idx = end_idx


        # -----------------------------------------------------------
        # Save CSV
        # -----------------------------------------------------------

        if not os.path.exists(csv_full_path):
            os.makedirs(os.path.dirname(csv_full_path), exist_ok=True)
        
        with open(csv_full_path, mode="w", newline="") as final_csv:
            writer = csv.writer(final_csv)
            writer.writerows(csv_data)
        logging.info(f"Final CSV file saved at {csv_full_path}")

        update_predictions_file(predictions_done_txt, csv_full_path)

        # -------------
        # UPLOAD TO BUCKET S3
        # ---------------
        if upload_s3 is not None:
            try:
                upload_file_to_s3(csv_full_path, s3_bucket_name, logging)
            except Exception as e:
                logging.error(f"Failed to upload {csv_full_path} to S3: {e}")
        else:
            logging.warning("The final CVS final will not be update to the bucket S3")

        # -------------
        # CONCATENATE DAILY CSVS
        # ---------------
        """
        try:

            concatenate_prediction_csvs_to_daily(
                prediction_folder,
                yamnet_classes,
                start_timestamp,
                logging
            )

        except Exception as e:
            logging.error(f"Error concatenating prediction CSVs into DAILY format: {e}")
        """
def load_args_config(model_path,point,window_size,threshold,upload_s3,home_dir,path):

        if path: path = path       
        else: path = os.path.join('/srv/contenedores/CONTENEDORES/CONTENEDORES/3-Medidas', point, OUTPUT_WAV_FOLDER)
              
        if os.path.exists(path):
            logging.info(f"Path exists --> {path}")
        else:
            raise Exception('Path doesnt exist.')

        if model_path: model_path = model_path
        else: model_path = MODEL_TF

        if window_size: window_size = window_size
        else: window_size = None
            
        if threshold: threshold = threshold
        else: threshold = None
            
        if upload_s3: upload_s3 = upload_s3
        else: upload_s3 = None
        
        return model_path,window_size,threshold,upload_s3,path

def parse_arguments():
    parser = argparse.ArgumentParser(description='Make prediction with YAMNet model for audio files')
    parser.add_argument('-f', '--path', type=str, required=False,
                        help='Folder containing WAV files to process')
    parser.add_argument('-p', '--point', type=str, required=True,
                        help='Point to process')

    parser.add_argument('-w', '--window-size', type=float, default=None,
                        help='Window size in seconds for processing audio files. '
                             'Default is None for processing the entire audio.')

    parser.add_argument('-t', '--threshold', type=float, default=None,
                        help='Classification threshold for predictions.')

    parser.add_argument('-m', '--model-path', type=str, default=None,
                        help='Insert the model path to make predictions.')

    parser.add_argument('-u', '--upload-S3', action='store_true',default=False,
                        help='If provided, upload the final CSV to S3.')

    return parser.parse_args()

def load_predictions_done(workingdir):

    txt_path = workingdir
    
    preds = []
    if os.path.exists(txt_path):
        with open(txt_path, 'r') as f:
            for line in f:
                filename = os.path.basename(line.strip())
                if 'tf_w_1.0.csv' in filename or 'tf.csv in filename':
                    filename = filename.replace('_tf_w_1.0.csv','.wav').replace('_tf.csv','.wav')
                preds.append(filename)
    return preds



def update_predictions_file(workingdir,file):

    txt_path = workingdir
    
    os.makedirs(os.path.dirname(txt_path), exist_ok=True)
    
    existing = set()

    with open(txt_path, 'r') as f:
        existing = set(line.strip() for line in f)
    
    with open(txt_path, 'a') as f:
        if file not in existing:
            f.write(file + '\n')

def main():
    
    
    
    try:

    # ----------------------------
    # 1 - PARSE ARGUMENTS & CONFIG
    # ----------------------------
        logging = setup_logging(script_name="inference")
        args = parse_arguments()
        cwd = os.path.dirname(os.path.realpath(__file__))
        home_dir = os.getenv("HOME")
        model_path,window_size,threshold,upload_s3,path = load_args_config(args.model_path,args.point,args.window_size,args.threshold,args.upload_S3,home_dir,args.path)
        "model_path,point,window_size,threshold,upload_s3,home_dir,path"
        logging.info(f"Path: {path}")
        logging.info(f"Model path: {model_path}")
        logging.info(f"Window size: {window_size}")
        logging.info(f"Probability treshold: {threshold}")
        logging.info(f"Upload to bucket S3: {upload_s3}")
    
    except Exception as e:
        logging.error(f"Errorgetting the config info: {e}")





    try:

    # -----------------------
    # 3 - MAKE INFERENCE
    # -----------------------
        
        inference(
            path = path,
            model_path=model_path,
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE,
            window_size=window_size,
            threshold=threshold,
            upload_s3=upload_s3,
            logging=logging,
            output_wav_folder=OUTPUT_WAV_FOLDER,
            output_predict_folder=OUTPUT_PREDICT_FOLDER,
            s3_bucket_name=S3_BUCKET_NAME,
            cwd=cwd,
            yamnet_class_map_csv=YAMNET_CLASS_MAP_CSV
        
        )
        
        logging.info("Inference finished.")
    # -----------------------
    # 4 - END
    # -----------------------
    except Exception as e:
        logging.error(f"Error making inference: {e}")



if __name__ == '__main__':
    main()
