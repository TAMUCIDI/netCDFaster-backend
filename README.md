# NetCDFaster Backend

A lightweight backend service for managing and serving netCDF data.

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

### Upload File

- **POST** `/file/upload`
- **Body**: Form data with a file.

### Fetch Variable Meta

- **GET** `/file/detail/<var_name>`
- **Params**: `var_name` - variable name.

### Plot Variable Subset

- **POST** `/file/varplot`
- **Body**: JSON data with variable name and coordinate ranges.

## Contributing

Please fork the repository and submit pull requests for improvements.

## Contact

For questions or support, please contact [songzl@tamu.edu](mailto:songzl@tamu.edu).
