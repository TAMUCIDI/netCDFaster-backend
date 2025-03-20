import xarray as xr
import pandas as pd

from env import BASE_DIR, DATASETS_DIR

required_dims = {'lon', 'lat'}

def get_dataset_file_list():
    return list(DATASETS_DIR.rglob('*.nc'))
def rename_dims(ds):
    if 'longitude' in set(ds.dims) and 'latitude' in set(ds.dims):
        ds = ds.rename(
            {
                'longitude': 'lon',
                'latitude': 'lat',
            }
        )
    elif 'LON' in set(ds.dims) and 'LAT' in set(ds.dims):
        ds = ds.rename(
            {
                'LON': 'lon',
                'LAT': 'lat',
            }
        )
    elif 'x' in set(ds.dims) and 'y' in set(ds.dims):
        ds = ds.rename(
            {
                'x': 'lon',
                'y': 'lat',
            }
        )
    
    if 'TIME' in set(ds.dims):
        ds = ds.rename(
            {
                'TIME': 'time',
            }
        )
    elif 'TIM' in set(ds.dims):
        ds = ds.rename(
            {
                'TIM': 'time',
            }
        )
    elif 't' in set(ds.dims):
        ds = ds.rename(
            {
                't': 'time',
            }
        )
    elif 'Time' in set(ds.dims):
        ds = ds.rename(
            {
                'Time': 'time',
            }
        )
    return ds

def main():
    variables_info = []
    fileList = get_dataset_file_list()
    for file in fileList:
        print(f"File: {file}")
        try:
            ds = xr.open_dataset(
                file,
                engine='netcdf4',
                decode_times=True,
                decode_cf=True,
                decode_coords=True,
                decode_timedelta=True,)
        except Exception as e:
            print(f"Error: {e}")
        
        ds = rename_dims(ds)

        lon_len = len(ds.lon) if 'lon' in set(ds.dims) else 0
        lat_len = len(ds.lat) if 'lat' in set(ds.dims) else 0
        time_len = len(ds.time) if 'time' in set(ds.dims) else 0

        var_list = []
        
        for name, var in ds.variables.items():
            if len(list(var.dims)) == 2:
                if {'lon','lat'} == set(var.dims):
                    var_list.append(name)
            elif len(list(var.dims)) == 3:
                if {'lon','lat','time'} == set(var.dims):
                    var_list.append(name)

        for var_name in var_list:
            var = ds[var_name]
            print(f"Variable: {var_name}")
            var_info = {
                'file_name': file,
                'lon_len': lon_len,
                'lat_len': lat_len,
                'time_len': time_len,
                'file_size': ds.nbytes,
                'variable_name': var_name,
                'var_dim_len': len(list(var.dims)),
                'variable_size': var.nbytes,
            }
            variables_info.append(var_info)
    variables_info = pd.DataFrame(variables_info)
    variables_info.to_csv(BASE_DIR / 'variables_info.csv', index=False)

if __name__ == "__main__":
    main()