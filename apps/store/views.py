import logging
import requests
import folium

from django.shortcuts import render, redirect
from django.templatetags.static import static

from .models import Location, Store, COUNTRY_CHOICES, COUNTRY_COORDINATES


logger = logging.getLogger(__name__)


def get_country_info(country_code):
    name = dict(COUNTRY_CHOICES).get(country_code)
    coords = COUNTRY_COORDINATES.get(country_code, (0, 0))
    return name, coords


def get_city_center_coord() -> tuple:
    response = requests.get('https://ipinfo.io/json')
    data = response.json()
    lat, lon = (data['loc'].split(',')[0], data['loc'].split(',')[1])
    country = data.get('country', '').lower()
    return float(lat), float(lon), country


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
            <img src="{logo_url}" alt="{store.name} logo" style="width: 100px; height: auto; margin-bottom: 10px;">
            <h4>{store.name}</h4>
            <p><strong></strong> {store.get_store_type_display()}</p>
            <p><strong>Ciudad:</strong> {store.location.city}</p>
            <p><strong>Dirección:</strong> {store.location.address}</p>
            <p><strong>Teléfono:</strong> {store.phone_number}</p>
            <p><strong>Email:</strong> {store.email}</p>
            <p><strong>Horario:</strong></p>
            <ul style="list-style: none; padding: 0; margin: 0;">
                {''.join([f'<li style="margin-left: 0; padding-left: 0;">{day}: {hours}</li>' for day, hours in (store.opening_hours or {}).items()])}
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
            'country': country,
            'country_choices': Location.COUNTRY_CHOICES,
        },
    )


def get_country_from_ip():
    response = requests.get('https://ipinfo.io/json')
    data = response.json()
    logger.info(f"IP Info Data: {data}")
    return data.get('country', '').lower()


def global_map_redirect(request):
    country = get_country_from_ip()
    country_name, _ = get_country_info(country)

    if country_name:
        return redirect('map_view', country=country)

    return redirect('map_view', country='unknown')
