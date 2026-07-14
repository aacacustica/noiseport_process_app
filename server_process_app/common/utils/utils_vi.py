import numpy as np
import pandas as pd
import re

import subprocess
import os
import json

from pathlib import Path
from pandas.api.types import is_datetime64_any_dtype
from typing import Optional

from server_process_app.common.config.config_vi import *
from server_process_app.common.utils.utils import * 

config = load_config()

RELATIVE_PATH_YAMNET_MAP = config['models']['yamnet_class_map']

RELATIVE_PATH_TAXONOMY_URBAN = config['models']['urban_taxonomy_mapping']
RELATIVE_PATH_TAXONOMY_PORT = config['models']['port_taxonomy_mapping']

def extract_file_date(path):
    match = re.search(r"(\d{8})",Path(path).stem)
    return match.group(1) if match else None

def map_files_by_date(files):
    result = {}

    for file_path in files:
        date = extract_file_date(file_path)
        if date:
            result[date] = file_path
    return result

def collect_df_server(reg_folder):


    groups = {
        "acoustics": [],
        "predictions": [],
        "peaks": [],
        "merged": []
    }

    for subfolder in os.listdir(reg_folder):
        subfolder_path = os.path.join(reg_folder,subfolder)

        if not os.path.isdir(subfolder_path): continue

        csvs = [os.path.join(subfolder_path,file) for file in os.listdir(subfolder_path) if file.endswith('.csv')]

        if 'acoustic_queries' in subfolder:
            groups['acoustics'] = csvs
        if 'prediction_queries' in subfolder:
            groups['predictions'] = csvs
        if 'peaks_query' in subfolder:
            groups['peaks'] = csvs
        if 'merged_csv_query' in subfolder:
            groups['merged'] = csvs
    

    acoustics = map_files_by_date(groups['acoustics'])
    predictions = map_files_by_date(groups['predictions'])
    peaks = map_files_by_date(groups['peaks'])
    merged = map_files_by_date(groups['merged'])

    common_dates = sorted(set(acoustics)&set(predictions)&set(peaks)&set(merged))
    return [(date,acoustics[date],predictions[date],peaks[date],merged[date]) for date in common_dates]

def parse_probability(x):
    import ast
    if pd.isna(x):
        return [0.0]

    if isinstance(x, list):
        return x

    if not isinstance(x, str):
        return [x]

    s = x.strip()

    if s == "":
        return [0.0]

    try:
        parsed = ast.literal_eval(s)
    except Exception:
        return [0.0]

    if isinstance(parsed, list):
        return parsed

    return [parsed]

def parse_prediction_class(x):
    import ast
    if x is None:
        return ["Silence"]

    if isinstance(x, list):
        return x

    if isinstance(x, tuple):
        return list(x)

    try:
        if pd.isna(x):
            return ["Silence"]
    except Exception:
        pass

    if not isinstance(x, str):
        return [x]

    s = x.strip()

    if s == "":
        return ["Silence"]

    try:
        parsed = ast.literal_eval(s)
    except Exception:
        return [s]

    if parsed is None:
        return ["Silence"]

    if isinstance(parsed, list):
        return parsed

    if isinstance(parsed, tuple):
        return list(parsed)

    return [parsed]

def sum_dBs(dB_values):
    return 10 * np.log10(np.sum(np.power(10, np.array(dB_values) / 10)))


def calculate_duration(start_time, end_time):
    duration = end_time - start_time
    return duration.total_seconds()


def evaluation_period_str(hour_column):
    period = ''
    if hour_column >= 7 and hour_column < 19:
        period = 'Ld'
    elif hour_column >= 19 and hour_column < 23:
        period = 'Le'
    else:
        period = 'Ln'
    return period


def evaluation_period_str_valencia(hour_column):
    period = ''
    if hour_column >= 8 and hour_column < 22:
        period = 'Ld_valencia'
    else:
        period = 'Ln_valencia'
    return period

def ensure_timestamp_column(df: pd.DataFrame,logger): 

    result = df.copy()
    if 'Timestamp' in result.columns:
        result['Timestamp'] = pd.to_datetime(result['Timestamp'],errors='coerce')
    elif isinstance(result.index,pd.DatetimeIndex):
        index_name = result.index.name or 'index'
        
        result = result.reset_index()
        result = result.rename(columns={index_name:'Timestamp'})
        result['Timestamp'] = pd.to_datetime(result['Timestamp'],errors='coerce')

    elif 'datetime' in result.columns:
        result['Timestamp'] = pd.to_datetime(result['datetime'],errors='coerce')
    else:
        logger.warning(f"Timestamp unavailable. Columns: {result.columns.to_list()}")
        return None
    
    result = result.dropna(subset='Timestamp').copy()

    return result

def add_night_column(hour_column, day_name):
    
    night_list = {
        'Lunes'     : "Lunes-Martes",
        'Martes'    : "Martes-Miércoles",
        'Miércoles' : "Miércoles-Jueves",
        'Jueves'    : "Jueves-Viernes",
        'Viernes'   : "Viernes-Sábado",
        'Sábado'    : "Sábado-Domingo",
        'Domingo'   : "Domingo-Lunes"
    }

    previous_day = {
        'Lunes'     : 'Domingo',
        'Martes'    : 'Lunes',
        'Miércoles' : 'Martes',
        'Jueves'    : 'Miércoles',
        'Viernes'   : 'Jueves',
        'Sábado'    : 'Viernes',
        'Domingo'   : 'Sábado'
    }
   
    day_name = str(day_name).strip()

    if day_name not in night_list:  return ""
    if hour_column >= 23:           return night_list[day_name]
    if hour_column < 7:             return night_list[previous_day[day_name]]

    return ""

def trim_dataframe(df, start_seconds, end_seconds, logger, name):

    if df is None or df.empty:
        logger.warning("%s dataframe is empty before trimming", name)
        return df
    
    start = df.index.min()
    end = df.index.max()
    duration = (end - start).total_seconds()

    required_duration = start_seconds + end_seconds

    if duration <= required_duration:
        logger.warning("%s duration is %.1f seconds; cannot trim %d + %d seconds. Skipping trimming",name,duration,start_seconds,end_seconds)
        return df
    
    return df.loc[start + pd.Timedelta(seconds=start_seconds) : end - pd.Timedelta(seconds=end_seconds)].copy()
    
def resolve_acoustic_level_column(df):

    candidates = ("LA_corrected","LA","LAeq","LAFeq","leq")

    for column in candidates:
        if column in df.columns:
            return column

    raise KeyError(f"No acoustic level column found. Available columns: {df.columns.tolist()}")

def add_datetime_columns(df,logging, date_col):

    df = df.copy()

    if date_col not in df.columns: raise KeyError(f"Missing datetime column {date_col!r} Available columns: {df.columns.tolist()}")

    df['Timestamp'] = pd.to_datetime(df[date_col], errors='coerce',utc=True)
    
    invalid_count = int(df['Timestamp'].isna().sum())

    if invalid_count:
        logging.warning("Dropping %d rows with invalid timestamps",invalid_count)
        df = df.dropna(subset=["Timestamp"]).copy()
    
    if df.empty: 
        logging.warning("DataFrame is empty after timestamp conversion")
        return df
    
    if not is_datetime64_any_dtype(df['Timestamp']): raise TypeError("Timestamp could not be converted to datetime")

    #df['day_hour'] = df.apply(lambda x: str(x[date_col].day) + '-' + str(x[date_col].hour),axis=1)
    weekday_translation = {
        "Monday": " Lunes",
        "Tuesday": " Martes",
        "Wednesday": " Miércoles",
        "Thursday": " Jueves",
        "Friday": " Viernes",
        "Saturday": " Sábado",
        "Sunday": " Domingo"
    }
    
    df["year"] = df['Timestamp'].dt.year
    df["month"] = df['Timestamp'].dt.month
    df['date'] = df['Timestamp'].dt.date
    df['day'] = df['Timestamp'].dt.day
    df['hour'] = df['Timestamp'].dt.hour
    df['weekday'] = df['Timestamp'].dt.weekday
    df['day_name'] = df['Timestamp'].dt.day_name()

    df['day_name'] = (df['Timestamp'].dt.day_name().map(weekday_translation))

    # df["weekday"] = df["weekday"].replace(WEEKDAY_TRANSLATION)
    # df["weekday"] = df["weekday"].astype(str)
    # df["day"] = df["day"].astype(str).str.zfill(2)
    # df["fullday"] = df["day"] + df["weekday"]

    # print(df)
    # exit()

    #df['min_sec_str'] = df.apply(lambda x: datetime.datetime.strftime(x[date_col],'%M:%S'),axis=1)
    #df['min_sec_15_str'] = df.apply(lambda x: str(x[date_col].minute % 15) + '-'+str(x[date_col].second),axis=1)
    return df



def insert_dates(df):
    df["year"] = df.index.year
    df["month"] = df.index.month
    df["day"] = df.index.day
    df["hour"] = df.index.hour
    df["minute"] = df.index.minute
    df["second"] = df.index.second
    df["weekday"] = df.index.day_name()

    weekday_translation = {
        "Monday": " Lunes",
        "Tuesday": " Martes",
        "Wednesday": " Miércoles",
        "Thursday": " Jueves",
        "Friday": " Viernes",
        "Saturday": " Sábado",
        "Sunday": " Domingo"
    }
    df["weekday"] = df["weekday"].replace(weekday_translation)
    df["weekday"] = df["weekday"].astype(str)
    df["day"] = df["day"].astype(str).str.zfill(2)
    df["fullday"] = df["day"] + df["weekday"]
    return df


def db_limit(hour_column,ld_limit,le_limit,ln_limit):
    limit = 0
    if hour_column >= 7 and hour_column < 19:
        limit = ld_limit
    elif hour_column >= 19 and hour_column < 23:
        limit = le_limit
    else:
        limit = ln_limit
    return limit


def categorize_time_of_day(hour):
    # hour = time_obj.hour
    if 7 <= hour < 19:
        return 'Ld'
    elif 19 <= hour < 23:
        return 'Le'
    else:
        return 'Ln'
    

def categorize_time_of_day_4(hour):
    if 7 <= hour < 11:
        return 'Ld_1'
    elif 11 <= hour < 15:
        return 'Ld_2'
    elif 15 <= hour < 19:
        return 'Ld_3'
    elif 19 <= hour < 23:
        return 'Le'
    elif 23 <= hour or hour < 3:
        return 'Ln_1'
    elif 3 <= hour < 7:
        return 'Ln_2'


def leq(levels):
    levels = levels[~np.isnan(levels)]
    l = np.array(levels)
    return 10*np.log10(np.mean(np.power(10,l/10)))


def get_day_levels(df,laeq_column):
    df['indicador_str'] = df.apply(lambda x: evaluation_period_str(x['hour']),axis=1)
    indicadores = df.groupby('indicador_str').agg({laeq_column:[leq]}).round(1)
    return indicadores
    

def get_day_levels_valencia(df,laeq_column):
    df['indicador_valencia'] = df.apply(lambda x: evaluation_period_str_valencia(x['hour']),axis=1)
    indicadores = df.groupby('indicador_valencia').agg({laeq_column:[leq]}).round(1)
    return indicadores




def remove_unnamed_columns(df_preds):
    df_preds = df_preds.loc[:, ~df_preds.columns.str.contains('^Unnamed')]
    df_preds = df_preds.drop(columns=['Brown_Level_1'])
    df_preds = df_preds.drop(columns=['index'])
    return df_preds


def yamnet_class_map_csv():
    
    yammnet_class_map_path = RELATIVE_PATH_YAMNET_MAP
    df_audioset = pd.read_csv(yammnet_class_map_path,sep=';')
    df_audioset = remove_unnamed_columns(df_audioset)
    return df_audioset


def taxonomy_json():
    
    urban_taxonomy_map_path = RELATIVE_PATH_TAXONOMY_URBAN
    urban_taxonomy_map = pd.read_json(urban_taxonomy_map_path, typ='series').to_dict()
    
    
    port_taxonomy_map_path = RELATIVE_PATH_TAXONOMY_PORT
    port_taxonomy_map = pd.read_json(port_taxonomy_map_path, typ='series').to_dict()
    return urban_taxonomy_map, port_taxonomy_map


def prediction_csv(path_input):
    df_prediction = pd.read_csv(path_input, converters={'class': eval, 'probability': eval})
    columns_to_check = ["classes_custom", "probabilities_custom", "sum_probs_custom", "sum_probs_original"]
    
    for col in columns_to_check:
        if col in df_prediction.columns:
            df_prediction = df_prediction.drop(col, axis=1)
            
    # columns to rename
    columns_to_rename = ["classes_original", "probabilities_original"]
    new_columns = ["classes", "probabilities"]
    
    for i in range(len(columns_to_rename)):
        if columns_to_rename[i] in df_prediction.columns:
            df_prediction = df_prediction.rename(columns={columns_to_rename[i]: new_columns[i]})

    return df_prediction



def remove_row_out_timespan(df_LAeq, df_Pred):
    df_LAeq.index = pd.to_datetime(df_LAeq.index)
    df_Pred['datetime'] = pd.to_datetime(df_Pred['datetime'])
    start_date = df_LAeq.index.min()
    end_date = df_LAeq.index.max()
    df_Pred_filtered = df_Pred[(df_Pred['datetime'] >= start_date) & (df_Pred['datetime'] <= end_date)]
    
    return df_Pred_filtered



def apply_db_correction(df, coefficient, sufix_string, logger):
    """
    Applying correction to the dataframe based on the provided coefficient and suffix string."""
    logger.info("")        
    
    if coefficient is None:
        df["LA_corrected"] = df["LA"]
        df["LAmax_corrected"] = df["LAmax"]
        df["LAmin_corrected"] = df["LAmin"]

        if not "LC-LA" in df.columns:
            df["LC-LA"] = df["LC"] - df["LA"]
            df["LCeq-LAeq_corrected"] = df["LC-LA"]
        else:
            df["LCeq-LAeq_corrected"] = df["LC-LA"]
        return df
    
    if not "LC-LA" in df.columns and "LC" in df.columns and "LA" in df.columns:
        try:
            logger.info("Creating the LC-LA column")
            df["LC-LA"] = df["LC"] - df["LA"]
        except Exception as e:
            logger.error(f"Error creating LC-LA column: {e}")
            return df


    ######################################################################
    if sufix_string == "AUDIOMOTH":
        logger.info("Applying the correction to the AUDIOMOTH data")
        if "LA" in df.columns:
            logger.info("Applying the correction to the LA column")
            df["LA_corrected"] = df["LA"] - coefficient
            df["LAmax_corrected"] = df["LAmax"] - coefficient
            df["LAmin_corrected"] = df["LAmin"] - coefficient
            df["LCeq-LAeq_corrected"] = df["LC-LA"] - coefficient
        elif "LA" in df.columns:
            logger.info("Applying the correction to the LA column")
            df["LA_corrected"] = df["LA"] - coefficient
            df["LAmax_corrected"] = df["LAmax"] - coefficient
            df["LAmin_corrected"] = df["LAmin"] - coefficient
            df["LCeq-LAeq_corrected"] = df["LC-LA"] - coefficient
        else:
            logger.error("No column found to apply the correction for SONOMETRO data")
            return None

    if (sufix_string == "SONOMETRO") or (('raspberry' or 'ccmp') in sufix_string):
        logger.info("Applying the correction to the SONOMETRO data")
        if "LAeq" in df.columns:
            logger.info("Applying the correction to the LAeq column")
            df["LA_corrected"] = df["LAeq"] - coefficient
            df["LAmax_corrected"] = df["LAFmax"] - coefficient
            df["LAmin_corrected"] = df["LAFmin"] - coefficient
            df["LCeq-LAeq_corrected"] = df["LCeq-LAeq"] - coefficient
        elif "LA" in df.columns:
            logger.info("Applying the correction to the LA column")
            df["LA_corrected"] = df["LA"] - coefficient
            df["LAmax_corrected"] = df["LAmax"] - coefficient
            df["LAmin_corrected"] = df["LAmin"] - coefficient
            df["LCeq-LAeq_corrected"] = df["LC-LA"] - coefficient
        else:
            logger.error("No column found to apply the correction for SONOMETRO data")
            return None
    ######################################################################




    if 'LA' in df.columns:
        logger.info('Entering --> Entering LA')
        df['LA_corrected'] = df['LA'] - coefficient
        df['LAmax_corrected'] = df['LAmax'] - coefficient
        df['LAmin_corrected'] = df['LAmin'] - coefficient
        if 'LC-LA' in df.columns:
            logger.info('Creating LC-LA column')
            df['LCeq-LAeq_corrected'] = df['LC-LA'] - coefficient


    elif 'LC-LA' in df.columns:
        logger.info('Entering --> LC-LA')
        df['LC-LA_corrected'] = df['LC-LA'] - coefficient



    elif 'LAeq' in df.columns:
        logger.info('Entering --> LAeq')
        df['LA_corrected'] = df['LAeq'] - coefficient
        df['LAmax_corrected'] = df['LAFmax'] - coefficient
        df['LAmin_corrected'] = df['LAFmin'] - coefficient
        # df['LC_corrected'] = df['LCeq'] - coefficient


    
    elif 'LAFeq' in df.columns:
        logger.info('Entering --> LAeq')
        df['LA_corrected'] = df['LAFeq'] - coefficient
        df['LAmax_corrected'] = df['LAFmax'] - coefficient
        df['LAmin_corrected'] = df['LAFmin'] - coefficient

    elif 'Value' in df.columns:
        logger.info('Entering --> Value')
        df['LA_corrected'] = df['Value'] - coefficient

    elif '' in df.columns:
        logger.info('Entering --> nothing in the apply_db_correction!!')
        df['LA_corrected'] = df[''] - coefficient

    else:
        logger.error('No column found to apply the correction')

    return df



def change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger):
    try:
        df = df.sort_values(by='datetime')
        ####################################################################################
        ####################################################################################
        # if new_date and new_time are provided
        if new_date is not None and new_time is not None:
            logger.info("new_date and new_time are provided")
            start_datetime = pd.Timestamp(f"{new_date} {new_time}")
            df['datetime'] = [start_datetime + pd.Timedelta(seconds=i) for i in range(len(df))]
            logger.info(f"New datetime column created with new date and time: {start_datetime}")
        

        # new_date is provided but new_time is None
        elif new_date is not None and new_time is None:
            logger.info("new_date is provided but new_time is None")
            # get the first item in 'datetime' column
            first_time = df.iloc[0]['datetime'] 
            logger.info(f"First time in 'datetime' column: {first_time}")

            # string if necessary
            if not isinstance(first_time, str):
                first_time = first_time.strftime("%H:%M:%S")
            logger.info(f"First time in 'datetime' column: {first_time}")
            
            start_datetime = pd.Timestamp(f"{new_date} {first_time}")
            df['datetime'] = [start_datetime + pd.Timedelta(seconds=i) for i in range(len(df))]
            logger.info(f"New datetime column created with new date: {start_datetime}")


        # new_time is provided but new_date is None
        elif new_time is not None and new_date is None:
            logger.info("new_time is provided but new_date is None")
            # get the first item in 'datetime' column
            first_date = df.iloc[0]['datetime']
            logger.info(f"First date in 'datetime' column: {first_date}")

            #  string if necessary
            if not isinstance(first_date, str):
                first_date = first_date.strftime("%Y-%m-%d")
            logger.info(f"First date in 'datetime' column: {first_date}")

            start_datetime = pd.Timestamp(f"{first_date} {new_time}")
            df['datetime'] = [start_datetime + pd.Timedelta(seconds=i) for i in range(len(df))]


        else:
            logger.info("No new date or time provided.")



        
        ####################################################################################
        ## If there is a limit threshold date or time, trim the df with this information ##
        ####################################################################################
        if new_threshold_date is not None and new_threshold_time is not None:
            logger.info("[0] new_threshold_date and new_threshold_time are provided")

            threshold_datetime = pd.Timestamp(f"{new_threshold_date} {new_threshold_time}")
            df = df[df['datetime'] <= threshold_datetime]

            logger.info(f"Trimming the dataframe with threshold date: {threshold_datetime}")
            

        elif new_threshold_date is not None and new_threshold_time is None:
            logger.info("[1] new_threshold_date is provided but new_threshold_time is None")

            thr_first_time = df.iloc[0]['datetime']
            logger.info(f"First time in 'datetime' column: {thr_first_time}")
            
            if not isinstance(thr_first_time, str):
                thr_first_time = thr_first_time.strftime("%H:%M:%S")
            logger.info(f"First time in 'datetime' column: {thr_first_time}")

            threshold_datetime = pd.Timestamp(f"{new_threshold_date} {thr_first_time}")
            df = df[df['datetime'] <= threshold_datetime]
            logger.info(f"Trimming the dataframe with threshold date: {threshold_datetime}")


        elif new_threshold_date is None and new_threshold_time is not None:
            logger.info("[2] new_threshold_time is provided but new_threshold_date is None")

            thr_first_date = df.iloc[0]['datetime']
            logger.info(f"First date in 'datetime' column: {thr_first_date}")

            if not isinstance(thr_first_date, str):
                thr_first_date = thr_first_date.strftime("%Y-%m-%d")
            logger.info(f"First date in 'datetime' column: {thr_first_date}")

            threshold_datetime = pd.Timestamp(f"{thr_first_date} {new_threshold_time}")
            df = df[df['datetime'] <= threshold_datetime]
            logger.info(f"Trimming the dataframe with threshold date: {threshold_datetime}")



        else:
            logger.info("No threshold limit date or time provided.")


    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    return df




def transform_1h(df, columns_dict, logger, agg_period):
    """
    Transform the dataframe to 1 hour period, using the columns_dict to select the columns"""
    try:
        print(df)
        print(df.columns)
        df = df.dropna(subset=[columns_dict["LAEQ_COLUMN_COEFF"]])
        # pd to datetime
        # df = df.copy()
        # df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        # df = df.set_index("Timestamp", drop=False)
        # print(df)
        # exit()


        # if there is just LAEQ_COLUMN_COEFF, then we use it for all the columns, otherwise use the max and min
        if columns_dict["LAEQ_COLUMN"] == "Value":
            agg_funcs = {
                columns_dict["LAEQ_COLUMN_COEFF"]: [leq, lambda x: x.quantile(0.9)]
            }
            logger.info(
                f"Using the columns_dict: df_LAeq[{columns_dict['LAEQ_COLUMN_COEFF']}]"
            )

        else:
            agg_funcs = {
                columns_dict["LAEQ_COLUMN_COEFF"]: [leq, lambda x: x.quantile(0.9)],
                columns_dict["LAMAX_COLUMN_COEFF"]: "max",
                columns_dict["LAMIN_COLUMN_COEFF"]: "min",
                columns_dict["LC-LA_COLUMN_COEFF"]: leq,
            }

        logger.info(f"Using the agg_funcs: {agg_funcs}")
        df_LAeq = df.resample(f"{agg_period}s").agg(agg_funcs)
        df_LAeq.columns = ["_".join(col).strip() for col in df_LAeq.columns.values]
        # exit()

        # rename column
        if "LA_corrected_<lambda_0>" in df_LAeq.columns:
            df_LAeq = df_LAeq.rename(columns={"LA_corrected_<lambda_0>": "90percentile"})

        # logger.info(f"Resampled data with 90th percentile: {df_LAeq}")

        return df_LAeq

    except Exception as e:
        logger.error(f"Error transforming data to 1 hour period: {e}")
        return None




def transform_1h_pred(df, logger, agg_period):
    try:
        print(df)
        print(df.columns)

        df['datetime'] = pd.to_datetime(df['Timestamp'])
        df = df.set_index('datetime')
        df = df.dropna(subset=["LA_corrected"])
        df['NoisePort_Level_1'] = df['NoisePort_Level_1'].fillna("Unknown").astype(str)


        agg_funcs = {
            "LA_corrected": [leq, lambda x: x.quantile(0.9)],
            "LAmax_corrected": "max",
            "LAmin_corrected": "min",
            "LCeq-LAeq_corrected": leq,
        }
        logger.info(f"Using the agg_funcs: {agg_funcs}")



        df_LAeq = df.resample(f"{agg_period}s").agg(agg_funcs)
        df_LAeq.columns = [
            "_".join(col).strip() if isinstance(col, tuple) else col
            for col in df_LAeq.columns
        ]

        if "LA_corrected_<lambda_0>" in df_LAeq.columns:
            df_LAeq = df_LAeq.rename(columns={"LA_corrected_<lambda_0>": "90percentile"})




        ############################
        ############################
        mode_class = df['NoisePort_Level_1'].resample(f"{agg_period}s").agg(
            lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"
        )
        df_LAeq['class_predominant'] = mode_class

        # top n
        top_classes = df['NoisePort_Level_1'].value_counts().nlargest(8).index.tolist()


        for cls in top_classes:
            cls_mask = df['NoisePort_Level_1'] == cls

            
            #pct
            class_pct = cls_mask.astype(int).resample(f"{agg_period}s").sum() / df['NoisePort_Level_1'].resample(f"{agg_period}s").count()
            df_LAeq[f'class_{cls}_pct'] = class_pct


            #leq
            class_LA = df[cls_mask][['LA_corrected']].resample(f"{agg_period}s").agg(leq)
            #not really necessary, but just in case
            class_pct_aligned = class_pct.reindex(class_LA.index)
            class_LA_aligned = class_LA.copy()

            class_LA_aligned['LA_corrected'] = class_LA_aligned['LA_corrected'].mask(class_pct_aligned == 0)
            df_LAeq[f'class_{cls}_LAeq'] = class_LA_aligned['LA_corrected']



        # df_LAeq = df_LAeq[df_LAeq['class_predominant'] != "Unknown"]
        # df_LAeq = df_LAeq.drop(columns=['class_Unknown_pct', 'class_Unknown_LAeq'], errors='ignore')
        df_LAeq = df_LAeq.round(2)

        # df_LAeq.to_csv('df_pred_leq_perce.csv')
        logger.info("Successfully transformed prediction dataframe to hourly aggregation.")
        return df_LAeq

    except Exception as e:
        logger.error(f"Error transforming data to 1 hour period: {e}")
        return None




def transformation(df, logger, oca_limits):
    # transformation
    if not 'datetime' in df.columns : df = add_datetime_columns(df, logger, date_col="datetime")
    df = df.sort_values("datetime")
    df.set_index("datetime", inplace=True, drop=False)
    df = df.rename(columns={"datetime": "date_time"})
    
    
    # add indicators column
    logger.info(f"Adding indicators column")
    if "hour" not in df.columns: df = insert_dates(df)
    df["indicador_str"] = df.apply(lambda x: evaluation_period_str(x["hour"]), axis=1)
    # add nights column
    logger.info(f"Adding nights column")
    df["night_str"] = df.apply(
        lambda x: add_night_column(x["hour"], x["weekday"]), axis=1
    )

    # removing nan values
    df = df.dropna()
    
    
    # oca column
    df['oca'] = df['hour'].apply(
                        lambda h: db_limit(h, **oca_limits)
                   )

    return df

def list_git_tags():
    try:
        tags = tags = subprocess.check_output(["git", "tag"]).strip().decode()
        return tags.split('\n')
    except subprocess.CalledProcessError:
        return None


def select_tag(tags, logger):
    for i, tag in enumerate(tags):
        logger.info(f"{i}: {tag}")
    
    choice = int(input("Select the tag to use: "))
    tag_selected = tags[choice]
    tag_selected = tag_selected.replace(".", "_")
    return tag_selected


def get_stable_version(logger):
    tags = list_git_tags()
    # get the latest stable version
    tag_selected = tags[-1]
    logger.info(f"Latest stable version: {tag_selected}")
    
    tag_selected = tag_selected.replace(".", "_")
    logger.info(f"Latest stable version string: {tag_selected}")
    return tag_selected

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
    

def collect_folders(input_folder,coeffs_path, change_time_flag,label_source_type, logger,point_filter):
    folders, coefficients, date_time, threshold = [], {}, {}, {}
    
    #Lectura de los coeficientes desde un JSON para no tener que escribirlos por consola
    with open(coeffs_path,'r') as f:
        coeffs = json.load(f)

    if "raspberry" or 'ccmp' in label_source_type:
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

def leq_safe(series):
    vals = series.dropna().values
    if len(vals) == 0:
        return pd.NA
    return leq(vals)

def agg_hour(group):
    result = {}
    
    if "id_micro" in group.columns:
        ids = group["id_micro"].dropna()
        if not ids.empty:
            result["id_micro"] = ids.iloc[0]
        else:
            result["id_micro"] = pd.NA

    """
    leq_cols = [
        "LA", "LC", "LZ", "LAmax", "LAmin",
        "12.6Hz", "15.8Hz", "20.0Hz", "25.1Hz", "31.6Hz", "39.8Hz",
        "50.1Hz", "63.1Hz", "79.4Hz", "100.0Hz", "125.9Hz", "158.5Hz",
        "199.5Hz", "251.2Hz", "316.2Hz", "398.1Hz", "501.2Hz", "631.0Hz",
        "794.3Hz", "1000.0Hz", "1258.9Hz", "1584.9Hz", "1995.3Hz",
        "2511.9Hz", "3162.3Hz", "3981.1Hz", "5011.9Hz", "6309.6Hz",
        "7943.3Hz", "10000.0Hz", "12589.3Hz", "15848.9Hz",
        "peak_leq",
    ]
    """
    leq_cols_V2 = [
    "LA", "LC", "LZ", "LAmax", "LAmin",

    "12.59Hz",
    "15.85Hz",
    "19.95Hz",
    "25.12Hz",
    "31.62Hz",
    "39.81Hz",

    "50.12Hz",
    "63.1Hz",
    "79.43Hz",
    "100.00Hz",
    "125.89Hz",
    "158.49Hz",

    "199.53Hz",
    "251.19Hz",
    "316.23Hz",
    "398.11Hz",
    "501.19Hz",
    "630.96Hz",
    "794.33Hz",
    "1000.00Hz",
    "1258.93Hz",

    "1584.89Hz",
    "1995.26Hz",
    "2511.89Hz",
    "3162.28Hz",
    "3981.07Hz",
    "5011.87Hz",
    "6309.57Hz",
    "7943.3Hz",

    "10000.00Hz",
    "12589.25Hz",
    "15848.93Hz",

    "peak_leq",
    ]
    for col in leq_cols_V2:
        if col in group:
            result[col] = leq_safe(group[col])


    if "LA" in group:
        vals = group["LA"].dropna().values
        if len(vals) > 0:
            result["90percentile"] = np.percentile(vals, 90)
        else:
            result["90percentile"] = pd.NA

    # average
    if "LC-LA" in group:
        result["LC-LA_mean"] = group["LC-LA"].mean()


    # n peaks per hour
    if "is_peak" in group:
        result["n_peaks"] = group["is_peak"].fillna(0).astype(bool).sum()


    # clase mas repetida
    if "NoisePort_Level_1" in group:
        cats = group["NoisePort_Level_1"].dropna()
        if not cats.empty:
            mode_cats = cats.mode()
            result["NoisePort_Level_1_mode"] = mode_cats.iloc[0]
        else:
            result["NoisePort_Level_1_mode"] = pd.NA

    if "Prediction_1" in group:
        cats = group["Prediction_1"].dropna()
        if not cats.empty:
            mode_cats = cats.mode()
            result["Prediction_1_mode"] = mode_cats.iloc[0]
        else:
            result["Prediction_1_mode"] = pd.NA

    return pd.Series(result)

