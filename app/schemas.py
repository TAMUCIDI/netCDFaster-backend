from marshmallow import Schema, fields, validate, ValidationError
from werkzeug.datastructures import FileStorage
import re


class FileUploadSchema(Schema):
    file = fields.Raw(required=True, error_messages={'required': 'File is required'})
    
    def validate_file(self, file):
        if not isinstance(file, FileStorage):
            raise ValidationError('Invalid file format')
        if not file.filename:
            raise ValidationError('No file selected')
        if not file.filename.lower().endswith('.nc'):
            raise ValidationError('Only NetCDF (.nc) files are allowed')
        return file


class RemoteFileQuerySchema(Schema):
    url = fields.Str(required=True, validate=validate.Length(min=10, max=2000))
    
    def validate_url(self, url):
        # Validate URL format
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            raise ValidationError('Invalid URL format')
        
        # Check if URL ends with .nc (NetCDF file)
        if not url.lower().endswith('.nc'):
            raise ValidationError('URL must point to a NetCDF (.nc) file')
        
        return url


class VariablePlotSchema(Schema):
    varName = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    lonMin = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    lonMax = fields.Float(required=True, validate=validate.Range(min=-180, max=180))
    latMin = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    latMax = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    time = fields.Str(required=True, validate=validate.Length(min=1))
    
    def validate_coordinates(self, data, **kwargs):
        if data.get('lonMin') and data.get('lonMax'):
            if data['lonMin'] >= data['lonMax']:
                raise ValidationError('lonMin must be less than lonMax')
        if data.get('latMin') and data.get('latMax'):
            if data['latMin'] >= data['latMax']:
                raise ValidationError('latMin must be less than latMax')


class ErrorResponse(Schema):
    error = fields.Str(required=True)
    message = fields.Str(required=True)
    status_code = fields.Int(required=True)


class SuccessResponse(Schema):
    success = fields.Bool(default=True)
    data = fields.Dict()
    message = fields.Str()