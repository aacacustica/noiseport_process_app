# relative path to the yamnet class map, urban taxonomy and port taxonomy
#RELATIVE_PATH_YAMNET_MAP = r"\AAC - CENTRO DE ACUSTICA APLICADA, S.L\I + D + i - Documentos\Modelos_IA\AAC_IA_Puerto\yamnet_class_AAC_v3_0.csv"
#RELATIVE_PATH_TAXONOMY_URBAN = r"\AAC - CENTRO DE ACUSTICA APLICADA, S.L\I + D + i - Documentos\Modelos_IA\taxonomies_json\urban_taxonomy_map_v1_0.json"
#RELATIVE_PATH_TAXONOMY_PORT = r"\AAC - CENTRO DE ACUSTICA APLICADA, S.L\I + D + i - Documentos\Modelos_IA\taxonomies_json\port_1_taxonomy_mapping_v2.0.json"


# PATH TO THE CSV FOR SHIP AT THE DOCK
#RELATIVE_PATH_SHIPS_1H = r"/home/aac/EMBARQUES/TCT/CONTENEDORES_TCT_embarques_1h.csv"
#RELATIVE_PATH_SHIPS_15MIN = r"/home/aac/EMBARQUES/TCT/CONTENEDORES_TCT_embarques_15min.csv"
#RELATIVE_PATH_SHIPS_1S = r"/home/aac/EMBARQUES/TCT/CONTENEDORES_TCT_embarques_1s.csv"

# Remove start time and end time
REMOVE_START_TIME = 900
REMOVE_END_TIME = 900


# TENERIFE TIME ZONE (-1 HOUR)
TENERIFE_TIMEZONE = False

# TIME PLOT dB limits
DB_UPPER_LIMIT = 105
DB_LOWER_LIMIT = 30
HOUR_INTERVAL = 5


# HOUR INTERVAL FOR DAY EVOLUTION PLOTS
DB_RANGE_TOP = 105
DB_RANGE_BOTTOM = 30
BD_RANGE_STEP = 5


#Font size
SMALL_SIZE = 10
MEDIUM_SIZE = 12
BIGGER_SIZE = 20
BIGGEST_SIZE = 22
BIGGEST_15_MIN_SIZE = 24
BIGGEST_PREDICT_MIN_SIZE = 50
BIGGEST_PREDICT_TITLE_SIZE = 60



# Time limits for evaluation indicadores
LD_SECONDS = 21600
LE_SECONDS = 7200
LN_SECONDS = 14400



#########################
#PROBABILITY THRESHOLDS
PROBABILITY_THRESHOLD = 0.3



########################
# FOLDER RESULT NAMES
########################
ACOUSTIC_PARAMS_FOLDER = "acoustics"
ACOUSTIC_PARAMS_QUERY_FOLDER = "acoustic_params_query"
PREDICTION_LITTLE_FOLDER = "predictions"
SONOMETER_FOLDER = "SONOMETRO"
AUDIOMOTH_FOLDER = "audiomoth"

ACOUSTIC_PARAMS_FOLDER_NEW = "acoustics"
ACOUSTIC_PARAMS_QUERY_FOLDER_NEW = "acoustics_queries"
PREDICTION_LITTLE_FOLDER_NEW = "predictions"
PREDICTION_QUERY_FOLDER_NEW = "prediction_queries"


###################################################################
### PLOTTING FLAGS
###################################################################
# Plotting Flags there are 15 flags to plot the following plots
PLOT_NIGHT_EVOLUTION = True
PLOT_NIGHT_EVOLUTION_WEEK = True

PLOT_NIGHT_EVOLUTION_15_MIN = True
PLOT_NIGHT_EVOLUTION_15_MIN_WEEK = False


# prediction
PLOT_PREDIC_LAEQ_MEAN = False
PLOT_PREDIC_LAEQ_MEAN_WEEK = False
PLOT_PREDIC_LAEQ_MEAN_4H = False
PLOT_PREDIC_LAEQ_DAY = True


PLOT_PREDIC_LAEQ_15_MIN_PERIOD = False
PLOT_PREDIC_LAEQ_15_MIN_PERIOD_WEEK = False


PLOT_PREDIC_LAEQ_15_MIN_4H = False
PLOT_PREDIC_LAEQ_15_MIN_4H_WEEK = False

PLOT_PREDICTION_STACK_BAR = False
PLOT_PREDICTION_STACK_BAR_WEEK = False

PLOT_PREDICTION_MAP = False # False
PLOT_PREDICTION_MAP_WEEK = False


PLOT_TREE_MAP = False
PLOT_TREE_MAP_WEEK = False




# Plotting Flags there are 15 flags to plot the following plots
PLOT_MAKE_TIME_PLOT = True
PLOT_MAKE_TIME_PLOT_WEEK = False

PLOT_HEATMAP_EVOLUTION_HOUR = True 
PLOT_HEATMAP_EVOLUTION_HOUR_WEEK = False

PLOT_HEATMAP_EVOLUTION_15_MIN = True 
PLOT_HEATMAP_EVOLUTION_15_MIN_WEEK = False 

PLOT_INDICADORES_HEATMAP = True
PLOT_INDICADORES_HEATMAP_WEEK = False



PLOT_DAY_EVOLUTION = True
PLOT_DAY_EVOLUTION_WEEK = False

PLOT_PERIOD_EVOLUTION = True
PLOT_PERIOD_EVOLUTION_WEEK = False

PLOT_SPECTROGRAM_1_3 = False

#### USING OCA
SHOW_OCA = True
########################




########################## 
# PLOTTING ALARMS 
# ########################
OCA_ALARM = True
OCA_ALARM_WEEK = False

LMAX_ALARM = True
LMAX_ALARM_WEEK = False

LC_LA_ALARM = True
LC_LA_ALARM_WEEK = False

L90_ALARM = False
L90_ALARM_WEEK = False

L90_ALARM_DYNAMIC = True
L90_ALARM_DYNAMIC_WEEK = False

FREQUENCY_COMPOSITION = True
FREQUENCY_COMPOSITION_WEEK = False

TONAL_FREQUENCY = True
TONAL_FREQUENCY_WEEK = False


# peak
PLOT_PEAK_DISTRIBUTION_HEATMAP = True
PLOT_PEAK_DISTRIBUTION_HEATMAP_WEEK = False


PLOT_PEAK_DISTRIBUTION = False
PLOT_PEAK_DISTRIBUTION_WEEK = False


PLOT_PEAK_DENSITY_DISTRIBUTION = False
PLOT_PEAK_DENSITY_DISTRIBUTION_WEEK = False



# predictions
PLOT_PEAK_PREDIC_LAEQ_MEAN = False
PLOT_PEAK_PREDIC_LAEQ_MEAN_WEEK = False

PLOT_PEAK_BOX_PLOT_PREDICTION = False
PLOT_PEAK_BOX_PLOT_PREDICTION_WEEK = False

PLOT_PEAK_HEATMAT_PREDICTION = False
PLOT_PEAK_HEATMAT_PREDICTION_WEEK = False




######################### ALAMARMS ############################

# CORRECTION FOR FREQUENCY COMPOSITION
LOW_FREQ_CORRECTION = -21
MEDIUM_FREQ_CORRECTION = -3
HIGH_FREQ_CORRECTION = +1

# '12.6Hz', '15.8Hz', '20.0Hz', '25.1Hz', '31.6Hz',
# '39.8Hz', '50.1Hz', '63.1Hz', '79.4Hz', '100.0Hz', '125.9Hz', '158.5Hz',
# '199.5Hz', '251.2Hz', '316.2Hz', '398.1Hz', '501.2Hz', '631.0Hz',
# '794.3Hz', '1000.0Hz', '1258.9Hz', '1584.9Hz', '1995.3Hz', '2511.9Hz',
# '3162.3Hz', '3981.1Hz', '5011.9Hz', '6309.6Hz', '7943.3Hz', '10000.0Hz',
# '12589.3Hz', '15848.9Hz'


#LOW_FREQ_BANDS = ['50.1Hz', '63.1Hz', '79.4Hz', '100.0Hz', '125.9Hz', '158.5Hz']
#MEDIUM_FREQ_BANDS = ['199.5Hz', '251.2Hz', '316.2Hz', '398.1Hz', '501.29Hz', '631.0Hz', '794.3Hz', '1000.0Hz', '1258.9Hz']
#HIGH_FREQ_BANDS = ['1584.9Hz','1995.3Hz', '2511.9Hz', '3162.3Hz', '3981.1Hz', '5011.9Hz', '6309.6Hz', '7943.3Hz', '10000.0Hz', '12589.3Hz']

LOW_FREQ_BANDS = ['50.12Hz', '63.10Hz', '79.43Hz', '100.00Hz', '125.89Hz', '158.49Hz']
MEDIUM_FREQ_BANDS = ['199.53Hz', '251.19Hz', '316.23Hz', '398.11Hz', '501.19Hz', '630.96Hz', '794.33Hz', '1000.00Hz', '1258.93Hz']
HIGH_FREQ_BANDS = ['1584.89Hz','1995.26Hz', '2511.89Hz', '3162.28Hz', '3981.07Hz', '5011.87Hz', '6309.57Hz']

# tonal freq
COLUMNS_DISCARD = ["LA", "LC", "LZ", "LAmax", "LAmin", "filename", "date"]


# BANDS FOR TONAL_FREQ
# LOW_BAND_TONAL_FREQ = ["12.40Hz", "15.62Hz",  "19.69Hz", "24.80Hz", "31.25Hz", "39.37Hz", "49.61Hz", "62.50Hz", "78.75Hz", "99.21Hz", "125.00Hz"]
# MEDIUM_BAND_TONAL_FREQ = ["157.49Hz", "198.43Hz", "250.00Hz", "314.98Hz", "396.85Hz"]
# HIGH_BAND_TONAL_FREQ = ["500.00Hz", "629.96Hz", "793.70Hz", "1000.00Hz", "1259.92Hz", "1587.40Hz", "2000.00Hz", "2519.84Hz", "3174.80Hz", "4000.00Hz", "5039.68Hz", "6349.60Hz", "8000.00Hz", "10079.37Hz", "12699.21Hz", "16000.00Hz", "20158.74Hz"]

#LOW_BAND_TONAL_FREQ = ['12.6Hz', '15.8Hz', '20.0Hz', '25.1Hz', '31.6Hz', '39.8Hz', '50.1Hz', '63.1Hz', '79.4Hz', '100.0Hz', '125.9Hz']
#MEDIUM_BAND_TONAL_FREQ = ['158.5Hz', '199.5Hz', '251.2Hz', '316.2Hz', '398.1Hz']
#HIGH_BAND_TONAL_FREQ = ['501.2Hz', '631.0Hz', '794.3Hz', '1000.0Hz', '1258.9Hz', '1584.9Hz', '1995.3Hz', '2511.9Hz', '3162.3Hz', '3981.1Hz', '5011.9Hz', '6309.6Hz', '7943.3Hz', '10000.0Hz', '12589.3Hz', '15848.9Hz']

"""
'25.12Hz', '31.62Hz', '39.81Hz',
       '50.12Hz', '63.10Hz', '79.43Hz', '100.00Hz', '125.89Hz', '158.49Hz',
       '199.53Hz', '251.19Hz', '316.23Hz', '398.11Hz', '501.19Hz', '630.96Hz',
       '794.33Hz', '1000.00Hz', '1258.93Hz', '1584.89Hz', '1995.26Hz',
       '2511.89Hz', '3162.28Hz', '3981.07Hz', '5011.87Hz', '6309.57Hz',
"""
LOW_BAND_TONAL_FREQ = ['25.12Hz', '31.62Hz', '39.81Hz', '50.12Hz', '63.10Hz', '79.43Hz', '100.00Hz', '125.89Hz']
MEDIUM_BAND_TONAL_FREQ = ['158.49Hz', '199.53Hz', '251.19Hz', '316.23Hz', '398.11Hz']
HIGH_BAND_TONAL_FREQ = ['501.19Hz', '630.96Hz', '794.33Hz', '1000.00Hz', '1258.93Hz', '1584.89Hz', '1995.26Hz', '2511.89Hz', '3162.28Hz', '3981.07Hz', '5011.87Hz', '6309.57Hz']

# frequency thresholds
LOW_BAND_THRESHOLD = 15
MEDIUM_BAND_THRESHOLD = 8
HIGH_BAND_THRESHOLD = 5

# Desire order bands
# TONAL_FREQ_BANDS_ORDERED = ["12.40Hz", "15.62Hz", "19.69Hz", "24.80Hz", "31.25Hz", "39.37Hz", "49.61Hz", "62.50Hz", "78.75Hz", "99.21Hz", "125.00Hz", "157.49Hz", "198.43Hz", "250.00Hz", "314.98Hz", "396.85Hz", "500.00Hz", "629.96Hz", "793.70Hz", "1000.00Hz", "1259.92Hz", "1587.40Hz", "2000.00Hz", "2519.84Hz", "3174.80Hz", "4000.00Hz", "5039.68Hz", "6349.60Hz", "8000.00Hz", "10079.37Hz", "12699.21Hz", "16000.00Hz"]
#TONAL_FREQ_BANDS_ORDERED = ['12.6Hz', '15.8Hz', '20.0Hz', '25.1Hz', '31.6Hz','39.8Hz', '50.1Hz', '63.1Hz', '79.4Hz', '100.0Hz', '125.9Hz', '158.5Hz','199.5Hz', '251.2Hz', '316.2Hz', '398.1Hz', '501.2Hz', '631.0Hz', '794.3Hz', '1000.0Hz', '1258.9Hz', '1584.9Hz', '1995.3Hz', '2511.9Hz', '3162.3Hz', '3981.1Hz', '5011.9Hz', '6309.6Hz', '7943.3Hz', '10000.0Hz','12589.3Hz', '15848.9Hz']
TONAL_FREQ_BANDS_ORDERED = ['25.12Hz', '31.62Hz', '39.81Hz','50.12Hz', '63.10Hz', '79.43Hz', '100.00Hz', '125.89Hz', '158.49Hz','199.53Hz', '251.19Hz', '316.23Hz', '398.11Hz', '501.19Hz', '630.96Hz','794.33Hz', '1000.00Hz', '1258.93Hz', '1584.89Hz', '1995.26Hz','2511.89Hz', '3162.28Hz', '3981.07Hz', '5011.87Hz', '6309.57Hz']



##################
# PEAK ALARMS
##################
WINDOW_SIZE = 30  # seconds
PROMINENCE = 1
WIDTH = 1
TOP_PREDIC = 3
ADDING_THRESHOLD = 10  # seconds




######################## OCA LIMITS #########################################
#############
OCA_RESIDENTIAL = {
    'ld_limit': 65,
    'le_limit': 65,
    'ln_limit': 55,
}

OCA_LEISURE = {
    'ld_limit': 73,
    'le_limit': 73,
    'ln_limit': 63,
}

OCA_OFFICE = {
    'ld_limit': 70,
    'le_limit': 70,
    'ln_limit': 65,
}

OCA_INDUSTRIAL = {
    'ld_limit': 75,
    'le_limit': 75,
    'ln_limit': 65,
}

OCA_CULTURE = {
    'ld_limit': 60,
    'le_limit': 60,
    'ln_limit': 50,
}




######################## UTILS THINGS #####################################
WEEKDAY_TRANSLATION = {
        "Monday": " Lunes",
        "Tuesday": " Martes",
        "Wednesday": " Miércoles",
        "Thursday": " Jueves",
        "Friday": " Viernes",
        "Saturday": " Sábado",
        "Sunday": " Domingo"
    }




######################## SLM COLUMN MAPS #####################################
"""
Sonometer column maps for different SLMs. The column maps are used to
   standardize the column names of the different SLMs. The column maps are
        LAEQ_COLUMN: LAeq column name
        LAMAX_COLUMN: LAFmax column name
        LAMIN_COLUMN: LAFmin column name

   The column maps are used in the following functions:
        get_data_814
        get_data_824
        get_data_lx_ES
        get_data_lx_EN
        get_data_cesva
        get_data_SV307
        get_data_audio
"""
        
larsonlx_dict = {'LAEQ_COLUMN': 'LAeq',
                 'LAMAX_COLUMN': 'LAFmax',
                 'LAMIN_COLUMN': 'LAFmin'}


larson824_dict = {'LAEQ_COLUMN': 'Leq',
                  'LAMAX_COLUMN': 'Max',
                  'LAMIN_COLUMN': 'Min'}


larson814_dict = {'LAEQ_COLUMN': 'Leq',
                  'LAMAX_COLUMN': 'Max',
                  'LAMIN_COLUMN': 'Min'}


cesva_dict = {'LAEQ_COLUMN': 'LA1s',
              'LAMAX_COLUMN': 'LAFmax1s',
              'LAMIN_COLUMN': 'LAFmin1s'}


sv307_dict = {'LAEQ_COLUMN': 'LAeq (Ch1, P1) [dB]',
              'LAMAX_COLUMN': 'LAFmax (Ch1, P1) [dB]',
              'LAMIN_COLUMN': 'LAFmin (Ch1, P1) [dB]'} 


sonometer_bilbo_dict = {'LAEQ_COLUMN': 'Value'}


audiopost_dict = {'LAEQ_COLUMN': 'LA',
                  'LAMAX_COLUMN': 'LAmax',
                  'LAMIN_COLUMN': 'LAmin'}


bruel_kjaer_dict = {'LAEQ_COLUMN': 'LAeq',
                    'LAMAX_COLUMN': 'LAFmax',
                    'LAMIN_COLUMN': 'LAFmin'}


tenerife_tct_dict = {'LAEQ_COLUMN': 'LA',
                    'LAMAX_COLUMN': 'LAmax',
                    'LAMIN_COLUMN': 'LAmin'}


# plotting Colors
C_MAP_WEEKDAY = {
            'Lunes': '#cc0000', # RED
            'Martes': '#8e7cc3', # PURPLE
            'Miércoles': '#9b5f00', # BROWN
            'Jueves': '#2986cc', # BLUE
            'Viernes': '#ffa500', # ORANGE
            'Sábado': '#6aa84f', # GREEN
            'Domingo': '#d172a4', # PINK
        }


C_MAP_WEEKDAY_NIGHT = {
            'Lunes-Martes': '#cc0000', # RED
            'Martes-Miércoles': '#8e7cc3', # PURPLE
            'Miércoles-Jueves': '#9b5f00', # BROWN
            'Jueves-Viernes': '#2986cc', # BLUE
            'Viernes-Sábado': '#ffa500', # ORANGE
            'Sábado-Domingo': '#6aa84f', # GREEN
            'Domingo-Lunes': '#d172a4', # PINK
}


PERCENTIL_COLOUR = {
    1: '#B28DFF',
    5: '#6EB5FF',
    10: '#B2E2F2',
    50: '#FFABAB',
    90: '#9E9E9E'
}


COLOR_PALLET_URBAN = {
            'Other human': '#2986cc', # BLUE
            'Electro-mechanical': '#cc0000', # RED
            'Voice': '#6aa84f', #  green 6aa84f
            'Motorised transport': '#ffa500', # orange
            'Geonature': '#8e7cc3', # PURPLE
            'Animal': '#9b5f00', # BROWN
            'Music': '#d172a4', # PINK
            'Background': '#000000', # BLACK
            'Other Sounds': '#c9d631', # yellow
            'Social/communal': '#d8cbf8', # Light purple
            'Human movement': '#40b674', # light green 40b674
        }



COLOR_PALLET_PORT_L1 = {
            'Siren': '#2986cc', # BLUE
            'Sound Event': '#cc0000', # RED
            'Transport': '#6aa84f', #  green 6aa84f
            'Human': '#ffa500', # orange
            'Nature': '#8e7cc3', # PURPLE
            'Animal': '#9b5f00', # BROWN
            'Music': '#d172a4', # PINK
            'Engine': '#000000', # BLACK
        }


C_MAP_GRADIENT = {
    1: '#C8FFC8',
    2: '#00C800',
    3: '#007800',
    4: '#FFFF00',
    5: '#FFC878',
    6: '#FF9600',
    7: '#FF0000',
    8: '#780000',
    9: '#FF00FF',
    10: '#8C3CFF',
    11: '#000078',
}




####################################
# SPECTROGRAM CONFIGURATION 
####################################
SPECTOGRAM_COLUMNS_LX_ES = [
    '1/3 LZeq 20,0', '1/3 LZeq 25,0', '1/3 LZeq 31,5', '1/3 LZeq 40,0', 
    '1/3 LZeq 50,0', '1/3 LZeq 63,0', '1/3 LZeq 80,0', '1/3 LZeq 100',
    '1/3 LZeq 125', '1/3 LZeq 160', '1/3 LZeq 200', '1/3 LZeq 250',
    '1/3 LZeq 315', '1/3 LZeq 400', '1/3 LZeq 500', '1/3 LZeq 630',
    '1/3 LZeq 800', '1/3 LZeq 1000', '1/3 LZeq 1250', '1/3 LZeq 1600',
    '1/3 LZeq 2000', '1/3 LZeq 2500', '1/3 LZeq 3150', '1/3 LZeq 4000',
    '1/3 LZeq 5000', '1/3 LZeq 6300', '1/3 LZeq 8000', '1/3 LZeq 10000',
    '1/3 LZeq 12500', '1/3 LZeq 16000', '1/3 LZeq 20000'
]