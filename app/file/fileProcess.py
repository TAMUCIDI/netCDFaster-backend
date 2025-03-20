import xarray as xr

from math import ceil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dateutil import parser
import io

def open_dataset(filename, interface, chunk_dict=None):
    return xr.open_dataset(filename, engine=interface, chunks=chunk_dict)

def calculate_chunk_size(total_length, num_divisions):
    if num_divisions is None:
        return None
    else:
        return ceil(total_length / num_divisions)

def read_metadata(file):
    """ 解析NetCDF文件的元信息并返回一个字典。"""
    with xr.open_dataset(file) as ds:
        metainfo = {
            'dimensions': dict(ds.dims),
            'variables': {},
            'attributes': dict(ds.attrs)
        }

        # 获取变量的元信息（不包含数据）
        for var_name, variable in ds.variables.items():
            var_info = {
                'dims': variable.dims,
                'dtype': str(variable.dtype),
                'shape': variable.shape,
                'attributes': dict(variable.attrs)
            }
            metainfo['variables'][var_name] = var_info

        return metainfo
    
def query_variable(file, var_name):
    """ 查询变量的元信息和数据。"""
    with xr.open_dataset(file) as ds:
        variable = ds[var_name]
        dim_names = variable.dims
        var_info = {
            'name': str(var_name),
            'long_name': str(variable.long_name),
            'units': str(variable.units),
            'shape': str(variable.shape),
            'dtype': str(variable.dtype),
            'coords': [],
        }
        for dim_name in dim_names:
            dim_array = variable[dim_name]
            dim_info = {
                'name': dim_name,
                'dtype': str(dim_array.dtype),
                'min': str(dim_array.values.min()),
                'max': str(dim_array.values.max()),
            }
            var_info['coords'].append(dim_info)

        return var_info

def get_coord_names(variable):
    """ 获取数据集的坐标变量名称。"""
    coord_names = {
        'time': None,
        'lon': None,
        'lat': None,
    }
    for coord_name in variable.coords:
        if 'time' == coord_name or 't' == coord_name or 'date' == coord_name or 'datetime' == coord_name or 'T' == coord_name or 'Time' == coord_name:
            coord_names['time'] = coord_name
        if 'lon' == coord_name or 'longitude' == coord_name or 'x' == coord_name or 'Lon' == coord_name or 'Longitude' == coord_name or 'X' == coord_name:
            coord_names['lon'] = coord_name
        if 'lat' == coord_name or 'latitude' == coord_name or 'y' == coord_name or 'Lat' == coord_name or 'Latitude' == coord_name or 'Y' == coord_name:
            coord_names['lat'] = coord_name
    return coord_names
    
def plot_subset(file_path, queryDict):

    # predict chunk size dict using model
    

    with xr.open_dataset(file_path) as ds:
        var_name = queryDict['varName']
        # lon value range
        lon_range = [float(queryDict['lonMin']), float(queryDict['lonMax'])]
        # lat value range
        lat_range = [float(queryDict['latMin']), float(queryDict['latMax'])]
        # time value
        time = parser.parse(queryDict['time'])
        variable = ds[var_name]
        coord_names = get_coord_names(variable)
        # 从数据集中获取指定变量和时间的子集
        try:
            # 使用.sel()选择最接近的时间点
            subset = variable.sel({coord_names['time']: time.replace(tzinfo=None)}, method="nearest")

            # 使用.where()过滤经纬度范围
            subset = subset.where(
                (subset[coord_names['lon']] >= lon_range[0]) & (subset[coord_names['lon']] <= lon_range[1]) &
                (subset[coord_names['lat']] >= lat_range[0]) & (subset[coord_names['lat']] <= lat_range[1]), 
                drop=True
            )
        except Exception as e:
            print(e)
            exit(1)

        # plot the subset
        fig, ax = plt.subplots()
        subset.plot(ax=ax)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        return buf
