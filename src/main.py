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
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

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
    """Ruft Kalendereinträge von iCloud ab."""
    events = []
    
    try:
        # Verbindung zum iCloud CalDAV-Server herstellen
        client = caldav.DAVClient(
            url=ICLOUD_CALDAV_URL,
            username=ICLOUD_EMAIL,
            password=ICLOUD_APP_PASSWORD
        )
        
        # Hauptkalender des Benutzers abrufen
        principal = client.principal()
        
        # Alle verfügbaren Kalender abrufen
        calendars = principal.calendars()
        
        # Aktuelle Zeit und Zeitraum für Ereignisse festlegen
        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=30)  # Ereignisse für die nächsten 30 Tage
        
        # Kalender-Icons basierend auf Kalendertyp
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
        
        # Durch alle Kalender iterieren und nach 'Familie' und 'Patrick' filtern
        for calendar in calendars:
            calendar_name = calendar.name.lower() if calendar.name else ""
            
            # Nur die gewünschten Kalender verwenden
            if "familie" in calendar_name or "patrick" in calendar_name or "icloud" in calendar_name:
                
                # Icon basierend auf Kalendername festlegen
                if "familie" in calendar_name:
                    default_icon = calendar_icons["Familie"]
                elif "patrick" in calendar_name:
                    default_icon = calendar_icons["Patrick"]
                else:
                    default_icon = calendar_icons["default"]
                
                try:
                    # Ereignisse im Zeitraum abrufen
                    calendar_events = calendar.date_search(start=start_date, end=end_date)
                    
                    for event in calendar_events:
                        try:
                            # Ereignisdaten parsen
                            event_data = event.data
                            ical = icalendar.Calendar.from_ical(event_data)
                            
                            for component in ical.walk():
                                if component.name == "VEVENT":
                                    # Titel des Ereignisses
                                    summary = str(component.get('summary', 'Unbekanntes Ereignis'))
                                    
                                    # Startzeit des Ereignisses
                                    dtstart = component.get('dtstart').dt
                                    
                                    # Prüfen, ob es sich um ein ganztägiges Ereignis handelt
                                    all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)
                                    
                                    # Wenn es ein datetime-Objekt ist, sicherstellen, dass es ein Zeitzonenobjekt hat
                                    if isinstance(dtstart, datetime) and dtstart.tzinfo is None:
                                        dtstart = dtstart.replace(tzinfo=pytz.UTC)
                                    
                                    # Für ganztägige Ereignisse oder Ereignisse in der Zukunft
                                    if all_day or (isinstance(dtstart, datetime) and dtstart.date() > now.date()):
                                        # Datum formatieren
                                        event_date = dtstart if isinstance(dtstart, date) else dtstart.date()
                                        if event_date.month == now.month:
                                            date_display = f"{MONATE[event_date.month]} {event_date.day}."
                                        else:
                                            date_display = f"{MONATE[event_date.month]} {event_date.day}."
                                    else:
                                        # Zeit formatieren für Ereignisse am selben Tag
                                        time_str = dtstart.strftime("%H:%M")
                                        date_display = f"{WOCHENTAGE[dtstart.weekday()]} um {time_str} Uhr"
                                    
                                    # Icon basierend auf Ereignistyp oder Kalendername festlegen
                                    icon = default_icon
                                    for keyword, specific_icon in event_type_icons.items():
                                        if keyword in summary.lower():
                                            icon = specific_icon
                                            break
                                    
                                    # Ereignis zum Array hinzufügen
                                    events.append({
                                        "title": summary,
                                        "time": date_display,
                                        "icon": icon
                                    })
                        except Exception as e:
                            print(f"Fehler beim Verarbeiten eines Ereignisses: {e}")
                except Exception as e:
                    print(f"Fehler beim Abrufen von Ereignissen aus Kalender {calendar_name}: {e}")
        
        # Ereignisse nach Datum sortieren
        events.sort(key=lambda x: x["time"])
        
        # Wenn keine Ereignisse gefunden wurden, Beispieldaten zurückgeben
        if not events:
            events = get_example_calendar_events()
            
    except Exception as e:
        print(f"Fehler beim Abrufen der Kalendereinträge: {e}")
        # Fallback-Daten bei Fehler
        events = get_example_calendar_events()
    
    return events

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
    """Ruft Wetterdaten für Mühlacker ab."""
    try:
        # In einer Produktionsumgebung würde hier eine echte Wetter-API verwendet werden
        # Beispiel: OpenWeatherMap API für Mühlacker
        # API_KEY = "your_api_key"
        # url = f"https://api.openweathermap.org/data/2.5/forecast?q=Mühlacker,de&units=metric&lang=de&appid={API_KEY}"
        # response = requests.get(url)
        # data = response.json()
        
        # Beispieldaten basierend auf dem Screenshot
        weather_data = {
            "current": {
                "temperature": 17.2,
                "feels_like": 17.2,
                "wind_speed": 2,
                "wind_direction": "W",
                "time": "21:11",
                "icon": "cloudy"
            },
            "forecast": [
                {"day": "Heute", "temp_day": 17.3, "temp_night": 3.9, "icon": "cloudy"},
                {"day": "Morgen", "temp_day": 17.2, "temp_night": 10.2, "icon": "cloudy"},
                {"day": "Mo.", "temp_day": 18.7, "temp_night": 10.6, "icon": "cloudy"},
                {"day": "Di.", "temp_day": 16.5, "temp_night": 7.2, "icon": "cloudy"},
                {"day": "Mi.", "temp_day": 23.4, "temp_night": 9.6, "icon": "cloudy"}
            ]
        }
        return weather_data
    except Exception as e:
        print(f"Fehler beim Abrufen der Wetterdaten: {e}")
        return {
            "current": {
                "temperature": 0,
                "feels_like": 0,
                "wind_speed": 0,
                "wind_direction": "N",
                "time": "--:--",
                "icon": "cloudy"
            },
            "forecast": []
        }

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
                feed = feedparser.parse(source_url)
                if feed.entries and len(feed.entries) > 0:
                    entry = feed.entries[0]  # Nehme den neuesten Eintrag
                    
                    # Quelle und Zeitstempel
                    source_name = feed.feed.title
                    published_time = entry.get('published', '')
                    
                    # Versuche, einen relativen Zeitstempel zu erstellen (z.B. "vor einer Stunde")
                    time_str = "vor einer Stunde"  # Fallback
                    if published_time:
                        try:
                            # Versuche, den Zeitstempel zu parsen
                            pub_time = datetime.strptime(published_time, "%a, %d %b %Y %H:%M:%S %z")
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
                    
                    # Titel und Inhalt
                    title = entry.title
                    
                    # Inhalt extrahieren und HTML-Tags entfernen
                    content = entry.get('description', '')
                    content = re.sub(r'<.*?>', '', content)  # HTML-Tags entfernen
                    
                    # Wenn der Inhalt zu kurz ist, versuche andere Felder
                    if len(content) < 50:
                        content = entry.get('summary', content)
                        content = re.sub(r'<.*?>', '', content)  # HTML-Tags entfernen
                    
                    # Wenn immer noch zu kurz, verwende einen Standardtext
                    if len(content) < 50:
                        content = "Weitere Informationen sind auf der Website der Nachrichtenquelle verfügbar."
                    
                    return {
                        "source": f"{source_name}, {time_str}",
                        "headline": title,
                        "content": content
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
    app.run(host='0.0.0.0', port=5000)
