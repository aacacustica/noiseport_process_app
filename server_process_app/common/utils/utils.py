
from pyfilterbank.octbank import FractionalOctaveFilterbank
from scipy.fft import fft
from pathlib import Path

from server_process_app.common.config.settings import config

import numpy as np
import os
import subprocess
import logging
import csv

inbox_folder = config['paths']['inbox']
# Constantes de inicializacion
T = 1
# C = -54.70

# [1]
def filterbanks(fs):
    """    
    :param fs: 
        Sample rate of the audio
    :return:
        third octave filterbank, octave filterbank
    """
    third_oct = FractionalOctaveFilterbank(
        sample_rate=fs,
        order=4, 
        nth_oct=3.0,
        norm_freq=1000.0,
        start_band=-19,
        end_band=13,
        edge_correction_percent=0.01, 
        filterfun='cffi' 
        )
    
    octave = FractionalOctaveFilterbank(
        sample_rate=fs,
        order=4,
        nth_oct=1.0,
        norm_freq=1000.0,
        start_band=-5,
        end_band=4,
        edge_correction_percent=0.01,
        filterfun='cffi')

    return third_oct, octave

# [2]
def get_edge_frequencies(idx_low=-16, idx_high=12):
    """
    Args:
        idx_low (int): The lower index for the range of fractional octave bands. Default is -16.
        idx_high (int): The upper index for the range of fractional octave bands. Default is 12.

    Returns:
        tuple: A tuple of three numpy arrays - lower edge frequencies (`f_lower`), center frequencies (`fm`), and upper edge frequencies (`f_upper`) of the defined fractional octave bands.
    """
    G = 10**(3/10) 
    fr = 1000
    b = 3    
    idx = np.arange(-16,12)    
    fm = G**(idx/b)*fr
    f_upper = fm*G**(1/(2*b))  
    f_lower = fm*G**(-1/(2*b))
    
    return f_lower, fm, f_upper

# [3]
def parseval(x_dft):
    """   
    Args:
        x_dft (numpy.ndarray): The Fast Fourier Transform (FFT) of a frame of audio data, represented as an array of complex numbers.

    Returns:
        float: The Sound Pressure Level (SPL), in decibels, of the given frame of audio data.  
    """
    n = len(x_dft)
    po = 0.000002
    x_mag = np.abs(x_dft)
    lp = 10*np.log10(np.sum(x_mag**2) / ((po**2)*(n**2)))
    return lp

# [4]
def third_octave_dft(frame, f_lower, f_upper, fs, C):
    """
    Args:
        frame (numpy.ndarray): An array representing the time domain signal of an audio frame.
        f_lower (numpy.ndarray): An array of lower frequency edges of each third-octave band.
        f_upper (numpy.ndarray): An array of upper frequency edges of each third-octave band.
        fs (float): The sample rate of the audio signal.
        C (float): A calibration constant to adjust the calculated Sound Pressure Level (SPL).

    Returns:
        list: A list of SPL values for each third-octave band.
    """
    x_dft = fft(frame)
    k = np.arange(0, fs, fs / len(frame))
    band_levels = []
    
    for fl, fh in zip(f_lower, f_upper):
        idx_band = (k >= fl) & (k < fh)
        x_dft_band = x_dft[idx_band]
        lp = parseval(x_dft_band) + C
        band_levels.append(lp)    
    return band_levels 

# [5]
def db_level(x, T, C):
    """    
    Args:
        x (numpy.ndarray): An array of audio signal values.
        T (float): A time interval over which the audio signal power is averaged.
        C (float): A calibration constant for the audio recording device. 

    Returns:
        float: The Sound Pressure Level (SPL) of the given audio signal in decibels.
    """
    po = 0.000002    
    level = 10 * np.log10(np.nansum((x / po) ** 2) / T) + C
    return level

# [6]
def get_db_level(x, C):
    """
    Args:
        x (numpy.ndarray): A multi-dimensional array of audio signal values.
        C (float): A calibration constant for the audio recording device.
        axis (int): The axis along which the means are computed. By default, it computes the mean over the last axis.

    Returns:
        numpy.ndarray or float: The Sound Pressure Level (SPL) of the given audio signal in decibels. If the input 'x' is a multi-dimensional array, then an array of SPL values is returned, otherwise a single float value is returned.

    """
    pref = 0.000002
    level = 10 * np.log10(np.mean(x ** 2) / pref ** 2) + C
    return level

# [7]
def get_calibration_constant(x, db_value, T):
    """
    Args:
        x (numpy.ndarray): An array of audio signal values.
        db_value (float): The known or desired Sound Pressure Level (SPL) of the input signal 'x'.
        T (int): The total number of samples in the audio signal 'x'.

    Returns:
        float: The calibration constant 'C' that, when added to the calculated SPL of any signal, adjusts it to the calibrated level.
    """
    po = 0.000002
    level = 10 * np.log10(np.nansum((x / po) ** 2) / T)
    C = db_value - level    
    return C



def leq(levels):
    levels = np.asarray(levels, dtype=float)
    levels = levels[~np.isnan(levels)]

    if levels.size == 0:
        return np.nan

    return 10 * np.log10(np.mean(10 ** (levels / 10)))
# [9]
def get_oct_levels(y, octave, C):
    """
    Args:
        y (numpy.ndarray): A 1-dimensional array containing audio signal values.
        octave (python object): An octave filterbank object. The filterbank should be designed to decompose the signal into its octave bands.
        C (float): A calibration constant for the audio recording device.
    Returns:
        list: A list of Sound Pressure Level (SPL) values in decibels for each octave band.
    """
    y_oct, _ = octave.filter(y)
    oct_level = [get_db_level(f, C) for f in y_oct.T]    
    return oct_level

# [10]
def get_audiofiles(path):
    """
    Args:
        path (str): The path to the directory containing the audio files.
    Returns:
        list: A list containing the full paths to all '.wav' files in the specified directory.
    """    
    audio_files = [file for file in os.listdir(path) if file.lower().endswith('.wav')]
    return audio_files


# -----------------------------------
# CONFIG & DEVICES
# -----------------------------------

def load_devices():
    
    inbox_path = config['paths']['inbox']
    enabled_devices = [device for device in config['devices'] if device.get("enabled",True)]
    
    return [os.path.join(inbox_path, d["id"]) for d in enabled_devices]

def load_config():

    return config

def get_enabled_devices() -> list[dict]:
    return [d for d in config["devices"] if d.get("enabled", True)]

def get_device_ids() -> list[str]:
    return [d["id"] for d in get_enabled_devices()]

def get_device_paths() -> list[str]:
    inbox = config["paths"]["inbox"]
    return [os.path.join(inbox, d["id"]) for d in get_enabled_devices()]

def get_device_config(device_id: str) -> dict:
    for d in config["devices"]:
        if d["id"] == device_id:
            return d
    raise KeyError(f"Device not configured: {device_id}")

def get_hourly_folders_device(device_folder_path,predictions_query_folder_name,peaks_query_folder_name,acoustics_query_folder_name):

    hour_path_acoustics = []
    hour_path_predictions = []
    hour_path_peaks = []
    

                    
    predictions_params_query = os.path.join(device_folder_path,predictions_query_folder_name)
    peaks_params_query = os.path.join(device_folder_path,peaks_query_folder_name)
    acoustic_params_query = os.path.join(device_folder_path,acoustics_query_folder_name)

    if not os.path.exists(peaks_params_query): os.makedirs(peaks_params_query)

    for file in os.listdir(acoustic_params_query):
        if file.endswith('.csv') and 'fixed' in file:
            hour_path_acoustics.append(os.path.join(acoustic_params_query,file))        
    for file in os.listdir(predictions_params_query):
        if file.endswith('.csv'):
            hour_path_predictions.append(os.path.join(predictions_params_query,file))
    for file in os.listdir(peaks_params_query):
        if file.endswith('.csv') and 'fixed' in file:
            hour_path_peaks.append(os.path.join(peaks_params_query,file))
    
    return hour_path_acoustics,hour_path_predictions,hour_path_peaks



# -----------------------------------
# REGULAR FUNCTIONS
# -----------------------------------

def class_names_csv(class_map_csv):
    with open(class_map_csv) as csv_file:
        reader = csv.reader(csv_file)
        next(reader)   # Skip header
        return np.array([display_name for (_, _, display_name) in reader])

#----------------------------
#  GIT
#----------------------------
def list_git_tags():
    try:
        tags = tags = subprocess.check_output(["git", "tag"]).strip().decode()
        return tags.split('\n')
    except subprocess.CalledProcessError:
        return None
    
    
def select_tag(tags):
    for i, tag in enumerate(tags):
        logging.info(f"{i}: {tag}")
    choice = int(input("Select the tag to use: "))
    tag_selected = tags[choice]
    # replace "." with "_" to be able to use it as a file name
    tag_selected = tag_selected.replace(".", "_")
    return tag_selected


def get_stable_version(logging):
    tags = list_git_tags()
    # get the latest stable version
    tag_selected = tags[-1]
    logging.info(f"Latest stable version: {tag_selected}")
    # replace "." with "_" to be able to use it as a file name
    tag_selected = tag_selected.replace(".", "_")
    logging.info(f"Latest stable version string: {tag_selected}")
    return tag_selected

def get_desired_query_folder(days_folder,desired_folder):
    
    for i,folder in enumerate(days_folder):
        if not desired_folder in folder.split('/'):
            days_folder[i] = days_folder[i].replace(days_folder[i].split('/')[-2],desired_folder)

    return days_folder

def collect_folders_days_devices(folders,devices):

    result = {
        Path(device).name: {
            "files": [],
            "processed": False,
        }
        for device in devices
    }

    for folder in map(Path,folders):
        device_name = folder.parent.name
        if device_name not in result:
            continue
            
        result[device_name].extend(
            str(file)
            for file in folder.iterdir()
            if file.is_file() and file.suffix.lower() == '.csv'
        )


    return result
