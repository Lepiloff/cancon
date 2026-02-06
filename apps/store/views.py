import requests

import folium
from canna.logging import logger

from django.shortcuts import render, redirect
from django.templatetags.static import static
from django.utils.html import escape

from .models import Location, Store, COUNTRY_CHOICES, COUNTRY_COORDINATES



def get_country_info(country_code):
    name = dict(COUNTRY_CHOICES).get(country_code)
    coords = COUNTRY_COORDINATES.get(country_code, (0, 0))
    return name, coords


def get_city_center_coord() -> tuple:
    try:
        response = requests.get('https://ipinfo.io/json', timeout=5)
        data = response.json()
        loc_parts = data.get('loc', '0,0').split(',')
        lat = float(loc_parts[0])
        lon = float(loc_parts[1]) if len(loc_parts) > 1 else 0.0
        country = data.get('country', '').lower()
        return lat, lon, country
    except Exception:
        return 0.0, 0.0, 'unknown'


def map_view(request, country):
    country_name, country_coords = get_country_info(country)
    user_lat, user_lon, user_country = get_city_center_coord()
    if not country_name or country == 'unknown':
        map_html = folium.Map(
            location=[0, 0], zoom_start=2, tiles='OpenStreetMap'
        )._repr_html_()
        return render(
            request,
            'store_map.html',
            {
                'map_html': map_html,
                'country': country,
                'message': 'Lo siento, no hay datos sobre tiendas para su país. Puede seleccionar el país que le interese en el filtro.',
                'country_choices': Location.COUNTRY_CHOICES,
            },
        )

    if country == user_country:
        center_coords = (user_lat, user_lon)
    else:
        center_coords = country_coords

    m = folium.Map(location=center_coords, zoom_start=7, tiles='OpenStreetMap')

    custom_icon = folium.CustomIcon(
        icon_image=request.build_absolute_uri(static('img/weed_map.png')),
        icon_size=(32, 32),
    )

    stores = Store.objects.filter(location__country=country).select_related('location')
    for store in stores:
        logo_url = (
            store.logo.url
            if store.logo
            else request.build_absolute_uri(static('img/default-logo.png'))
        )
        popup_html = f"""
        <div style="text-align: center; max-width: 300px;">
            <img src="{escape(logo_url)}" alt="{escape(store.name)} logo" style="width: 100px; height: auto; margin-bottom: 10px;">
            <h4>{escape(store.name)}</h4>
            <p><strong></strong> {escape(store.get_store_type_display())}</p>
            <p><strong>Ciudad:</strong> {escape(store.location.city)}</p>
            <p><strong>Dirección:</strong> {escape(store.location.address)}</p>
            <p><strong>Teléfono:</strong> {escape(store.phone_number or '')}</p>
            <p><strong>Email:</strong> {escape(store.email or '')}</p>
            <p><strong>Horario:</strong></p>
            <ul style="list-style: none; padding: 0; margin: 0;">
                {''.join([f'<li style="margin-left: 0; padding-left: 0;">{escape(day)}: {escape(hours)}</li>' for day, hours in (store.opening_hours or {}).items()])}
            </ul>
            <a href="#" class="btn " style="margin-top: 10px; display: inline-block;">Ver</a>
        </div>
        """
        folium.Marker(
            location=[store.location.latitude, store.location.longitude],
            popup=popup_html,
            icon=custom_icon,
        ).add_to(m)

    map_html = m._repr_html_()

    return render(
        request,
        'store_map.html',
        {
            'map_html': map_html,
            'country': country_name,
            'country_choices': Location.COUNTRY_CHOICES,
        },
    )


def get_country_from_ip():
    try:
        response = requests.get('https://ipinfo.io/json')
        data = response.json()
        logger.info(f"IP Info Data: {data}")
        return data.get('country', '').lower()
    except Exception as e:
        logger.error(f"Error getting country from IP: {e}")
        return 'unknown'


def global_map_redirect(request):
    country = get_country_from_ip()
    country_name, _ = get_country_info(country)

    if country_name:
        return redirect('map_view', country=country)

    return redirect('map_view', country='unknown')
