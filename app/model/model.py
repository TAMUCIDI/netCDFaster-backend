import os
import joblib
from math import ceil
import numpy as np
import pandas as pd
from dotenv import load_dotenv

X_columns = [
    'lon_len',
    'lat_len', 
    'time_len', 
    'file_size',
    'var_dim_len', 
    'variable_size', 
    'lon_query_len', 
    'lat_query_len',
    'time_query_len'
]

def get_query_policy(n):
    # 定义表格数据，NaN用np.nan表示
    data = [
        [np.nan, np.nan, np.nan],  # 第1行
        [2.0, 2.0, 2.0],           # 第2行
        [4.0, 4.0, 4.0],           # 第3行
        [2.0, np.nan, np.nan],     # 第4行
        [np.nan, 2.0, np.nan],     # 第5行
        [np.nan, np.nan, 2.0],     # 第6行
        [np.nan, 2.0, 4.0],        # 第7行
        [2.0, np.nan, 4.0],        # 第8行
        [2.0, 4.0, np.nan],        # 第9行
    ]
    if 0 <= n <= 8:
        return data[n]  # 输入1对应索引0，依此类推
    else:
        raise ValueError("输入必须为1到9之间的整数")

def calculate_chunk_size(total_length, num_divisions):
    if np.isnan(num_divisions):
        return None
    else:
        return ceil(total_length / num_divisions)

def predict_query_chunk(x_array):

    load_dotenv(dotenv_path=".env")
    MODEL_PATH = os.getenv("MODEL_PKL_PATH")

    model = joblib.load(MODEL_PATH)
    
    #x_test = np.array([144.0,73.0,62.0,44319956.0,3.0,2606976.0,5.321315153879916,49.53573696922402,28.071473938448033])
    #x_test = x_test.reshape(1, -1)

    if len(x_array) != 9:
        raise ValueError("输入数组长度必须为9")
    
    y_pred = model.predict(x_array).reshape(-1)

    # convert classified result to interface
    policyTable = get_query_policy(y_pred[0])
    print(f"Predicted Policy: lon_div={policyTable[0]}, lat_div={policyTable[1]}, time_div={policyTable[2]}")
    print(policyTable)

    chunk_dict = {
        'lon': calculate_chunk_size(
            x_array[6], 
            policyTable[0]),
        'lat': calculate_chunk_size(
            x_array[7], 
            policyTable[1]),
        'time': calculate_chunk_size(
            x_array[8], 
            policyTable[2]) if x_array[4] == 3 else None,
    }

    return chunk_dict