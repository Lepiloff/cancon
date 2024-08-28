import requests
import folium

from django.shortcuts import render, redirect
from .models import Location, Store


SUPPORTED_COUNTRIES = [country_code for country_code, _ in Location.COUNTRY_CHOICES]


def get_city_center_coord() -> tuple:
    response = requests.get('https://ipinfo.io/json')
    data = response.json()
    lat, lon = (data['loc'].split(',')[0], data['loc'].split(',')[1])
    country = data.get('country', '').lower()
    return float(lat), float(lon), country


def map_view(request, country):
    if country == 'unknown':
        # Если страна не поддерживается, показываем пустую карту с сообщением
        map_html = folium.Map(location=[0, 0], zoom_start=2, tiles='OpenStreetMap')._repr_html_()
        return render(request, 'store_map.html', {'map_html': map_html, 'country': country, 'message': 'Lo siento, no hay datos sobre tiendas para su país. Puede seleccionar el país que le interese en el filtro.'})

    user_lat, user_lon, _ = get_city_center_coord()

    m = folium.Map(location=[user_lat, user_lon], zoom_start=13, tiles='OpenStreetMap')

    stores = Store.objects.filter(location__country=country).select_related('location')
    for store in stores:
        folium.Marker(
            location=[store.location.latitude, store.location.longitude],
            popup=f"<b>{store.name}</b><br>{store.location.address}<br>Hours: {store.opening_hours}",
        ).add_to(m)

    map_html = m._repr_html_()

    return render(request, 'store_map.html', {'map_html': map_html, 'country': country})


def get_country_from_ip():
    response = requests.get('https://ipinfo.io/json')
    data = response.json()
    return data.get('country', '').lower()

def global_map_redirect(request):
    country = get_country_from_ip()
    if country and country in SUPPORTED_COUNTRIES:
        return redirect('map_view', country=country)
    return redirect('map_view', country='unknown')
