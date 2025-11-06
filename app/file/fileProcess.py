import numpy as np
import xarray as xr

from math import ceil
import logging
import time as time_module

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dateutil import parser
import io

from app.model.model import predict_query_chunk

logger = logging.getLogger(__name__)

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
        info = {
            'file_size': str(ds.nbytes),
            'var_short_name': str(var_name),
            'var_long_name': str(variable.long_name),
            'units': str(variable.units),
            'shape': str(variable.shape),
            'dtype': str(variable.dtype),
            'variable_size': str(variable.nbytes),
            'var_dim_len': str(len(dim_names)),
            'coords': [],
        }
        for dim_name in dim_names:
            dim_array = variable[dim_name]
            dim_info = {
                'name': dim_name,
                'dtype': str(dim_array.dtype),
                'min': str(dim_array.values.min()),
                'max': str(dim_array.values.max()),
                'len': str(len(dim_array)),
            }
            info['coords'].append(dim_info)

        return info

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
    
def plot_subset(file_path, queryDict, session):
    """
    Generate a plot for a subset of data based on coordinates and time.

    Args:
        file_path: Path to the NetCDF file
        queryDict: Dictionary with keys varName, time, lonMin, lonMax, latMin, latMax
        session: Flask session containing variable metadata

    Returns:
        BytesIO object containing PNG image data

    Raises:
        ValueError: If coordinates or data validation fails
    """
    start_time = time_module.time()

    try:
        var_name = queryDict['varName']
        logger.info(f"Starting plot generation for variable: {var_name}")

        file_size = float(session[var_name]['file_size'])
        var_dim_len = float(session[var_name]['var_dim_len'])
        variable_size = float(session[var_name]['variable_size'])

        # First, open dataset to get actual coordinate names using get_coord_names
        logger.debug(f"Opening dataset to extract coordinate names from {file_path}")
        with xr.open_dataset(file_path) as temp_ds:
            variable = temp_ds[var_name]
            coord_names = get_coord_names(variable)
        logger.debug(f"Extracted coordinate names: {coord_names}")

        # Now find coordinates in session data using the actual coordinate names
        lon_coord_name = coord_names['lon']
        if lon_coord_name is None:
            raise ValueError("Longitude coordinate not found in dataset.")
        lon_coord = next((coord for coord in session[var_name]['coords'] if coord.get('name') == lon_coord_name), None)
        if lon_coord is None:
            raise ValueError(f"Longitude coordinate '{lon_coord_name}' not found in session data.")
        lon_len = float(lon_coord['len'])

        lat_coord_name = coord_names['lat']
        if lat_coord_name is None:
            raise ValueError("Latitude coordinate not found in dataset.")
        lat_coord = next((coord for coord in session[var_name]['coords'] if coord.get('name') == lat_coord_name), None)
        if lat_coord is None:
            raise ValueError(f"Latitude coordinate '{lat_coord_name}' not found in session data.")
        lat_len = float(lat_coord['len'])

        time_coord_name = coord_names['time']
        if time_coord_name is None:
            raise ValueError("Time coordinate not found in dataset.")
        time_coord = next((coord for coord in session[var_name]['coords'] if coord.get('name') == time_coord_name), None)
        if time_coord is None:
            raise ValueError(f"Time coordinate '{time_coord_name}' not found in session data.")
        time_len = float(time_coord['len'])

        # lon value range
        lon_range = [float(queryDict['lonMin']), float(queryDict['lonMax'])]
        lon_query_len = float(lon_range[1] - lon_range[0])
        # lat value range
        lat_range = [float(queryDict['latMin']), float(queryDict['latMax'])]
        lat_query_len = float(lat_range[1] - lat_range[0])
        # time value
        time_query_len = float(1)

        logger.debug(f"Coordinate ranges - Lon: [{lon_range[0]}, {lon_range[1]}], Lat: [{lat_range[0]}, {lat_range[1]}]")

        x_array = [
            lon_len, lat_len, time_len, file_size, var_dim_len, variable_size, lon_query_len, lat_query_len, time_query_len,
        ]

        # predict chunk size dict using model
        logger.debug(f"Predicting chunk size with parameters: {x_array}")
        chunk_dict = predict_query_chunk(x_array)
        logger.debug(f"Predicted chunk dictionary: {chunk_dict}")

        with xr.open_dataset(
            file_path,
            chunks=chunk_dict) as ds:

            # time value
            logger.debug(f"Parsing time value: {queryDict['time']}")
            time = parser.parse(queryDict['time'])
            variable = ds[var_name]

            # Extract data subset and filter by coordinates
            logger.debug("Extracting time index and creating subset")
            subset_start = time_module.time()

            try:
                # Use datetime64 to find the closest time point
                time_ns = np.datetime64(time.replace(tzinfo=None))
                logger.debug(f"Converted time to: {time_ns}")

                # Load time values - note: this loads the entire time dimension into memory
                logger.debug(f"Loading time dimension values (size: {time_len})")
                time_values = variable[coord_names['time']].values

                # Find closest time index
                time_index = int(np.abs(time_values - time_ns).argmin())
                logger.debug(f"Found time index: {time_index} for requested time {time_ns}")

                # Select time slice
                subset = variable.isel({coord_names['time']: time_index})
                logger.debug(f"Created time slice, shape: {subset.shape}")

                # Filter by geographic range
                logger.debug(f"Filtering by geographic bounds")
                subset = subset.where(
                    (subset[coord_names['lon']] >= lon_range[0]) & (subset[coord_names['lon']] <= lon_range[1]) &
                    (subset[coord_names['lat']] >= lat_range[0]) & (subset[coord_names['lat']] <= lat_range[1]),
                    drop=True
                )
                logger.debug(f"Filtered subset shape: {subset.shape}")

            except Exception as e:
                logger.error(f"Failed to extract data subset: {str(e)}", exc_info=True)
                raise ValueError(f"Failed to extract data subset: {str(e)}")

            subset_time = time_module.time() - subset_start
            logger.info(f"Data subset extraction completed in {subset_time:.2f}s")

            # Generate plot
            logger.debug("Generating matplotlib figure")
            plot_start = time_module.time()

            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                logger.debug("Created figure and axes")

                subset.plot(ax=ax)
                logger.debug("Plotted data on axes")

                ax.set_title(f"Subset of '{var_name}' at time {queryDict['time']}", fontsize=14)
                ax.set_xlabel("Longitude", fontsize=12)
                ax.set_ylabel("Latitude", fontsize=12)
                ax.grid(True)
                logger.debug("Set plot labels and grid")

                buf = io.BytesIO()
                logger.debug("Saving figure to buffer")
                plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
                buf.seek(0)
                logger.debug(f"Saved PNG, buffer size: {len(buf.getvalue())} bytes")

                plt.close(fig)
                logger.debug("Closed figure to release memory")

            except Exception as e:
                logger.error(f"Failed to generate plot: {str(e)}", exc_info=True)
                plt.close('all')  # Clean up all figures on error
                raise ValueError(f"Failed to generate plot: {str(e)}")

            plot_time = time_module.time() - plot_start
            logger.info(f"Plot generation completed in {plot_time:.2f}s")

            total_time = time_module.time() - start_time
            logger.info(f"Total plot_subset execution time: {total_time:.2f}s")

            return buf

    except Exception as e:
        logger.error(f"plot_subset failed for variable {queryDict.get('varName', 'unknown')}: {str(e)}", exc_info=True)
        # Make sure to close any open figures on error
        plt.close('all')
        raise
