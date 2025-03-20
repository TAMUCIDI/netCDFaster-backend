import random
import time
import psutil
import os
from math import ceil
from itertools import product

import pandas as pd
import xarray as xr

from env import BASE_DIR, ENGINES, DIV_NUMS



def random_range(length, max_range_size=None):
    start = random.randint(0,length-1)
    end = min(start + random.randint(1, max_range_size or length), length)
    return start, end

def open_dataset(filename, interface, chunk_dict=None):
    return xr.open_dataset(filename, engine=interface, chunks=chunk_dict)

def calculate_chunk_size(total_length, num_divisions):
    if num_divisions is None:
        return None
    else:
        return ceil(total_length / num_divisions)
def create_empty_dataframe():
    return pd.DataFrame(
        columns=[
            'file_name',
            'lon_len',
            'lat_len',
            'time_len',
            'file_size',
            'variable_name',
            'var_dim_len',
            'variable_size',
            'interface',
            'lon_query_len',
            'lat_query_len',
            'time_query_len',
            'lon_div',
            'lat_div',
            'time_div',
            'time_cost',
        ]
    )
def query_subset(query_dict):
    """
    query_dict = {
        'file_name': '...',
        'var_name': '...',
        'dimension_ranges': {
            'lon': (0, 100),
            'lat': (0, 100),
            'time': (0, 100),
        }
    }
    """
    fileName = query_dict['var_meta']['file_name']
    var_dim_len = query_dict['var_meta']['var_dim_len']
    result_df = create_empty_dataframe()
    for engine, lon_div, lat_div, time_div in product(ENGINES, DIV_NUMS, DIV_NUMS, DIV_NUMS):
        start_time = time.time()
        lon_query_len = query_dict['dimension_ranges']['lon'][1] - query_dict['dimension_ranges']['lon'][0]
        lat_query_len = query_dict['dimension_ranges']['lat'][1] - query_dict['dimension_ranges']['lat'][0]
        time_query_len = query_dict['dimension_ranges']['time'][1] - query_dict['dimension_ranges']['time'][0] if var_dim_len == 3 else None
        chunk_dict = {
            'lon': calculate_chunk_size(
                lon_query_len, 
                lon_div),
            'lat': calculate_chunk_size(
                lat_query_len, 
                lat_div),
            'time': calculate_chunk_size(
                time_query_len, 
                time_div) if var_dim_len == 3 else None,
        }
        with open_dataset(
                fileName, 
                interface=engine, 
                chunk_dict=chunk_dict) as ds:
            var = ds[query_dict['var_meta']['variable_name']]
            slices = tuple(slice(query_dict['dimension_ranges'].get(dim, (None, None))[0], 
                                query_dict['dimension_ranges'].get(dim, (None, None))[1]) 
                        for dim in var.dims)
            subset = var[slices]
        end_time = time.time()
        time_cost = end_time - start_time
        #print(f"Lon Div: {lon_div}, Lat Div: {lat_div}, Time Div: {time_div}, Time Cost: {time_cost}")
        result_df_tmp = pd.DataFrame(
            {
                'file_name': [fileName],
                'lon_len': [query_dict['var_meta']['lon_len']],
                'lat_len': [query_dict['var_meta']['lat_len']],
                'time_len': [query_dict['var_meta']['time_len']],
                'file_size': [query_dict['var_meta']['file_size']],
                'variable_name': [query_dict['var_meta']['variable_name']],
                'var_dim_len': [query_dict['var_meta']['var_dim_len']],
                'variable_size': [query_dict['var_meta']['variable_size']],
                'interface': [engine],
                'lon_query_len': [lon_query_len],
                'lat_query_len': [lat_query_len],
                'time_query_len': [time_query_len],
                'lon_div': [lon_div],
                'lat_div': [lat_div],
                'time_div': [time_div],
                'time_cost': [time_cost],
            }
        )
        result_df = pd.concat([result_df, result_df_tmp], ignore_index=True)
        print(result_df_tmp)
    return result_df

    
def main():
    df = pd.read_csv(BASE_DIR / 'variables_info.csv')
    results_df = create_empty_dataframe()
    for index, row in df.iterrows():
        for _ in range(10):
            file_name, variable_name = row['file_name'], row['variable_name']
            lon_len, lat_len, time_len = row['lon_len'], row['lat_len'], row['time_len']
            dim_len = row['var_dim_len']

            lon_range = random_range(lon_len)
            lat_range = random_range(lat_len)
            time_range = random_range(time_len) if dim_len == 3 else None

            query_dict = {
                'var_meta': row,
                'dimension_ranges': {
                    'lon': lon_range,
                    'lat': lat_range,
                    'time': time_range if dim_len == 3 else None,
                }
            }
            
            result_df = query_subset(query_dict)
            results_df = pd.concat([results_df, result_df], ignore_index=True)
    results_df.to_csv(BASE_DIR / 'timecost.csv', index=False)



if __name__ == '__main__':
    main()