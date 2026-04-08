from storages.backends.s3boto3 import S3Boto3Storage, S3ManifestStaticStorage


class StaticStorage(S3ManifestStaticStorage):
    location = 'static'


class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = False
