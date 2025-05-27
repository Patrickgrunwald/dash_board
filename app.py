from flask import Flask, render_template, jsonify
import requests
import icalendar
import datetime
import pytz
import json
import os
import feedparser
from datetime import datetime, timedelta, date
import time
import re
import caldav
from caldav.elements import dav, cdav
import xml.etree.ElementTree as ET

app = Flask(__name__)

# iCloud Kalender Konfiguration
ICLOUD_EMAIL = "patricklevart@me.com"
ICLOUD_APP_PASSWORD = "xgrw-qssx-ruch-cbcd"
ICLOUD_CALDAV_URL = "https://caldav.icloud.com"

# Deutsche Wochentage und Monate für Datumsformatierung
WOCHENTAGE = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag"
}

MONATE = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember"
}

def format_date_german(date):
    """Formatiert ein Datum im deutschen Format."""
    return f"{WOCHENTAGE[date.weekday()]}, {date.day}. {MONATE[date.month]} {date.year}"

def format_time_german(time):
    """Formatiert eine Uhrzeit im deutschen Format."""
    return f"{time.hour}:{time.minute:02d} Uhr"

def get_calendar_events():
    """Ruft Kalendereinträge von iCloud ab, filtert vergangene Ereignisse, sortiert und begrenzt auf die nächsten 5."""
    events = []
    
    try:
        print("Versuche, Verbindung zum iCloud-Kalender herzustellen...")
        # Verbindung zum iCloud CalDAV-Server herstellen
        client = caldav.DAVClient(
            url=ICLOUD_CALDAV_URL,
            username=ICLOUD_EMAIL,
            password=ICLOUD_APP_PASSWORD
        )
        
        print("Verbindung hergestellt, rufe Hauptkalender ab...")
        # Hauptkalender des Benutzers abrufen
        principal = client.principal()
        
        print("Hauptkalender abgerufen, suche nach verfügbaren Kalendern...")
        # Alle verfügbaren Kalender abrufen (keine Filterung nach Namen)
        calendars = principal.calendars()
        print(f"Gefundene Kalender: {len(calendars)}")
        
        # Aktuelle Zeit für Vergleiche. Verwende eine Zeitzone, z.B. Europe/Berlin.
        local_tz = pytz.timezone('Europe/Berlin') 
        now = datetime.now(local_tz)

        # Suche Ereignisse vom gestrigen Tag bis weit in die Zukunft (um auch Ereignisse zu erfassen, die heute früh begonnen haben)
        start_search_date = now - timedelta(days=1)
        end_search_date = now + timedelta(days=365) # Ereignisse für das nächste Jahr suchen
        
        # Kalender-Icons basierend auf Kalendertyp (können beibehalten oder angepasst werden)
        calendar_icons = {
            "Familie": "👪",
            "Patrick": "👤",
            "default": "👤"
        }
        
        # Spezielle Icons für bestimmte Ereignistypen
        event_type_icons = {
            "hochzeit": "🎵",
            "musik": "🎵",
            "konzert": "🎵",
            "tiktok": "👤",
            "meeting": "👤",
            "termin": "👤"
        }
        
        # Durch alle Kalender iterieren
        for calendar in calendars:
            calendar_name = calendar.name.lower() if calendar.name else ""
            print(f"Verarbeite Kalender: {calendar_name}")
            
            # Icon basierend auf Kalendername festlegen (optional)
            default_icon = calendar_icons.get("familie" if "familie" in calendar_name else ("patrick" if "patrick" in calendar_name else "default"), "👤")
            
            try:
                # Ereignisse im Zeitraum abrufen
                print(f"Suche Ereignisse von {start_search_date} bis {end_search_date} in {calendar.name}")
                # Nutze date_search mit erweiterten Parametern, falls vom Server unterstützt, sonst fall back
                try:
                    calendar_events = calendar.date_search(start=start_search_date, end=end_search_date, expand=True)
                except:
                     calendar_events = calendar.date_search(start=start_search_date, end=end_search_date)

                print(f"Gefundene Ereignisse in {calendar.name}: {len(calendar_events)}")
                
                for event in calendar_events:
                    try:
                        # Ereignisdaten parsen
                        event_data = event.data
                        ical = icalendar.Calendar.from_ical(event_data)
                        
                        for component in ical.walk():
                            if component.name == "VEVENT":
                                # Titel des Ereignisses
                                summary = str(component.get('summary', 'Unbekanntes Ereignis'))
                                
                                # Start- und Endzeit des Ereignisses
                                dtstart_comp = component.get('dtstart')
                                dtend_comp = component.get('dtend')

                                if not dtstart_comp:
                                    print(f"Überspringe Ereignis ohne Startzeit: {summary}")
                                    continue # Überspringe Ereignisse ohne Startzeit

                                dtstart = dtstart_comp.dt
                                dtend = dtend_comp.dt if dtend_comp else None

                                # Speichern, ob das ursprüngliche dtstart ein Datum (ganztägig) war
                                original_dtstart_is_date = isinstance(dtstart_comp.dt, date) and not isinstance(dtstart_comp.dt, datetime)

                                # Konvertiere Start- und Endzeiten in die lokale Zeitzone (Europe/Berlin) für Vergleiche und Anzeige.
                                # iCalendar hat verschiedene Formate (UTC, Floating, Tzid, Date).
                                # caldav-python parst diese, wir müssen sicherstellen, dass wir ein Zeitzonen-aware Objekt haben.

                                local_tz = pytz.timezone('Europe/Berlin')
                                now_localized = datetime.now(local_tz) # Aktuelle Zeit in lokaler Zeitzone

                                # Konvertiere dtstart
                                if isinstance(dtstart, datetime):
                                    if dtstart.tzinfo is None:
                                        # Naive datetime: Annahme ist lokale Zeit, dann lokalisieren
                                        dtstart_localized = local_tz.localize(dtstart)
                                    else:
                                        # Aware datetime: In lokale Zeitzone konvertieren
                                        dtstart_localized = dtstart.astimezone(local_tz)
                                elif isinstance(dtstart, date):
                                     # Date-only: Behandle als Beginn des Tages in lokaler Zeit für Vergleiche.
                                     # Für die Anzeige behandeln wir es separat (nur Datum).
                                     dtstart_localized = local_tz.localize(datetime.combine(dtstart, datetime.min.time()))
                                else:
                                     print(f"Unbekannter dtstart Typ für Ereignis {summary}: {type(dtstart)}")
                                     continue # Überspringe unbekannte Typen

                                # Konvertiere dtend (falls vorhanden)
                                dtend_localized = None
                                if dtend:
                                    if isinstance(dtend, datetime):
                                        if dtend.tzinfo is None:
                                            # Naive datetime: Annahme ist lokale Zeit, dann lokalisieren
                                            dtend_localized = local_tz.localize(dtend)
                                        else:
                                            # Aware datetime: In lokale Zeitzone konvertieren
                                            dtend_localized = dtend.astimezone(local_tz)
                                    elif isinstance(dtend, date):
                                         # Date-only: Behandle als Ende des Tages vorher (iCalendar exclusive end date for all-day)
                                        dtend_localized = local_tz.localize(datetime.combine(dtend, datetime.min.time())) - timedelta(seconds=1)
                                    else:
                                         print(f"Unbekannter dtend Typ für Ereignis {summary}: {type(dtend)}")
                                         # Wenn dtend unbekannt, Vergangenheitsprüfung basierend auf dtstart
                                         dtend_localized = dtstart_localized + timedelta(hours=1) # Fallback für Vergangenheitsprüfung
                                else:
                                    # Kein Enddatum, nimm Startdatum plus eine kurze Dauer für Vergangenheitsprüfung
                                    dtend_localized = dtstart_localized + timedelta(minutes=30) # Angenommene Dauer, falls kein Enddatum

                                # Filter: Ereignisse, die vor mehr als 1 Stunde endeten (basierend auf lokaler Zeit)
                                if dtend_localized < now_localized - timedelta(hours=1):
                                     # print(f"Überspringe vergangenes Ereignis: {summary} (Endet {dtend_localized.strftime('%Y-%m-%d %H:%M')})") # Debugging-Ausgabe
                                     continue
                                
                                # Datum und Zeit für die Anzeige formatieren
                                # Nutze das original_dtstart_is_date Flag, um zwischen Datum-only und Datum+Zeit zu unterscheiden

                                if original_dtstart_is_date:
                                    # Ganztägiges Ereignis: Zeige nur das Datum
                                    event_date_display = dtstart_comp.dt # Hier das ursprüngliche Datum (date-Objekt) verwenden
                                    
                                    # Formatierung für ganztägige Ereignisse
                                    today = now_localized.date()
                                    tomorrow = today + timedelta(days=1)

                                    if event_date_display == today:
                                        date_display = "Heute"
                                    elif event_date_display == tomorrow:
                                        date_display = "Morgen"
                                    elif event_date_display.year == today.year:
                                         # Im selben Jahr, zeige Monat und Tag
                                         date_display = f"{MONATE[event_date_display.month]} {event_date_display.day}."
                                    else:
                                         # Anderes Jahr, zeige Datum mit Jahr
                                         date_display = f"{event_date_display.day}. {MONATE[event_date_display.month]} {event_date_display.year}"

                                else:
                                    # Ereignis mit spezifischer Uhrzeit: Zeige Datum und Uhrzeit
                                    # Nutze die bereits lokalisierte Startzeit (dtstart_localized) für die Anzeigeformatierung
                                    
                                    today = now_localized.date()
                                    tomorrow = today + timedelta(days=1)

                                    event_date_display = dtstart_localized.date()
                                    time_str = dtstart_localized.strftime("%H:%M")
                                    weekday_str = WOCHENTAGE[dtstart_localized.weekday()]
                                    month_str = MONATE[event_date_display.month]

                                    if event_date_display == today:
                                        # Heute
                                        date_display = f"Heute um {time_str} Uhr"
                                    elif event_date_display == tomorrow:
                                        # Morgen
                                        date_display = f"Morgen um {time_str} Uhr"
                                    elif event_date_display.year == today.year:
                                        # Im selben Jahr, zeige Wochentag, Datum und Uhrzeit
                                        date_display = f"{weekday_str}, {event_date_display.day}. {month_str} um {time_str} Uhr"
                                    else:
                                        # Anderes Jahr, zeige vollständiges Datum und Uhrzeit
                                        date_display = f"{weekday_str}, {event_date_display.day}. {month_str} {event_date_display.year} um {time_str} Uhr"

                                # Icon basierend auf Ereignistyp oder Kalendername festlegen
                                icon = default_icon
                                for keyword, specific_icon in event_type_icons.items():
                                    if keyword in summary.lower():
                                        icon = specific_icon
                                        break
                                
                                # Ereignis zum Array hinzufügen, inklusive der lokalen Startzeit für Sortierung
                                events.append({
                                    "title": summary,
                                    "time": date_display,
                                    "icon": icon,
                                    "start_local": dtstart_localized # Speichern der LOKALISIERTEN Zeit für Sortierung
                                })
                    except Exception as e:
                        print(f"Fehler beim Verarbeiten eines Ereignisses in Kalender {calendar.name}: {e}")
            except Exception as e:
                print(f"Fehler beim Abrufen von Ereignissen aus Kalender {calendar.name}: {e}")
        
        # Ereignisse nach lokaler Startzeit sortieren
        events.sort(key=lambda x: x["start_local"])
        
        # Begrenze auf die nächsten 5 Ereignisse
        limited_events = events[:5]

        print(f"Insgesamt gefundene zukünftige Ereignisse (vor Filterung): {len(events)}, Zeige die nächsten {len(limited_events)}")
        
        # Wenn keine Ereignisse gefunden wurden oder nach Filterung weniger als 5 übrig sind,
        # und die ursprüngliche Suche keine Fehler hatte, Fallback oder leere Liste zurückgeben.
        # Wenn ein Fehler auftrat, Fallback mit Beispieldaten.
        if not limited_events and len(calendars) > 0: # Nur Fallback, wenn wirklich keine Ereignisse gefunden wurden und Kalender da waren
             print("Keine oder weniger als 5 zukünftige Ereignisse gefunden. Verwende Beispieldaten.")
             limited_events = get_example_calendar_events() # Stellt sicher, dass Fallback 5 liefert
        elif not limited_events and len(calendars) == 0:
              print("Keine Kalender gefunden, verwende Beispieldaten")
              limited_events = get_example_calendar_events()
        
        # Entferne das temporäre Sortierfeld 'start_local'
        for event in limited_events:
             if 'start_local' in event:
                 del event['start_local']

    except Exception as e:
        print(f"Schwerwiegender Fehler beim Abrufen der Kalendereinträge: {e}")
        # Fallback-Daten bei schwerwiegendem Fehler (z.B. Verbindungsprobleme)
        limited_events = get_example_calendar_events()
    
    return limited_events

def get_example_calendar_events():
    """Liefert Beispiel-Kalenderdaten zurück."""
    current_date = datetime.now()
    
    example_events = [
        {
            "title": "Keaz Start",
            "time": f"{WOCHENTAGE[0]} um 14:30 Uhr",
            "icon": "👤"
        },
        {
            "title": "Harry Durst",
            "time": f"{WOCHENTAGE[0]} um 17:00 Uhr",
            "icon": "👤"
        },
        {
            "title": "Inolab Pforzheim 10:30",
            "time": "Juni 2.",
            "icon": "👤"
        },
        {
            "title": "Mama hab dich lieb",
            "time": "Juni 2.",
            "icon": "👪"
        },
        {
            "title": "Velly Blue meets Adstrong",
            "time": "Juni 3.",
            "icon": "👤"
        },
        {
            "title": "Hochzeit Silke Follner",
            "time": "Juni 6.",
            "icon": "🎵"
        },
        {
            "title": "TikTok at Cannes 2025",
            "time": "Juni 16.",
            "icon": "👤"
        }
    ]
    
    return example_events

def get_weather_data():
    """Ruft Wetterdaten (aktuell und Vorhersage) für Mühlacker ab."""
    try:
        API_KEY = "0a2a868ed80b8df9e7308888e0c387cf"
        city = "Mühlacker,de"
        # Verwende den Vorhersage-Endpunkt
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&lang=de&appid={API_KEY}"
        response = requests.get(url)
        data = response.json()

        # Überprüfen, ob die API-Antwort erfolgreich war
        if data['cod'] != "200":
            print(f"Fehler von OpenWeatherMap API: {data.get('message', 'Unbekannter Fehler')}")
            raise Exception("API Fehler")

        # Aktuelles Wetter (kann auch aus dem ersten Eintrag der Vorhersageliste extrahiert werden)
        current_entry = data['list'][0]
        current_weather = current_entry['main']
        current_description = current_entry['weather'][0]['description']
        wind_data = current_entry['wind']

        # Einfache Zuordnung von OpenWeatherMap-Beschreibungen zu Icons
        def map_weather_icon(description):
            desc_lower = description.lower()
            if "regen" in desc_lower or "schauer" in desc_lower:
                return "rainy"
            elif "wolken" in desc_lower or "bedeckt" in desc_lower:
                return "cloudy"
            elif "klar" in desc_lower or "sonne" in desc_lower:
                return "sunny"
            elif "schnee" in desc_lower:
                return "snowy"
            elif "gewitter" in desc_lower:
                return "stormy"
            else:
                return "cloudy" # Standard-Icon

        weather_data = {
            "current": {
                "temperature": current_weather['temp'],
                "feels_like": current_weather['feels_like'],
                "wind_speed": wind_data['speed'],
                "wind_direction": "N/A", # OpenWeatherMap gibt Windrichtung in Grad an, müsste umgerechnet werden
                "time": datetime.now().strftime("%H:%M"),
                "icon": map_weather_icon(current_description)
            },
            "forecast": []
        }

        # Verarbeitung der Vorhersagedaten (3-Stunden-Intervalle)
        forecast_list = data['list']
        daily_forecast = {}

        for entry in forecast_list:
            timestamp = entry['dt']
            forecast_time = datetime.fromtimestamp(timestamp)
            forecast_date = forecast_time.date()

            # Ignoriere den heutigen Tag für die separate Vorhersageliste, da 'current' heute abdeckt
            if forecast_date == datetime.now().date():
                 continue

            # Gruppiere Daten nach Tag
            if forecast_date not in daily_forecast:
                daily_forecast[forecast_date] = {
                    'temps': [],
                    'icons': [],
                    'day_name': ""
                }

            daily_forecast[forecast_date]['temps'].append(entry['main']['temp'])
            daily_forecast[forecast_date]['icons'].append(entry['weather'][0]['description'])

            # Wochentag für den ersten Eintrag des Tages festlegen
            if not daily_forecast[forecast_date]['day_name']:
                 # Bestimme den Anzeigenamen für den Tag (Morgen, Mo, Di, etc.)
                today = datetime.now().date()
                tomorrow = today + timedelta(days=1)

                if forecast_date == tomorrow:
                    daily_forecast[forecast_date]['day_name'] = "Morgen"
                else:
                    # Verwende die deutsche Abkürzung für den Wochentag
                    weekday_index = forecast_date.weekday()
                    daily_forecast[forecast_date]['day_name'] = WOCHENTAGE[weekday_index][:2] + "."


        # Erstelle die formatierte Vorhersageliste
        for date, data in daily_forecast.items():
            min_temp = min(data['temps']) if data['temps'] else 0
            max_temp = max(data['temps']) if data['temps'] else 0
            # Wähle ein repräsentatives Icon für den Tag (z.B. das erste des Tages oder das häufigste)
            day_icon = map_weather_icon(data['icons'][0]) if data['icons'] else "cloudy"

            weather_data['forecast'].append({
                "day": data['day_name'],
                "temp_day": round(max_temp, 1),
                "temp_night": round(min_temp, 1),
                "icon": day_icon
            })

        # Begrenze die Vorhersage auf die nächsten 5 Tage (ähnlich dem Screenshot)
        weather_data['forecast'] = weather_data['forecast'][:5]

        return weather_data

    except Exception as e:
        print(f"Fehler beim Abrufen der Wetterdaten: {e}")
        # Fallback-Daten bei Fehler
        return {
            "current": {
                "temperature": 0,
                "feels_like": 0,
                "wind_speed": 0,
                "wind_direction": "N",
                "time": "--:--",
                "icon": "cloudy"
            },
            "forecast": get_example_weather_forecast() # Fallback für Vorhersage
        }

# Neue Fallback-Funktion für die Vorhersage
def get_example_weather_forecast():
     return [
        {"day": "Heute", "temp_day": 17.3, "temp_night": 3.9, "icon": "cloudy"},
        {"day": "Morgen", "temp_day": 17.2, "temp_night": 10.2, "icon": "cloudy"},
        {"day": "Mo.", "temp_day": 18.7, "temp_night": 10.6, "icon": "cloudy"},
        {"day": "Di.", "temp_day": 16.5, "temp_night": 7.2, "icon": "cloudy"},
        {"day": "Mi.", "temp_day": 23.4, "temp_night": 9.6, "icon": "cloudy"}
    ]

def get_news_data():
    """Ruft aktuelle Nachrichten aus Deutschland ab."""
    try:
        # Deutsche Nachrichtenquellen
        news_sources = [
            "https://www.tagesschau.de/xml/rss2/",
            "https://rss.sueddeutsche.de/rss/Topthemen",
            "https://www.spiegel.de/schlagzeilen/tops/index.rss"
        ]
        
        # Versuche, Nachrichten von einer der Quellen zu erhalten
        for source_url in news_sources:
            try:
                response = requests.get(source_url)
                if response.status_code == 200:
                    # Parse XML
                    root = ET.fromstring(response.content)
                    
                    # Finde den ersten Eintrag
                    channel = root.find('channel')
                    if channel is not None:
                        item = channel.find('item')
                        if item is not None:
                            # Extrahiere Informationen
                            title = item.find('title').text if item.find('title') is not None else "Kein Titel verfügbar"
                            description = item.find('description').text if item.find('description') is not None else ""
                            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                            
                            # Berechne relative Zeit
                            time_str = "vor einer Stunde"  # Fallback
                            if pub_date:
                                try:
                                    pub_time = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                                    now = datetime.now(pub_time.tzinfo)
                                    diff = now - pub_time
                                    
                                    if diff.days > 0:
                                        time_str = f"vor {diff.days} Tagen"
                                    elif diff.seconds // 3600 > 0:
                                        hours = diff.seconds // 3600
                                        time_str = f"vor {hours} Stunde{'n' if hours > 1 else ''}"
                                    elif diff.seconds // 60 > 0:
                                        minutes = diff.seconds // 60
                                        time_str = f"vor {minutes} Minute{'n' if minutes > 1 else ''}"
                                    else:
                                        time_str = "gerade eben"
                                except:
                                    pass
                            
                            # Entferne HTML-Tags
                            description = re.sub(r'<.*?>', '', description)
                            
                            # Wenn der Inhalt zu kurz ist, verwende einen Standardtext
                            if len(description) < 50:
                                description = "Weitere Informationen sind auf der Website der Nachrichtenquelle verfügbar."
                            
                            return {
                                "source": f"{channel.find('title').text}, {time_str}",
                                "headline": title,
                                "content": description
                            }
            except Exception as e:
                print(f"Fehler beim Abrufen von {source_url}: {e}")
                continue
        
        # Fallback, wenn keine Quelle funktioniert
        return {
            "source": "Süddeutsche Zeitung, vor einer Stunde",
            "headline": "Viechtach: Söder grillt – Peta protestiert",
            "content": "Markus Söder, eingefleischter Wurstfan, lässt sich das Schweinegrillen in Viechtach nicht entgehen. Während auf dem Rost die Tiere brutzeln, gehen die Protestschilder hoch."
        }
    except Exception as e:
        print(f"Fehler beim Abrufen der Nachrichten: {e}")
        return {
            "source": "Nachrichtendienst nicht verfügbar",
            "headline": "Keine aktuellen Nachrichten",
            "content": "Derzeit können keine Nachrichten abgerufen werden. Bitte versuchen Sie es später erneut."
        }

@app.route('/')
def index():
    """Hauptroute für das Dashboard."""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API-Endpunkt, der alle Daten für das Dashboard bereitstellt."""
    now = datetime.now()
    
    data = {
        "datetime": {
            "date": format_date_german(now),
            "time": now.strftime("%H:%M"),
            "seconds": now.strftime("%S")
        },
        "calendar": get_calendar_events(),
        "weather": get_weather_data(),
        "news": get_news_data()
    }
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
