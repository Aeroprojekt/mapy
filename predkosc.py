import numpy as np
import matplotlib.pyplot as plt

# --- Stałe fizyczne ---
g = 9.81  # Przyspieszenie ziemskie [m/s^2]
M_air = 0.02896  # Średnia masa molowa powietrza [kg/mol]
R_gas = 8.314  # Uniwersalna stała gazowa [J/(mol*K)]
P0 = 101325  # Ciśnienie atmosferyczne na poziomie morza [Pa]
L = 0.0065  # Standardowy gradient temperatury w atmosferze [K/m] (-6.5°C na km)
H_base = 0  # Wysokość bazowa [m] (poziom morza)

# --- Parametry balonu ---
balloon_radius = 1.5 / 2  # Promień balonu [m]
V_initial_full = (4 / 3) * np.pi * balloon_radius ** 3  # Początkowa, pełna objętość balonu [m^3]
mass_total_kg = 0.260  # Masa balonu w locie (powłoka + wzmocnienia + klej) [kg]
weight_force_newtons = mass_total_kg * g

# --- Parametry otworu na dole balonu ---
opening_diameter = 0.20  # Średnica otworu na dole balonu [m]
opening_area = np.pi * (opening_diameter / 2) ** 2  # Pole powierzchni otworu [m^2]

# --- Parametry aerodynamiczne ---
frontal_area = np.pi * balloon_radius ** 2  # Powierzchnia czołowa balonu [m^2] (dla kuli)
CD = 0.47  # Współczynnik oporu aerodynamicznego (dla kuli, uproszczenie)

# --- Kluczowe założenia symulacji (stałe dla wszystkich przebiegów) ---
initial_balloon_temp_celsius = 70  # Początkowa temperatura powietrza w balonie [°C]
heat_loss_coeff = 0.25  # Empiryczny współczynnik strat ciepła [jednostki/s] - do kalibracji!

# --- Parametry flaczenia (liniowa zależność) ---
flac_start_delta_T = 30  # [°C] - Balon zaczyna flaczeć, gdy delta_T spadnie poniżej tej wartości
flac_end_delta_T = 5  # [°C] - Balon osiąga minimalną objętość, gdy delta_T spadnie poniżej tej wartości
min_volume_factor = 0.6  # Minimalna objętość jako ułamek V_initial_full (60%)


# --- Funkcje modelu atmosfery ---
def temperature_at_altitude_K(T_ground_celsius, altitude_m):
    """Oblicza temperaturę zewnętrzną na danej wysokości w Kelvinach."""
    T_ground_kelvin = T_ground_celsius + 273.15
    temp_at_alt_K = T_ground_kelvin - L * (altitude_m - H_base)
    return max(temp_at_alt_K, 220)


def pressure_at_altitude(T_ground_celsius, altitude_m):
    """Oblicza ciśnienie na danej wysokości."""
    T_ground_kelvin = T_ground_celsius + 273.15
    base = 1 - (L * (altitude_m - H_base)) / T_ground_kelvin
    if base <= 0: return 0
    return P0 * (base) ** (g * M_air / (R_gas * L))


def density_of_air(temperature_kelvin, pressure_pa):
    """Oblicza gęstość powietrza dla danej temperatury w Kelvinach i ciśnienia."""
    if temperature_kelvin <= 0: return float('inf') if pressure_pa > 0 else 0
    return (pressure_pa * M_air) / (R_gas * temperature_kelvin)


# --- Funkcja do dynamicznego znajdowania maksymalnej wysokości ---
def find_max_altitude_dynamic(ground_temp_celsius_param):
    """
    Przeprowadza symulację lotu dla danej temperatury zewnętrznej na ziemi
    i zwraca maksymalnie osiągniętą wysokość.
    """
    # Zmienne stanu balonu (resetowane dla każdej symulacji)
    current_altitude = 0.0
    vertical_velocity = 0.0
    # Początkowa temperatura wewnętrzna jest stała 70 stopni Celsjusza
    current_internal_temp_celsius = initial_balloon_temp_celsius
    current_balloon_volume = V_initial_full

    max_altitude_reached = 0.0

    time_step = 0.2  # Krok czasowy symulacji [s]
    max_sim_time = 300  # Maksymalny czas symulacji [s] (5 minut - dłużej dla wyższych lotów)

    for t in np.arange(0, max_sim_time, time_step):
        # 1. Oblicz parametry atmosfery na aktualnej wysokości
        current_external_temp_K = temperature_at_altitude_K(ground_temp_celsius_param, current_altitude)
        current_external_temp_celsius = current_external_temp_K - 273.15
        current_pressure = pressure_at_altitude(ground_temp_celsius_param, current_altitude)

        # 2. Oblicz gęstość powietrza zewnętrznego i wewnętrznego
        rho_external = density_of_air(current_external_temp_K, current_pressure)
        rho_internal = density_of_air(current_internal_temp_celsius + 273.15, current_pressure)

        # 3. Oblicz siłę nośną (zależną od aktualnej objętości)
        current_lift_force = current_balloon_volume * g * (rho_external - rho_internal)

        # 4. Oblicz siłę oporu powietrza
        drag_force = 0.5 * rho_external * (vertical_velocity ** 2) * frontal_area * CD
        drag_force_direction = -drag_force if vertical_velocity > 0 else drag_force

        # 5. Oblicz siłę wypadkową (netto siłę)
        net_force = current_lift_force - weight_force_newtons + drag_force_direction

        # 6. Oblicz przyspieszenie i nową prędkość pionową
        acceleration = net_force / mass_total_kg
        vertical_velocity += acceleration * time_step

        if current_altitude <= 0 and vertical_velocity < 0:
            vertical_velocity = 0
            current_altitude = 0

        current_altitude += vertical_velocity * time_step

        # Aktualizuj maksymalną osiągniętą wysokość
        max_altitude_reached = max(max_altitude_reached, current_altitude)

        # 7. Modelowanie ochładzania powietrza wewnątrz balonu
        delta_T_current = current_internal_temp_celsius - current_external_temp_celsius

        if delta_T_current > 0:
            current_internal_temp_celsius -= heat_loss_coeff * delta_T_current * time_step * (
                        opening_area / V_initial_full)
        else:
            current_internal_temp_celsius = current_external_temp_celsius

            # 8. Modelowanie proporcjonalnego flaczenia balonu
        if delta_T_current <= flac_start_delta_T:
            flac_progress = max(0, min(1, (flac_start_delta_T - delta_T_current) / (
                        flac_start_delta_T - flac_end_delta_T)))
            current_balloon_volume = V_initial_full * (1 - flac_progress * (1 - min_volume_factor))
        else:
            current_balloon_volume = V_initial_full

            # Warunek zakończenia symulacji, jeśli balon wylądował i już się nie wznosi
        if current_altitude <= 0 and vertical_velocity <= 0 and net_force <= 0 and t > 0:
            break

    return max_altitude_reached


# --- Zakres temperatur zewnętrznych na ziemi do analizy ---
external_ground_temps_celsius_range = np.arange(-10, 35, 1)

# --- Obliczenia pułapu dla różnych temperatur zewnętrznych ---
max_altitudes_for_temps = []
print(f"Obliczanie maksymalnych wysokości dla różnych temperatur zewnętrznych...")
for temp_ground in external_ground_temps_celsius_range:
    altitude = find_max_altitude_dynamic(temp_ground)
    max_altitudes_for_temps.append(altitude)
    print(f"  Dla temperatury {temp_ground}°C, osiągnięto pułap: {altitude:.2f} m")

# --- Wykres Pułapu vs. Temperatura Zewnętrzna ---
plt.figure(figsize=(10, 6))
plt.plot(external_ground_temps_celsius_range, max_altitudes_for_temps, marker='o', linestyle='-', color='blue')

plt.xlabel('Temperatura powietrza zewnętrznego na ziemi [°C]')
plt.ylabel('Maksymalna osiągalna wysokość (pułap) [m]')
plt.title(f'Maksymalny pułap balonu w zależności od temperatury zewnętrznej')
plt.suptitle(
    f'(Masa: {mass_total_kg * 1000:.0f}g, Początkowa temp. w balonie: {initial_balloon_temp_celsius}°C,\n $\Delta T$ flaczenia: {flac_start_delta_T}°C - {flac_end_delta_T}°C do {min_volume_factor * 100:.0f}% objętości)')
plt.grid(True)
plt.axhline(y=0, color='gray', linestyle='-')
plt.ylim(bottom=0)
plt.show()

print(f"\n--- Podsumowanie Analizy Pułapu ---")
print(f"Model balonu: Średnica {1.5} m, Masa {mass_total_kg * 1000:.0f} g")
print(f"Założona początkowa temperatura w balonie: {initial_balloon_temp_celsius}°C")
print(f"Zastosowany współczynnik strat ciepła: {heat_loss_coeff}")
print(
    f"Parametry flaczenia: start przy {flac_start_delta_T}°C, koniec przy {flac_end_delta_T}°C, min. objętość {min_volume_factor * 100:.0f}%")