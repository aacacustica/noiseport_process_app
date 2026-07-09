QUERYS = {
    "load_acoustics_db":"""
        LOAD DATA LOCAL INFILE '{data_path}'
            INTO TABLE {table_name}
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\n'
        IGNORE 1 LINES
        (
        `LA`, `LC`, `LZ`, `LAmax`, `LAmin`,
        `12.6Hz`, `15.8Hz`, `20.0Hz`, `25.1Hz`, `31.6Hz`, `39.8Hz`, `50.1Hz`, `63.1Hz`, `79.4Hz`,
        `100.0Hz`, `125.9Hz`, `158.5Hz`, `199.5Hz`, `251.2Hz`, `316.2Hz`, `398.1Hz`, `501.2Hz`,
        `631.0Hz`, `794.3Hz`, `1000.0Hz`, `1258.9Hz`, `1584.9Hz`, `1995.3Hz`, `2511.9Hz`,
        `3162.3Hz`, `3981.1Hz`, `5011.9Hz`, `6309.6Hz`, `7943.3Hz`, `10000.0Hz`, `12589.3Hz`,
        `15848.9Hz`,`Timestamp`,`Filename`,`Unixtimestamp`,`sensor_id`
        )
    """,

    "load_wavs_db":"""
        LOAD DATA LOCAL INFILE '{data_path}'
            INTO TABLE {table_name}
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\n'
        IGNORE 1 LINES
        (Filename,Timestamp,Duration);
    """,

    "load_preds_db":"""
        LOAD DATA LOCAL INFILE '{data_path}'
            INTO TABLE {table_name}
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\n'
        IGNORE 1 LINES
        (Prediction_1,Prediction_2,Prediction_3,Prob_1,Prob_2,Prob_3,Filename,Timestamp);
    """,

    "load_sonometers_db":"""
        LOAD DATA LOCAL INFILE '{data_path}'
            INTO TABLE {table_name}
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\n'
        IGNORE 1 LINES
        (LAeq,LCeq,LAmax,LAmin,
        `1/3 LZeq 6.3`, `1/3 LZeq 8.0`, `1/3 LZeq 10.0`, `1/3 LZeq 12.5`, `1/3 LZeq 16.0`,
        `1/3 LZeq 20.0`, `1/3 LZeq 25.0`, `1/3 LZeq 31.5`, `1/3 LZeq 40.0`, `1/3 LZeq 50.0`,
        `1/3 LZeq 63.0`, `1/3 LZeq 80.0`, `1/3 LZeq 100`, `1/3 LZeq 125`, `1/3 LZeq 160`,
        `1/3 LZeq 200`, `1/3 LZeq 250`, `1/3 LZeq 315`, `1/3 LZeq 400`, `1/3 LZeq 500`,
        `1/3 LZeq 630`, `1/3 LZeq 800`, `1/3 LZeq 1000`, `1/3 LZeq 1250`, `1/3 LZeq 1600`,
        `1/3 LZeq 2000`, `1/3 LZeq 2500`, `1/3 LZeq 3150`, `1/3 LZeq 4000`, `1/3 LZeq 5000`,
        `1/3 LZeq 6300`, `1/3 LZeq 8000`, `1/3 LZeq 10000`, `1/3 LZeq 12500`, `1/3 LZeq 16000`,
        `1/3 LZeq 20000`,Timestamp,Filename,Unixtimestamp,sensor_id
    )
    """,
    "load_acoustics_db_sensor_RP": """
        LOAD DATA LOCAL INFILE '{data_path}'
            INTO TABLE {table_name}
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\\n'
        IGNORE 1 LINES
        (
            `LA`, `LC`, `LZ`, `LAmax`, `LAmin`,
            `25.12Hz`,
            `31.62Hz`,
            `39.81Hz`,
            `50.12Hz`,
            `63.10Hz`,
            `79.43Hz`,
            `100.00Hz`,
            `125.89Hz`,
            `158.49Hz`,
            `199.53Hz`,
            `251.19Hz`,
            `316.23Hz`,
            `398.11Hz`,
            `501.19Hz`,
            `630.96Hz`,
            `794.33Hz`,
            `1000.00Hz`,
            `1258.93Hz`,
            `1584.89Hz`,
            `1995.26Hz`,
            `2511.89Hz`,
            `3162.28Hz`,
            `3981.07Hz`,
            `5011.87Hz`,
            `6309.57Hz`,
            `Timestamp`,
            `Filename`,
            `Unixtimestamp`,
            @csv_id_micro
        )
        SET
            `sensor_id` = '{device_id}'
    """,
    }

TABLES = {
    "acoustic_data": """
        CREATE TABLE IF NOT EXISTS noise_port_test.acoustic_data (
            record_id INT AUTO_INCREMENT PRIMARY KEY,
            LA DECIMAL(10,2),
            LC DECIMAL(10,2),
            LZ DECIMAL(10,2),
            LAmax DECIMAL(10,2),
            LAmin DECIMAL(10,2),
            `12.6Hz` DECIMAL(10,2),
            `15.8Hz` DECIMAL(10,2),
            `20.0Hz` DECIMAL(10,2),
            `25.1Hz` DECIMAL(10,2),
            `31.6Hz` DECIMAL(10,2),
            `39.8Hz` DECIMAL(10,2),
            `50.1Hz` DECIMAL(10,2),
            `63.1Hz` DECIMAL(10,2),
            `79.4Hz` DECIMAL(10,2),
            `100.0Hz` DECIMAL(10,2),
            `125.9Hz` DECIMAL(10,2),
            `158.5Hz` DECIMAL(10,2),
            `199.5Hz` DECIMAL(10,2),
            `251.2Hz` DECIMAL(10,2),
            `316.2Hz` DECIMAL(10,2),
            `398.1Hz` DECIMAL(10,2),
            `501.2Hz` DECIMAL(10,2),
            `631.0Hz` DECIMAL(10,2),
            `794.3Hz` DECIMAL(10,2),
            `1000.0Hz` DECIMAL(10,2),
            `1258.9Hz` DECIMAL(10,2),
            `1584.9Hz` DECIMAL(10,2),
            `1995.3Hz` DECIMAL(10,2),
            `2511.9Hz` DECIMAL(10,2),
            `3162.3Hz` DECIMAL(10,2),
            `3981.1Hz` DECIMAL(10,2),
            `5011.9Hz` DECIMAL(10,2),
            `6309.6Hz` DECIMAL(10,2),
            `7943.3Hz` DECIMAL(10,2),
            `10000.0Hz` DECIMAL(10,2),
            `12589.3Hz` DECIMAL(10,2),
            `15848.9Hz` DECIMAL(10,2),
            Filename VARCHAR(255),
            Timestamp DATETIME,
            Unixtimestamp BIGINT,
            sensor_id VARCHAR(32)
        );
    """,


    "predict_data": """
        CREATE TABLE IF NOT EXISTS noise_port_test.predict_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Prediction_1 VARCHAR(100),
            Prediction_2 VARCHAR(100),
            Prediction_3 VARCHAR(100),
            Prob_1 DECIMAL(5,2),
            Prob_2 DECIMAL(5,2),
            Prob_3 DECIMAL(5,2),
            Filename VARCHAR(255),
            Timestamp DATETIME
        );
    """,


    "wav_data": """
        CREATE TABLE IF NOT EXISTS noise_port_test.wav_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Filename VARCHAR(255),
            Timestamp DATETIME,
            Duration DECIMAL(10,2)
        );
    """,
    "sonometer_acoustic_data":
    """CREATE TABLE IF NOT EXISTS noise_port_test.sonometer_acoustic_data (
        record_id INT AUTO_INCREMENT PRIMARY KEY,
        LAeq DECIMAL(10,2),
        LCeq DECIMAL(10,2),
        LAmax DECIMAL(10,2),
        LAmin DECIMAL(10,2),
        `1/3 LZeq 6.3` DECIMAL(10,2),
        `1/3 LZeq 8.0` DECIMAL(10,2),
        `1/3 LZeq 10.0` DECIMAL(10,2),
        `1/3 LZeq 12.5` DECIMAL(10,2),
        `1/3 LZeq 16.0` DECIMAL(10,2),
        `1/3 LZeq 20.0` DECIMAL(10,2),
        `1/3 LZeq 25.0` DECIMAL(10,2),
        `1/3 LZeq 31.5` DECIMAL(10,2),
        `1/3 LZeq 40.0` DECIMAL(10,2),
        `1/3 LZeq 50.0` DECIMAL(10,2),
        `1/3 LZeq 63.0` DECIMAL(10,2),
        `1/3 LZeq 80.0` DECIMAL(10,2),
        `1/3 LZeq 100` DECIMAL(10,2),
        `1/3 LZeq 125` DECIMAL(10,2),
        `1/3 LZeq 160` DECIMAL(10,2),
        `1/3 LZeq 200` DECIMAL(10,2),
        `1/3 LZeq 250` DECIMAL(10,2),
        `1/3 LZeq 315` DECIMAL(10,2),
        `1/3 LZeq 400` DECIMAL(10,2),
        `1/3 LZeq 500` DECIMAL(10,2),
        `1/3 LZeq 630` DECIMAL(10,2),
        `1/3 LZeq 800` DECIMAL(10,2),
        `1/3 LZeq 1000` DECIMAL(10,2),
        `1/3 LZeq 1250` DECIMAL(10,2),
        `1/3 LZeq 1600` DECIMAL(10,2),
        `1/3 LZeq 2000` DECIMAL(10,2),
        `1/3 LZeq 2500` DECIMAL(10,2),
        `1/3 LZeq 3150` DECIMAL(10,2),
        `1/3 LZeq 4000` DECIMAL(10,2),
        `1/3 LZeq 5000` DECIMAL(10,2),
        `1/3 LZeq 6300` DECIMAL(10,2),
        `1/3 LZeq 8000` DECIMAL(10,2),
        `1/3 LZeq 10000` DECIMAL(10,2),
        `1/3 LZeq 12500` DECIMAL(10,2),
        `1/3 LZeq 16000` DECIMAL(10,2),
        `1/3 LZeq 20000` DECIMAL(10,2),
        Timestamp DATETIME,
        Filename VARCHAR(255),
        Unixtimestamp BIGINT,
        sensor_id VARCHAR(32)
    );
    """

}