import os

from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    location = 'static'
    object_parameters = {
        'CacheControl': os.getenv('AWS_S3_STATIC_CACHE_CONTROL', 'max-age=3600')
    }


class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = False
    object_parameters = {
        'CacheControl': os.getenv(
            'AWS_S3_MEDIA_CACHE_CONTROL',
            'public, max-age=31536000, immutable',
        )
    }
