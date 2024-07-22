import requests
import folium
from django.shortcuts import render
from .models import Store


def get_city_center_coord():
    response = requests.get('https://ipinfo.io/json')
    data = response.json()
    lat, lon = (data['loc'].split(',')[0], data['loc'].split(',')[1])
    return float(lat), float(lon)


def map_view(request):
    user_lat, user_lon = get_city_center_coord()
    m = folium.Map(location=[user_lat, user_lon], zoom_start=13, tiles='OpenStreetMap')

    stores = Store.objects.select_related('location').all()
    for store in stores:
        folium.Marker(
            location=[store.location.latitude, store.location.longitude],
            popup=f"<b>{store.name}</b><br>{store.location.address}<br>Hours: {store.opening_hours}",
        ).add_to(m)

    map_html = m._repr_html_()

    return render(request, 'store_map.html', {'map_html': map_html})
