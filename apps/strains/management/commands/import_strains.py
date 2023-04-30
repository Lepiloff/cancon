# import os
# import json
# import requests
# from PIL import Image
# from io import BytesIO
# from django.core.files import File
# from django.core.management.base import BaseCommand, CommandError
# from django.db import transaction
# from django.template.defaultfilters import slugify
# from apps.strains.models import Strain, Feeling, Negative, HelpsWith, Flavor
#
#
# def get_extension_from_image_format(image_format):
#     format_map = {
#         'JPEG': '.jpg',
#         'PNG': '.png',
#         'GIF': '.gif',
#     }
#     return format_map.get(image_format.upper())
#
#
# class Command(BaseCommand):
#     help = 'Imports strain data from a JSON file.'
#
#     def add_arguments(self, parser):
#         parser.add_argument('file_path', type=str, help='Path to the JSON file with strain data.')
#
#     def handle(self, *args, **options):
#         file_path = options['file_path']
#
#         try:
#             with open(file_path, 'r', encoding='utf-8') as file:
#                 data = json.load(file)
#
#             with transaction.atomic():
#                 for strain_data in data.values():
#                     strain_name = strain_data['strain_name']
#
#                     defaults = {
#                         'rating': strain_data['rating'],
#                         'category': strain_data['category'],
#                         'thc': strain_data['thc'],
#                         'text_content': strain_data['text_content'],
#                         'slug': slugify(strain_name),
#                     }
#
#                     if 'cbd' in strain_data:
#                         defaults['cbd'] = strain_data['cbd']
#
#                     if 'cbg' in strain_data:
#                         defaults['cbg'] = strain_data['cbg']
#
#                     strain, created = Strain.objects.get_or_create(
#                         name=strain_name,
#                         defaults=defaults
#                     )
#
#                     if created:
#                         self.stdout.write(self.style.SUCCESS(f"Created strain: {strain_name}"))
#
#                     # Download and save the image
#                     img_url = strain_data['img_url']
#                     response = requests.get(img_url)
#                     img_file = BytesIO(response.content)
#
#                     strain_image = Image.open(img_file)
#                     img_extension = get_extension_from_image_format(strain_image.format)
#
#                     if img_extension:
#                         img_filename = f"{slugify(strain_name)}{img_extension}"
#                         strain.img.save(img_filename, File(img_file), save=True)
#                     else:
#                         self.stdout.write(self.style.WARNING(f"Unsupported image format: {img_url}"))
#
#                     # Create or get related objects and add them to the strain
#                     for field, model in [('feelings', Feeling), ('negatives', Negative),
#                                          ('helps_with', HelpsWith), ('flavors', Flavor)]:
#                         for item_name in strain_data[field]:
#                             item, created = model.objects.get_or_create(name=item_name)
#                             if created:
#                                 self.stdout.write(
#                                     self.style.SUCCESS(f"Created {model.__name__}: {item_name}"))
#                             getattr(strain, field).add(item)
#
#         except FileNotFoundError:
#             raise CommandError(f"File not {file_path}")


import json
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.strains.models import (
    Strain,
    Feeling,
    Negative,
    HelpsWith,
    Flavor,
)


class Command(BaseCommand):
    help = "Import strains from JSON file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to JSON file")

    def handle(self, *args, **options):
        with open(options["file"], "r") as f:
            strains_data = json.load(f)

        for strain_data in strains_data.values():
            strain, _ = Strain.objects.get_or_create(
                name=strain_data["strain_name"],
                defaults={
                    "rating": float(strain_data["rating"]),
                    "category": strain_data["category"],
                    "thc": float(strain_data["thc"]),
                    "cbg": float(strain_data["cbg"]),
                    "text_content": strain_data["text_content"],
                },
            )

            for feeling_name in strain_data["feelings"]:
                feeling, _ = Feeling.objects.get_or_create(name=feeling_name)
                strain.feelings.add(feeling)

            for negative_name in strain_data["negatives"]:
                negative, _ = Negative.objects.get_or_create(name=negative_name)
                strain.negatives.add(negative)

            for helps_with_name in strain_data["helps_with"]:
                helps_with, _ = HelpsWith.objects.get_or_create(name=helps_with_name)
                strain.helps_with.add(helps_with)

            for flavor_name in strain_data["flavors"]:
                flavor, _ = Flavor.objects.get_or_create(name=flavor_name)
                strain.flavors.add(flavor)

            # Download and save the image
            if strain_data["img_url"]:
                response = requests.get(strain_data["img_url"])
                if response.status_code == 200:
                    img_content = ContentFile(response.content)
                    file_name = f"{strain.slug}.png"
                    strain.img.save(file_name, img_content)
                    strain.img_alt_text = f"{strain.name} image"
                    strain.save()

            self.stdout.write(self.style.SUCCESS(f"Imported {strain.name}"))
