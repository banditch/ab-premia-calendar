# AB Premià Calendar

Calendarios iCalendar suscribibles para los equipos de Agrupació Bàsquet Premià.

## Estado

El proyecto está conectado a los servicios públicos utilizados por la aplicación oficial de Bàsquet Català. No necesita tokens personales ni secretos.

## Cómo funciona

1. Obtiene la configuración pública actual de la app oficial.
2. Consulta los equipos del club `16`.
3. Consulta el calendario completo de cada `idSignedTeam`.
4. Genera un archivo `.ics` por equipo en `docs/calendars/`.
5. GitHub Actions actualiza los calendarios cada hora.
6. GitHub Pages publica el selector para Apple Calendar y Google Calendar.

Los nombres de archivo se basan en categoría y código de equipo, no en el identificador anual, para que las suscripciones puedan mantenerse entre temporadas.

## Activación

1. Abre **Settings → Actions → General → Workflow permissions**.
2. Selecciona **Read and write permissions** y guarda.
3. Abre **Settings → Pages → Build and deployment**.
4. Selecciona **GitHub Actions** como fuente.
5. Ejecuta manualmente **Actualizar calendarios**.
6. Ejecuta manualmente **Publicar GitHub Pages** si no se inicia automáticamente.

La página estará disponible en:

https://banditch.github.io/ab-premia-calendar/

Cada calendario tendrá una URL permanente:

```
https://banditch.github.io/ab-premia-calendar/calendars/<equipo>.ics
```

## Ejecución local

```bash
python src/generate.py
python -m http.server 8000 --directory docs
```

Abre http://localhost:8000.

## Privacidad

El proyecto consulta únicamente los endpoints públicos de clubes, equipos y partidos utilizados por la app oficial. No almacena credenciales, convocatorias ni datos personales.
