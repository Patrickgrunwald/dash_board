// Aktuelles Datum und Uhrzeit anzeigen
function updateDateTime() {
    const now = new Date();
    
    // Datum formatieren
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const dateStr = now.toLocaleDateString('de-DE', options);
    
    // Zeit formatieren
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    
    // DOM aktualisieren
    document.getElementById('current-date').textContent = dateStr;
    document.getElementById('current-time').textContent = `${hours}:${minutes}`;
    document.getElementById('current-seconds').textContent = seconds;
}

// Wetter-Icons erstellen
function createWeatherIcon(type, container) {
    let iconSvg = '';
    
    switch(type) {
        case 'sunny':
            iconSvg = '<svg viewBox="0 0 24 24" class="sunny-icon"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
            break;
        case 'cloudy':
            iconSvg = '<svg viewBox="0 0 24 24" class="cloudy-icon"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>';
            break;
        case 'rainy':
            iconSvg = '<svg viewBox="0 0 24 24" class="rainy-icon"><path d="M16 13v8"/><path d="M8 13v8"/><path d="M12 15v8"/><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/></svg>';
            break;
        default:
            iconSvg = '<svg viewBox="0 0 24 24" class="cloudy-icon"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>';
    }
    
    container.innerHTML = iconSvg;
}

// Kalendereinträge anzeigen
function displayCalendarEntries(entries) {
    const container = document.getElementById('calendar-entries');
    container.innerHTML = '';
    
    entries.forEach(entry => {
        const entryDiv = document.createElement('div');
        entryDiv.className = 'calendar-entry';
        
        entryDiv.innerHTML = `
            <div class="calendar-entry-icon">${entry.icon}</div>
            <div class="calendar-entry-content">
                <div class="calendar-entry-title">${entry.title}</div>
                <div class="calendar-entry-time">${entry.time}</div>
            </div>
        `;
        
        container.appendChild(entryDiv);
    });
}

// Wetterdaten anzeigen
function displayWeatherData(weather) {
    // Aktuelles Wetter
    document.getElementById('wind-value').textContent = weather.current.wind_speed;
    document.getElementById('weather-time').textContent = weather.current.time;
    document.getElementById('temp-value').textContent = weather.current.temperature;
    document.getElementById('feels-like').textContent = `Gefühlt ${weather.current.feels_like}°`;
    
    // Wetter-Icon
    createWeatherIcon(weather.current.icon, document.getElementById('weather-icon'));
    
    // Wettervorhersage
    const forecastDays = document.querySelectorAll('.forecast-day');
    
    weather.forecast.forEach((forecast, index) => {
        if (index < forecastDays.length) {
            const dayElement = forecastDays[index];
            
            dayElement.querySelector('.day-name').textContent = forecast.day;
            createWeatherIcon(forecast.icon, dayElement.querySelector('.day-icon'));
            dayElement.querySelector('.day-temp').textContent = `${forecast.temp_day}°`;
            dayElement.querySelector('.night-temp').textContent = `${forecast.temp_night}°`;
        }
    });
}

// Nachrichtendaten anzeigen
function displayNewsData(news) {
    document.getElementById('news-source').textContent = news.source;
    document.getElementById('news-headline').textContent = news.headline;
    document.getElementById('news-content').textContent = news.content;
}

// Daten vom Server abrufen
function fetchDashboardData() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            // Datum und Uhrzeit aktualisieren
            document.getElementById('current-date').textContent = data.datetime.date;
            document.getElementById('current-time').textContent = data.datetime.time;
            document.getElementById('current-seconds').textContent = data.datetime.seconds;
            
            // Kalendereinträge anzeigen
            displayCalendarEntries(data.calendar);
            
            // Wetterdaten anzeigen
            displayWeatherData(data.weather);
            
            // Nachrichtendaten anzeigen
            displayNewsData(data.news);
        })
        .catch(error => {
            console.error('Fehler beim Abrufen der Daten:', error);
        });
}

// Seite alle 5 Minuten neu laden
function setupAutoRefresh() {
    // Seite alle 5 Minuten neu laden
    setTimeout(() => {
        window.location.reload();
    }, 5 * 60 * 1000); // 5 Minuten in Millisekunden
}

// Initialisierung
document.addEventListener('DOMContentLoaded', () => {
    // Initiale Anzeige der Uhrzeit
    updateDateTime();
    
    // Uhrzeit jede Sekunde aktualisieren
    setInterval(updateDateTime, 1000);
    
    // Daten vom Server abrufen
    fetchDashboardData();
    
    // Daten alle 30 Sekunden aktualisieren (ohne Neuladen der Seite)
    setInterval(fetchDashboardData, 30 * 1000);
    
    // Seite alle 5 Minuten neu laden
    setupAutoRefresh();
});
