import os
import json
import requests
from PIL import Image
from io import BytesIO
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.template.defaultfilters import slugify
from strains.models import Strain, Feeling, Negative, HelpsWith, Flavor


def get_extension_from_image_format(image_format):
    format_map = {
        'JPEG': '.jpg',
        'PNG': '.png',
        'GIF': '.gif',
    }
    return format_map.get(image_format.upper())


class Command(BaseCommand):
    help = 'Imports strain data from a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the JSON file with strain data.')

    def handle(self, *args, **options):
        file_path = options['file_path']

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            with transaction.atomic():
                for strain_data in data.values():
                    strain_name = strain_data['strain_name']

                    defaults = {
                        'rating': strain_data['rating'],
                        'category': strain_data['category'],
                        'thc': strain_data['thc'],
                        'text_content': strain_data['text_content'],
                        'slug': slugify(strain_name),
                    }

                    if 'cbd' in strain_data:
                        defaults['cbd'] = strain_data['cbd']

                    if 'cbg' in strain_data:
                        defaults['cbg'] = strain_data['cbg']

                    strain, created = Strain.objects.get_or_create(
                        name=strain_name,
                        defaults=defaults
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Created strain: {strain_name}"))

                    # Download and save the image
                    img_url = strain_data['img_url']
                    response = requests.get(img_url)
                    img_file = BytesIO(response.content)

                    strain_image = Image.open(img_file)
                    img_extension = get_extension_from_image_format(strain_image.format)

                    if img_extension:
                        img_filename = f"{slugify(strain_name)}{img_extension}"
                        strain.img.save(img_filename, File(img_file), save=True)
                    else:
                        self.stdout.write(self.style.WARNING(f"Unsupported image format: {img_url}"))

                    # Create or get related objects and add them to the strain
                    for field, model in [('feelings', Feeling), ('negatives', Negative),
                                         ('helps_with', HelpsWith), ('flavors', Flavor)]:
                        for item_name in strain_data[field]:
                            item, created = model.objects.get_or_create(name=item_name)
                            if created:
                                self.stdout.write(
                                    self.style.SUCCESS(f"Created {model.__name__}: {item_name}"))
                            getattr(strain, field).add(item)

        except FileNotFoundError:
            raise CommandError(f"File not {file_path}")
