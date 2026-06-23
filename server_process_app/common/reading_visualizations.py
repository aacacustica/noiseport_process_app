from datetime import datetime
import os
import pandas as pd
from utils_vi import *
from tqdm import tqdm
from io import StringIO




def get_data_bilbo(file_path: str, logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    try:
        df = pd.read_csv(file_path)
    except:
        df = pd.read_csv(file_path, encoding='latin1', sep=';')

    try:
        df['datetime'] = pd.to_datetime(df['datetime'], errors='raise')
    except KeyError:
        logger.info("No 'datetime' column found in CSV.")
    except pd.errors.OutOfBoundsDatetime:
        logger.error("Error converting 'datetime' column.")
    
    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    return df



def get_data_814(file_path: str, logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    try:
        df = pd.read_csv(file_path, header=16, encoding='latin1')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, header=16)
   
    if "Leq" not in df.columns:
        df = pd.read_csv(file_path, header=19, sep=';', encoding='latin1')
    df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])

    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
    
    except Exception as e:
        logger.info(f"Error: {e}")
        return None
    return df




def get_data_lx_ES(file_path: str, logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    df = pd.read_excel(file_path, sheet_name='Historia del tiempo')
    df['datetime'] = pd.to_datetime(df['Fecha'])

    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

    return df




def get_data_lx_EN(file_path: str,logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    df = pd.read_excel(file_path,sheet_name=4)
    df['datetime'] = pd.to_datetime(df['Date'])

    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    return df



def get_data_824(file_path: str,logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    df = pd.read_csv(file_path, sep=',', encoding='latin1', header=15)
    df = df.dropna(axis=1)
    
    if "Leq" not in df.columns:
        df = pd.read_csv(file_path,header=15, sep=',')
    
    df['datetime'] = pd.to_datetime(df['Date'] + ' '+ df['Time'])

    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    
    return df




def read_sv307_time_history(csv_path, logger):
    time_history_df = None
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        
        time_history_start = None
        for i, line in enumerate(lines):
            if "TIME HISTORY" in line.upper():
                time_history_start = i
                break

        if time_history_start is None:
            raise ValueError("TIME HISTORY section not found.")

        
        header_index = None
        for i in range(time_history_start, len(lines)):
            if lines[i].strip().startswith("Time"):
                header_index = i
                break

        if header_index is None:
            raise ValueError("TIME HISTORY header line not found.")



        data_lines = lines[header_index:]
        buffer = StringIO("".join(data_lines))
        time_history_df = pd.read_csv(buffer, sep=",|\t|;", engine='python')
        time_history_df = time_history_df.loc[:, ~time_history_df.columns.str.contains('^Unnamed')]
        # remove the lastest 8 rows if there is a row called 'MEASUREMENT INFORMATION'
        if time_history_df.iloc[-8]['Time'] == 'MEASUREMENT INFORMATION':
            # remove the last 8 rows
            time_history_df = time_history_df[:-8]    
        
        return time_history_df


    except Exception as e:
        logger.error(f"Error reading SV307 time history from {csv_path}: {e}")
        return None
    


def get_data_SV307_new(file_path: str, logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    folder_path = os.path.dirname(file_path)
    logger.info(f"Folder: {folder_path}")
    point = folder_path.split('\\')[-2]


    if not os.path.exists(folder_path):
        logger.error(f"Folder {folder_path} does not exist")
        return None

    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    logger.info(f"CSV files in the folder: {len(files)}")

    csv_final_path = os.path.join(folder_path, f'{point}.csv')


    if os.path.exists(csv_final_path):
        logger.info(f"CSV file already exists: {csv_final_path}")
        df = pd.read_csv(csv_final_path)
        logger.info(f"CSV file read successfully, length: {len(df)}")
        return df

    else:
        if len(files) == 1:
            logger.info("Only one file in the folder, reading it directly")
            df = read_sv307_time_history(file_path, logger)
            if df is None:
                return None
            


        else:
            logger.info("Multiple CSV files found, reading and concatenating")
            df_all = []
            for fname in files:
                fpath = os.path.join(folder_path, fname)
                df_temp = read_sv307_time_history(fpath, logger)
                if df_temp is not None:
                    df_all.append(df_temp)
                

            if not df_all:
                logger.error("No valid CSV files could be read.")
                return None

            df = pd.concat(df_all, ignore_index=True)
            df = df.sort_values(by='Time')

        # time columns formar --> 01/04/2025 12:47:00
        df['datetime'] = pd.to_datetime(df['Time'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        
        # remove columns with nan values
        df = df.dropna(axis=1, how='all')

        try:    
            logger.info("Changing date and time")
            df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
        
        
        df.rename(columns={'LAeq (Ch1, P1) [dB]': 'LAeq',
                        'LAFmax (Ch1, P1) [dB]': 'LAFmax',
                        'LAFmin (Ch1, P1) [dB]': 'LAFmin',
                        'LCeq (Ch1, P2) [dB]': 'LCeq'}, inplace=True)


        df["LCeq-LAeq"] = df["LCeq"] - df["LAeq"]
        logger.info(f"Length of the combined dataframe: {len(df)}")


        # saving the dataframe to a csv file
        if selected_folder is not None:
            logger.info(f"Saving the dataframe to {csv_final_path}")
            try:
                df.to_csv(csv_final_path, index=False)
                logger.info("CSV file saved successfully.")
            except Exception as e:
                logger.error(f"Error saving CSV file: {e}")
                return None
            
    return df







def get_data_SV307(file_path: str,logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    logger.info("Testing how many SV307 files are in the folder")
    # testing if there are more than 1 csv file in the folder
    folder_path = file_path.split('\\')[:-1]
    # joining the elements
    folder_path = '\\'.join(folder_path)

    # counting how many csv files are in the folder:
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    logger.info(f"Number of csv files in the folder: {len(csv_files)}")
    
    if len(csv_files) > 1:
        logger.info("Concatenating all the csv files in the folder and ordering them by date")
        df_all = []
        for file in csv_files:
            file_path = os.path.join(folder_path, file)
            try:
                df = read_SV307(file_path, logger)
                logger.info(f"Reading file: {file_path}")
            except Exception as e:
                filename = file_path.split('\\')[-1]
                logger.error(f"Error reading file: {filename}")
                logger.error(f"Error: {e}")
                continue

            df_all.append(df)

        df = pd.concat(df_all)
        # order it by datetime
        df = df.sort_values(by='datetime')
        # remove column name Unnamed:
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    else:
        # read the only csv file in the folder
        try:
            df = read_SV307(file_path, logger)
        except Exception as e:
            logger.error(f"Error reading file: {file_path}")
            logger.error(f"Error: {e}")
            return None
        
    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
        logger.info("Changing date and time")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    
    
    df.rename(columns={'LAeq (Ch1, P1) [dB]': 'LAeq',
                       'LAFmax (Ch1, P1) [dB]': 'LAFmax',
                       'LAFmin (Ch1, P1) [dB]': 'LAFmin'}, inplace=True)
    
    # df = df[['datetime','LAeq','LAFmax','LAFmin']]
    logger.info(f"Final length of the file: {len(df)}")
    return df



def get_data_audiomoth(file_path: str,logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    df = pd.read_csv(file_path)
    if 'Time' in df.columns:
        df['datetime'] = pd.to_datetime(df['Time'], format='%Y-%m-%d_%H:%M:%S')
    else:
        df['datetime'] = pd.to_datetime(df['date'])
    

    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    
    return df 



def get_data_cesva(measurement_folder: str, logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    if os.path.isfile(measurement_folder):
        cesva_index = measurement_folder.find('CESVA')
        if cesva_index != -1:
            measurement_folder = measurement_folder[:cesva_index] + 'CESVA'
        else:
            raise ValueError("CESVA folder not found in the file path.")

    elif 'CESVA' not in measurement_folder:
        raise ValueError("The directory does not contain 'CESVA'.")
    
    cesva_files = []
    cols_to_use = ['Date hour','Elapsed t','LA1s','LAFmax1s','LAFmin1s']
    
    for root, dirs, files in os.walk(measurement_folder, topdown=False):
        for name in files:
            if name.endswith('.csv'):
                cesva_files.append(os.path.join(root, name))
    
    df_all = pd.DataFrame()

    for file_path in cesva_files:
        try:
            df = pd.read_csv(file_path,sep=';',header=11,decimal=',', usecols=cols_to_use)
            df.dropna(subset=['Elapsed t'],inplace=True) 
        
        except Exception as e:
            pass
        try:
            df = pd.read_csv(file_path,sep=';',header=12,decimal=',',usecols=cols_to_use)
            df.dropna(subset=['Elapsed t'],inplace=True)   
        
        except Exception as e: 
            pass
        
        #df = df[['Date hour','Elapsed t','LA1s','LAFmax1s','LAFmin1s']]
        df_all = pd.concat([df_all,df])
    
    df = df_all.copy()
    del df_all
    for col in df.columns:
        if col not in  ["Date hour", "Elapsed t"]:
            df[col] = pd.to_numeric(df[col])
    
    df['datetime'] = df.apply(lambda x: datetime.strptime(x['Date hour'], '%d/%m/%Y %H:%M:%S'),axis=1)
    df['datetime'] = pd.to_datetime(df['datetime'])

    try:    
        df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    
    return df



def get_data_bruel_kjaer(measurement_folder: str, logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    if os.path.isfile(measurement_folder):
        # remove last part of the path to get the folder
        measurement_folder = measurement_folder.split('\\')[:-1]
        #join
        measurement_folder = '\\'.join(measurement_folder)

        #check if the folder exists
        if not os.path.exists(measurement_folder):
            logger.error(f"Folder {measurement_folder} does not exist")
            return None

        
        files = os.listdir(measurement_folder)
        dfs = []
        sheet_name = 'LoggedBB'

        for fname in files:
            if not fname.endswith('.xlsx'):
                continue

            file_path = os.path.join(measurement_folder, fname)
            try:
                logger.info(f"Reading files...")
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                df['datetime'] = pd.to_datetime(df["Start Time"], format='%d/%m/%Y %H:%M:%S')
                dfs.append(df)

            except Exception as e:
                logger.error(f"Error reading file: {file_path} --> {e}")
                continue

        if dfs:
            df_all = pd.concat(dfs, ignore_index=True)
        else:
            df_all = pd.DataFrame()
        
        # sort the dataframe by datetime
        df_all = df_all.sort_values(by='datetime')

        return df_all
        










def read_tenerife_TCT(file_path: str, logger):
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Error reading file: {file_path}")

    try:
        # detect the time zone in the Timestamp column
        if 'Timestamp' not in df.columns:
            return None
        # if there are +__:__, take that as string
        if df['Timestamp'].str.contains(r'\+\d{2}:\d{2}').any():
            time_zone = df['Timestamp'].str.extract(r'(\+\d{2}:\d{2})')[0].iloc[0]
            df['time_zone'] = time_zone
            df['Timestamp'] = df['Timestamp'].str.replace(time_zone, '', regex=False)
    except KeyError:
        logger.error("KeyError: 'Timestamp' column not found in the dataframe.")
        return None


    try:
        # date_time_format 2025-04-06 06:00:38
        df = df[pd.to_datetime(df['Timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce').notnull()]
        df['datetime'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d %H:%M:%S')


    except KeyError:
        logger.error("KeyError: 'Timestamp' column not found in the dataframe.")
        return None
    
    return df



def get_data_tenerife_TCT(folder_path: str,logger, new_date=None, new_time=None, new_threshold_date=None, new_threshold_time=None, selected_folder=None):
    logger.info("")
    logger.info("get_data_tenerife_TCT function called")
    logger.info(f"Folder path: {folder_path}")
    point_folder = folder_path.split('\\')[-2]
    logger.info(f"Point folder: {point_folder}")


    if selected_folder is ACOUSTIC_PARAMS_FOLDER:
        csv_final_path = os.path.join(folder_path, f'{point_folder}_{ACOUSTIC_PARAMS_FOLDER}.csv')
        logger.info(f"CSV final path: {csv_final_path}")
    elif selected_folder is PREDICTION_LITTLE_FOLDER:
        csv_final_path = os.path.join(folder_path, f'{point_folder}_{PREDICTION_LITTLE_FOLDER}.csv')
        logger.info(f"CSV final path: {csv_final_path}")
    else:
        logger.error("Selected folder is not valid. Please select either ACOUSTIC_PARAMS_FOLDER or PREDICTION_LITTLE_FOLDER.")
        return None

    
    # getting the acoustic params csv files
    logger.info("Searching for csv files")
    csv_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if selected_folder is ACOUSTIC_PARAMS_FOLDER:
                if file.endswith('.csv'):
                    csv_path = os.path.abspath(os.path.join(root, file))
                    csv_files.append(csv_path)
            elif selected_folder is PREDICTION_LITTLE_FOLDER:
                if file.endswith('_w_1.0.csv'):
                    csv_path = os.path.abspath(os.path.join(root, file))
                    csv_files.append(csv_path)
            else:
                logger.error("Selected folder is not valid. Please select either ACOUSTIC_PARAMS_FOLDER or PREDICTION_LITTLE_FOLDER.")
                return None
    logger.info(f"Number of csv files in the folder: {len(csv_files)}")



    ##########################################
    # read all csv files in the folder #
    ##########################################
    if len(csv_files) > 1:
        logger.info("Concatenating all the csv files in the folder and ordering them by date")
        df_all = []
        for file in csv_files:
            csv_file_path = os.path.join(folder_path, file)
            try:
                df = read_tenerife_TCT(csv_file_path, logger)
            except Exception as e:
                logger.error(f"Error reading file: {csv_file_path}")
                logger.error(f"Error: {e}")
                continue

            df_all.append(df)

        df = pd.concat(df_all)
        df = df.sort_values(by='datetime')


        try:    
            df = change_date_and_time(df, new_date, new_time, new_threshold_date, new_threshold_time, logger)
            logger.info("Changing date and time")
        
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
        


        if selected_folder is ACOUSTIC_PARAMS_FOLDER:
            logger.info("Creating LC, LA, and LC-LA columns")
            try:
                # create LC-LA colum --> LC - LA = LC_LA.
                df['LC-LA'] = df['LC'] - df['LA']
            except KeyError:
                logger.error("KeyError: 'LC' or 'LA' column not found in the dataframe.")
                return None
        else:
            logger.info("No need to create LC, LA, and LC-LA columns for prediction files.")

        logger.info(f"Final length of the file: {len(df)}")


        try:
            # save the file
            logger.info(f"Saving CSV file...")
            df.to_csv(csv_final_path, index=False)
            logger.info("CSV file saved successfully.")
        except Exception as e:
            logger.error(f"Error saving CSV file: {e}")
            return None



    ##########################################
    # read the only csv file in the folder #
    ##########################################
    else:
        try:
            logger.info("Reading the only csv file in the folder")
            df = read_tenerife_TCT(folder_path, logger)
            logger.info(f"{folder_path} file read successfully")
        except Exception as e:
            logger.error(f"Error reading file: {folder_path}")
            logger.error(f"Error: {e}")
            return None
    
    return df
