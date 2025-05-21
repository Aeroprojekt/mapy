# program do wykreslania na mapie samolotow w odleglosci 50 km od warsawy
# niestety jest dzienny limit zapytan wiec to bez sensu
import folium
import requests
import webbrowser
import time
from math import radians, sin, cos, sqrt, atan2

def get_aircraft_data():
    url = "https://opensky-network.org/api/states/all"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Sprawdzenie, czy odpowiedź jest poprawna
        data = response.json()
        return data.get('states', [])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:  # Błąd 429 - limit zapytań
            print("Przekroczono limit zapytań. Czekam 1 minutę...")
            time.sleep(60)  # Czekaj 1 minutę przed kolejnym zapytaniem
            return get_aircraft_data()  # Spróbuj ponownie po 1 minucie
        print(f"Błąd HTTP: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Błąd zapytania: {e}")
    return []  # Zwróć pustą listę, jeśli wystąpi błąd

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Promień Ziemi w kilometrach
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c  # Zwraca odległość w kilometrach

def generate_map():
    aircraft_data = get_aircraft_data()  # Pobierz dane o samolotach
    if not aircraft_data:  # Jeśli brak danych, wyświetl komunikat i zakończ
        print("Brak danych do wyświetlenia.")
        return

    warsaw_lat, warsaw_lon = 52.2297, 21.0122  # Współrzędne Warszawy
    warsaw_map = folium.Map(location=[warsaw_lat, warsaw_lon], zoom_start=9)
    radius_km = 50  # Promień wokół Warszawy (50 km)
    aircraft_count = 0

    for aircraft in aircraft_data:
        try:
            lat = aircraft[6]  # Szerokość geograficzna
            lon = aircraft[5]  # Długość geograficzna
            callsign = aircraft[1].strip() if aircraft[1] else "Brak numeru lotu"
            velocity = aircraft[9]  # Prędkość (m/s)
            track = aircraft[10]  # Kierunek lotu (°)

            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                distance = haversine(warsaw_lat, warsaw_lon, lat, lon)  # Odległość od Warszawy
                if distance <= radius_km:
                    folium.map.Marker(
                        [lat, lon],
                        icon=folium.DivIcon(
                            html=f"""<div style="font-size: 10pt; color: black; background-color: yellow; padding: 2px; border: 1px solid black; border-radius: 3px;">{callsign}</div>"""
                        ),
                        popup=f"{callsign}\n{distance:.1f} km od Warszawy\nPrędkość: {velocity:.1f} m/s\nKierunek: {track:.1f}°"
                    ).add_to(warsaw_map)

                    if isinstance(track, (int, float)):
                        length_km = 10
                        dest_lat = lat + (length_km / 111.32) * cos(radians(track))
                        dest_lon = lon + (length_km / (111.32 * cos(radians(lat)))) * sin(radians(track))

                        folium.PolyLine(
                            locations=[[lat, lon], [dest_lat, dest_lon]],
                            color='red',
                            weight=2,
                            opacity=0.7
                        ).add_to(warsaw_map)

                        folium.RegularPolygonMarker(
                            location=[dest_lat, dest_lon],
                            number_of_sides=3,
                            radius=5,
                            rotation=track,
                            color='red',
                            fill_color='red',
                            fill_opacity=0.9
                        ).add_to(warsaw_map)

                    aircraft_count += 1

        except (TypeError, IndexError) as e:
            print(f"Błąd przetwarzania samolotu: {e}")

    folium.Circle(
        location=[warsaw_lat, warsaw_lon],
        radius=radius_km * 1000,
        color='blue',
        fill=True,
        fill_opacity=0.1
    ).add_to(warsaw_map)

    refresh_script = """
        <script>
            setTimeout(function(){
               window.location.reload(1);
            }, 10000);
        </script>
    """
    warsaw_map.get_root().html.add_child(folium.Element(refresh_script))
    warsaw_map.save("warsaw_aircraft_map.html")
    print(f"Mapa z {aircraft_count} samolotami zapisana jako warsaw_aircraft_map.html.")

if __name__ == "__main__":
    generate_map()
    webbrowser.open("warsaw_aircraft_map.html")
    while True:
        time.sleep(10)  # Zwiększone opóźnienie między zapytaniami do API
        generate_map()
