import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import os
import plotly.express as px
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from matplotlib.colors import ListedColormap
from scipy.stats import gaussian_kde

import pytz

from server_process_app.common.utils_vi import *
from server_process_app.common.config_vi import *

plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title



cmap_dict = sns.color_palette(palette=["#C8FFC8", "#00C800", "#007800", "#FFFF00", "#FFC878", "#FF9600", "#FF0000", "#780000", "#FF00FF", "#8C3CFF", "#000078"],n_colors=11)

hex_colors = [mcolors.to_hex(color) for color in cmap_dict]
custom_color_scale = [[i/len(hex_colors), color] for i, color in enumerate(hex_colors)]
custom_color_scale.append([1, hex_colors[-1]])
    



def plot_night_evolution(df, folder_output_dir: str, logger, laeq_column:str, plotname:str, indicador_noche:str):
    try:
        df = df.dropna(subset=[laeq_column])
        logger.info(f"Using the laeq_column: {laeq_column}")
        sns.set_style("whitegrid")
        sns.set_palette("tab10")
        
        df['Día'] = df['night_str']
        
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values(by=['date', 'hour'], inplace=True)

        night_data = pd.DataFrame()
        unique_dates = df['date'].dt.date.unique()

        for current_date in unique_dates:
            next_date = current_date + pd.Timedelta(days=1)
            data_23 = df[(df['date'].dt.date == current_date) & (df['hour'] == 23)]
            data_00_06 = df[(df['date'].dt.date == next_date) & (df['hour'].isin(range(0, 7)))]

            if not data_23.empty and not data_00_06.empty:
                combined_data = pd.concat([data_23, data_00_06])
                night_data = pd.concat([night_data, combined_data])

        night_data['plot_hour'] = night_data['hour'].replace({23: -1}).astype(int)
        night_data.sort_values(by=['date', 'plot_hour'], inplace=True)
        
        # save to excel
        os.makedirs(folder_output_dir, exist_ok=True)
        night_data.to_csv(f"{folder_output_dir}/night_evolution_{indicador_noche}_evolution.csv", index=False)
        logger.info(f"Night evolution data saved to {folder_output_dir}/{plotname}_{indicador_noche}_evolution.csv")

        fig = sns.relplot(
            data=night_data, 
            x="plot_hour", 
            y=laeq_column, 
            kind="line", 
            hue="Día",
            estimator=leq, 
            aspect=1.3,
            palette=C_MAP_WEEKDAY_NIGHT
        )
        
        plt.xticks(range(-1, 7), ['23:00', '00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00'])
        plt.yticks(range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP), [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)])

        plt.xlim(-1.5, 6.5)

        for ax in fig.axes.flat:
            ax.spines['top'].set_visible(True)
            ax.spines['right'].set_visible(True)

        plt.title(f'Evolución {indicador_noche}')
        plt.ylabel('dB(A)')
        plt.xlabel('Hora')

        os.makedirs(folder_output_dir, exist_ok=True)

        logger.info(f"Saving the plot {plotname}_{indicador_noche}")
        fig.savefig(f"{folder_output_dir}/night_evolution_{indicador_noche}_evolution.png", dpi=150)
        logger.info(f"Night evolution plot saved to {folder_output_dir}/{plotname}_{indicador_noche}_evolution.png")

    except Exception as e:
        logger.error(f"Error in plot_night_evolution: {e}")



def plot_night_evolution_week(df, folder_output_dir: str, logger, laeq_column: str, plotname: str, indicador_noche: str):
    try:
        df = df.dropna(subset=[laeq_column])
        logger.info(f"Using the laeq_column: {laeq_column}")
        sns.set_style("whitegrid")
        sns.set_palette("tab10")

        df['Día'] = df['night_str']
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values(by=['date', 'hour'], inplace=True)

        night_data = pd.DataFrame()
        unique_dates = df['date'].dt.date.unique()

        for current_date in unique_dates:
            next_date = current_date + pd.Timedelta(days=1)
            data_23 = df[(df['date'].dt.date == current_date) & (df['hour'] == 23)]
            data_00_06 = df[(df['date'].dt.date == next_date) & (df['hour'].isin(range(0, 7)))]

            if not data_23.empty and not data_00_06.empty:
                combined_data = pd.concat([data_23, data_00_06])
                night_data = pd.concat([night_data, combined_data])

        night_data['plot_hour'] = night_data['hour'].replace({23: -1}).astype(int)
        night_data.sort_values(by=['date', 'plot_hour'], inplace=True)


        ####################
        # @grouping by week
        night_data['week'] = night_data['date'].dt.to_period('W').apply(lambda r: r.start_time)
        weeks = night_data['week'].unique()

        for week_start in weeks:
            week_data = night_data[night_data['week'] == week_start]

            fig = sns.relplot(
                data=week_data,
                x="plot_hour",
                y=laeq_column,
                kind="line",
                hue="Día",
                estimator=leq,
                aspect=1.3,
                palette=C_MAP_WEEKDAY_NIGHT
            )

            plt.xticks(
                range(-1, 7),
                ['23:00', '00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00']
            )
            plt.yticks(
                range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP),
                [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)]
            )
            plt.xlim(-1.5, 6.5)

            for ax in fig.axes.flat:
                ax.spines['top'].set_visible(True)
                ax.spines['right'].set_visible(True)

            plt.title(f'Evolución {indicador_noche} - Semana {week_start.strftime("%Y-%m-%d")}')
            plt.ylabel('dB(A)')
            plt.xlabel('Hora')

            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)


            filename = f"{week_folder}/{plotname}_{indicador_noche}_evolution_week_{week_start.strftime('%Y-%m-%d')}.png"
            fig.savefig(filename, dpi=150)
            logger.info(f"Saved plot: {filename}")

    except Exception as e:
        logger.error(f"Error in plot_night_evolution: {e}")




def plot_night_evolution_15_min(df, folder_output_dir: str, logger, name_extension, laeq_column:str, plotname:str, indicador_noche:str):
    try:
        print(df)
        print(df.columns)
        
        df = df.dropna(subset=[laeq_column])
        logger.info(f"Using the laeq_column: {laeq_column}")        
        sns.set_style("whitegrid")
        sns.set_palette("tab10")
        
        df['Día'] = df['night_str']
        # df.index = pd.to_datetime(df.index)
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
            df = df.set_index('Timestamp')
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df = df.set_index('datetime')
        else:
            raise ValueError("The 'datetime' column is missing.")


        df_resampled = df.resample('15min')[laeq_column].agg(leq)
        df_night_str = df.resample('15min')['Día'].agg(lambda x: x.value_counts().index[0] if len(x) > 0 else None)
        df_resampled = pd.DataFrame(df_resampled).join([df_night_str])
        
        # date and time columns
        df_resampled['date'] = df_resampled.index.date
        df_resampled['time'] = df_resampled.index.time
        
        # convert time column to a plottable format with a 15-minute offset
        df_resampled['plot_time'] = [(t.hour * 60 + t.minute - 15) - (23 * 60) if t.hour >= 23 else (t.hour * 60 + t.minute - 15) + 60 for t in df_resampled['time']]
        print(df_resampled)
        print(df_resampled.columns)
        print(df_resampled['plot_time'])
        #exit()
        

        # filter data
        unique_dates = pd.to_datetime(df_resampled.index.date).unique()
        night_data = pd.DataFrame()

        print(type(df_resampled.index))
        print(df_resampled.index.dtype)
        print("Zona horaria del índice:", df_resampled.index.tz)

        # data for each night
        for current_date in unique_dates:
            #  time, which is the last 15-minute interval of the previous day
            start_time = pd.Timestamp(current_date - pd.Timedelta(days=1),tzinfo=pytz.UTC).replace(hour=23, minute=0)
            
            # end time, which is the first 6 hours and 45 minutes of the current day
            end_time = pd.Timestamp(current_date,tzinfo = pytz.UTC).replace(hour=6, minute=45)
            
            # slice the data, which is the last 15-minute interval of the previous day and the first 6 hours and 45 minutes of the current day
            data_slice = df_resampled[start_time:end_time]
            
            # if the slice is not empty and the minimum index hour is 23, then it is a night
            if not data_slice.empty and data_slice.index.min().hour == 23:
                # so we add it to the night data
                night_data = pd.concat([night_data, data_slice])
        
        #save to csv
        os.makedirs(folder_output_dir, exist_ok=True)
        
        logger.info(f"Saving the data {plotname}_{indicador_noche}")
        night_data.to_csv(f"{folder_output_dir}/{plotname}_{indicador_noche}_evolution_{name_extension}.csv", index=False)
        logger.info(f"Night evolution data saved to {folder_output_dir}/{plotname}_{indicador_noche}_evolution_{name_extension}.csv")
        
        fig = sns.relplot(
                data=night_data, 
                x="plot_time", 
                y=laeq_column, 
                kind="line",
                errorbar=None,
                hue="Día",
                estimator=leq, 
                aspect=1.3,
                palette=C_MAP_WEEKDAY_NIGHT
            )

        x_labels = [f'{hour:02d}:{minute:02d}' for hour in range(23, 24) for minute in range(0, 60, 15)] + \
                [f'{hour:02d}:{minute:02d}' for hour in range(0, 7) for minute in range(0, 60, 15)]
                
        x_ticks = range(-15, 465, 15)
        plt.xticks(x_ticks, x_labels, rotation=90)
        plt.yticks(range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP), [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)])
        
        plt.xlim(-30, 465)
        
        for ax in fig.axes.flat:
            ax.spines['top'].set_visible(True)
            ax.spines['right'].set_visible(True)
        
        plt.title(f'Evolución {indicador_noche} cada 15 minutos')
        plt.ylabel('dB(A)')
        plt.xlabel('Hora')

        # save the plot
        logger.info(f"Saving the plot {plotname}_{indicador_noche}")
        fig.savefig(os.path.join(folder_output_dir, f'{plotname}_{indicador_noche}_evolution_{name_extension}.png'),  dpi=150)
        logger.info(f"Night evolution plot saved to {folder_output_dir}/{plotname}_{indicador_noche}_evolution_{name_extension}.png")
    except Exception as e:
        logger.error(f"Error in plot_night_evolution_15_min: {e}")




def plot_night_evolution_15_min_week(df, folder_output_dir: str, logger, name_extension, laeq_column: str, plotname: str, indicador_noche: str):
    try:
        df = df.dropna(subset=[laeq_column])
        logger.info(f"Using the laeq_column: {laeq_column}")
        sns.set_style("whitegrid")
        sns.set_palette("tab10")

        df['Día'] = df['night_str']

        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
            df = df.set_index('Timestamp')
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df = df.set_index('datetime')
        else:
            raise ValueError("The 'datetime' column is missing.")

        df_resampled = df.resample('15min')[laeq_column].agg(leq)
        df_night_str = df.resample('15min')['Día'].agg(lambda x: x.value_counts().index[0] if len(x) > 0 else None)
        df_resampled = pd.DataFrame(df_resampled).join([df_night_str])

        df_resampled['date'] = df_resampled.index.date
        df_resampled['time'] = df_resampled.index.time

        # Adjust time for plotting
        df_resampled['plot_time'] = [
            (t.hour * 60 + t.minute - 15) - (23 * 60) if t.hour >= 23 else (t.hour * 60 + t.minute - 15) + 60
            for t in df_resampled['time']
        ]

        unique_dates = pd.to_datetime(df_resampled.index.date).unique()
        night_data = pd.DataFrame()

        print(type(df_resampled.index))
        print(df_resampled.index.dtype)
        print("Zona horaria del índice:", df_resampled.index.tz)

        for current_date in unique_dates:
            
            start_time = pd.Timestamp(current_date - pd.Timedelta(days=1),tzinfo=pytz.UTC).replace(hour=23, minute=0)
            
            end_time = pd.Timestamp(current_date,tzinfo=pytz.UTC).replace(hour=6, minute=45)
            
            data_slice = df_resampled[start_time:end_time]

            if not data_slice.empty and data_slice.index.min().hour == 23:
                night_data = pd.concat([night_data, data_slice])


        ################################
        ################################
        # weeks
        # night_data['week'] = pd.to_datetime(night_data.index).to_period('W').apply(lambda r: r.start_time)
        night_data['week'] = pd.to_datetime(night_data.index).to_period('W').start_time
        weeks = night_data['week'].unique()


        for week_start in weeks:
            week_data = night_data[night_data['week'] == week_start]

            fig = sns.relplot(
                data=week_data,
                x="plot_time",
                y=laeq_column,
                kind="line",
                hue="Día",
                errorbar=None,
                estimator=leq,
                aspect=1.3,
                palette=C_MAP_WEEKDAY_NIGHT
            )

            x_labels = [f'{hour:02d}:{minute:02d}' for hour in range(23, 24) for minute in range(0, 60, 15)] + \
                       [f'{hour:02d}:{minute:02d}' for hour in range(0, 7) for minute in range(0, 60, 15)]
            x_ticks = range(-15, 465, 15)

            plt.xticks(x_ticks, x_labels, rotation=90)
            plt.yticks(range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP),
                       [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)])
            plt.xlim(-30, 465)

            for ax in fig.axes.flat:
                ax.spines['top'].set_visible(True)
                ax.spines['right'].set_visible(True)

            plt.title(f'Evolución {indicador_noche} cada 15 minutos - Semana {week_start.strftime("%Y-%m-%d")}')
            plt.ylabel('dB(A)')
            plt.xlabel('Hora')


            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            fig_path = os.path.join(week_folder, f'{plotname}_{indicador_noche}_evolution_{name_extension}_week_{week_start.strftime("%Y-%m-%d")}.png')
            fig.savefig(fig_path, dpi=150)
            logger.info(f"Saved weekly plot: {fig_path}")

    except Exception as e:
        logger.error(f"Error in plot_night_evolution_15_min_week: {e}")




  
def plot_predic_laeq_mean(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        #########################################################
        #### Plotting the data ####
        
        display_name = 'display_name'
        iso_taxonomy = 'iso_taxonomy'
        classes = 'class'

        brown_2 = 'Brown_Level_2'
        brown_3 = 'Brown_Level_3'
        noiseport_1 = 'NoisePort_Level_1'
        noiseport_2 = 'NoisePort_Level_2'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")


        ####################################
        grouped_df = df_all_yamnet.groupby(class_to_plot).agg(
            number=(classes, 'size'),
            LAeq=('LA_corrected', lambda x: leq(x))
        ).reset_index()

        fig = px.treemap(
                grouped_df,
                path=[class_to_plot],  
                values='number',
                color=class_to_plot,#color by category
                color_discrete_map= color_palet,
                hover_data={'LAeq': True, 'number': True},
                custom_data=['LAeq']                  
            )

        # title and hover settings
        fig.update_layout(title=f'{plotname} | Promedio Energético (LAeq) por Clases')
        fig.update_traces(
            hovertemplate=(
                '<b>%{label}</b><br>'
                'LAeq: %{customdata[0]:.2f} dB<br>'
                'Count: %{value}'
            ),
            texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB'
        )
            
        
        os.makedirs(folder_output_dir, exist_ok=True)
        fig.write_html(f"{folder_output_dir}/{plotname}_LAeq_class_mean.html")
        grouped_df.to_csv(f"{folder_output_dir}/{plotname}_LAeq_class_mean.csv", index=False)
        
        logger.info(f"LAeq class mean plot saved to {folder_output_dir}/{plotname}_LAeq_class_mean.html")
        logger.info(f"LAeq class mean data saved to {folder_output_dir}/{plotname}_LAeq_class_mean.csv")

    except Exception as e:
        logger.error(f"Error in plot_predic_laeq_15_min: {e}")
        




def plot_predic_laeq_mean_4h(df_all_yamnet: pd.DataFrame,df_ship_dock: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        df_all = df_all_yamnet.copy()
        df_all['Timestamp'] = pd.to_datetime(df_all['Timestamp'], errors='coerce')
        df_all = df_all.dropna(subset=['LA_corrected'])
        df_all.set_index('Timestamp', inplace=True)

        df_all['hour'] = df_all.index.hour
        df_all['time_of_day'] = df_all['hour'].apply(categorize_time_of_day_4)

        display_name = 'display_name'
        classes = 'class'
        brown_2 = 'Brown_Level_2'
        noiseport_1 = 'NoisePort_Level_1'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")

        #order
        order_time_of_day = ['Ld_1', 'Ld_2', 'Ld_3', 'Le', 'Ln_1', 'Ln_2']
        df_all['time_of_day'] = pd.Categorical(df_all['time_of_day'], categories=order_time_of_day, ordered=True)
        df_all['order_index'] = df_all['time_of_day'].cat.codes



        grouped_df = df_all.groupby([class_to_plot, 'time_of_day']).agg(
            number=(classes, 'size'),
            LAeq=('LA_corrected', lambda x: leq(x)),
            order_index=('order_index', 'first')
        ).reset_index()

        grouped_df = grouped_df.dropna(subset=['LAeq'])
        os.makedirs(folder_output_dir, exist_ok=True)

        for period in order_time_of_day:
            period_df = grouped_df[grouped_df['time_of_day'] == period]

            fig = px.treemap(
                period_df,
                path=[px.Constant(period), class_to_plot],
                values='number',
                color=class_to_plot,
                color_discrete_map=color_palet,
                hover_data={'LAeq': True, 'number': True},
                custom_data=['LAeq'],
            )

            fig.update_layout(title=f'{plotname} | LAeq Promedio por Clase - Periodo {period}')
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>LAeq: %{customdata[0]:.2f} dB<br>Count: %{value}',
                texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB'
            )

            fig.write_html(f"{folder_output_dir}/{plotname}_LAeq_class_period_{period}.html")
            logger.info(f"Saved treemap and CSV for period {period}")

    except Exception as e:
        logger.error(f"Error in plot_predic_laeq_mean_4h_periods: {e}")



def plot_predic_laeq_mean_day(df_all_yamnet: pd.DataFrame, df_ship_dock:pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        # folder outpout 
        treemap_folder = os.path.join(folder_output_dir, 'TreeMaps_days')
        os.makedirs(treemap_folder, exist_ok=True)


        df_all = df_all_yamnet.copy()
        df_all['Timestamp'] = pd.to_datetime(df_all['Timestamp'], errors='coerce')
        df_all = df_all.dropna(subset=['LA_corrected'])
        df_all.set_index('Timestamp', inplace=True)

        df_all['date'] = df_all.index.date

        display_name = 'display_name'
        classes = 'class'
        brown_2 = 'Brown_Level_2'
        noiseport_1 = 'NoisePort_Level_1'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")

        grouped_df = df_all.groupby([class_to_plot, 'date']).agg(
            number=(classes, 'size'),
            LAeq=('LA_corrected', lambda x: leq(x))
        ).reset_index()


        grouped_df = grouped_df.dropna(subset=['LAeq'])
        for date in grouped_df['date'].unique():
            date_df = grouped_df[grouped_df['date'] == date]

            fig = px.treemap(
                date_df,
                path=[px.Constant(str(date)), class_to_plot],
                values='number',
                color=class_to_plot,
                color_discrete_map=color_palet,
                hover_data={'LAeq': True, 'number': True},
                custom_data=['LAeq'],
            )

            fig.update_layout(title=f'{plotname} | LAeq Promedio por Clase - Día {date}')
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>LAeq: %{customdata[0]:.2f} dB<br>Count: %{value}',
                texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB'
            )

            plot_name_path = (f"{treemap_folder}/{plotname}_LAeq_class_day_{date}.html")
            fig.write_html(plot_name_path)
            logger.info(f"Saved treemap at {plot_name_path}")
    
    except Exception as e:
        logger.error(f"Error in plot_predic_laeq_mean_day: {e}")




def plot_predic_laeq_mean_week(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        df_all_yamnet = df_all_yamnet.copy()
        df_all_yamnet['Timestamp'] = pd.to_datetime(df_all_yamnet['Timestamp'])
        try:
            df_all_yamnet['week'] = df_all_yamnet['Timestamp'].dt.to_period('W').start_time
        except Exception as e:
            df_all_yamnet['week'] = df_all_yamnet['Timestamp'].dt.to_period('W').apply(lambda r: r.start_time)

        
        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = 'NoisePort_Level_1'
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = 'Brown_Level_2'
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")

        class_column = 'class'
        weeks = df_all_yamnet['week'].unique()

        for week_start in weeks:
            df_week = df_all_yamnet[df_all_yamnet['week'] == week_start].copy()
            if df_week.empty:
                continue

            

            grouped_df = df_week.groupby(class_to_plot).agg(
                number=(class_column, 'size'),
                LAeq=('LA_corrected', lambda x: leq(x))
            ).reset_index()

            fig = px.treemap(
                grouped_df,
                path=[class_to_plot],
                values='number',
                color=class_to_plot,
                color_discrete_map=color_palet,
                hover_data={'LAeq': True, 'number': True},
                custom_data=['LAeq']
            )

            fig.update_layout(title=f'{plotname} | Promedio Energético (LAeq) por Clases | Semana {week_start.strftime("%Y-%m-%d")}')
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>LAeq: %{customdata[0]:.2f} dB<br>Count: %{value}',
                texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB'
            )

            
            

            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            
            html_path = os.path.join(week_folder, f"{plotname}_LAeq_class_mean_{week_start.strftime('%Y-%m-%d')}.html")
            fig.write_html(html_path)
            logger.info(f"Saved treemap to {html_path}")
    except Exception as e:
        logger.error(f"Error in plot_predic_laeq_mean_weekly: {e}")





def plot_predic_laeq_15_min_period(df: pd.DataFrame, yamnet_csv:pd.DataFrame, taxonomy_map, df_Pred:pd.DataFrame, folder_output_dir: str, logger, columns_dict: dict, agg_period: int, plotname: str):
    try:
        folder_output_dir = os.path.join(folder_output_dir, 'Prediction_LAeq_15_min_Period')
        # remove nan values
        df = df.dropna(subset=[columns_dict['LAEQ_COLUMN_COEFF']])
        logger.info(f"Using the columns_dict: {columns_dict}")

        # # check
        spl_start_date = df['datetime'].iloc[0]
        spl_end_date = df['datetime'].iloc[-1]
        spl_difference_between_first_days = df['datetime'].iloc[10] - df['datetime'].iloc[9]
        logger.info(f"SPL file: Start date {spl_start_date} and End date {spl_end_date}")
        logger.info(f"SPL file: Difference between first and second date: {spl_difference_between_first_days}")

        pred_start_date = df_Pred['date'].iloc[0]
        pred_end_date = df_Pred['date'].iloc[-1]
        logger.info(f"Pred file: Start date {pred_start_date} and End date {pred_end_date}")
        pred_difference_between_first_days = df_Pred['date'].iloc[10] - df_Pred['date'].iloc[9]
        logger.info(f"Pred file: Difference between first and second date: {pred_difference_between_first_days}")

        agg_funcs = {
            columns_dict['LAEQ_COLUMN_COEFF']: leq,
        }

        if pred_difference_between_first_days >= pd.Timedelta(minutes=15):
            logger.info(f"Resampling the SPL file to 15 minutes")
            df_LAeq = df.resample(f'{agg_period}s').agg(agg_funcs)
        else:
            logger.info(f"No Resampling the SPL file")
            df_LAeq = df


        start_date = max(df_LAeq.index.min(), df_Pred.index.min())
        end_date = min(df_LAeq.index.max(), df_Pred.index.max())

        df_LAeq = df_LAeq[start_date:end_date]
        df_Pred = df_Pred[start_date:end_date]
        df_Pred.index = df_Pred.index.round('15min')



        # check if the first date for lae and pred is the same
        check_dilay = df_LAeq.index[0] - df_Pred.index[0]
        if check_dilay != pd.Timedelta(seconds=0):
            logger.info(f"The mismatch for LAeq and Pred date is {check_dilay}")

            # check which is earlier, and apply the shift
            if df_LAeq.index[0] < df_Pred.index[0]:
                df_LAeq = df_LAeq.shift(periods=abs(check_dilay.seconds), freq='s')
            else:
                df_Pred = df_Pred.shift(periods=abs(check_dilay.seconds), freq='s')
            logger.info(f"Shifted the data to match the dates")


        # merge df
        df_aligned = df_LAeq.merge(df_Pred, how='left', left_index=True, right_index=True)
        # remove rows with NaN values
        df_aligned.dropna(inplace=True)

        # set date_y as index
        if "date_y" in df_aligned.columns:
            df_aligned.set_index('date_y', inplace=True, drop=False)
        else:
            df_aligned.set_index('date', inplace=True, drop=False)
        

        ####################################################################
        df_aligned['class_probability'] = df_aligned.apply(
            lambda x: (x['class'], x['probability']) if isinstance(x['class'], float) else list(zip(x['class'], x['probability'])),
            axis=1
        )
        df_exploded = df_aligned.explode('class_probability')
        df_exploded['class'] = df_exploded['class_probability'].apply(lambda x: x[0] if isinstance(x, tuple) else x)
        df_exploded['probability'] = df_exploded['class_probability'].apply(lambda x: x[1] if isinstance(x, tuple) else None)
        ####################################################################

        # create the df_all, merge with the audioset dataframe
        df_exploded['display_name'] = df_exploded['class']
        df_all = df_exploded.merge(yamnet_csv, how='left', on='display_name')
        df_all = df_all.dropna(subset=['display_name'])

        if 'datetime_y' in df_all.columns and 'hour_x' in df_all.columns:
            logger.info("Using 'datetime_y' and 'hour_x' columns for datetime and hour categorization.")
            df_all['datetime_y'] = pd.to_datetime(df_all['datetime_y'])
            df_all['time_of_day'] = df_all['hour_x'].apply(categorize_time_of_day)

        else:
            logger.info("Using 'date' and 'hour' columns for datetime and hour categorization.")
            df_all['datetime_y'] = pd.to_datetime(df_all['date'])
            df_all['time_of_day'] = df_all['hour'].apply(categorize_time_of_day)
    


        #########################################################
        #### Plotting the data ####
        
        display_name = 'display_name'
        iso_taxonomy = 'iso_taxonomy'
        classes = 'class'

        brown_1 = 'Brown_Level_1'
        brown_2 = 'Brown_Level_2'
        brown_3 = 'Brown_Level_3'
        noiseport_1 = 'NoisePort_Level_1'
        noiseport_2 = 'NoisePort_Level_2'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")

        order_time_of_day = ['Ld', 'Le', 'Ln']

        df_all['time_of_day'] = pd.Categorical(df_all['time_of_day'], categories=order_time_of_day, ordered=True)
        df_all['order_index'] = df_all['time_of_day'].cat.codes

        grouped_df = df_all.groupby([class_to_plot, df_all['time_of_day']]).agg(
            number=(classes, 'size'),
            LAeq=('LA_corrected', lambda x: leq(x)),
            order_index=('order_index', 'first')
        ).reset_index()

        grouped_df = grouped_df.dropna(subset=['LAeq'])

        # iterate for each period and save it individually
        for period in order_time_of_day:
            period_df = grouped_df[grouped_df['time_of_day'] == period]

            fig = px.treemap(
                            period_df, 
                            path=[px.Constant(period), class_to_plot],  
                            values='number',
                            color=class_to_plot,
                            color_discrete_map=color_palet,# <--- color_discrete_map, and not 'color_continuous_scale=color_palet' 
                            hover_data={'LAeq': True, 'number': True},
                            custom_data=['LAeq'],
                        )

            fig.update_layout(title=f'{plotname} | Promedio Energético (LAeq) distribución por Periodo {period} por Clases')
            fig.update_traces(hovertemplate='<b>%{label}</b><br>LAeq: %{customdata[0]:.2f} dB<br>Count: %{value}')
            fig.update_traces(texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB')

            os.makedirs(folder_output_dir, exist_ok=True)

            logger.info(f"Saving the plot {plotname}")
            fig.write_html(f"{folder_output_dir}/{plotname}_LAeq_class_period_{period}.html")
            logger.info(f"LAeq class period plot saved to {folder_output_dir}/{plotname}_LAeq_class_period_{period}.html")

            logger.info(f"Saving the data {plotname}")
            period_df.to_csv(f"{folder_output_dir}/{plotname}_LAeq_class_period_{period}.csv", index=False)     
            logger.info(f"LAeq class period data saved to {folder_output_dir}/{plotname}_LAeq_class_period_{period}.csv")

    except Exception as e:
        logger.error(f"Error in plot_predic_laeq_15_min_period: {e}")




def plot_predic_laeq_15_min_4h(df: pd.DataFrame, yamnet_csv:pd.DataFrame, taxonomy_map, df_Pred:pd.DataFrame, folder_output_dir: str, logger, columns_dict: dict, agg_period: int, plotname: str):
    try:
        folder_output_dir = os.path.join(folder_output_dir, 'Prediction_LAeq_15_min_4h')
        # remove nan values
        df = df.dropna(subset=[columns_dict['LAEQ_COLUMN_COEFF']])
        logger.info(f"Using the columns_dict: {columns_dict}")


        # # check
        spl_start_date = df['datetime'].iloc[0]
        spl_end_date = df['datetime'].iloc[-1]
        spl_difference_between_first_days = df['datetime'].iloc[10] - df['datetime'].iloc[9]
        logger.info(f"SPL file: Start date {spl_start_date} and End date {spl_end_date}")
        logger.info(f"SPL file: Difference between first and second date: {spl_difference_between_first_days}")

        pred_start_date = df_Pred['date'].iloc[0]
        pred_end_date = df_Pred['date'].iloc[-1]
        logger.info(f"Pred file: Start date {pred_start_date} and End date {pred_end_date}")
        pred_difference_between_first_days = df_Pred['date'].iloc[10] - df_Pred['date'].iloc[9]
        logger.info(f"Pred file: Difference between first and second date: {pred_difference_between_first_days}")

        agg_funcs = {columns_dict['LAEQ_COLUMN_COEFF']: leq}

        if pred_difference_between_first_days >= pd.Timedelta(minutes=15):
            logger.info(f"Resampling the SPL file to 15 minutes")
            df_LAeq = df.resample(f'{agg_period}s').agg(agg_funcs)
        else:
            logger.info(f"No Resampling the SPL file")
            df_LAeq = df


        start_date = max(df_LAeq.index.min(), df_Pred.index.min())
        end_date = min(df_LAeq.index.max(), df_Pred.index.max())

        df_LAeq = df_LAeq[start_date:end_date]
        df_Pred = df_Pred[start_date:end_date]

        df_Pred.index = df_Pred.index.round('15min')
        

        # check if the first date for lae and pred is the same
        check_dilay = df_LAeq.index[0] - df_Pred.index[0]
        if check_dilay != pd.Timedelta(seconds=0):
            logger.info(f"The mismatch for LAeq and Pred date is {check_dilay}")

            # check which is earlier, and apply the shift
            if df_LAeq.index[0] < df_Pred.index[0]:
                df_LAeq = df_LAeq.shift(periods=abs(check_dilay.seconds), freq='s')
            else:
                df_Pred = df_Pred.shift(periods=abs(check_dilay.seconds), freq='s')
            logger.info(f"Shifted the data to match the dates")



        # merge df
        df_aligned = df_LAeq.merge(df_Pred, how='left', left_index=True, right_index=True)
        # remove rows with NaN values
        df_aligned.dropna(inplace=True)


        # set date_y as index
        if "date_y" in df_aligned.columns:
            df_aligned.set_index('date_y', inplace=True, drop=False)      
        else:
            df_aligned.set_index('date', inplace=True, drop=False)

        ####################################################################
        df_aligned['class_probability'] = df_aligned.apply(
            lambda x: (x['class'], x['probability']) if isinstance(x['class'], float) else list(zip(x['class'], x['probability'])),
            axis=1
        )
        df_exploded = df_aligned.explode('class_probability')
        df_exploded['class'] = df_exploded['class_probability'].apply(lambda x: x[0] if isinstance(x, tuple) else x)
        df_exploded['probability'] = df_exploded['class_probability'].apply(lambda x: x[1] if isinstance(x, tuple) else None)
        ####################################################################

        # create the df_all, merge with the audioset dataframe
        df_exploded['display_name'] = df_exploded['class']
        df_all = df_exploded.merge(yamnet_csv, how='left', on='display_name')
        df_all = df_all.dropna(subset=['display_name'])

        # convert data time type datetime_y column
        if 'datetime_y' in df_all.columns and 'hour_x' in df_all.columns:
            logger.info("Using 'datetime_y' and 'hour_x' columns for datetime and hour categorization.")
            df_all['datetime_y'] = pd.to_datetime(df_all['datetime_y'])
            df_all['time_of_day'] = df_all['hour_x'].apply(categorize_time_of_day_4)

        else:
            logger.info("Using 'date' and 'hour' columns for datetime and hour categorization.")
            df_all['datetime_y'] = pd.to_datetime(df_all['date'])
            df_all['time_of_day'] = df_all['hour'].apply(categorize_time_of_day_4)
        
        
        
        #########################################################
        #### Plotting the data ####
        display_name = 'display_name'
        iso_taxonomy = 'iso_taxonomy'
        classes = 'class'

        brown_1 = 'Brown_Level_1'
        brown_2 = 'Brown_Level_2'
        brown_3 = 'Brown_Level_3'
        noiseport_1 = 'NoisePort_Level_1'
        noiseport_2 = 'NoisePort_Level_2'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")


        order_time_of_day = ['Ld_1', 'Ld_2', 'Ld_3', 'Le', 'Ln_1', 'Ln_2']

        df_all['time_of_day'] = pd.Categorical(df_all['time_of_day'], categories=order_time_of_day, ordered=True)
        df_all['order_index'] = df_all['time_of_day'].cat.codes
        

        grouped_df = df_all.groupby([class_to_plot, df_all['time_of_day']]).agg(
            number=(classes, 'size'),
            LAeq=('LA_corrected', lambda x: leq(x)),
            order_index=('order_index', 'first')
        ).reset_index()


        # remove rows with nan values
        grouped_df = grouped_df.dropna(subset=['LAeq'])
        for period in order_time_of_day:
            period_df = grouped_df[grouped_df['time_of_day'] == period]

            fig = px.treemap(period_df, 
                            path=[px.Constant(period),class_to_plot],  
                            values='number',
                            color=class_to_plot,
                            color_discrete_map=color_palet,
                            # range_color=[30, 85],
                            hover_data={'LAeq': True, 'number': True},
                            custom_data=['LAeq'],                  
                        )

            fig.update_layout(title=f'{plotname} | Promedio Energético (LAeq) distribución por Periodo {period} por Clases')
            fig.update_traces(hovertemplate='<b>%{label}</b><br>LAeq: %{customdata[0]:.2f} dB<br>Count: %{value}')
            fig.update_traces(texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB')

            os.makedirs(folder_output_dir, exist_ok=True)

            logger.info(f"Saving the plot {plotname}")
            fig.write_html(f"{folder_output_dir}/{plotname}_LAeq_class_period_{period}.html")
            logger.info(f"LAeq class period plot saved to {folder_output_dir}/{plotname}_LAeq_class_period_{period}.html")

            logger.info(f"Saving the data {plotname}")
            period_df.to_csv(f"{folder_output_dir}/{plotname}_LAeq_class_period_{period}.csv", index=False)
            logger.info(f"LAeq class period data saved to {folder_output_dir}/{plotname}_LAeq_class_period_{period}.csv")


    except Exception as e:
        logger.error(f"Error in PLOT_PREDIC_LAEQ_4H: {e}")




def plot_prediction_stack_bar(df_Pred:pd.DataFrame, yamnet_csv, taxonomy_map, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("white")
        sns.set_palette("tab10")

        # make duration to make the resample to 15 minutes
        start_date = df_Pred['date'].iloc[0]
        end_date = df_Pred['date'].iloc[-1]
        difference_between_first_days = df_Pred['date'].iloc[10] - df_Pred['date'].iloc[9]
        logger.info(f"Start date {start_date} and End date {end_date}")
        logger.info(f"Difference between first and second date: {difference_between_first_days}")

        # explode
        df_exploded = df_Pred.explode('class')
        df_exploded['display_name'] = df_exploded['class']
        df_exploded['number'] = 1

        #~insert date
        df_exploded = insert_dates(df_exploded)
        df_exploded['mapped_class'] = df_exploded['class'].map(taxonomy_map)

        #################################
        home_dir = os.path.expanduser('~')
        full_path = os.path.join(home_dir, RELATIVE_PATH_YAMNET_MAP.lstrip('\\'))
        union = pd.read_csv(full_path, sep=';')
        # merge classes with ontology
        df_exploded = df_exploded.merge(union,how='left',on='display_name')

        # remove Unnamed columns
        df_exploded = df_exploded.loc[:, ~df_exploded.columns.str.contains('^Unnamed')]
        # rename columns
        df_exploded.rename(columns={"fullday": "Día", "hour": "Hora", "mid": "Distribución de clases"}, inplace=True)
        unique_día_weekday = df_exploded['Día'].unique()
        #set to categorical
        df_exploded['Día'] = pd.Categorical(df_exploded['Día'], categories=unique_día_weekday, ordered=True)



        ################################ PLOT ################################
        display_name = 'display_name'
        iso_taxonomy = 'iso_taxonomy'
        classes = 'class'

        brown_2 = 'Brown_Level_2'
        brown_3 = 'Brown_Level_3'
        noiseport_1 = 'NoisePort_Level_1'
        noiseport_2 = 'NoisePort_Level_2'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_pallet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2  
            color_pallet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")

        dfg = df_exploded.groupby([class_to_plot,'Día']).count().reset_index()
        fig = px.bar(
            dfg, 
            x='Día',
            y='Distribución de clases',
            color=class_to_plot,
            title=f'{plotname} | Clases por Día',
            color_discrete_sequence=px.colors.qualitative.Alphabet, 
            color_discrete_map=color_pallet,
            height=900,
            width=2000
        )

        fig.write_html(f"{folder_output_dir}/{plotname}_prediction_stack_map.html")
        logger.info(f"Prediccion stack bar saved at: {folder_output_dir}/{plotname}_prediction_stack_map.html")

        # save csv with the data
        dfg.to_csv(f"{folder_output_dir}/{plotname}_prediction_stack_map.csv")
        logger.info(f"Saved csv at {folder_output_dir}/{plotname}_prediction_stack_map.csv")

    except Exception as e:
        logger.error(f"Error in plot_prediction_stack_bar: {e}")





def plot_prediction_map(df_Pred:pd.DataFrame, taxonomy_map, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("white")
        sns.set_palette("tab10")

        # remove empty entries in class column
        df_Pred = df_Pred.dropna(subset=['class'])

        # make duration to make the resample to 15 minutes
        start_date = df_Pred['date'].iloc[0]
        end_date = df_Pred['date'].iloc[-1]
        difference_between_first_days = df_Pred['date'].iloc[10] - df_Pred['date'].iloc[9]
        logger.info(f"Start date {start_date} and End date {end_date}")
        logger.info(f"Difference between first and second date: {difference_between_first_days}")

        # explode
        df_exploded = df_Pred.explode('class')
        df_exploded['display_name'] = df_exploded['class']
        df_exploded['number'] = 1

        #~insert date
        df_exploded = insert_dates(df_exploded)
        df_exploded = df_exploded.dropna(subset=['class'])
        # print if there is nan values
        if df_exploded['class'].isnull().values.any():
            logger.error("There are nan values in the class column")

        df_exploded['mapped_class'] = df_exploded['class'].map(taxonomy_map)
        df_exploded = df_exploded.dropna(subset=['mapped_class'])



        ################################ PLOT ################################
        # if plot_prediction_stack_bar is greater than 1 second
        if difference_between_first_days == pd.Timedelta(seconds=1):
            logger.info(f"Plotting the prediction map for {plotname} equal to 1 second")
            resampled_df = df_exploded.resample('15min').agg({
                'filename': 'first',  # taking the first filename in each bin
                'class': 'first',
                'probability': 'first', 
                'display_name': 'first', 
                'number': 'sum',  # summing up the numbers in each bin
                'year': 'first',
                'month': 'first',
                'day': 'first',
                'hour': 'first',
                'minute': 'first',
                'second': 'first',
                'weekday': 'first',
                'fullday': 'first',
                'mapped_class': 'first'
            })
            ###################### PLOTTING ######################
            df_resampled = resampled_df.sort_values(by=["year", "month", "fullday"])
        
        else:
            logger.info(f"Plotting the prediction map for {plotname} greater than 1 second")
            ###################### PLOTTING ######################
            df_resampled = df_exploded.sort_values(by=["year", "month", "fullday"])


        # drop None values
        df_resampled = df_resampled.dropna(subset=['mapped_class'])
        # map class to number
        class_to_num = {class_name: index+1 for index, class_name in enumerate(df_resampled['mapped_class'].unique())}

        df_resampled['class_num'] = df_resampled['mapped_class'].map(class_to_num)
        # drop nan values
        df_resampled = df_resampled.dropna(subset=['class_num'])
        
        # inverting the dictionary to get the name of the class for the legend
        name_class = {v: k for k, v in class_to_num.items()}
        



        # mapping from classes numbers to colors
        if 'Siren' in set(taxonomy_map.values()):
            num_to_color = {num: COLOR_PALLET_PORT_L1[class_name] for class_name, num in class_to_num.items()}
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            num_to_color = {num: COLOR_PALLET_URBAN[class_name] for class_name, num in class_to_num.items()}
            logger.info("Using 'Brown_Level_2' class for plotting")
        cmap = [num_to_color[cls_num] for cls_num in name_class.keys()]
        
        # leggend elements colors
        legend_elements = [Patch(facecolor=num_to_color[cls_num], label=f"Clase {cls_num} - {name_class.get(cls_num, '')}") for cls_num in name_class.keys()]
        day_class = pd.pivot_table(data=df_resampled, columns=df_resampled.index.time, index=["year", "month", "fullday"], values="class_num", aggfunc='mean')


        plt.figure(figsize=(45, 35))
        if day_class.isna().all().all() or day_class.empty:
            logger.warning("No valid data. Skipping...")
        else:
            ax = sns.heatmap(day_class, annot=False, cmap=cmap, linewidth=0.5, cbar=False)

            # show every 4th column as an example
            step = 2
            xtick_locs = range(0, len(day_class.columns), step)
            xtick_labels = [day_class.columns[i].strftime('%H:%M:%S') for i in xtick_locs]
            
            ax.set_xticks(xtick_locs)
            ax.set_xticklabels(xtick_labels, rotation=90, fontsize=50)

            yticklabels = [f"{idx[0]}-{idx[1]}-{idx[2]}" for idx in day_class.index]
            ax.set_yticklabels(yticklabels, rotation=0, fontsize=50)
            
            plt.legend(
                handles=legend_elements, 
                title="Clases", 
                loc='center left', 
                bbox_to_anchor=(1, 0.5),
                fontsize=40
            )
            plt.title(f"{plotname} | Clases 15 min", fontsize=60)

            plt.savefig(f"{folder_output_dir}/{plotname}_prediction_map.png", bbox_inches='tight')
            logger.info(f"Saved image at {folder_output_dir}/{plotname}_prediction_map.png")

            # save csv with the data
            day_class.to_csv(f"{folder_output_dir}/{plotname}_prediction_map.csv")
            logger.info(f"Saved csv at {folder_output_dir}/{plotname}_prediction_map.csv")
          
    except Exception as e:
        logger.error(f"Error in plot_prediction_map: {e}")




def plot_prediction_map_new(df_all_yamnet: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    try:
        df_copy = df_all_yamnet.copy()
        print(df_copy)
        # exit()


        #######################################
        df_copy = add_datetime_columns(df_copy, logger, date_col='Timestamp')

        #######################################
        df_copy.set_index('Timestamp', inplace=True)
        #resample 1h
        df_all_yamnet_1h_resample = df_copy.resample('1h').agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        df_all_yamnet_1h = df_all_yamnet_1h_resample
        ########################################


        # df_copy['mapped_class'] = df_copy['class'].map(taxonomy_map)
        # df_copy = df_copy.dropna(subset=['mapped_class'])

        # #class names to numbers
        # class_to_num = {cls: i+1 for i, cls in enumerate(df_copy['mapped_class'].unique())}
        # df_copy['class_num'] = df_copy['mapped_class'].map(class_to_num)
        # name_class = {v: k for k, v in class_to_num.items()}
        # df_copy['Timestamp'] = pd.to_datetime(df_copy['Timestamp'])
        # df_copy.set_index('Timestamp', inplace=True)



        # #######################################
        # #resample 15 min
        # resampled = df_copy.resample('15min').agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        # resampled = resampled.dropna(subset=['class_num'])


        # #######################################
        # #time
        # resampled['date'] = resampled.index.date
        # resampled['time_block'] = resampled.index.time  # Or .strftime('%H:%M') for cleaner strings
        # pivot = resampled.pivot(index='date', columns='time_block', values='class_num')

        # #######################################
        # #color mapping
        # if 'Siren' in set(taxonomy_map.values()):
        #     num_to_color = {num: COLOR_PALLET_PORT_L1[cls] for cls, num in class_to_num.items()}
        #     logger.info("Using 'NoisePort_Level_1' class for plotting")

        # ordered_colors = [num_to_color[i] for i in sorted(name_class.keys())]
        # cmap = ListedColormap(ordered_colors)

        # #######################################
        # #plotting
        # plt.figure(figsize=(20, 10))
        # ax = sns.heatmap(pivot, cmap=cmap, linewidth=0.3, cbar=False, linecolor='gray')

        # ax.set_title("Sound Class Predictions — Daily 15min Timeline")
        # ax.set_xlabel("Hora del Día", fontsize=14)
        # ax.set_ylabel("Fecha", fontsize=14)

        # label_step = 1 # 15 min 96 
        # # label_step = 2 #30 min
        # # label_step = 4  # 1h


        # xtick_locs = list(range(0, len(pivot.columns), label_step))
        # xtick_labels = [t.strftime('%H:%M') for i, t in enumerate(pivot.columns) if i % label_step == 0]

        # ax.set_xticks(xtick_locs)
        # ax.set_xticklabels(xtick_labels, rotation=90, fontsize=8)


        # # lwegend
        # legend_elements = [
        #     Patch(facecolor=num_to_color[num], label=f"{num} - {name_class.get(num)}")
        #     for num in sorted(name_class.keys())
        # ]

        # plt.legend(handles=legend_elements, title="Clases", bbox_to_anchor=(1.01, 1), loc='upper left')
        # plt.tight_layout()
        # plt.title(f"{plotname} | Clases 15 min")


        # #######################################
        # plt.savefig(f"{folder_output_dir}/{plotname}_prediction_map.png", bbox_inches='tight')
        # logger.info(f"Saved image at {folder_output_dir}/{plotname}_prediction_map.png")

        # # save csv with the data
        # pivot.to_csv(f"{folder_output_dir}/{plotname}_prediction_map.csv")
        # logger.info(f"Saved csv at {folder_output_dir}/{plotname}_prediction_map.csv")
        # exit()


        return df_all_yamnet_1h
          

    except Exception as e:
        logger.error(f"Error in plot_prediction_map: {e}")



def plot_prediction_map_15_min_4h(df_all_yamnet: pd.DataFrame, df_ship_dock: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    try:
        df_copy = df_all_yamnet.copy()
        print(df_copy)
        # exit()


        #######################################
        df_copy = add_datetime_columns(df_copy, logger, date_col='Timestamp')

        #######################################
        df_copy.set_index('Timestamp', inplace=True)
        #resample 1h
        df_all_yamnet_1h_resample = df_copy.resample('1h').agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        df_all_yamnet_1h = df_all_yamnet_1h_resample
        ########################################


        # df_copy['mapped_class'] = df_copy['class'].map(taxonomy_map)
        # df_copy = df_copy.dropna(subset=['mapped_class'])

        # #class names to numbers
        # class_to_num = {cls: i+1 for i, cls in enumerate(df_copy['mapped_class'].unique())}
        # df_copy['class_num'] = df_copy['mapped_class'].map(class_to_num)
        # name_class = {v: k for k, v in class_to_num.items()}
        # df_copy['Timestamp'] = pd.to_datetime(df_copy['Timestamp'])
        # df_copy.set_index('Timestamp', inplace=True)



        # #######################################
        # #resample 15 min
        # resampled = df_copy.resample('15min').agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        # resampled = resampled.dropna(subset=['class_num'])


        # #######################################
        # #time
        # resampled['date'] = resampled.index.date
        # resampled['time_block'] = resampled.index.time  # Or .strftime('%H:%M') for cleaner strings
        # pivot = resampled.pivot(index='date', columns='time_block', values='class_num')

        # #######################################
        # #color mapping
        # if 'Siren' in set(taxonomy_map.values()):
        #     num_to_color = {num: COLOR_PALLET_PORT_L1[cls] for cls, num in class_to_num.items()}
        #     logger.info("Using 'NoisePort_Level_1' class for plotting")

        # ordered_colors = [num_to_color[i] for i in sorted(name_class.keys())]
        # cmap = ListedColormap(ordered_colors)

        # #######################################
        # #plotting
        # plt.figure(figsize=(20, 10))
        # ax = sns.heatmap(pivot, cmap=cmap, linewidth=0.3, cbar=False, linecolor='gray')

        # ax.set_title("Sound Class Predictions — Daily 15min Timeline")
        # ax.set_xlabel("Hora del Día", fontsize=14)
        # ax.set_ylabel("Fecha", fontsize=14)

        # label_step = 1 # 15 min 96 
        # # label_step = 2 #30 min
        # # label_step = 4  # 1h


        # xtick_locs = list(range(0, len(pivot.columns), label_step))
        # xtick_labels = [t.strftime('%H:%M') for i, t in enumerate(pivot.columns) if i % label_step == 0]

        # ax.set_xticks(xtick_locs)
        # ax.set_xticklabels(xtick_labels, rotation=90, fontsize=8)


        # # lwegend
        # legend_elements = [
        #     Patch(facecolor=num_to_color[num], label=f"{num} - {name_class.get(num)}")
        #     for num in sorted(name_class.keys())
        # ]

        # plt.legend(handles=legend_elements, title="Clases", bbox_to_anchor=(1.01, 1), loc='upper left')
        # plt.tight_layout()
        # plt.title(f"{plotname} | Clases 15 min")


        # #######################################
        # plt.savefig(f"{folder_output_dir}/{plotname}_prediction_map.png", bbox_inches='tight')
        # logger.info(f"Saved image at {folder_output_dir}/{plotname}_prediction_map.png")

        # # save csv with the data
        # pivot.to_csv(f"{folder_output_dir}/{plotname}_prediction_map.csv")
        # logger.info(f"Saved csv at {folder_output_dir}/{plotname}_prediction_map.csv")
        # exit()


        return df_all_yamnet_1h
          

    except Exception as e:
        logger.error(f"Error in plot_prediction_map: {e}")




def plot_prediction_map_new_week(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        df_copy = df_all_yamnet.copy()
        df_copy = add_datetime_columns(df_copy, logger, date_col='Timestamp')
        df_copy['Timestamp'] = pd.to_datetime(df_copy['Timestamp'])

        df_copy['mapped_class'] = df_copy['class'].map(taxonomy_map)
        df_copy = df_copy.dropna(subset=['mapped_class'])

        
        class_to_num = {cls: i + 1 for i, cls in enumerate(df_copy['mapped_class'].unique())}
        name_class = {v: k for k, v in class_to_num.items()}
        df_copy['class_num'] = df_copy['mapped_class'].map(class_to_num)

        
        try:
            df_copy['week'] = df_copy['Timestamp'].dt.to_period('W').start_time
        except Exception as e:
            df_copy['week'] = df_copy['Timestamp'].dt.to_period('W').apply(lambda r: r.start_time)


        
        if 'Siren' in set(taxonomy_map.values()):
            num_to_color = {num: COLOR_PALLET_PORT_L1[cls] for cls, num in class_to_num.items()}
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            num_to_color = {num: 'gray' for num in class_to_num.values()}  # fallback if no palette given

        ordered_colors = [num_to_color[i] for i in sorted(name_class.keys())]
        cmap = ListedColormap(ordered_colors)

        
        #######################3
        for week_start in df_copy['week'].unique():
            df_week = df_copy[df_copy['week'] == week_start].copy()
            if df_week.empty:
                continue

            df_week.set_index('Timestamp', inplace=True)
            resampled = df_week.resample('15min').agg(
                lambda x: x.mode().iloc[0] if not x.mode().empty else None
            ).dropna(subset=['class_num'])

            resampled['date'] = resampled.index.date
            resampled['time_block'] = resampled.index.time
            pivot = resampled.pivot(index='date', columns='time_block', values='class_num')

            


            #############################
            #############################
            plt.figure(figsize=(20, 10))
            ax = sns.heatmap(pivot, cmap=cmap, linewidth=0.3, cbar=False, linecolor='gray')

            ax.set_title("Sound Class Predictions — Daily 15min Timeline")
            ax.set_xlabel("Hora del Día", fontsize=14)
            ax.set_ylabel("Fecha", fontsize=14)

            xtick_locs = list(range(0, len(pivot.columns), 1))  # every 15min
            xtick_labels = [t.strftime('%H:%M') for i, t in enumerate(pivot.columns)]

            ax.set_xticks(xtick_locs)
            ax.set_xticklabels(xtick_labels, rotation=90, fontsize=8)

            
            legend_elements = [
                Patch(facecolor=num_to_color[num], label=f"{num} - {name_class.get(num)}")
                for num in sorted(name_class.keys())
            ]
            plt.legend(handles=legend_elements, title="Clases", bbox_to_anchor=(1.01, 1), loc='upper left')
            plt.tight_layout()
            plt.title(f"{plotname} | Clases 15 min | Semana {week_start.strftime('%Y-%m-%d')}")

            
            
            ###############
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            image_path = os.path.join(week_folder, f"{plotname}_prediction_map_{week_start.strftime('%Y-%m-%d')}.png")
            plt.savefig(image_path, bbox_inches='tight')
            plt.close()
            logger.info(f"Saved map image: {image_path}")


    except Exception as e:
        logger.error(f"Error in plot_prediction_map_weekly: {e}")




def plot_tree_map(df_Pred:pd.DataFrame,taxonomy_map, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("white")
        sns.set_palette("tab10")

        # prediction map foñder
        folder_output_dir = os.path.join(folder_output_dir, 'Prediction_Tree_Map')
        os.makedirs(folder_output_dir, exist_ok=True)

        # make duration to make the resample to 15 minutes
        start_date = df_Pred['date'].iloc[0]
        end_date = df_Pred['date'].iloc[-1]
        difference_between_first_days = df_Pred['date'].iloc[10] - df_Pred['date'].iloc[9]
        logger.info(f"Start date {start_date} and End date {end_date}")
        logger.info(f"Difference between first and second date: {difference_between_first_days}")

        # explode
        df_exploded = df_Pred.explode('class')
        df_exploded['display_name'] = df_exploded['class']
        df_exploded['number'] = 1

        #~insert date
        df_exploded = insert_dates(df_exploded)
        df_exploded['mapped_class'] = df_exploded['class'].map(taxonomy_map)

        #################################
        home_dir = os.path.expanduser('~')
        full_path = os.path.join(home_dir, RELATIVE_PATH_YAMNET_MAP.lstrip('\\'))
        union = pd.read_csv(full_path, sep=';')

        # merge classes with ontology
        df_exploded = df_exploded.merge(union, how='left', on='display_name')
        # remove Unnamed columns
        df_exploded = df_exploded.loc[:, ~df_exploded.columns.str.contains('^Unnamed')]


        display_name = 'display_name'
        iso_taxonomy = 'iso_taxonomy'
        classes = 'class'

        brown_1 = 'Brown_Level_1'
        brown_2 = 'Brown_Level_2'
        brown_3 = 'Brown_Level_3'
        noiseport_1 = 'NoisePort_Level_1'
        noiseport_2 = 'NoisePort_Level_2'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_pallet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2  
            color_pallet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")

        df_exploded = df_exploded.dropna(subset=[class_to_plot, 'class'])

        fig = px.treemap(df_exploded, 
                 path=[class_to_plot, 'class'], 
                 values='number',
                 color=class_to_plot,  #for coloring
                color_discrete_map=color_pallet
                )

        fig.update_layout(title=f'{plotname} | Clases')

        fig.write_html(f"{folder_output_dir}/{plotname}_prediction_tree_map.html")
        logger.info(f"{folder_output_dir}/{plotname}_prediction_tree_map.html")

        # save csv with the data
        df_exploded.to_csv(f"{folder_output_dir}/{plotname}_prediction_tree_map.csv")
        logger.info(f"Saved csv at {folder_output_dir}/{plotname}_prediction_tree_map.csv")

        #####################################      
        for day in df_exploded['day'].unique():
            day_df = df_exploded[df_exploded['day'] == day]
            fig = px.treemap(day_df, 
                     path=[class_to_plot, 'class'], 
                     values='number',
                     color=class_to_plot,  #for coloring
                    color_discrete_map=color_pallet
                    )
            
            fig.update_layout(title=f'{plotname} | {day_df["year"].iloc[0]}-{day_df["month"].iloc[0]}-{day}')

            fig.write_html(f"{folder_output_dir}/{plotname}_prediction_tree_map{day}.html")
            logger.info(f"{folder_output_dir}/{plotname}_prediction_tree_map{day}.html")

            # save csv with the data
            day_df.to_csv(f"{folder_output_dir}/{plotname}_prediction_tree_map{day}.csv")
            logger.info(f"Saved csv at {folder_output_dir}/{plotname}_prediction_tree_map{day}.csv")

    except Exception as e:
        logger.error(f"Error in plot_tree_map: {e}")




def make_time_plot(df: pd.DataFrame, folder_output_dir: str, logger, columns_dict: dict, agg_period: int, plotname: str, percentiles: list):
    try:
        logger.info(f"Using the columns_dict: {columns_dict}")
        # add an hour to the dataframe
        # df.index = df.index + pd.DateOffset(hours=1)
        # remove nan values
        df = df.dropna(subset=[columns_dict['LAEQ_COLUMN_COEFF']])
        
        agg_funcs = {
            columns_dict['LAEQ_COLUMN_COEFF']: leq,
            # columns_dict['LCEQ_COLUMN_COEFF']: leq,
            columns_dict['LAMAX_COLUMN_COEFF']: 'max',
            columns_dict['LAMIN_COLUMN_COEFF']: 'min'
            
        }

        df['Timestamp'] = pd.to_datetime(
            df['Timestamp'],
            errors='coerce',
            utc=True
        )

        df = (
            df.dropna(subset=['Timestamp'])
            .set_index('Timestamp')
            .sort_index()
        )
        logger.info(f"Using the columns_dict: {columns_dict}")

        logger.info(f"Using the agg_funcs: {agg_funcs}")
        df_LAeq = df.resample(f'{agg_period}s').agg(agg_funcs)
        oca = df.resample(f'{agg_period}s').agg({'oca': 'min'})


        # try a style, if not, use seaborn-whitegrid
        try:
            plt.style.use('seaborn-v0_8-whitegrid')
        except:
            plt.style.use('seaborn-whitegrid')
            
        fig, ax = plt.subplots(figsize=(20, 10))
        ax.set_facecolor("white")

        logger.info(f"Using the percentiles: {percentiles}")
        logger.info(f"Using the agg_period: {agg_period}")
        
        
        logger.info(f"Using the columns_dict: {columns_dict['LAEQ_COLUMN_COEFF']}, {columns_dict['LAMAX_COLUMN_COEFF']}, {columns_dict['LAMIN_COLUMN_COEFF']}")
        x = df_LAeq.index
        ax.plot(x, df_LAeq[columns_dict['LAEQ_COLUMN_COEFF']], linewidth=3, color='red', label='LAeq')
        #plot LCEQ
        # ax.plot(x, df_LAeq[columns_dict['LCEQ_COLUMN_COEFF']], linewidth=1, color='blue', label='LCeq')
        ax.plot(x, df_LAeq[columns_dict['LAMAX_COLUMN_COEFF']], linewidth=1, color='#FF99FF', label='Lmax')
        ax.plot(x, df_LAeq[columns_dict['LAMIN_COLUMN_COEFF']], linewidth=1, color='#92D050', label='Lmin')
        
        if SHOW_OCA:
            # OCA
            ax.plot(x, oca.values, color='#00B0F0', label='OCA')


        percentile_data = {}
        for percentile in percentiles:
            quantile_value = (100 - percentile) / 100
            percentile_series = df[columns_dict['LAEQ_COLUMN_COEFF']].resample(f'{agg_period}s').quantile(quantile_value)
            ax.plot(x, percentile_series, linewidth=0.5, label=f'L{percentile}', color=PERCENTIL_COLOUR[percentile])
            percentile_data[f'L{percentile}'] = percentile_series


        # debugg time of the plot
        hours = mdates.HourLocator(interval=HOUR_INTERVAL)
        h_fmt = mdates.DateFormatter('%d-%m-%y %H:%M')
        
        ax.xaxis.set_major_locator(hours)
        ax.xaxis.set_major_formatter(h_fmt)

        plt.xlim(df.index.min(), df.index.max())
        plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
        plt.ylabel('dB(A)', fontsize=BIGGEST_SIZE)
        plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
        plt.title(f'{plotname} Nivel equivalente {agg_period}s', fontsize=BIGGEST_SIZE)

        plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)
        plt.yticks(fontsize=BIGGEST_SIZE)

        plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0.1, fancybox=True, framealpha=1, edgecolor='black', fontsize=BIGGEST_SIZE)
        
        plt.tight_layout()
        
        # make grid
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)

        # save
        os.makedirs(folder_output_dir, exist_ok=True)

        logger.info(f"Saving the plot {plotname}")
        plt.savefig(f'{folder_output_dir}/{plotname}_{agg_period}s_time_plot.png', dpi=350) # dpi stands for dots per inch, the more the dpi the better the quality of the image
        logger.info(f"Timeplot saved to {folder_output_dir}/{plotname}_{agg_period}s_time_plot.png")




        # --- save CSV ---
        df_plot_data = df_LAeq.copy()
        df_plot_data['oca'] = oca['oca']
        for col_name, series in percentile_data.items():
            df_plot_data[col_name] = series

        # save
        output_csv = f'{folder_output_dir}/{plotname}_{agg_period}s_time_plot.csv'
        logger.info(f"Saving the data to {output_csv}")
        df_plot_data.to_csv(output_csv, index=True)
        logger.info(f"Timeplot data saved to {output_csv}")

        plt.close()


    except Exception as e:
        logger.error(f"Error in make_timeplot: {e}")





def make_time_plot_week(df: pd.DataFrame, folder_output_dir: str, logger, columns_dict: dict, agg_period: int, plotname: str, percentiles: list):
    try:
        logger.info(f"Using the columns_dict: {columns_dict}")
        df = df.dropna(subset=[columns_dict['LAEQ_COLUMN_COEFF']])
        df.index = pd.to_datetime(df.index)

        df['week'] = df.index.to_period('W').start_time
        weeks = df['week'].unique()

        for week_start in weeks:
            df_week = df[df['week'] == week_start]

            agg_funcs = {
                columns_dict['LAEQ_COLUMN_COEFF']: leq,
                columns_dict['LAMAX_COLUMN_COEFF']: 'max',
                columns_dict['LAMIN_COLUMN_COEFF']: 'min'
            }

            df_LAeq = df_week.resample(f'{agg_period}s').agg(agg_funcs)
            oca = df_week.resample(f'{agg_period}s').agg({'oca': 'min'})

            try:
                plt.style.use('seaborn-v0_8-whitegrid')
            except:
                plt.style.use('seaborn-whitegrid')

            fig, ax = plt.subplots(figsize=(20, 10))
            ax.set_facecolor("white")

            x = df_LAeq.index
            ax.plot(x, df_LAeq[columns_dict['LAEQ_COLUMN_COEFF']], linewidth=3, color='red', label='LAeq')
            ax.plot(x, df_LAeq[columns_dict['LAMAX_COLUMN_COEFF']], linewidth=1, color='#FF99FF', label='Lmax')
            ax.plot(x, df_LAeq[columns_dict['LAMIN_COLUMN_COEFF']], linewidth=1, color='#92D050', label='Lmin')

            if SHOW_OCA:
                ax.plot(x, oca.values, color='#00B0F0', label='OCA')

            for percentile in percentiles:
                quantile_value = (100 - percentile) / 100
                percentile_series = df_week[columns_dict['LAEQ_COLUMN_COEFF']].resample(f'{agg_period}s').quantile(quantile_value)
                ax.plot(x, percentile_series, linewidth=0.5, label=f'L{percentile}', color=PERCENTIL_COLOUR[percentile])

            # time formatting
            hours = mdates.HourLocator(interval=HOUR_INTERVAL)
            h_fmt = mdates.DateFormatter('%d-%m-%y %H:%M')
            ax.xaxis.set_major_locator(hours)
            ax.xaxis.set_major_formatter(h_fmt)

            plt.xlim(df_week.index.min(), df_week.index.max())
            plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
            plt.ylabel('dB(A)', fontsize=BIGGEST_SIZE)
            plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
            plt.title(f'{plotname} Nivel equivalente {agg_period}s - Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)

            plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)
            plt.yticks(fontsize=BIGGEST_SIZE)
            plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0.1, fancybox=True, framealpha=1, edgecolor='black', fontsize=BIGGEST_SIZE)
            plt.grid(True, which='both', linestyle='--', linewidth=0.5)

            plt.tight_layout()

            #make folder for week
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            output_path = f'{week_folder}/{plotname}_{agg_period}s_time_plot_week_{week_start.strftime("%Y-%m-%d")}.png'
            logger.info(f"Saving the weekly plot to {output_path}")
            plt.savefig(output_path, dpi=350)
            plt.close()
            logger.info(f"Plot saved: {output_path}")

    except Exception as e:
        logger.error(f"Error in make_time_plot_weekly: {e}")






def plot_heatmap_evolution_hour(df, folder_output_dir: str, logger, values_column: str, agg_func: str, plotname:str):
    try:
        # remove nan values
        df = df.dropna(subset=[values_column])
        logger.info(f"Using the values_column: {values_column}")
        sns.set_style("white")
        sns.set_palette("tab10")
        
        df['Día'] = df['day_name'].replace(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        df['date_day'] = df['date'].astype(str) + ' ' + df['Día']
        
        leq_day_hour = pd.pivot_table(
            df, 
            values=values_column, 
            index=['date_day'],
            columns=['hour'], 
            aggfunc=agg_func
        ).round(1)
  
        leq_day_hour.columns = [f"{hour:02d}:00" for hour in leq_day_hour.columns]
        
        plt.figure(figsize=(20,10))
        heatmap =sns.heatmap(
            leq_day_hour, 
            vmin=30, 
            vmax=85, 
            cmap=cmap_dict, 
            annot=True,
            annot_kws={"size": BIGGER_SIZE}
        )
        
        plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
        plt.ylabel('Día', fontsize=BIGGEST_SIZE)
        plt.title(f'{plotname} Nivel equivalente', fontsize=BIGGEST_SIZE)
        
        plt.yticks(rotation=0, fontsize=BIGGEST_SIZE)
        plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)

        cbar = heatmap.collections[0].colorbar
        cbar.ax.tick_params(labelsize=BIGGEST_SIZE)

        plt.tight_layout()
        
        os.makedirs(f'{folder_output_dir}', exist_ok=True)
        
        logger.info(f"Saving the plot {plotname}")
        plt.savefig(f'{folder_output_dir}/{plotname}_heatmap_evolucion.png',dpi=350)
        logger.info(f"Heatmap plot saved to {folder_output_dir}/{plotname}_heatmap_evolucion.png")

        logger.info(f"Saving the data {plotname}")
        leq_day_hour.to_csv(f'{folder_output_dir}/{plotname}_heatmap_evolucion.csv', index=True)
        logger.info(f"Heatmap data saved to {folder_output_dir}/{plotname}_heatmap_evolucion.csv")
        
        plt.close()
        
    except Exception as e:
        logger.error(f"Error in plot_heatmap_evolution_hour: {e}")




def plot_heatmap_evolution_hour_week(df, folder_output_dir: str, logger, values_column: str, agg_func: str, plotname: str):
    try:
        df = df.dropna(subset=[values_column])
        df['date'] = pd.to_datetime(df['date'])
        df['day_name'] = df['date'].dt.day_name()
        df['hour'] = df['date'].dt.hour
        df.index = pd.to_datetime(df['date'])

        # df['week'] = df['date'].dt.to_period('W').start_time
        df['week'] = df['date'].dt.to_period('W').dt.start_time
        weeks = df['week'].unique()

        for week_start in weeks:
            df_week = df[df['week'] == week_start].copy()
            df_week['Día'] = df_week['day_name'].replace([
                'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
            ], [
                'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'
            ])
            df_week['date_day'] = df_week['date'].dt.strftime('%Y-%m-%d') + ' ' + df_week['Día']

            leq_day_hour = pd.pivot_table(
                df_week,
                values=values_column,
                index=['date_day'],
                columns=['hour'],
                aggfunc=agg_func
            ).round(1)

            if leq_day_hour.empty:
                logger.warning(f"No data to plot for week {week_start.strftime('%Y-%m-%d')}")
                continue

            leq_day_hour.columns = [f"{hour:02d}:00" for hour in leq_day_hour.columns]

            plt.figure(figsize=(20, 10))
            heatmap = sns.heatmap(
                leq_day_hour,
                vmin=30,
                vmax=85,
                cmap=cmap_dict,
                annot=True,
                annot_kws={"size": BIGGER_SIZE}
            )

            plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
            plt.ylabel('Día', fontsize=BIGGEST_SIZE)
            plt.title(f'{plotname} Nivel equivalente - Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)

            plt.yticks(rotation=0, fontsize=BIGGEST_SIZE)
            plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)

            cbar = heatmap.collections[0].colorbar
            cbar.ax.tick_params(labelsize=BIGGEST_SIZE)
            plt.tight_layout()


            #make folder for week
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)


            #save
            filename = f"{plotname}_heatmap_evolucion_week_{week_start.strftime('%Y-%m-%d')}"
            image_path = f'{week_folder}/{filename}.png'

            logger.info(f"Saving heatmap to {image_path}")
            plt.savefig(image_path, dpi=350)
            plt.close()

    except Exception as e:
        logger.error(f"Error in plot_heatmap_evolution_hour_week: {e}")





def plot_heatmap_evolution_15_min(df, folder_output_dir: str, logger, values_column: str, agg_func: str, plotname:str):
    if not isinstance(df.index, pd.DatetimeIndex):
        logger.error("DataFrame index is not a datetime index.")
        return

    try:
        # remove nan values
        df = df.dropna(subset=[values_column])
        logger.info(f"Using the values_column: {values_column}")
        sns.set_style("white")
        sns.set_palette("tab10")
        
        def get_15min_interval(dt):
            return f"{dt.hour:02d}:{(dt.minute // 15) * 15:02d}"

        df['Día'] = df['day_name'].replace(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        df['date_day'] = df['date'].astype(str) + ' ' + df['Día']
        df['15min_interval'] = df.index.map(get_15min_interval)

        leq_day_15min = pd.pivot_table(
            df, 
            values=values_column, 
            index=['date_day'],
            columns=['15min_interval'], 
            aggfunc=agg_func
        ).round(1)
        

        plt.figure(figsize=(20,10))
        heatmap =sns.heatmap(
            leq_day_15min, 
            vmin=30, 
            vmax=85, 
            cmap=cmap_dict, 
            # annot=True,
            # annot_kws={"size": MEDIUM_SIZE}
        )
        
        plt.xlabel('Hora', fontsize=BIGGEST_15_MIN_SIZE)
        plt.ylabel('Día', fontsize=BIGGEST_15_MIN_SIZE)
        plt.title(f'{plotname} Nivel equivalente 15 minutos', fontsize=30)
        
        plt.yticks(rotation=0, fontsize=BIGGEST_15_MIN_SIZE)
        plt.xticks(rotation=90, fontsize=BIGGEST_15_MIN_SIZE)

        cbar = heatmap.collections[0].colorbar
        cbar.ax.tick_params(labelsize=BIGGEST_15_MIN_SIZE)
        
        plt.tight_layout()
        
        os.makedirs(f'{folder_output_dir}', exist_ok=True)

        logger.info(f"Saving the plot {plotname}")
        plt.savefig(f'{folder_output_dir}/{plotname}_heatmap_evolucion_15_min.png',dpi=150)
        logger.info(f"Heatmap plot saved to {folder_output_dir}/{plotname}_heatmap_evolucion_15_min.png")

        logger.info(f"Saving the data {plotname}")
        leq_day_15min.to_csv(f'{folder_output_dir}/{plotname}_heatmap_evolucion_15_min.csv', index=False)
        logger.info(f"Heatmap data saved to {folder_output_dir}/{plotname}_heatmap_evolucion_15_min.csv")
        
        plt.close()
        
    except Exception as e:
        logger.error(f"Error in plot_heatmap: {e}")



def plot_heatmap_evolution_15_min_week(df, folder_output_dir: str, logger, values_column: str, agg_func: str, plotname: str):
    if not isinstance(df.index, pd.DatetimeIndex):
        logger.error("DataFrame index is not a datetime index.")
        return

    try:
        #remove nan
        df = df.dropna(subset=[values_column])
        df['date'] = pd.to_datetime(df['date'])
        df['day_name'] = df['date'].dt.day_name()
        df['week'] = df['date'].dt.to_period('W').dt.start_time
        logger.info(f"Using the values_column: {values_column}")
        
        sns.set_style("white")
        sns.set_palette("tab10")
        
        def get_15min_interval(dt):
            return f"{dt.hour:02d}:{(dt.minute // 15) * 15:02d}"

        weeks = df['week'].unique()
        
        for week_start in weeks:
            df_week = df[df['week'] == week_start].copy()
            df_week['Día'] = df_week['day_name'].replace([
                'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
            ], [
                'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'
            ])
            df_week['date_day'] = df_week['date'].dt.strftime('%Y-%m-%d') + ' ' + df_week['Día']
            df_week['15min_interval'] = df_week.index.map(get_15min_interval)

            leq_day_15min = pd.pivot_table(
                df_week, 
                values=values_column, 
                index=['date_day'],
                columns=['15min_interval'], 
                aggfunc=agg_func
            ).round(1)

            if leq_day_15min.empty:
                logger.warning(f"No data for week {week_start.strftime('%Y-%m-%d')}")
                continue

            plt.figure(figsize=(20, 10))
            heatmap = sns.heatmap(
                leq_day_15min,
                vmin=30,
                vmax=85,
                cmap=cmap_dict,
                # annot=True,
                # annot_kws={"size": MEDIUM_SIZE}
            )

            plt.xlabel('Hora (15 min)', fontsize=BIGGEST_15_MIN_SIZE)
            plt.ylabel('Día', fontsize=BIGGEST_15_MIN_SIZE)
            plt.title(f'{plotname} Nivel equivalente 15 minutos - Semana {week_start.strftime("%Y-%m-%d")}', fontsize=30)

            plt.yticks(rotation=0, fontsize=BIGGEST_15_MIN_SIZE)
            plt.xticks(rotation=90, fontsize=BIGGEST_15_MIN_SIZE)

            cbar = heatmap.collections[0].colorbar
            cbar.ax.tick_params(labelsize=BIGGEST_15_MIN_SIZE)
            plt.tight_layout()


            #make folder for week
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            filename = f"{plotname}_heatmap_evolucion_15_min_week_{week_start.strftime('%Y-%m-%d')}"
            image_path = f'{week_folder}/{filename}.png'

            logger.info(f"Saving heatmap to {image_path}")
            plt.savefig(image_path, dpi=150)
            plt.close()


    except Exception as e:
        logger.error(f"Error in plot_heatmap_evolution_15_min_week: {e}")






def plot_indicadores_heatmap(df, folder_output_dir: str, logger, plotname:str, ind_column:str):
    try:
        # remove nan values
        df = df.dropna(subset=[ind_column])
        logger.info(f"Using the ind_column: {ind_column}")
        sns.set_style("white")
        sns.set_palette("tab10")

        if "Fecha" not in df.columns and "Date hour" in df.columns:
            logger.info(f"Date hour column found, using it as Fecha")
            # df["Fecha"] = df["Date hour"]
            df["Fecha"] = pd.to_datetime(df['Date hour'], dayfirst=True)
            logger.info(f"Date hour column found, using it as Fecha")
        
        if "Fecha" not in df.columns and "Time" in df.columns:
            logger.info(f"Time column found, using it as Fecha")
            df["Fecha"] = pd.to_datetime(df['Time'], dayfirst=True)
            logger.info(f"Time column found, using it as Fecha")
            
        if "Fecha" not in df.columns and "marcadores" in df.columns:
            logger.info("No Fecha column found")
            # reindex datetime index column
            if isinstance(df.index, pd.DatetimeIndex):
                # uncomment if you want to reset the index
                # df.reset_index(inplace=True)
                df["Fecha"] = pd.to_datetime(df['datetime'], dayfirst=True)
                logger.info(f"Using the datetime index as Fecha")

        if "Fecha" not in df.columns and 'OVLD' not in df.columns:
            # copy 'date' colimn and named it as 'Fecha'
            df['Fecha'] = df['datetime']
            logger.info(f"Using the datetime index as Fecha")

        # if 'Fecha' and 'datetime' columns are present, use 'datetime' as 'Fecha'
        if 'Fecha' in df.columns and 'datetime' in df.columns:
            df['Fecha'] = df['datetime']
            logger.info(f"Using the datetime index as Fecha")


        df_indicadores = (df.groupby(['date','indicador_str'])['Fecha'].agg(['first','last']))
        df_indicadores['duration'] = df_indicadores.apply(lambda row: calculate_duration(row['first'], row['last']), axis=1)
        
        # set weekday in the plot
        df['date_weekday'] = df['Fecha'].dt.strftime('%Y-%m-%d') + ' ' + df['Fecha'].dt.day_name().replace(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        
        # indicators to check
        indicators_to_check = ['Ld', 'Le', 'Ln']

        # select first and last day
        first_day = df['date'].min()
        last_day = df['date'].max()

        # check presence of indicators
        presence_first_day = {indicator: indicator in df[df['date'] == first_day]['indicador_str'].unique() for indicator in indicators_to_check}
        presence_last_day = {indicator: indicator in df[df['date'] == last_day]['indicador_str'].unique() for indicator in indicators_to_check}
        logger.info(f"Presence of indicators in first day {first_day}: {presence_first_day}")
        logger.info(f"Presence of indicators in last day {last_day}: {presence_last_day}")

        # 'duration of indicators
        duration_first_day = {indicator: df_indicadores.loc[(first_day, indicator), 'duration'] if presence_first_day[indicator] else 0 for indicator in indicators_to_check}
        duration_last_day = {indicator: df_indicadores.loc[(last_day, indicator), 'duration'] if presence_last_day[indicator] else 0 for indicator in indicators_to_check}
        
        # log duration information
        for indicator in indicators_to_check:
            logger.info(f"Duration of {indicator} on the first day {first_day}: {duration_first_day[indicator]}")
            logger.info(f"Duration of {indicator} on the last day {last_day}: {duration_last_day[indicator]}")

        # apply filter based on duration and presence
        for indicator in indicators_to_check:
            if presence_first_day[indicator] and duration_first_day[indicator] <= LE_SECONDS:
                df = df[~((df['date'] == first_day) & (df['indicador_str'] == indicator))]
                logger.info(f"{indicator} indicator from first day {first_day} removed, less than {LE_SECONDS} seconds")

            if presence_last_day[indicator] and duration_last_day[indicator] <= LE_SECONDS:
                df = df[~((df['date'] == last_day) & (df['indicador_str'] == indicator))]
                logger.info(f"{indicator} indicator from last day {last_day} removed, less than {LE_SECONDS} seconds")
        


        # make the energy average of the indicators
        indicadores_table = pd.pivot_table(
            data=df,
            index="date_weekday",
            columns="indicador_str",
            values=ind_column,
            aggfunc=leq
        ).round(1)

        desired_order = ["Ln", "Ld", "Le"]
        indicadores_table = indicadores_table.reindex(columns=desired_order)

        plt.figure(figsize=(15, 8))
        
        ax = sns.heatmap(
            indicadores_table, 
            annot=True, 
            fmt=".1f", 
            linewidth=0.5, 
            cmap=cmap_dict, 
            vmin=30, 
            vmax=85,
            annot_kws={"size": MEDIUM_SIZE}
        )
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
        
        plt.ylabel('Día', fontsize=BIGGEST_SIZE)
        plt.xlabel('Indicador', fontsize=BIGGEST_SIZE)
        plt.title(f'{plotname} Indicadores', fontsize=BIGGEST_SIZE)

        plt.yticks(rotation=0, fontsize=BIGGEST_SIZE)
        plt.xticks(rotation=0, fontsize=BIGGEST_SIZE)

        cbar = ax.collections[0].colorbar
        cbar.ax.tick_params(labelsize=BIGGEST_SIZE)

        plt.tight_layout()
        
        os.makedirs(f'{folder_output_dir}', exist_ok=True)

        logger.info(f"Saving the plot {plotname}")
        plt.savefig(f"{folder_output_dir}/{plotname}_indicadores.png")
        logger.info(f"Indicadores plot saved to {folder_output_dir}\{plotname}_indicadores.png")
        
        logger.info(f"Saving the data {plotname}")
        indicadores_table.to_csv(f"{folder_output_dir}/{plotname}_indicadores.csv", index=True)
        logger.info(f"Indicadores data saved to {folder_output_dir}\{plotname}_indicadores.csv")
        
        plt.close()
        
        
        # indicador power average
        general_power_averages = indicadores_table.apply(leq).round(1)
        general_power_averages_df = general_power_averages.to_frame().transpose()
        
        os.makedirs(f'{folder_output_dir}', exist_ok=True)

        logger.info(f"Indicadores generales data {plotname}")
        general_power_averages_df.to_csv(f'{folder_output_dir}/{plotname}_indicadores_generales.csv', index=False)
        logger.info(f"Indicadores generales data saved to {folder_output_dir}/{plotname}_indicadores_generales.csv")
    
    except Exception as e:
        logger.error(f"Error in plot_indicadores_heatmap: {e}")




def plot_indicadores_heatmap_week(df, folder_output_dir: str, logger, plotname: str, ind_column: str):
    try:
        # remove nan values
        df = df.dropna(subset=[ind_column])
        logger.info(f"Using the ind_column: {ind_column}")
        sns.set_style("white")
        sns.set_palette("tab10")

        # Set or correct Fecha column
        if "Fecha" not in df.columns:
            if "Date hour" in df.columns:
                df["Fecha"] = pd.to_datetime(df['Date hour'], dayfirst=True)
            elif "Time" in df.columns:
                df["Fecha"] = pd.to_datetime(df['Time'], dayfirst=True)
            elif "marcadores" in df.columns and isinstance(df.index, pd.DatetimeIndex):
                df["Fecha"] = df.index
            elif 'OVLD' not in df.columns and 'datetime' in df.columns:
                df['Fecha'] = df['datetime']
            else:
                logger.error("No valid Fecha or datetime column found.")
                return
        elif "datetime" in df.columns:
            df['Fecha'] = df['datetime']

        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['week'] = df['Fecha'].dt.to_period('W').dt.start_time
        df['date'] = df['Fecha'].dt.date

        weeks = df['week'].unique()

        for week_start in weeks:
            df_week = df[df['week'] == week_start].copy()

            # Calculate duration of indicators
            df_indicadores = df_week.groupby(['date', 'indicador_str'])['Fecha'].agg(['first', 'last'])
            df_indicadores['duration'] = df_indicadores.apply(lambda row: calculate_duration(row['first'], row['last']), axis=1)

            df_week['date_weekday'] = df_week['Fecha'].dt.strftime('%Y-%m-%d') + ' ' + df_week['Fecha'].dt.day_name().replace(
                ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            )

            # Indicators to check
            indicators_to_check = ['Ld', 'Le', 'Ln']
            first_day = df_week['date'].min()
            last_day = df_week['date'].max()

            # Filter based on short duration
            for indicator in indicators_to_check:
                for target_day, tag in [(first_day, "first"), (last_day, "last")]:
                    present = indicator in df_week[df_week['date'] == target_day]['indicador_str'].unique()
                    if present:
                        try:
                            duration = df_indicadores.loc[(target_day, indicator), 'duration']
                            logger.info(f"Duration of {indicator} on {tag} day {target_day}: {duration}")
                            if duration <= LE_SECONDS:
                                df_week = df_week[~((df_week['date'] == target_day) & (df_week['indicador_str'] == indicator))]
                                logger.info(f"{indicator} indicator from {tag} day {target_day} removed (<={LE_SECONDS} s)")
                        except KeyError:
                            continue

            # Pivot to get energy average per indicator
            indicadores_table = pd.pivot_table(
                data=df_week,
                index="date_weekday",
                columns="indicador_str",
                values=ind_column,
                aggfunc=leq
            ).round(1)

            if indicadores_table.empty:
                logger.warning(f"No data to plot for week {week_start.strftime('%Y-%m-%d')}")
                continue

            desired_order = ["Ln", "Ld", "Le"]
            indicadores_table = indicadores_table.reindex(columns=desired_order)

            plt.figure(figsize=(15, 8))
            ax = sns.heatmap(
                indicadores_table,
                annot=True,
                fmt=".1f",
                linewidth=0.5,
                cmap=cmap_dict,
                vmin=30,
                vmax=85,
                annot_kws={"size": MEDIUM_SIZE}
            )
            ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
            plt.ylabel('Día', fontsize=BIGGEST_SIZE)
            plt.xlabel('Indicador', fontsize=BIGGEST_SIZE)
            plt.title(f'{plotname} Indicadores - Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)

            plt.yticks(rotation=0, fontsize=BIGGEST_SIZE)
            plt.xticks(rotation=0, fontsize=BIGGEST_SIZE)

            cbar = ax.collections[0].colorbar
            cbar.ax.tick_params(labelsize=BIGGEST_SIZE)
            plt.tight_layout()


            #creating folder for week
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)




            filename_base = f"{plotname}_indicadores_week_{week_start.strftime('%Y-%m-%d')}"
            plot_path = f"{week_folder}/{filename_base}.png"
            csv_path = f"{week_folder}/{filename_base}.csv"
            summary_path = f"{week_folder}/{filename_base}_generales.csv"

            plt.savefig(plot_path)
            logger.info(f"Saved heatmap to {plot_path}")
            plt.close()

            indicadores_table.to_csv(csv_path, index=True)
            logger.info(f"Saved table to {csv_path}")

            general_power_averages = indicadores_table.apply(leq).round(1).to_frame().transpose()
            general_power_averages.to_csv(summary_path, index=False)
            logger.info(f"Saved general averages to {summary_path}")

    except Exception as e:
        logger.error(f"Error in plot_indicadores_heatmap_week: {e}")




def plot_day_evolution(df, folder_output_dir: str, logger, laeq_column: str, plotname: str):
    try:
        # remove nan values
        df = df.dropna(subset=[laeq_column])
        df = df.reset_index(drop=True)
        df = df.drop_duplicates()
        logger.info(f"Using the laeq_column: {laeq_column}")

        sns.set_style("whitegrid")
        sns.set_palette("tab10")
        
        # translate the day name to Spanish
        df['Día'] = df['day_name'].replace(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        )
        
        weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        df['Día'] = pd.Categorical(df['Día'], categories=weekdays, ordered=True)
        
        fig = sns.relplot(
            data=df,
            x="hour",
            y=laeq_column,
            kind="line", # kind is the type of plot to draw
            hue="Día", # hue is the column to split the data
            estimator=leq,  # estimator is the function to apply to the data
            aspect=1.3, # aspect is the width/height ratio
            palette=C_MAP_WEEKDAY,
        )

        fig.set(xlim=(-1, 24), ylim=(DB_RANGE_BOTTOM, DB_RANGE_TOP))

        # change the x-axis labels to 24-hour format
        hour_labels = [f"{hour:02d}:00" for hour in range(24)]
        plt.xticks(range(24), hour_labels, rotation=90)

        plt.yticks(range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP), [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)])

        for ax in fig.axes.flat:
            ax.spines['top'].set_visible(True)
            ax.spines['right'].set_visible(True)
        
        plt.axvline(x=6.50, color=".7", dashes=(2, 1), zorder=0)  # 6:45 AM
        plt.axvline(x=18.50, color=".7", dashes=(2, 1), zorder=0)  # 6:45 PM
        plt.axvline(x=22.50, color=".7", dashes=(2, 1), zorder=0)  # 10:45 PM

        plt.text(s="Ln", x=0.13, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")
        plt.text(s="Ld", x=0.53, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")
        plt.text(s="Le", x=0.85, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")
        plt.text(s="Ln", x=0.96, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")
        
        plt.title(f"Evolución día {plotname} Date {df['date'].iloc[0]} - {df['date'].iloc[-1]}", fontsize=14)
        plt.ylabel('dB(A)')
        plt.xlabel('Hora')

        logger.info(f"Day evolution plot created for {plotname} Date {df['date'].iloc[0]} - {df['date'].iloc[-1]}")
        
        os.makedirs(folder_output_dir, exist_ok=True)

        logger.info(f"Saving the plot {plotname}")
        fig.savefig(f"{folder_output_dir}/{plotname}_day_evolution.png", dpi=300)
        logger.info(f"Day evolution plot saved to {folder_output_dir}/{plotname}_day_evolution.png")

        logger.info(f"Saving the data {plotname}")
        df.to_csv(f"{folder_output_dir}/{plotname}_day_evolution.csv", index=False)
        logger.info(f"Day evolution data saved to {folder_output_dir}/{plotname}_day_evolution.csv")

        plt.close()

    except Exception as e:
        logger.error(f"Error in plot_day_evolution: {e}")



def plot_day_evolution_week(df, folder_output_dir: str, logger, laeq_column: str, plotname: str):
    try:
        df = df.dropna(subset=[laeq_column])
        df = df.reset_index(drop=True)
        df = df.drop_duplicates()
        logger.info(f"Using the laeq_column: {laeq_column}")


        sns.set_style("whitegrid")
        sns.set_palette("tab10")

        df['Día'] = df['day_name'].replace(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        )
        weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        df['Día'] = pd.Categorical(df['Día'], categories=weekdays, ordered=True)

        # df['week'] = df['date'].dt.to_period('W').dt.start_time
        df['week'] = pd.to_datetime(df['date']).dt.to_period('W').dt.start_time
        weeks = df['week'].unique()

        for week_start in weeks:
            df_week = df[df['week'] == week_start].copy()

            if df_week.empty:
                logger.warning(f"No data for week starting {week_start}")
                continue

            fig = sns.relplot(
                data=df_week,
                x="hour",
                y=laeq_column,
                kind="line",
                hue="Día",
                estimator=leq,
                aspect=1.3,
                palette=C_MAP_WEEKDAY,
            )

            fig.set(xlim=(-1, 24), ylim=(DB_RANGE_BOTTOM, DB_RANGE_TOP))

            hour_labels = [f"{hour:02d}:00" for hour in range(24)]
            plt.xticks(range(24), hour_labels, rotation=90)
            plt.yticks(
                range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP),
                [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)]
            )

            for ax in fig.axes.flat:
                ax.spines['top'].set_visible(True)
                ax.spines['right'].set_visible(True)

            plt.axvline(x=6.50, color=".7", dashes=(2, 1), zorder=0)
            plt.axvline(x=18.50, color=".7", dashes=(2, 1), zorder=0)
            plt.axvline(x=22.50, color=".7", dashes=(2, 1), zorder=0)

            # labels
            plt.text(s="Ln", x=0.13, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")
            plt.text(s="Ld", x=0.53, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")
            plt.text(s="Le", x=0.85, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")
            plt.text(s="Ln", x=0.96, y=0.97, transform=plt.gca().transAxes, c="Black", weight="bold")

            start_date = df_week['date'].min().strftime('%Y-%m-%d')
            end_date = df_week['date'].max().strftime('%Y-%m-%d')
            plt.title(f"Evolución día {plotname} Semana {week_start.strftime('%Y-%m-%d')}", fontsize=14)
            plt.ylabel('dB(A)')
            plt.xlabel('Hora')

            #creating folder for week
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)


            filename_base = f"{plotname}_day_evolution_week_{week_start.strftime('%Y-%m-%d')}"
            image_path = f"{week_folder}/{filename_base}.png"

            logger.info(f"Saving plot to {image_path}")
            fig.savefig(image_path, dpi=300)
            plt.close()

    except Exception as e:
        logger.error(f"Error in plot_day_evolution_weekly: {e}")





def plot_period_evolution(df,  folder_output_dir: str, logger, laeq_column:str, plotname:str):
    try:
        df = df.dropna(subset=[laeq_column])
        df = df.reset_index(drop=True)
        df = df.drop_duplicates()
        logger.info(f"Using the laeq_column: {laeq_column}")
        
        sns.set_style("whitegrid")
        sns.set_palette("tab10")
        
        # translate the day name to spanish from english in day_name
        df['Día'] = df['day_name'].replace(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        
        weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        df['Día'] = pd.Categorical(df['Día'], categories=weekdays, ordered=True)
        
        for ind in df["indicador_str"].unique():
            if ind == 'Ln':
                continue
            
            df_temp = df[df["indicador_str"] == ind]
            
            fig = sns.relplot(
                data=df_temp,
                x="hour",
                y=laeq_column,
                kind="line", # kind is the type of plot to draw
                hue="Día", # hue is the column to split the data
                estimator=leq,  # estimator is the function to apply to the data
                aspect=1.3, # aspect is the width/height ratio
                palette=C_MAP_WEEKDAY,
            )
            
            if ind == 'Ld':
                fig.set(xlim=(6, 19), ylim=(DB_RANGE_BOTTOM, DB_RANGE_TOP))
                plt.xticks(range(7, 19), [f"{hour:02d}:00" for hour in range(7, 19)])
                logger.info(f"Plotted Ld")
                
            elif ind == 'Le':
                fig.set(xlim=(18.7, 22.3), ylim=(DB_RANGE_BOTTOM, DB_RANGE_TOP))
                plt.xticks([18.7, 19, 20, 21, 22, 22.3], ['', '19:00', '20:00', '21:00', '22:00', ''])
                logger.info(f"Ploted Le")

            plt.yticks(range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP), [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)])

            for ax in fig.axes.flat:
                ax.spines['top'].set_visible(True)
            
            ax.spines['right'].set_visible(True)
            plt.title(f"Evolución {ind}")
            plt.ylabel('dB(A)')
            plt.xlabel('Hora')
        
            os.makedirs(f'{folder_output_dir}', exist_ok=True)
            
            logger.info(f"Saving the plot {plotname}_{ind}")
            fig.savefig(f"{folder_output_dir}/{plotname}_{ind}_evolution.png",dpi=150)
            logger.info(f"Period evolution plot saved to {folder_output_dir}/{plotname}_{ind}_evolution.png")

            logger.info(f"Saving the data {plotname}_{ind}")
            df_temp.to_csv(f"{folder_output_dir}/{plotname}_{ind}_evolution.csv", index=False)
            logger.info(f"Period evolution data saved to {folder_output_dir}/{plotname}_{ind}_evolution.csv")
        
            plt.close()
        
    
    except Exception as e:
        logger.error(f"Error in plot_period_evolution: {e}")




def plot_period_evolution_week(df,  folder_output_dir: str, logger, laeq_column:str, plotname:str):
    try:
        df = df.dropna(subset=[laeq_column])
        df = df.reset_index(drop=True)
        df = df.drop_duplicates()
        logger.info(f"Using the laeq_column: {laeq_column}")
        
        sns.set_style("whitegrid")
        sns.set_palette("tab10")
        
        # translate the day name to spanish from english in day_name
        df['Día'] = df['day_name'].replace(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        
        weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        df['Día'] = pd.Categorical(df['Día'], categories=weekdays, ordered=True)

        df['week'] = pd.to_datetime(df['date']).dt.to_period('W').dt.start_time
        # df['week'] = df['date'].dt.to_period('W').dt.start_time
        weeks = df['week'].unique()
        
        for ind in df["indicador_str"].unique():
            if ind == 'Ln':
                continue  # skip Ln as per your original logic

            df_ind = df[df["indicador_str"] == ind]

            for week_start in weeks:
                df_week = df_ind[df_ind['week'] == week_start]

                if df_week.empty:
                    logger.warning(f"No data for {ind} during week {week_start}")
                    continue

                fig = sns.relplot(
                    data=df_week,
                    x="hour",
                    y=laeq_column,
                    kind="line",
                    hue="Día",
                    estimator=leq,
                    aspect=1.3,
                    palette=C_MAP_WEEKDAY,
                )

                if ind == 'Ld':
                    fig.set(xlim=(6, 19), ylim=(DB_RANGE_BOTTOM, DB_RANGE_TOP))
                    plt.xticks(range(7, 19), [f"{hour:02d}:00" for hour in range(7, 19)])
                    logger.info(f"Plotted Ld - Week {week_start.strftime('%Y-%m-%d')}")
                elif ind == 'Le':
                    fig.set(xlim=(18.7, 22.3), ylim=(DB_RANGE_BOTTOM, DB_RANGE_TOP))
                    plt.xticks([18.7, 19, 20, 21, 22, 22.3], ['', '19:00', '20:00', '21:00', '22:00', ''])
                    logger.info(f"Plotted Le - Week {week_start.strftime('%Y-%m-%d')}")

                plt.yticks(
                    range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP),
                    [str(level) for level in range(DB_RANGE_BOTTOM, DB_RANGE_TOP, BD_RANGE_STEP)]
                )

                for ax in fig.axes.flat:
                    ax.spines['top'].set_visible(True)
                    ax.spines['right'].set_visible(True)

                plt.title(f"Evolución {ind} - Semana {week_start.strftime('%Y-%m-%d')}")
                plt.ylabel('dB(A)')
                plt.xlabel('Hora')



                #creating folder for week
                week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
                os.makedirs(week_folder, exist_ok=True)


                filename_base = f"{plotname}_{ind}_evolution_week_{week_start.strftime('%Y-%m-%d')}"
                plot_path = f"{week_folder}/{filename_base}.png"

                logger.info(f"Saving plot to {plot_path}")
                fig.savefig(plot_path, dpi=150)
                plt.close()


    except Exception as e:
        logger.error(f"Error in plot_period_evolution_week: {e}")



# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# TODO
def plt_spectrogram(df, folder_output_dir, sufix_string, logger, plotname):
    # print(df)
    print(df.columns)
    print(sufix_string)

    if sufix_string == "SONOMETRO":
        logger.info("Sufix string is SONOMETRO")
        exit()

    else:
        frequency_columns = df.columns[5:-2] 
        frequencies = [float(col.replace('Hz', '').replace('k', '000')) for col in frequency_columns]
        times = pd.to_datetime(df['date'])



        # select datatime from 22:30 to 23:30 of just one day
        # df = df[(df['date'] >= '2024-07-09 22:30:00') & (df['date'] <= '2024-07-09 23:30:00')]
        # times = pd.to_datetime(df['date'])



        spectrogram_data = df[frequency_columns].T.values
        spectrogram_data = spectrogram_data.clip(20, 110)
        freq_labels = [f"{freq} Hz" for freq in frequencies]
        
        plt.figure(figsize=(20, 10))
        plt.pcolormesh(times, frequencies, spectrogram_data, shading='auto', cmap='inferno')
        plt.colorbar(label='Magnitude (dB)')

        plt.yticks(frequencies, freq_labels)
        plt.ylabel('Frequency (Hz)')

        plt.xlabel('Time')
        plt.title(f'Spectrogram: {plotname}')
        plt.yscale('log')
        plt.ylim([min(frequencies), max(frequencies)])

        plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=300))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

        plt.xticks(rotation=90)
        plt.tight_layout()
        # remove the grid
        plt.grid(False)

        # Save the plot
        output_file = f'{folder_output_dir}/Spectrogram/{plotname}_spectrogram.png'
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        plt.savefig(output_file, dpi=150)
        plt.close()
        logger.info(f"Spectrogram saved to {output_file}")










########## OCA ALARM ##########
def oca_alarm(df_1h_leq, folder_output_dir: str, logger, plotname: str):
    # remove grey color background
    sns.set_style("whitegrid")
    
    # filter the data based on the thresholds
    filtered_df_1h_leq = df_1h_leq[(df_1h_leq["LA_corrected_leq"] > df_1h_leq["oca"])]

    plt.figure(figsize=(15, 8))
    plt.plot(df_1h_leq["LA_corrected_leq"], label="LAeq")
    plt.plot(filtered_df_1h_leq["LA_corrected_leq"], "ro", label="LAeq Alarm")


    plt.title(f"{plotname} LAeq - OCA | Alarm")
    plt.ylabel("dB(A)")

    # draw horizontal lines for the thresholds for the OCA values
    plt.plot(df_1h_leq.index, df_1h_leq["oca"], "r--", label="OCA", linewidth=2)

    plt.legend()
    plt.xticks(rotation=90)
    plt.grid(True)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))


    plt.xlim(df_1h_leq.index.min(), df_1h_leq.index.max())
    plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))

    plt.tight_layout()

    # save imgage
    plt.savefig(f'{folder_output_dir}/{plotname}_OCA_Alarm.png', dpi=150)
    logger.info(f"Saved plot at {folder_output_dir}/{plotname}_OCA_Alarm.png")



    ########################
    # marking with an 1 when an alarm is detected in the dataframe, otherwise leave it as blank
    df_1h_leq["oca_alarm"] = np.where(df_1h_leq["LA_corrected_leq"] > df_1h_leq["oca"], 1, np.nan)
    return df_1h_leq





def oca_alarm_week(df_1h_leq, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")

        # Make sure date_time is datetime
        df_1h_leq['date_time'] = pd.to_datetime(df_1h_leq['date_time'])
        df_1h_leq = df_1h_leq.sort_values('date_time').copy()
        df_1h_leq.set_index('date_time', inplace=True)

        # Add week column based on start of the ISO week
        df_1h_leq['week'] = df_1h_leq.index.to_period('W').start_time
        weeks = df_1h_leq['week'].unique()

        for week_start in weeks:
            df_week = df_1h_leq[df_1h_leq['week'] == week_start]

            # Filter alarms where LAeq > OCA
            filtered_df_week = df_week[df_week["LA_corrected_leq"] > df_week["oca"]]

            plt.figure(figsize=(15, 8))
            plt.plot(df_week.index, df_week["LA_corrected_leq"], label="LAeq")
            plt.plot(filtered_df_week.index, filtered_df_week["LA_corrected_leq"], "ro", label="LAeq Alarm")
            plt.plot(df_week.index, df_week["oca"], "r--", label="OCA", linewidth=2)

            plt.title(f"{plotname} LAeq - OCA | Alarms | Week of {week_start.strftime('%Y-%m-%d')}")
            plt.ylabel("dB(A)")
            plt.xticks(rotation=90)
            plt.grid(True)

            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

            plt.xlim(df_week.index.min(), df_week.index.max())
            plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
            plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))

            plt.tight_layout()


            #week folder
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            # Save the plot
            output_path = os.path.join(week_folder, f"{plotname}_OCA_Alarm.png")
            plt.savefig(output_path, dpi=150)
            plt.close()
            logger.info(f"Saved OCA weekly alarm plot: {output_path}")

    except Exception as e:
        logger.error(f"Error in oca_alarm_weekly: {e}")





########## LMAX ALARM ##########
def lmax_alarm(df_1h_leq: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold: int):
    sns.set_style("whitegrid")
    filter_df = df_1h_leq[df_1h_leq['LAmax_corrected_max'] > threshold]

    plt.figure(figsize=(15, 8))
    plt.plot(df_1h_leq['LAmax_corrected_max'], label='LAmax')
    plt.plot(filter_df['LAmax_corrected_max'], 'ro', label='LAeqmax Alarm')
    
    plt.legend()
    plt.grid(True)
    
    plt.title(f"{plotname} LAmax | Alarm")
    plt.ylabel('dB(A)')

    plt.plot(df_1h_leq.index, [threshold] * len(df_1h_leq), 'r--', label='Threshold', linewidth=2)
    plt.xlim(df_1h_leq.index.min(), df_1h_leq.index.max())
    
    plt.xticks(rotation=90)
    plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
    
    plt.tight_layout()

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
    
    plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
    
    # save image
    plt.savefig(f'{folder_output_dir}/{plotname}_LAmax_Alarm.png', dpi=150)
    logger.info(f"Saved plot at {folder_output_dir}/{plotname}_LAmax_Alarm.png")


    #########################
    # marking with an 1 when an alarm is detected in the dataframe, otherwise leave it as blank
    df_1h_leq['LAmax_alarm'] = np.where(df_1h_leq['LAmax_corrected_max'] > threshold, 1, np.nan)
    return df_1h_leq




def lmax_alarm_week(df_1h_leq: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold: int):
    try:
        sns.set_style("whitegrid")

        # Ensure datetime format and set as index
        df_1h_leq['date_time'] = pd.to_datetime(df_1h_leq['date_time'])
        df_1h_leq = df_1h_leq.sort_values('date_time').copy()
        df_1h_leq.set_index('date_time', inplace=True)

        # Add 'week' column
        df_1h_leq['week'] = df_1h_leq.index.to_period('W').start_time
        weeks = df_1h_leq['week'].unique()

        for week_start in weeks:
            df_week = df_1h_leq[df_1h_leq['week'] == week_start]
            filter_df = df_week[df_week['LAmax_corrected_max'] > threshold]

            plt.figure(figsize=(15, 8))
            plt.plot(df_week.index, df_week['LAmax_corrected_max'], label='LAmax')
            plt.plot(filter_df.index, filter_df['LAmax_corrected_max'], 'ro', label='LAmax Alarm')

            # Threshold line
            plt.plot(df_week.index, [threshold] * len(df_week), 'r--', label='Threshold', linewidth=2)

            plt.title(f"{plotname} LAmax | Alarm | Week of {week_start.strftime('%Y-%m-%d')}")
            plt.ylabel('dB(A)')
            plt.xticks(rotation=90)
            plt.grid(True)

            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

            plt.xlim(df_week.index.min(), df_week.index.max())
            plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
            plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1))

            plt.tight_layout()

            # Save image
            #creating folder for week
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)


            output_path = f'{week_folder}/{plotname}_LAmax_Alarm_week_{week_start.strftime("%Y-%m-%d")}.png'
            plt.savefig(output_path, dpi=150)
            plt.close()
            logger.info(f"Saved LAmax weekly alarm plot: {output_path}")

    except Exception as e:
        logger.error(f"Error in lmax_alarm_weekly: {e}")




########## LC_LA ALARM ##########
def LC_LA_alarm(df_1h_leq: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold_norma: int, threshold_dB: int):
    sns.set_style("whitegrid")
    df_1h_leq['LC_LA_threshold'] = df_1h_leq.groupby("indicador_str")["LCeq-LAeq_corrected_leq"].transform(leq).round(2)

    # filter [2]: threshold_dB upper the average threshold (Ld, Le, Ln)
    filter1 = (df_1h_leq["LCeq-LAeq_corrected_leq"] > df_1h_leq["LC_LA_threshold"] + threshold_dB)
    # filter [1]: LC-LA > 10 dB which is the law
    filter2 = df_1h_leq["LCeq-LAeq_corrected_leq"] > threshold_norma
    # combine the filters
    combined_filter = filter1 | filter2
    filtered_df_1h_leq = df_1h_leq[combined_filter]



    plt.figure(figsize=(15, 8))
    plt.plot(df_1h_leq.index, df_1h_leq["LCeq-LAeq_corrected_leq"], label="LC-LA")
    plt.plot(filtered_df_1h_leq.index, filtered_df_1h_leq["LCeq-LAeq_corrected_leq"], "ro", label="Alarm")

    # horizontal lines for the threshold values
    plt.plot(df_1h_leq.index, df_1h_leq["LC_LA_threshold"], "r--", label="Threshold", linewidth=2)
    # plot horizontal line for the threshold + constant
    plt.plot(df_1h_leq.index, df_1h_leq["LC_LA_threshold"] + threshold_dB, "y--", label=f"Threshold + {threshold_dB}", linewidth=2)
    # DRAW HORITZONTAL LINES FOR THE 10 dB THRESHOLD
    plt.plot(df_1h_leq.index, [threshold_norma] * len(df_1h_leq), "g--", label="10 dB Threshold", linewidth=2)


    plt.title(f"{plotname} LCeq - LAeq | Alarm")
    plt.ylabel("dB(A)")
    plt.xticks(rotation=90)
    plt.grid(True)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

    plt.xlim(df_1h_leq.index.min(), df_1h_leq.index.max())
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    plt.tight_layout()

    # save the plot
    plt.savefig(f"{folder_output_dir}/{plotname}_LC_LA_Alarm.png", dpi=150)
    logger.info(f"Saved plot at {folder_output_dir}/{plotname}_LC_LA_Alarm.png")



    #########################
    # marking with an 1 when an alarm is detected in the dataframe, otherwise leave it as blank
    df_1h_leq["LC_LA_alarm"] = np.where(combined_filter, 1, np.nan)

    #removing the LC_LA_threshold column
    df_1h_leq.drop(columns=["LC_LA_threshold"], inplace=True)
    return df_1h_leq



def LC_LA_alarm_week(df_1h_leq: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold_norma: int, threshold_dB: int):
    try:
        sns.set_style("whitegrid")

        # Ensure datetime is in proper format and set index
        df_1h_leq['date_time'] = pd.to_datetime(df_1h_leq['date_time'])
        df_1h_leq = df_1h_leq.sort_values('date_time').copy()
        df_1h_leq.set_index('date_time', inplace=True)

        # Add 'week' column for iteration
        df_1h_leq['week'] = df_1h_leq.index.to_period('W').start_time
        weeks = df_1h_leq['week'].unique()

        for week_start in weeks:
            df_week = df_1h_leq[df_1h_leq['week'] == week_start].copy()

            # Compute dynamic threshold based on 'indicador_str'
            df_week['LC_LA_threshold'] = df_week.groupby("indicador_str")["LCeq-LAeq_corrected_leq"].transform(leq).round(2)

            # Two filters for alarms
            filter1 = df_week["LCeq-LAeq_corrected_leq"] > df_week["LC_LA_threshold"] + threshold_dB
            filter2 = df_week["LCeq-LAeq_corrected_leq"] > threshold_norma
            combined_filter = filter1 | filter2
            filtered_df_week = df_week[combined_filter]

            plt.figure(figsize=(15, 8))
            plt.plot(df_week.index, df_week["LCeq-LAeq_corrected_leq"], label="LC-LA")
            plt.plot(filtered_df_week.index, filtered_df_week["LCeq-LAeq_corrected_leq"], "ro", label="Alarm")

            # Threshold lines
            plt.plot(df_week.index, df_week["LC_LA_threshold"], "r--", label="Threshold", linewidth=2)
            plt.plot(df_week.index, df_week["LC_LA_threshold"] + threshold_dB, "y--", label=f"Threshold + {threshold_dB}", linewidth=2)
            plt.plot(df_week.index, [threshold_norma] * len(df_week), "g--", label="10 dB Threshold", linewidth=2)

            plt.title(f"{plotname} LCeq - LAeq | Alarms | Week of {week_start.strftime('%Y-%m-%d')}")
            plt.ylabel("dB(A)")
            plt.xticks(rotation=90)
            plt.grid(True)

            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

            plt.xlim(df_week.index.min(), df_week.index.max())
            plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
            plt.tight_layout()

            # Save weekly plot
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)


            output_path = f"{week_folder}/{plotname}_LC_LA_Alarm_week_{week_start.strftime('%Y-%m-%d')}.png"
            plt.savefig(output_path, dpi=150)
            plt.close()
            logger.info(f"Saved LC-LA weekly alarm plot: {output_path}")

    except Exception as e:
        logger.error(f"Error in LC_LA_alarm_weekly: {e}")





########## L90 ALARM ##########
def l90_alarm(df_1h_leq: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold_dB: int):
    sns.set_style("whitegrid")

    l90_column = df_1h_leq["90percentile"].dropna()

    # average of the week and jump when it exceeds a specific value (+5?)
    # [1] average of the week (leq function)
    avg_week = leq(l90_column).round(2)
    # print(f"Leq of the 90th percentile: {avg_week}")

    # [2] alarm when the difference is greater than 5 dB
    # filter df
    filter_df = l90_column > avg_week + threshold_dB
    # print(filter_df)


    plt.figure(figsize=(15, 8))
    plt.plot(df_1h_leq.index, l90_column, label="90th Percentile")
    plt.plot(df_1h_leq[filter_df].index, df_1h_leq[filter_df]["90percentile"], "ro", label="Alarm")
    
    # horizontal line for the average of the week
    plt.axhline(avg_week, color="r", linestyle="--", label="avg", linewidth=2)
    plt.axhline(avg_week + threshold_dB, color="g", linestyle="--", label=f"avg + {threshold_dB}", linewidth=2)

    plt.title("90th Percentile | Alarm")
    plt.ylabel("dB(A)")
    plt.xticks(rotation=90)
    plt.grid(True)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

    plt.xlim(df_1h_leq.index.min(), df_1h_leq.index.max())
    plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    plt.tight_layout()


    # save the plot
    plt.savefig(f'{folder_output_dir}/{plotname}_L90_Alarm.png', dpi=150)
    logger.info(f"Saved plot at {folder_output_dir}/{plotname}_L90_Alarm.png")



def l90_alarm_week(df_1h_leq: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold_dB: int):
    try:
        sns.set_style("whitegrid")

        # Ensure datetime is correct and set index
        df_1h_leq['date_time'] = pd.to_datetime(df_1h_leq['date_time'])
        df_1h_leq = df_1h_leq.sort_values('date_time').copy()
        df_1h_leq.set_index('date_time', inplace=True)

        # Add week column
        df_1h_leq['week'] = df_1h_leq.index.to_period('W').start_time
        weeks = df_1h_leq['week'].unique()

        for week_start in weeks:
            df_week = df_1h_leq[df_1h_leq['week'] == week_start].copy()

            if df_week['90percentile'].dropna().empty:
                logger.warning(f"No valid L90 data for week {week_start.strftime('%Y-%m-%d')}")
                continue

            l90_column = df_week['90percentile'].dropna()
            avg_week = leq(l90_column).round(2)
            filter_df = l90_column > avg_week + threshold_dB

            plt.figure(figsize=(15, 8))
            plt.plot(df_week.index, l90_column, label="90th Percentile")
            plt.plot(df_week[filter_df].index, df_week[filter_df]["90percentile"], "ro", label="Alarm")

            plt.axhline(avg_week, color="r", linestyle="--", label="avg", linewidth=2)
            plt.axhline(avg_week + threshold_dB, color="g", linestyle="--", label=f"avg + {threshold_dB}", linewidth=2)

            plt.title(f"90th Percentile | Alarm | Week of {week_start.strftime('%Y-%m-%d')}")
            plt.ylabel("dB(A)")
            plt.xticks(rotation=90)
            plt.grid(True)

            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

            plt.xlim(df_week.index.min(), df_week.index.max())
            plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
            plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
            plt.tight_layout()

            # Save weekly plot
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)
            output_path = f'{week_folder}/{plotname}_L90_Alarm_week_{week_start.strftime("%Y-%m-%d")}.png'
            plt.savefig(output_path, dpi=150)
            plt.close()
            logger.info(f"Saved L90 weekly alarm plot: {output_path}")

    except Exception as e:
        logger.error(f"Error in l90_alarm_weekly: {e}")





########## L90 ALARM DYNAMIC ##########
def l90_alarm_dynamic(df_1h: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold_dB: int):
    sns.set_style("whitegrid")


    #######################
    df_1h = df_1h.copy()
    df_1h.rename(columns={"90percentile": "L90"}, inplace=True)

    df_1h["L90_rolling_median"] = df_1h["L90"].rolling(window=3, min_periods=1).median()
    df_1h["alarm"] = df_1h["L90"] > df_1h["L90_rolling_median"] + threshold_dB



    #######################
    plt.figure(figsize=(15, 8))
    plt.plot(df_1h.index, df_1h["L90"], label="L90")
    plt.plot(df_1h.index, df_1h["L90_rolling_median"] + threshold_dB, "--", color="green", label=f"+{threshold_dB} dB")
    # plt.plot(df_1h.index, df_1h["L90_rolling_median"], "--", color="orange", label="Rolling Median")
    plt.plot(df_1h[df_1h["alarm"]].index, df_1h[df_1h["alarm"]]["L90"], "ro", label="Alarma")

    plt.title("Alarma L90 Dinamica")
    plt.ylabel("dB(A)")
    plt.xticks(rotation=90)
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

    plt.xlim(df_1h.index.min(), df_1h.index.max())
    plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    plt.tight_layout()



    #######################
    filename = f'{folder_output_dir}/{plotname}_L90_Dyn_Alarm.png'
    plt.savefig(filename, dpi=150)
    logger.info(f"Saved plot at {filename}")


    ########################
    # marking with an 1 when an alarm is detected in the dataframe, otherwise leave it as blank
    df_1h["l90_alarm"] = np.where(df_1h["alarm"], 1, np.nan)
    # remove columns L90_rolling_median and alarm
    df_1h.drop(columns=["L90_rolling_median", "alarm"], inplace=True)
    
    return df_1h



def l90_alarm_dynamic_week(df_1h: pd.DataFrame, folder_output_dir: str, logger, plotname: str, threshold_dB: int):
    try:
        sns.set_style("whitegrid")

        # Ensure datetime and sort
        df_1h['date_time'] = pd.to_datetime(df_1h['date_time'])
        df_1h = df_1h.sort_values('date_time').copy()
        df_1h.set_index('date_time', inplace=True)

        # Add week column
        df_1h['week'] = df_1h.index.to_period('W').start_time
        weeks = df_1h['week'].unique()

        for week_start in weeks:
            df_week = df_1h[df_1h['week'] == week_start].copy()

            if '90percentile' not in df_week.columns:
                logger.warning(f"No L90 data available for week {week_start.strftime('%Y-%m-%d')}")
                continue

            df_week.rename(columns={"90percentile": "L90"}, inplace=True)
            df_week["L90_rolling_median"] = df_week["L90"].rolling(window=3, min_periods=1).median()
            df_week["alarm"] = df_week["L90"] > df_week["L90_rolling_median"] + threshold_dB

            plt.figure(figsize=(15, 8))
            plt.plot(df_week.index, df_week["L90"], label="L90")
            plt.plot(df_week.index, df_week["L90_rolling_median"] + threshold_dB, "--", color="green", label=f"+{threshold_dB} dB")
            plt.plot(df_week[df_week["alarm"]].index, df_week[df_week["alarm"]]["L90"], "ro", label="Alarma")

            plt.title(f"L90 Dinámica | Alarma | Semana {week_start.strftime('%Y-%m-%d')}")
            plt.ylabel("dB(A)")
            plt.xticks(rotation=90)
            plt.grid(True)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

            plt.xlim(df_week.index.min(), df_week.index.max())
            plt.ylim([DB_LOWER_LIMIT, DB_UPPER_LIMIT])
            plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
            plt.tight_layout()

            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            filename = f'{week_folder}/{plotname}_L90_Dyn_Alarm_week_{week_start.strftime("%Y-%m-%d")}.png'
            plt.savefig(filename, dpi=150)
            plt.close()
            logger.info(f"Saved dynamic L90 alarm plot: {filename}")

    except Exception as e:
        logger.error(f"Error in l90_alarm_dynamic_weekly: {e}")




# FREQUENCY COMPOSITION
def frequency_composition(df_oct: pd.DataFrame, df_alarms_1h: pd.DataFrame, folder_output_dir_1h_folder: str, logger, plotname: str, threshold_comp: int):
    sns.set_style("whitegrid")
    df_oct_cp = df_oct.copy()

    # creating the columns for the frequency bands
    df_oct_cp["low_freq"] = df_oct_cp[LOW_FREQ_BANDS].apply(sum_dBs, axis=1)
    df_oct_cp["medium_freq"] = df_oct_cp[MEDIUM_FREQ_BANDS].apply(sum_dBs, axis=1)
    df_oct_cp["high_freq"] = df_oct_cp[HIGH_FREQ_BANDS].apply(sum_dBs, axis=1)

    #     low_freq  medium_freq  high_freq
    # datetime
    #  for hour
    #set index
    
    df_oct_cp['Timestamp'] = pd.to_datetime(
        df_oct_cp['Timestamp'],
        errors='coerce',
        utc=True
    )

    df_oct_cp = (
        df_oct_cp.dropna(subset=['Timestamp'])
        .set_index('Timestamp')
        .sort_index()
    )

    df_oct_cp[["low_freq", "medium_freq", "high_freq"]]
    df_oct_1hour = df_oct_cp.resample("h").agg(
        {"low_freq": leq, "medium_freq": leq, "high_freq": leq}
    )

    # apply correction
    df_oct_1hour["low_freq"] = df_oct_1hour["low_freq"] + LOW_FREQ_CORRECTION
    df_oct_1hour["medium_freq"] = df_oct_1hour["medium_freq"] + MEDIUM_FREQ_CORRECTION
    df_oct_1hour["high_freq"] = df_oct_1hour["high_freq"] + HIGH_FREQ_CORRECTION
    
    # remove nan values
    df_oct_1hour = df_oct_1hour.dropna()
    
    # copy for the low and high frequency analñysis
    df_oct_1hour_lineal_comparsion = df_oct_1hour.copy()
    df_oct_1hour = df_oct_1hour.dropna().reset_index()


    df_oct_1hour["predominant_freq"] = "None"
    for index, row in df_oct_1hour.iterrows():
        if row["low_freq"] > row["medium_freq"] or row["low_freq"] > row["high_freq"]:
            df_oct_1hour.at[index, "predominant_freq"] = "Low frequency"
        elif row["medium_freq"] > row["low_freq"] or row["medium_freq"] > row["high_freq"]:
            df_oct_1hour.at[index, "predominant_freq"] = "Medium frequency"
        elif row["high_freq"] > row["low_freq"] or row["high_freq"] > row["medium_freq"]:
            df_oct_1hour.at[index, "predominant_freq"] = "High frequency"
        else:
            df_oct_1hour.at[index, "predominant_freq"] = "No predominant frequency"

    df_oct_1hour = df_oct_1hour.dropna()
    # print(df_oct_1hour)
    # print(df_alarms_1h)


    ################################
    ################################
    # join the df_oct_1hour['predominant_freq] column to the df_alarms_1h dataframe
    if 'date_time' in df_alarms_1h.columns: df_alarms_1h["date_time"] = pd.to_datetime(df_alarms_1h["date_time"])
    else: df_alarms_1h["Timestamp"] = pd.to_datetime(df_alarms_1h["Timestamp"])

    if 'datetime' in df_oct_1hour.columns: df_oct_1hour["datetime"] = pd.to_datetime(df_oct_1hour["datetime"])
    else: df_oct_1hour["Timestamp"] = pd.to_datetime(df_oct_1hour["Timestamp"])
    
    if 'datetime' in df_oct_1hour.columns:
        df_alarms_1h = df_alarms_1h.merge(
            df_oct_1hour[["datetime", "predominant_freq"]],
            left_on="date_time",
            right_on="datetime",
            how="left"
        )
        #df_alarms_1h.drop(columns=["datetime"], inplace=True)
    else:
        df_alarms_1h = df_alarms_1h.merge(
            df_oct_1hour[["Timestamp", "predominant_freq"]],
            left_on="date_time",
            right_on="Timestamp",
            how="left"
        )
        #df_alarms_1h.drop(columns=["date_time"], inplace=True)

    
    #rename 
    df_alarms_1h.rename(columns={"predominant_freq": "predominant_freq_alarm"}, inplace=True)
    # print(df_alarms_1h)
    ################################
    ################################


    # plt.figure(figsize=(20, 6))
    # color_map = {
    #     "Low frequency": "blue",
    #     "Medium frequency": "green",
    #     "High frequency": "red",
    # }
    # colors = df_oct_1hour["predominant_freq"].map(color_map)

    # # set a X for the points value
    # plt.scatter(
    #     df_oct_1hour.index,
    #     df_oct_1hour["predominant_freq"],
    #     c=colors,
    #     marker="X",
    #     linewidths=0.1,
    #     s=100,
    #     label="Predominant Frequency",
    # )

    # plt.title(f"{plotname} Predominant Frequency")
    # plt.xlim(df_oct_1hour.index.min(), df_oct_1hour.index.max())
    # plt.xticks(rotation=90)
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    # plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

    # # legend
    # legend_labels = [
    #     plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=10)
    #     for color in color_map.values()
    # ]
    # plt.legend(
    #     legend_labels,
    #     color_map.keys(),
    #     title="Frequency Bands",
    #     loc="upper left",
    #     bbox_to_anchor=(1, 1),
    # )
    # plt.tight_layout()

    # # save the plot
    # plt.savefig(f"{folder_output_dir_1h_folder}/{plotname}_Predominant_Frequency.png", dpi=150)
    # logger.info(f"Saved plot at {folder_output_dir_1h_folder}/{plotname}_Predominant_Frequency.png")



    ################################
    ################################
    # LINEAL COMPARISON
    logger.info(f"[6] Plotting frequency composition comparation for folder {plotname}")
    low_freq_filter = df_oct_1hour_lineal_comparsion["low_freq"] > df_oct_1hour_lineal_comparsion["low_freq"].shift(1) + threshold_comp
    high_freq_filter = df_oct_1hour_lineal_comparsion["high_freq"] > df_oct_1hour_lineal_comparsion["high_freq"].shift(1) + threshold_comp

    df_oct_1hour_lineal_comparsion["low_high_freq_alarm"] = np.where(low_freq_filter | high_freq_filter, 1, np.nan)
    # print(df_oct_1hour_lineal_comparsion)


    ################################
    ################################
    # join the df_oct_1hour['predominant_freq] column to the df_alarms_1h dataframe
    df_oct_1hour_lineal_comparsion = df_oct_1hour_lineal_comparsion.reset_index()

    df_alarms_1h["date_time"] = pd.to_datetime(df_alarms_1h["date_time"])
    df_alarms_1h = df_alarms_1h.merge(
        df_oct_1hour_lineal_comparsion[["Timestamp", "low_high_freq_alarm"]],
        left_on="date_time",
        right_on="Timestamp",
        how="left"
    )
    df_alarms_1h.drop(columns=["date_time"], inplace=True)


    ################################
    ################################


    # # plot the low frequency values
    # plt.figure(figsize=(20, 6))
    # plt.plot(df_oct_1hour_lineal_comparsion["high_freq"], label="hIGH Freq")
    # plt.plot(df_oct_1hour_lineal_comparsion[high_freq_filter].index, df_oct_1hour_lineal_comparsion[high_freq_filter]["high_freq"], "ro", label="Alarm")

    # plt.plot(df_oct_1hour_lineal_comparsion["low_freq"], label="Low Freq", color="orange")
    # plt.plot(df_oct_1hour_lineal_comparsion[low_freq_filter].index, df_oct_1hour_lineal_comparsion[low_freq_filter]["low_freq"], "go", label="Alarm")

    # plt.title(f"{plotname} Low and High Frequency | Alarm")
    # plt.ylabel("dB")
    # plt.xticks(rotation=90)
    # plt.grid(True)

    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y %H-%M"))
    # plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

    # plt.xlim(df_oct_1hour_lineal_comparsion.index.min(), df_oct_1hour_lineal_comparsion.index.max())
    # plt.ylim([0, DB_UPPER_LIMIT])
    # plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    # plt.tight_layout()

    # # save the plot
    # plt.savefig(f"{folder_output_dir_1h_folder}/{plotname}_Low_High_Frequency_Alarm.png", dpi=150)
    # logger.info(f"Saved plot at {folder_output_dir_1h_folder}/{plotname}_Low_High_Frequency_Alarm.png")


    return df_alarms_1h



# FREQUENCY COMPOSITION
def frequency_composition_week(df_oct: pd.DataFrame, folder_output_dir_1h_folder: str, logger, plotname: str, threshold_comp: int):
    sns.set_style("whitegrid")
    df_oct_cp = df_oct.copy()
    df_oct_cp.index = pd.to_datetime(df_oct_cp.index)

    df_oct_cp["week"] = df_oct_cp.index.to_period("W").start_time

    for week_start, df_week in df_oct_cp.groupby("week"):
        weekly_folder = os.path.join(folder_output_dir_1h_folder, f"week_{week_start.strftime('%Y-%m-%d')}")
        os.makedirs(weekly_folder, exist_ok=True)

        df_week["low_freq"] = df_week[LOW_FREQ_BANDS].apply(sum_dBs, axis=1)
        df_week["medium_freq"] = df_week[MEDIUM_FREQ_BANDS].apply(sum_dBs, axis=1)
        df_week["high_freq"] = df_week[HIGH_FREQ_BANDS].apply(sum_dBs, axis=1)

        df_hourly = df_week.resample("h").agg({
            "low_freq": leq,
            "medium_freq": leq,
            "high_freq": leq
        }).dropna()

        df_hourly["low_freq"] += LOW_FREQ_CORRECTION
        df_hourly["medium_freq"] += MEDIUM_FREQ_CORRECTION
        df_hourly["high_freq"] += HIGH_FREQ_CORRECTION

        df_hourly_lineal = df_hourly.copy()
        df_hourly["predominant_freq"] = df_hourly.apply(
            lambda row: max(("Low frequency", row["low_freq"]),
                            ("Medium frequency", row["medium_freq"]),
                            ("High frequency", row["high_freq"]),
                            key=lambda x: x[1])[0], axis=1)




        ######################### Predominant frequency markers #########################
        plt.figure(figsize=(20, 6))
        colors = df_hourly["predominant_freq"].map({
            "Low frequency": "blue",
            "Medium frequency": "green",
            "High frequency": "red"
        })

        plt.scatter(df_hourly.index, df_hourly["predominant_freq"], c=colors, marker="X", s=100)
        plt.title(f"{plotname} Predominant Frequency | Week of {week_start.strftime('%Y-%m-%d')}")
        plt.xticks(rotation=90)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
        plt.tight_layout()
        plt.savefig(os.path.join(weekly_folder, f"{plotname}_Predominant_Frequency_{week_start.strftime('%Y-%m-%d')}.png"), dpi=150)
        plt.close()



        ##########################Alarm comparison #########################
        low_alarm = df_hourly_lineal["low_freq"] > df_hourly_lineal["low_freq"].shift(1) + threshold_comp
        high_alarm = df_hourly_lineal["high_freq"] > df_hourly_lineal["high_freq"].shift(1) + threshold_comp

        plt.figure(figsize=(20, 6))
        plt.plot(df_hourly_lineal["high_freq"], label="High Freq")
        plt.plot(df_hourly_lineal[high_alarm].index, df_hourly_lineal[high_alarm]["high_freq"], "ro", label="High Alarm")

        plt.plot(df_hourly_lineal["low_freq"], label="Low Freq", color="orange")
        plt.plot(df_hourly_lineal[low_alarm].index, df_hourly_lineal[low_alarm]["low_freq"], "go", label="Low Alarm")

        plt.title(f"{plotname} Low & High Frequency Alarm | Week of {week_start.strftime('%Y-%m-%d')}")
        plt.ylabel("dB")
        plt.xticks(rotation=90)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
        plt.ylim([0, DB_UPPER_LIMIT])
        plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
        plt.tight_layout()
        plt.savefig(os.path.join(weekly_folder, f"{plotname}_Low_High_Frequency_Alarm_{week_start.strftime('%Y-%m-%d')}.png"), dpi=150)
        plt.close()

        logger.info(f"Saved frequency composition plots for week {week_start.strftime('%Y-%m-%d')} in {weekly_folder}")





def tonal_frequency(df_oct: pd.DataFrame, df_alarms_1h: pd.DataFrame, folder_output_dir_1h_folder: str, logger, plotname: str):
    sns.set_style("whitegrid")

    tonal_frequency = []
    tonal_frequency_value = []
    previous_tonal_frequency = []
    previous_tonal_value_frequency = []
    next_tonal_frequency = []
    next_tonal_value_frequency = []
    previous_diff = []
    next_diff = []
    filenames = []
    dates = []
    bands = []
    band_thresholds = []

    detections = []
    
    logger.info("Detecting tonal frequencies. It may take a while (5-10 min)...")
    for _, row in df_oct.iterrows():
        for i in range(len(df_oct.columns)):
            current_column = df_oct.columns[i]
            current_filename = row["Filename"]
            current_date = row["Timestamp"]

            if current_column in COLUMNS_DISCARD:
                continue

            current_column_value = row[current_column]

            # get previous and next columns and values
            previous_column = df_oct.columns[i - 1] if i - 1 >= 0 else None
            previos_column_value = row[previous_column] if previous_column else None
            next_column = df_oct.columns[i + 1] if i + 1 < len(df_oct.columns) else None
            next_column_value = row[next_column] if next_column else None


            # convert values to float
            current_column_value = pd.to_numeric(current_column_value, errors="coerce")
            previos_column_value = pd.to_numeric(previos_column_value, errors="coerce")
            next_column_value = pd.to_numeric(next_column_value, errors="coerce")

            if pd.isna(previos_column_value):
                previos_column_value = next_column_value
            if pd.isna(next_column_value):
                next_column_value = previos_column_value

            # differences
            diff_previous_band = (
                current_column_value - previos_column_value
                if pd.notna(previos_column_value)
                else None
            )
            diff_next_band = (
                current_column_value - next_column_value
                if pd.notna(next_column_value)
                else None
            )
            diff_previous_band = (
                round(diff_previous_band, 2) if diff_previous_band is not None else None
            )
            diff_next_band = (
                round(diff_next_band, 2) if diff_next_band is not None else None
            )

            detected_band = None
            band_threshold = None

            if current_column in LOW_BAND_TONAL_FREQ:
                if (
                    diff_previous_band is not None
                    and diff_next_band is not None
                    and diff_previous_band > LOW_BAND_THRESHOLD
                    and diff_next_band > LOW_BAND_THRESHOLD
                ):
                    detected_band = "LOW"
                    band_threshold = LOW_BAND_THRESHOLD

            elif current_column in MEDIUM_BAND_TONAL_FREQ:
                if (
                    diff_previous_band is not None
                    and diff_next_band is not None
                    and diff_previous_band > MEDIUM_BAND_THRESHOLD
                    and diff_next_band > MEDIUM_BAND_THRESHOLD
                ):
                    detected_band = "MEDIUM"
                    band_threshold = MEDIUM_BAND_THRESHOLD

            elif current_column in HIGH_BAND_TONAL_FREQ:
                if (
                    diff_previous_band is not None
                    and diff_next_band is not None
                    and diff_previous_band > HIGH_BAND_THRESHOLD
                    and diff_next_band > HIGH_BAND_THRESHOLD
                ):
                    detected_band = "HIGH"
                    band_threshold = HIGH_BAND_THRESHOLD


            if detected_band:
                detections.append({
                    "Filename": current_filename,
                    "Timestamp": current_date,
                    "band": detected_band,
                    "band_threshold": band_threshold,
                    "tonal_frequency": current_column,
                    "tonal_frequency_value": current_column_value,
                    "previous_tonal_frequency": previous_column,
                    "previous_tonal_value_frequency": previos_column_value,
                    "next_tonal_frequency": next_column,
                    "next_tonal_value_frequency": next_column_value,
                    "previous_diff": diff_previous_band,
                    "next_diff": diff_next_band,
                })


    df_tonal_freq = pd.DataFrame(detections)

    # plotting  
    df_tonal_freq['Timestamp'] = pd.to_datetime(df_tonal_freq['Timestamp'], errors='coerce')
    print(df_tonal_freq)
    

    # drop row with values -np.inf, -np.inf and np.nan
    # TODO --> TEST THIS
    #df_tonal_freq["date"] = pd.to_datetime(df_tonal_freq["date"])

    # filter out any invalid values
    df_tonal_freq = df_tonal_freq[
        (df_tonal_freq["tonal_frequency_value"] != -np.inf)
        & (df_tonal_freq["tonal_frequency_value"] != np.inf)
        & (~df_tonal_freq["tonal_frequency_value"].isna())
    ]


    # setup desired order
    df_tonal_freq["tonal_frequency"] = pd.Categorical(
        df_tonal_freq["tonal_frequency"], categories=TONAL_FREQ_BANDS_ORDERED, ordered=True
    )
    
    print(df_tonal_freq)





    df_tonal_freq["hour"] = df_tonal_freq["Timestamp"].dt.floor("h")
    band_counts = df_tonal_freq.groupby(["hour", "band"]).size().unstack(fill_value=0)
    def get_predominant_band(row):
        top = row[row == row.max()]
        if len(top) == 1:
            return top.index[0]  #band name
        else:
            return ""  #empty string

    band_counts["predominant_tonal_band"] = band_counts.apply(get_predominant_band, axis=1)
    df_predominant_bands = band_counts[["predominant_tonal_band"]].reset_index()
    print(df_predominant_bands)
    # print(df_alarms_1h)



    ################################
    ################################
    # join the df_oct_1hour['predominant_freq] column to the df_alarms_1h dataframe
    df_predominant_bands["hour"] = pd.to_datetime(df_predominant_bands["hour"])
    df_alarms_1h["Timestamp_x"] = pd.to_datetime(df_alarms_1h["Timestamp_x"])

    df_alarms_1h = df_alarms_1h.merge(
        df_predominant_bands,
        left_on="Timestamp_x",
        right_on="hour",
        how="left"
    )
    df_alarms_1h.drop(columns=["hour_y"], inplace=True)
    #rename
    df_alarms_1h.rename(columns={"predominant_tonal_band": "tonal_band_alarm"}, inplace=True)
    ################################
    ################################
    print(df_alarms_1h)

    

    plt.figure(figsize=(18, 10))
    # plt.figure(figsize=(25, 12))
    plt.scatter(df_tonal_freq["Timestamp"], df_tonal_freq["tonal_frequency"].cat.codes, marker="x", color="orange")
    plt.title(f"{plotname} | Tonal Frequency Alarm Detection")
    plt.xticks(rotation=90)
    plt.yticks(range(len(TONAL_FREQ_BANDS_ORDERED)), TONAL_FREQ_BANDS_ORDERED)  # !!!!!! set y-ticks to ordered frequencies !!!!!! 

    plt.grid(True)

    # # date column format --> 2023-12-11 13:37:24
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))

    # X AND Y LMIT
    plt.xlim(df_tonal_freq["Timestamp"].min(), df_tonal_freq["Timestamp"].max())
    plt.ylim(-1, len(TONAL_FREQ_BANDS_ORDERED)) 

    plt.tight_layout()
    
    # # save the plot
    plt.savefig(f"{folder_output_dir_1h_folder}/{plotname}_tonal_frequency.png", dpi=150)
    logger.info(f"Saved plot at {folder_output_dir_1h_folder}/{plotname}_tonal_frequency.png")


    return df_alarms_1h




##################################################################
##################################################################
##################################################################
def plot_peak_distribution_heatmap(df_peaks: pd.DataFrame,df_alarms_1h: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")
        df_peaks = df_peaks.copy()


        ##############################
        ##############################
        ##############################
        df_peaks["Timestamp"] = pd.to_datetime(df_peaks["Timestamp"], errors="coerce")
        df_peaks["datetime_hour"] = df_peaks["Timestamp"].dt.floor("h")
        df_peak_counts = df_peaks.groupby("datetime_hour").size().reset_index(name="peak_count")
        df_alarms_1h["date_time"] = pd.to_datetime(df_alarms_1h["date_time"]).dt.floor("h")

        #creating the LAeq_peak column in df_alarms_1h. 
        # group the peaks by hour and make the leq fucntion average with the LA_corrected column

        df_la_eq_peak = df_peaks.groupby("datetime_hour")["LA_corrected"].apply(leq).reset_index()
        df_la_eq_peak.rename(columns={"datetime_hour": "date_time", "LA_corrected": "LAeq_peak"}, inplace=True)
        df_alarms_1h = df_alarms_1h.merge(df_la_eq_peak, on="date_time", how="left")
        # exit()


        df_alarms_1h = df_alarms_1h.merge(
            df_peak_counts,
            left_on="date_time",
            right_on="datetime_hour",
            how="left"
        )

        df_alarms_1h.drop(columns=["datetime_hour"], inplace=True)
        ##############################
        ##############################
        ##############################
        print(df_alarms_1h)


        df_peaks['Día'] = df_peaks['day_name'].replace(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        df_peaks['date_day'] = df_peaks['date'].astype(str) + ' ' + df_peaks['Día']

        df_peaks['full_date'] = pd.to_datetime(df_peaks['Timestamp']).dt.strftime('%Y-%m-%d') + \
                                 '\n' + pd.to_datetime(df_peaks['Timestamp']).dt.day_name()
        
    
        pivot_table = df_peaks.pivot_table(
            index=['date_day'],
            columns=['hour'], 
            aggfunc='size',
            )

        pivot_table.replace(0, np.nan, inplace=True)

        plt.figure(figsize=(20, 10))
        sns.heatmap(pivot_table, annot=True, fmt=".0f", cmap=cmap_dict)

        plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
        plt.ylabel('Día', fontsize=BIGGEST_SIZE)
        plt.title(f'{plotname} Heatmap de Ocurrencias de Picos por Hora y Día', fontsize=BIGGEST_SIZE)

        plt.yticks(np.arange(len(pivot_table.index)) + 0.5, pivot_table.index, rotation=0, fontsize=BIGGEST_SIZE)
        plt.xticks(np.arange(0.5, len(pivot_table.columns), 1), range(24), fontsize=BIGGEST_SIZE) 
        
        plt.tight_layout()
        plt.grid(False)

        #save the plot
        plt.savefig(f"{folder_output_dir}/{plotname}_peak_distribution_heatmap.png", dpi=150)
        logger.info(f"Saved plot at {folder_output_dir}/{plotname}_peak_distribution_heatmap.png")
        


        ########################################
        ########################################
        # plot the same informaiton but in 4h intervals
        ########################################
        ########################################
        # create 4 hour blocks
        df_peaks['4HourBlock'] = (df_peaks['Timestamp'].dt.hour // 4) * 4

        pivot_table_4h = df_peaks.pivot_table(
            index='date_day',        
            columns='4HourBlock',   
            aggfunc='size'
        )
        
        pivot_table_4h.replace(0, np.nan, inplace=True)

        plt.figure(figsize=(20, 10))
        sns.heatmap(pivot_table_4h, annot=True, fmt=".0f", cmap=cmap_dict)

        plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
        plt.ylabel('Día', fontsize=BIGGEST_SIZE)
        plt.title(f'{plotname} Heatmap de Ocurrencias de Picos por Hora y Día (4h)', fontsize=BIGGEST_SIZE)
        plt.yticks(np.arange(len(pivot_table_4h.index)) + 0.5, pivot_table_4h.index, rotation=0, fontsize=BIGGEST_SIZE)
        plt.xticks(np.arange(0.5, len(pivot_table_4h.columns), 1), range(0, 24, 4))

        plt.tight_layout()
        plt.grid(False)

        #save the plot
        plt.savefig(f"{folder_output_dir}/{plotname}_peak_distribution_heatmap_4h.png", dpi=150)
        logger.info(f"Saved plot at {folder_output_dir}/{plotname}_peak_distribution_heatmap_4h.png")


        return df_alarms_1h

    except Exception as e:
        logger.error(f"Error in plot_peak_distribution_heatmap: {e}")




def plot_peak_distribution_heatmap_week(df_peaks: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")
        df_peaks = df_peaks.copy()

        df_peaks['Día'] = df_peaks['day_name'].replace(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        df_peaks['date_day'] = df_peaks['date'].astype(str) + ' ' + df_peaks['Día']

        df_peaks['full_date'] = pd.to_datetime(df_peaks['Timestamp']).dt.strftime('%Y-%m-%d') + \
                                 '\n' + pd.to_datetime(df_peaks['Timestamp']).dt.day_name()
        

        # make the week column
        # df['week'] = df['date'].dt.to_period('W').dt.start_time
        df_peaks['week'] = pd.to_datetime(df_peaks['date']).dt.to_period('W').dt.start_time
        weeks = df_peaks['week'].unique()

        for week_start in weeks:
            df_week = df_peaks[df_peaks['week'] == week_start].copy()
            if df_week.empty:
                continue
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            ########################################
            ########################################
            # hourly heatmap
            ########################################
            ########################################
            pivot_table = df_week.pivot_table(
                index='date_day',
                columns='hour',
                aggfunc='size'
            ).replace(0, np.nan)

            plt.figure(figsize=(20, 10))
            sns.heatmap(pivot_table, annot=True, fmt=".0f", cmap=cmap_dict)

            plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
            plt.ylabel('Día', fontsize=BIGGEST_SIZE)
            plt.title(f'{plotname} | Picos por Hora y Día | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)

            plt.yticks(np.arange(len(pivot_table.index)) + 0.5, pivot_table.index, rotation=0, fontsize=BIGGEST_SIZE)
            plt.xticks(np.arange(0.5, len(pivot_table.columns), 1), range(24), fontsize=BIGGEST_SIZE)

            plt.tight_layout()
            plt.grid(False)

            filename_hour = os.path.join(week_folder, f"{plotname}_heatmap_hour.png")
            plt.savefig(filename_hour, dpi=150)
            plt.close()
            logger.info(f"Saved hourly heatmap: {filename_hour}")
            


            ########################################
            ########################################
            # plot the same informaiton but in 4h intervals
            ########################################
            ########################################
            # create 4 hour blocks
            df_week['4HourBlock'] = (df_week['Timestamp'].dt.hour // 4) * 4

            pivot_table_4h = df_week.pivot_table(
                index='date_day',
                columns='4HourBlock',
                aggfunc='size'
            ).replace(0, np.nan)

            plt.figure(figsize=(20, 10))
            sns.heatmap(pivot_table_4h, annot=True, fmt=".0f", cmap=cmap_dict)

            plt.xlabel('Hora', fontsize=BIGGEST_SIZE)
            plt.ylabel('Día', fontsize=BIGGEST_SIZE)
            plt.title(f'{plotname} | Picos por Bloque de 4h | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)

            plt.yticks(np.arange(len(pivot_table_4h.index)) + 0.5, pivot_table_4h.index, rotation=0, fontsize=BIGGEST_SIZE)
            plt.xticks(np.arange(0.5, len(pivot_table_4h.columns), 1), range(0, 24, 4), fontsize=BIGGEST_SIZE)

            plt.tight_layout()
            plt.grid(False)

            filename_4h = os.path.join(week_folder, f"{plotname}_heatmap_4h.png")
            plt.savefig(filename_4h, dpi=150)
            plt.close()
            logger.info(f"Saved 4h block heatmap: {filename_4h}")

    except Exception as e:
        logger.error(f"Error in plot_peak_distribution_heatmap: {e}")




##################################################################
def plot_peak_distribution(df_merged: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")

        df_merged = df_merged.copy()
        df_merged.sort_values('Timestamp', inplace=True)

        plt.figure(figsize=(25, 9))
        plt.plot(
            df_merged['Timestamp'], 
            df_merged['LA_corrected'], 
            marker='o', 
            linestyle='-', 
            color='red'
        )

        
        plt.xlabel('Tiempo', fontsize=BIGGEST_SIZE)
        plt.ylabel('LAeq', fontsize=BIGGEST_SIZE)
        plt.title(f'{plotname} Valores LAeq a lo largo del tiempo', fontsize=BIGGEST_SIZE)

        plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)
        plt.xlim(df_merged['Timestamp'].iloc[0], df_merged['Timestamp'].iloc[-1])
        
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        plt.tight_layout()
        plt.grid(True)


        # #save the plot
        plt.savefig(f"{folder_output_dir}/{plotname}_peak_distribution.png", dpi=150)
        logger.info(f"Saved plot at {folder_output_dir}/{plotname}_peak_distribution.png")



        ########################################
        ########################################
        # plot the same informaiton but with shadow area for night time
        ########################################
        ########################################
        min_date = df_merged['Timestamp'].dt.date.min()
        max_date = df_merged['Timestamp'].dt.date.max()

        plt.figure(figsize=(25, 9))
        plt.plot(df_merged['Timestamp'], df_merged['LA_corrected'], marker='o', linestyle='-', color='red')
        
        
        # highlighting night periods
        for single_date in pd.date_range(min_date, max_date):
            start_night = pd.Timestamp.combine(single_date, pd.Timestamp('20:00:00').time())
            end_night = pd.Timestamp.combine(single_date + pd.Timedelta(days=1), pd.Timestamp('07:00:00').time())
            plt.fill_betweenx(y=[df_merged['LA_corrected'].min(), df_merged['LA_corrected'].max()], 
                            x1=start_night, x2=end_night, color='grey', alpha=0.3)


        plt.title(f'{plotname} Valores LAeq a lo largo del tiempo con Distribución Nocturna', fontsize=BIGGEST_SIZE)
        plt.xlabel('Tiempo', fontsize=BIGGEST_SIZE)
        plt.ylabel('LAeq (dB)', fontsize=BIGGEST_SIZE)

        plt.grid(True)
        plt.xticks(rotation=90)

        plt.xlim(df_merged['Timestamp'].iloc[0], df_merged['Timestamp'].iloc[-1])
        plt.ylim(df_merged['LA_corrected'].min(), df_merged['LA_corrected'].max())
        
        
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        plt.tight_layout()


        # save the plot
        plt.savefig(f"{folder_output_dir}/{plotname}_peak_distribution_night.png", dpi=150)
        logger.info(f"Saved plot at {folder_output_dir}/{plotname}_peak_distribution_night.png")


    except Exception as e:
        logger.error(f"Error in plot_peak_distribution: {e}")
        raise 




def plot_peak_distribution_week(df_peaks: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")

        df_peaks = df_peaks.copy()
        # df_peaks['week'] = df_peaks['Timestamp'].dt.to_period('W').start_time
        df_peaks['week'] = pd.to_datetime(df_peaks['date']).dt.to_period('W').dt.start_time
        df_peaks.sort_values('Timestamp', inplace=True)

        weeks = df_peaks['week'].unique()

        for week_start in weeks:
            df_week = df_peaks[df_peaks['week'] == week_start].copy()
            if df_week.empty:
                continue

            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            plt.figure(figsize=(25, 9))
            plt.plot(df_week['Timestamp'], df_week['LA_corrected'], marker='o', linestyle='-', color='red')
            plt.xlabel('Tiempo', fontsize=BIGGEST_SIZE)
            plt.ylabel('LAeq', fontsize=BIGGEST_SIZE)
            plt.title(f'{plotname} LAeq | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)

            plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)
            plt.xlim(df_week['Timestamp'].iloc[0], df_week['Timestamp'].iloc[-1])

            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
            plt.tight_layout()
            plt.grid(True)

            basic_plot_path = os.path.join(week_folder, f"{plotname}_peak_distribution.png")
            plt.savefig(basic_plot_path, dpi=150)
            plt.close()
            logger.info(f"Saved plot at {basic_plot_path}")



            ########################################
            ########################################
            # plot the same informaiton but with shadow area for night time
            ########################################
            ########################################
            min_date = df_week['Timestamp'].dt.date.min()
            max_date = df_week['Timestamp'].dt.date.max()

            plt.figure(figsize=(25, 9))
            plt.plot(df_week['Timestamp'], df_week['LA_corrected'], marker='o', linestyle='-', color='red')

            for single_date in pd.date_range(min_date, max_date):
                start_night = pd.Timestamp.combine(single_date, pd.Timestamp('20:00:00').time())
                end_night = pd.Timestamp.combine(single_date + pd.Timedelta(days=1), pd.Timestamp('07:00:00').time())
                plt.fill_betweenx(
                    y=[df_week['LA_corrected'].min(), df_week['LA_corrected'].max()],
                    x1=start_night,
                    x2=end_night,
                    color='grey',
                    alpha=0.3
                )

            plt.title(f'{plotname} LAeq con Nocturnidad | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)
            plt.xlabel('Tiempo', fontsize=BIGGEST_SIZE)
            plt.ylabel('LAeq (dB)', fontsize=BIGGEST_SIZE)
            plt.grid(True)
            plt.xticks(rotation=90)

            plt.xlim(df_week['Timestamp'].iloc[0], df_week['Timestamp'].iloc[-1])
            plt.ylim(df_week['LA_corrected'].min(), df_week['LA_corrected'].max())

            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=4))
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
            plt.tight_layout()

            night_plot_path = os.path.join(week_folder, f"{plotname}_peak_distribution_night.png")
            plt.savefig(night_plot_path, dpi=150)
            plt.close()
            logger.info(f"Saved plot at {night_plot_path}")


    except Exception as e:
        logger.error(f"Error in plot_peak_distribution: {e}")
        raise 



###################################################################
def plot_density_distribution_peaks(df_merged: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    
    try:
    
        sns.set_style("whitegrid")

        df_merged = df_merged.copy()

        hourly_peaks = df_merged.groupby('hour').size()

        plt.figure(figsize=(12, 6))
        
        hourly_peaks.plot(kind='bar')

        plt.xlabel('Hora del Día', fontsize=BIGGEST_SIZE)
        plt.ylabel('Número de Picos', fontsize=BIGGEST_SIZE)
        plt.title('Distribución de Picos por Hora', fontsize=BIGGEST_SIZE)
        # rotate the x-axis labels
        plt.xticks(rotation=0, fontsize=BIGGEST_SIZE)
        
        plt.grid(True)
        plt.tight_layout()

        # save plot
        plt.savefig(f"{folder_output_dir}/{plotname}_peak_distribution_hourly.png", dpi=150)
        logger.info(f"Saved plot at {folder_output_dir}/{plotname}_peak_distribution_hourly.png")



        ########################################
        ########################################
        # plot the same informaiton but with kernel density estimation
        ########################################
        ########################################
        time_of_day = df_merged['Timestamp'].dt.hour + df_merged['Timestamp'].dt.minute/60

        density = gaussian_kde(time_of_day)
        xs = np.linspace(0,24,100)
        density.covariance_factor = lambda : .25
        density._compute_covariance()

        plt.figure(figsize=(12, 6))
        plt.plot(xs, density(xs))
        
        plt.title(f'{plotname} Distribución de Densidad de Picos por Hora', fontsize=BIGGEST_SIZE)
        plt.xlabel('Hora del Día', fontsize=BIGGEST_SIZE)
        plt.ylabel('Densidad', fontsize=BIGGEST_SIZE)

        # plt.xticks(range(25))
        plt.xlim(0, 24)
        plt.grid(True)

        plt.tight_layout()

        # save plot
        plt.savefig(f"{folder_output_dir}/{plotname}_peak_density_distribution_hourly.png", dpi=150)
        logger.info(f"Saved plot at {folder_output_dir}/{plotname}_peak_density_distribution_hourly.png")



    except Exception as e:
        logger.error(f"Error in plot_density_distribution_peaks: {e}")



def plot_density_distribution_peaks_week(df_merged: pd.DataFrame, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")
        df_merged = df_merged.copy()
        df_merged['Timestamp'] = pd.to_datetime(df_merged['Timestamp'])
        # df_merged['week'] = df_merged['Timestamp'].dt.to_period('W').start_time
        df_merged['week'] = pd.to_datetime(df_merged['date']).dt.to_period('W').dt.start_time

        weeks = df_merged['week'].unique()

        for week_start in weeks:
            df_week = df_merged[df_merged['week'] == week_start].copy()
            if df_week.empty:
                continue

            # Create week folder
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            # ------------------ Bar plot ------------------
            hourly_peaks = df_week.groupby('hour').size()

            plt.figure(figsize=(12, 6))
            hourly_peaks.plot(kind='bar')

            plt.xlabel('Hora del Día', fontsize=BIGGEST_SIZE)
            plt.ylabel('Número de Picos', fontsize=BIGGEST_SIZE)
            plt.title(f'{plotname} | Picos por Hora | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)
            plt.xticks(rotation=0, fontsize=BIGGEST_SIZE)
            plt.grid(True)
            plt.tight_layout()

            bar_path = os.path.join(week_folder, f"{plotname}_peak_distribution_hourly.png")
            plt.savefig(bar_path, dpi=150)
            plt.close()
            logger.info(f"Saved hourly peak distribution bar chart: {bar_path}")

            # ------------------ Density plot ------------------
            time_of_day = df_week['Timestamp'].dt.hour + df_week['Timestamp'].dt.minute / 60

            if len(time_of_day) >= 2:  # KDE requires at least 2 data points
                density = gaussian_kde(time_of_day)
                xs = np.linspace(0, 24, 100)
                density.covariance_factor = lambda: 0.25
                density._compute_covariance()

                plt.figure(figsize=(12, 6))
                plt.plot(xs, density(xs))

                plt.title(f'{plotname} | Densidad de Picos por Hora | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)
                plt.xlabel('Hora del Día', fontsize=BIGGEST_SIZE)
                plt.ylabel('Densidad', fontsize=BIGGEST_SIZE)
                plt.xlim(0, 24)
                plt.grid(True)
                plt.tight_layout()

                density_path = os.path.join(week_folder, f"{plotname}_peak_density_distribution_hourly.png")
                plt.savefig(density_path, dpi=150)
                plt.close()
                logger.info(f"Saved KDE density plot: {density_path}")
            else:
                logger.warning(f"Not enough data for KDE in week {week_start.strftime('%Y-%m-%d')}")

    except Exception as e:
        logger.error(f"Error in plot_density_distribution_peaks_weekly: {e}")




def plot_predic_peak_laeq_mean(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        # select just the row which has a 1 value on the "Peak" column
        # df_all_yamnet = df_all_yamnet[df_all_yamnet['Peak'] == 1].copy()
        # print(f"Number of peaks found: {len(df_all_yamnet)}")
        # exit()
        #########################################################
        #### Plotting the data ####
        
        display_name = 'display_name'
        iso_taxonomy = 'iso_taxonomy'
        classes = 'class'

        brown_2 = 'Brown_Level_2'
        brown_3 = 'Brown_Level_3'
        noiseport_1 = 'NoisePort_Level_1'
        noiseport_2 = 'NoisePort_Level_2'

        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = noiseport_1
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = brown_2
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")


        ####################################
        grouped_df = df_all_yamnet.groupby(class_to_plot).agg(
            number=(classes, 'size'),
            LAeq=('LA_corrected', lambda x: leq(x))
        ).reset_index()

        fig = px.treemap(
                grouped_df,
                path=[class_to_plot],  
                values='number',
                color=class_to_plot,#color by category
                color_discrete_map= color_palet,
                hover_data={'LAeq': True, 'number': True},
                custom_data=['LAeq']                  
            )

        # title and hover settings
        fig.update_layout(title=f'{plotname} | Promedio Energético (LAeq) de Picos por Clases |')
        fig.update_traces(
            hovertemplate=(
                '<b>%{label}</b><br>'
                'LAeq: %{customdata[0]:.2f} dB<br>'
                'Count: %{value}'
            ),
            texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB'
        )
            
        # Save plot
        os.makedirs(folder_output_dir, exist_ok=True)
        fig.write_html(f"{folder_output_dir}/{plotname}_LAeq_Peak_class_mean.html")
        grouped_df.to_csv(f"{folder_output_dir}/{plotname}_LAeq_Peak_class_mean.csv", index=False)
        
        logger.info(f"LAeq class Peak mean plot saved to {folder_output_dir}/{plotname}_LAeq_Peak_class_mean.html")
        logger.info(f"LAeq class Peak mean data saved to {folder_output_dir}/{plotname}_LAeq_Peak_class_mean.csv")

    except Exception as e:
        logger.error(f"Error in plot_predic_laeq_15_min: {e}")



def plot_predic_peak_laeq_mean_week(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        df_all_yamnet = df_all_yamnet[df_all_yamnet['Peak'] == 1].copy()
        df_all_yamnet['Timestamp'] = pd.to_datetime(df_all_yamnet['Timestamp'])
        try:
            df_all_yamnet['week'] = df_all_yamnet['Timestamp'].dt.to_period('W').start_time
        except Exception as e:
            df_all_yamnet['week'] = pd.to_datetime(df_all_yamnet['date']).dt.to_period('W').dt.start_time


        class_column = 'class'
        laeq_column = 'LA_corrected'


        ###############
        if 'Siren' in set(taxonomy_map.values()):
            class_to_plot = 'NoisePort_Level_1'
            color_palet = COLOR_PALLET_PORT_L1
            logger.info("Using 'NoisePort_Level_1' class for plotting")
        else:
            class_to_plot = 'Brown_Level_2'
            color_palet = COLOR_PALLET_URBAN
            logger.info("Using 'Brown_Level_2' class for plotting")

        weeks = df_all_yamnet['week'].unique()



        ###############
        ###############
        for week_start in weeks:
            df_week = df_all_yamnet[df_all_yamnet['week'] == week_start].copy()
            if df_week.empty:
                continue

            grouped_df = df_week.groupby(class_to_plot).agg(
                number=(class_column, 'size'),
                LAeq=(laeq_column, lambda x: leq(x))
            ).reset_index()

            if grouped_df.empty:
                logger.warning(f"No peak data to plot for week {week_start.strftime('%Y-%m-%d')}")
                continue

            fig = px.treemap(
                grouped_df,
                path=[class_to_plot],
                values='number',
                color=class_to_plot,
                color_discrete_map=color_palet,
                hover_data={'LAeq': True, 'number': True},
                custom_data=['LAeq']
            )

            fig.update_layout(title=f'{plotname} | Promedio Energético (LAeq) de Picos | Semana {week_start.strftime("%Y-%m-%d")}')
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>LAeq: %{customdata[0]:.2f} dB<br>Count: %{value}',
                texttemplate='%{label}<br><br>LAeq: %{customdata[0]:.2f} dB'
            )



            ############
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            html_path = os.path.join(week_folder, f"{plotname}_LAeq_Peak_class_mean_{week_start.strftime('%Y-%m-%d')}.html")
            fig.write_html(html_path)
            logger.info(f"Saved peak LAeq treemap for week: {html_path}")

    except Exception as e:
        logger.error(f"Error in plot_predic_peak_laeq_mean_weekly: {e}")




def plot_box_plot_prediction(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")
        df_all_yamnet = df_all_yamnet[df_all_yamnet['Peak'] == 1].copy()

        sns.boxplot(data=df_all_yamnet, x='NoisePort_Level_1', y='LA_corrected')

        plt.title(f'{plotname} Predicciones de Picos por Clases')
        plt.xlabel('Clase', fontsize=BIGGEST_SIZE)
        plt.ylabel('LAeq (dB)', fontsize=BIGGEST_SIZE)

        plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)
        plt.yticks(fontsize=BIGGEST_SIZE)
        plt.grid(True)

        plt.ylim([30, 110])
        plt.tight_layout()

        # save the plot
        plt.savefig(f"{folder_output_dir}/{plotname}_peak_box_plot.png", dpi=150)
        logger.info(f"Saved plot at {folder_output_dir}/{plotname}_peak_box_plot.png")

    except Exception as e:
        logger.error(f"Error in plot_box_plot_prediction: {e}")




def plot_box_plot_prediction_week(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        sns.set_style("whitegrid")
        df_all_yamnet = df_all_yamnet[df_all_yamnet['Peak'] == 1].copy()
        df_all_yamnet['Timestamp'] = pd.to_datetime(df_all_yamnet['Timestamp'])
        try:
            df_all_yamnet['week'] = df_all_yamnet['Timestamp'].dt.to_period('W').start_time
        except Exception as e:
            df_all_yamnet['week'] = pd.to_datetime(df_all_yamnet['date']).dt.to_period('W').dt.start_time


        # week
        weeks = df_all_yamnet['week'].unique()

        for week_start in weeks:
            df_week = df_all_yamnet[df_all_yamnet['week'] == week_start].copy()
            if df_week.empty:
                continue

            plt.figure(figsize=(15, 8))
            sns.boxplot(data=df_week, x='NoisePort_Level_1', y='LA_corrected')

            plt.title(f'{plotname} Predicciones de Picos por Clases | Semana {week_start.strftime("%Y-%m-%d")}')
            plt.xlabel('Clase', fontsize=BIGGEST_SIZE)
            plt.ylabel('LAeq (dB)', fontsize=BIGGEST_SIZE)

            plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)
            plt.yticks(fontsize=BIGGEST_SIZE)
            plt.grid(True)

            plt.ylim([30, 110])
            plt.tight_layout()

            # save the plot
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)
            plt.savefig(f"{week_folder}/{plotname}_peak_box_plot_{week_start.strftime('%Y-%m-%d')}.png", dpi=150)
            logger.info(f"Saved plot at {week_folder}/{plotname}_peak_box_plot_{week_start.strftime('%Y-%m-%d')}.png")

    except Exception as e:
        logger.error(f"Error in plot_box_plot_prediction: {e}")



def plot_heat_map_prediction(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        df_all_yamnet = df_all_yamnet[df_all_yamnet['Peak'] == 1].copy()
        df_all_yamnet['Timestamp'] = pd.to_datetime(df_all_yamnet['Timestamp'])
        try:
            df_all_yamnet['week'] = df_all_yamnet['Timestamp'].dt.to_period('W').start_time
        except Exception as e:
            df_all_yamnet['week'] = pd.to_datetime(df_all_yamnet['date']).dt.to_period('W').dt.start_time


        bins = [0, 60, 70, 80, 90, 100, 110]
        labels = ['0-60 dBs', '60-70 dBs', '70-80 dBs', '80-90 dBs', '90-100 dBs', '100-110 dBs']

        df_all_yamnet['LAeq_bins'] = pd.cut(df_all_yamnet['LA_corrected'], bins=bins, labels=labels, include_lowest=True)

        # week
        weeks = df_all_yamnet['week'].unique()

        for week_start in weeks:
            df_week = df_all_yamnet[df_all_yamnet['week'] == week_start].copy()
            if df_week.empty:
                continue

            heatmap_data = df_week.pivot_table(
                index='NoisePort_Level_1',
                columns='LAeq_bins',
                values='LA_corrected',
                aggfunc='count'
            ).fillna(0)

            heatmap_data = heatmap_data.T
            reversed_bins = labels[::-1]
            heatmap_data = heatmap_data.reindex(index=reversed_bins)
            plt.figure(figsize=(15, 8))
            sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap='Blues')
            plt.title(f'{plotname} | Heatmap de Clases y LAeq | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)
            plt.xlabel('', rotation=0)
            plt.ylabel('', rotation=0)
            plt.yticks(rotation=0, fontsize=BIGGEST_SIZE)
            plt.xticks(rotation=90, fontsize=BIGGEST_SIZE)
            plt.grid(False)
            plt.tight_layout()

            # save the plot
            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)
            plt.savefig(f"{week_folder}/{plotname}_peak_heatmap_{week_start.strftime('%Y-%m-%d')}.png", dpi=150)
            logger.info(f"Saved plot at {week_folder}/{plotname}_peak_heatmap_{week_start.strftime('%Y-%m-%d')}.png")


    except Exception as e:
        logger.error(f"Error in plot_heat_map_prediction: {e}")
        



def plot_heat_map_prediction_week(df_all_yamnet: pd.DataFrame, taxonomy_map: dict, folder_output_dir: str, logger, plotname: str):
    try:
        df_all_yamnet = df_all_yamnet[df_all_yamnet['Peak'] == 1].copy()
        df_all_yamnet['Timestamp'] = pd.to_datetime(df_all_yamnet['Timestamp'])

        try:
            df_all_yamnet['week'] = df_all_yamnet['Timestamp'].dt.to_period('W').start_time
        except Exception as e:
            df_all_yamnet['week'] = pd.to_datetime(df_all_yamnet['date']).dt.to_period('W').dt.start_time

        bins = [0, 60, 70, 80, 90, 100, 110]
        labels = ['0-60 dBs', '60-70 dBs', '70-80 dBs', '80-90 dBs', '90-100 dBs', '100-110 dBs']
        reversed_labels = labels[::-1]

        for week_start in df_all_yamnet['week'].unique():
            df_week = df_all_yamnet[df_all_yamnet['week'] == week_start].copy()
            if df_week.empty:
                continue

            df_week['LAeq_bins'] = pd.cut(df_week['LA_corrected'], bins=bins, labels=labels, include_lowest=True)

            heatmap_data = df_week.pivot_table(
                index='NoisePort_Level_1',
                columns='LAeq_bins',
                values='LA_corrected',
                aggfunc='count'
            ).fillna(0).T

            heatmap_data = heatmap_data.reindex(index=reversed_labels)

            plt.figure(figsize=(15, 8))
            sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap='Blues')

            plt.title(f'{plotname} | Heatmap Clases vs LAeq | Semana {week_start.strftime("%Y-%m-%d")}', fontsize=BIGGEST_SIZE)
            plt.xlabel('', rotation=0)
            plt.ylabel('', rotation=0)
            plt.yticks(rotation=0)
            plt.grid(False)
            plt.tight_layout()

            week_folder = os.path.join(folder_output_dir, f"week_{week_start.strftime('%Y-%m-%d')}")
            os.makedirs(week_folder, exist_ok=True)

            file_path = os.path.join(week_folder, f"{plotname}_peak_heatmap_{week_start.strftime('%Y-%m-%d')}.png")
            plt.savefig(file_path, dpi=150)
            plt.close()

            logger.info(f"Saved peak LAeq heatmap for week {week_start.strftime('%Y-%m-%d')} at {file_path}")

    except Exception as e:
        logger.error(f"Error in plot_heat_map_prediction_weekly: {e}")
