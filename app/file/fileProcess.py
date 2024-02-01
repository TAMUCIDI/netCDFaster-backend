import xarray as xr

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