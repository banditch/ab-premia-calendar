# AB Premià Calendar

Calendarios iCalendar suscribibles para los equipos de Agrupació Bàsquet Premià.

## Estado

El generador, la web y la automatización de GitHub Actions están preparados. Para obtener datos reales falta configurar el endpoint público de horarios utilizado por la aplicación oficial de Bàsquet Català.

## Cómo funciona

1. `src/generate.py` lee partidos normalizados desde `data/matches.json` o desde `DATA_URL`.
2. Genera un archivo `.ics` estable por equipo dentro de `docs/calendars/`.
3. Genera `docs/calendars/index.json` para alimentar el selector web.
4. GitHub Actions ejecuta el proceso cada hora y publica GitHub Pages.

## Formato de entrada

```json
[
  {
    "id": "partido-123",
    "date": "2026-09-12",
    "time": "10:45",
    "home_team": "AB PREMIÀ BLAU",
    "away_team": "CB EXEMPLE",
    "home_team_id": "ab-premia-blau",
    "away_team_id": "cb-exemple",
    "category": "MINI MASCULÍ",
    "venue": "PAV. MUNICIPAL PREMIÀ DE MAR",
    "address": "Camí del Mig, 62",
    "status": "scheduled"
  }
]
```

Los equipos del club se detectan mediante `config/settings.json`. Si la API devuelve identificadores estables, añade sus identificadores a `club_team_ids`.

## Configuración de la fuente

Cuando se identifique el endpoint público de la app:

1. Guarda su URL como secreto de Actions llamado `DATA_URL`.
2. Si su JSON no coincide con el formato anterior, adapta únicamente `normalize_payload()` en `src/generate.py`.
3. Ejecuta manualmente el workflow **Actualizar calendarios**.

No guardes tokens personales ni credenciales de usuario en el repositorio.

## Publicar la web

En GitHub abre **Settings → Pages → Build and deployment → GitHub Actions**. El workflow **Publicar GitHub Pages** desplegará el selector.

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
