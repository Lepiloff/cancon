from django.db import IntegrityError

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

from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO


angle = 45
brightness_factor = 1.1
contrast_factor = 1.1
blur_radius = 2


def process_image(image, angle, brightness_factor, contrast_factor, blur_radius):
    # Конвертируем изображение в формат RGB
    image = image.convert('RGB')

    # Поворачиваем изображение
    # rotated_image = image.rotate(angle)

    # Изменяем яркость изображения
    enhancer_brightness = ImageEnhance.Brightness(image)
    bright_image = enhancer_brightness.enhance(brightness_factor)

    # Изменяем контраст изображения
    enhancer_contrast = ImageEnhance.Contrast(bright_image)
    contrast_image = enhancer_contrast.enhance(contrast_factor)

    # Накладываем фильтр размытия
    # blurred_image = contrast_image.filter(ImageFilter.GaussianBlur(blur_radius))

    return contrast_image




class Command(BaseCommand):
    help = "Import strains from JSON file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to JSON file")

    def handle(self, *args, **options):
        with open(options["file"], "r") as f:
            strains_data = json.load(f)

        for strain_data in strains_data.values():
            defaults = {
                'title': f"{strain_data['strain_name']} | Variedad de cannabis",
                'description': f"Obtén más información sobre la variedad de cannabis {strain_data['strain_name']} , sus efectos y sabores.",
                'keywords': f"{strain_data['strain_name']} , cannabis, variedad, efectos, sabores",
                'rating': float(strain_data['rating']),
                'category': strain_data['category'],
                'thc': float(strain_data.get('thc')) if strain_data.get('thc') is not None else None,
                'text_content': strain_data['text_content'],
            }

            if 'cbd' in strain_data:
                defaults['cbd'] = float(strain_data['cbd'])

            if 'cbg' in strain_data:
                defaults['cbg'] = float(strain_data['cbg'])

            try:
                strain, created = Strain.objects.get_or_create(
                    name=strain_data['strain_name'],
                    defaults=defaults,
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Imported {strain.name}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Found existing {strain.name}'))
            except IntegrityError:
                self.stdout.write(
                    self.style.WARNING(f'Skipped duplicate {strain_data["strain_name"]}'))

            for feeling_name in strain_data['feelings']:
                feeling, _ = Feeling.objects.get_or_create(name=feeling_name)
                strain.feelings.add(feeling)

            for negative_name in strain_data['negatives']:
                negative, _ = Negative.objects.get_or_create(name=negative_name)
                strain.negatives.add(negative)

            # for helps_with_name in strain_data['helps_with']:
            #     helps_with, _ = HelpsWith.objects.get_or_create(name=helps_with_name)
            #     strain.helps_with.add(helps_with)

            for flavor_name in strain_data['flavors']:
                flavor, _ = Flavor.objects.get_or_create(name=flavor_name)
                strain.flavors.add(flavor)

            # Download and save the image
            if strain_data['img_url']:
                response = requests.get(strain_data['img_url'])
                if response.status_code == 200:
                    img_content = ContentFile(response.content)
                    file_name = f'{strain.slug}.png'

                    # Обработка изображения с использованием process_image
                    image = Image.open(BytesIO(response.content))
                    modified_image = process_image(image, angle, brightness_factor, contrast_factor, blur_radius)
                    image_io = BytesIO()
                    modified_image.save(image_io, format='PNG')
                    img_content = ContentFile(image_io.getvalue())

                    strain.img.save(file_name, img_content)
                    strain.img_alt_text = f'{strain.name} image'
                    strain.save()

            self.stdout.write(self.style.SUCCESS(f'Imported {strain.name}'))
