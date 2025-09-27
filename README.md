# NetCDFaster Backend

A lightweight backend service for managing and serving netCDF data.

## Acknowledgements

This project is developed and maintained by [Zhenlei Song](https://orcid.org/0009-0007-5205-3808) and supervised by [Dr. Zhe Zhang](https://orcid.org/0000-0001-7108-182X) from CIDI Lab, Department of Geography at Texas A&M University.

Any individual or organization using this code should cite the following paper:

```
Song, Z., Zhang, Z., Sussman, A., Xie, Y., Brenner, J., & Liu, J. (2025). NetCDFaster: Optimizing NetCDF data querying and geo-visualization using high-performance machine learning. SoftwareX, 31, 102269.
```

## Features

- API for uploading and retrieving netCDF files.
- Metadata extraction and validation.
- Integration with Docker for easy deployment.
- Scalable architecture.

## Prerequisites

- Docker
- Python3.8
- NetCDF4
- Flask
- gunicorn

## Usage

1. Clone the repository:
    ```bash
    git clone https://your-repo-url.git
    ```
2. Navigate to the project directory:
    ```bash
    cd netCDFaster-backend
    pip install -r requirements.txt
    ```
3. Development Run:
    ```bash
    python run.py
    ```
4. Production Run:
    ```bash
    gunicorn --bind 127.0.0.1:5000 --workers 4 wsgi:application
    ```

## Configuration

Follow the `.env.example` file to create a `.env` file with the required environment variables.

## API Endpoints

### File Operations

#### Upload NetCDF File
- **POST** `/file/upload`
- **Body**: Form data with NetCDF file
- **Description**: Upload and parse NetCDF file metadata
- **Response**: File metadata and upload information

#### Get Variable Details
- **GET** `/file/detail/<var_name>`
- **Parameters**: `var_name` - variable name
- **Description**: Retrieve detailed information about a specific variable
- **Response**: Variable metadata including dimensions, data types, and coordinate ranges

#### Generate Variable Plot
- **GET** `/file/varplot`
- **Query Parameters**: 
  - `varName` - variable name
  - `lonMin`, `lonMax` - longitude range
  - `latMin`, `latMax` - latitude range  
  - `time` - time point
- **Description**: Generate visualization plot for variable subset
- **Response**: PNG image

### System Monitoring

#### Get Resource Statistics
- **GET** `/file/resources`
- **Description**: Get system resource usage (memory, disk space, upload folder status)
- **Response**: Resource usage statistics

#### Check ML Model Status
- **GET** `/file/model/status`
- **Description**: Check ML model availability and fallback strategy status
- **Response**: Model loading status and configuration

#### Reload ML Model
- **POST** `/file/model/reload`
- **Description**: Force reload of ML prediction model
- **Response**: Reload success status

## Contributing

Please fork the repository and submit pull requests for improvements.

## Contact

For questions or support, please contact [songzl@tamu.edu](mailto:songzl@tamu.edu).
