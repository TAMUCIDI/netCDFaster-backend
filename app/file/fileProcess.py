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