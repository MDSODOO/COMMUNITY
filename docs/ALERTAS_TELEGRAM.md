# Alertas del servidor → grupo de Telegram

Sistema de notificaciones del healthcheck de `ionos` hacia un grupo de Telegram con
todos los involucrados en el proyecto.

**Estado:** el script ya está desplegado y funcionando. **Falta solo poner las
credenciales del bot** (§2). Mientras estén vacías el healthcheck corre igual,
solo que no notifica a nadie.

---

## 1. Qué vigila y cuándo avisa

`scripts/healthcheck.sh` corre **cada 5 minutos** por cron
(`/etc/cron.d/medicinedepot-healthcheck`) y comprueba:

| Check | Se considera sano si… |
|---|---|
| Odoo Dev | `localhost:8069/web/health` → 200 |
| Odoo Test | `localhost:8070/web/health` → 200 |
| Caddy | `localhost:80` → **200 o 308** (el 308 es el redirect a HTTPS, es lo correcto) |
| **Sitio público (HTTPS)** | `https://odoo.bodegademedicamentos.com/web/health` → 200 |
| **Ollama (IA local)** | `100.84.63.23:11434/api/version` → 200 |
| Contenedores (5) | estado `running` |
| Disco | uso ≤ 85% |
| Memoria | uso ≤ 85% |

### Cómo notifica (importante para un grupo con varias personas)

Avisa **solo cuando cambia el estado**, no en cada ciclo:

- 🔴 **FALLO** — la primera vez que algo se cae.
- 🔴 **SIGUE CAÍDO** — recordatorio cada ~65 min mientras siga mal.
- ✅ **RECUPERADO** — cuando vuelve a estar bien.

> **Por qué así:** con 5 min de intervalo, una caída de 3 horas serían 36 mensajes
> idénticos. En un grupo con varias personas eso termina en que todos lo silencian,
> y entonces las alertas no sirven para nada. El estado se guarda en
> `/var/lib/medicinedepot-healthcheck/`.

### Dos correcciones aplicadas al montar esto

1. **Caddy generaba una falsa alarma permanente.** El script exigía HTTP 200, pero
   Caddy responde **308** (redirige a HTTPS), que es su comportamiento sano. Llevaba
   **623 alertas falsas** acumuladas en el log, una cada 5 minutos desde que se
   instaló, sin que nadie las viera. De haber activado Telegram sin corregirlo, el
   grupo habría arrancado con spam permanente desde el primer minuto.
2. **Se añadió el check de Ollama**, que no existía. Su ausencia es la razón de que
   la caída del pipeline de visión del 2026-07-31 pasara inadvertida.

---

## 2. Configuración (esto lo haces tú — requiere tu cuenta de Telegram)

### 2.1 Crear el bot

1. En Telegram, habla con **[@BotFather](https://t.me/BotFather)**.
2. `/newbot` → te pide un nombre y un usuario (debe terminar en `bot`,
   p. ej. `medicinedepot_alertas_bot`).
3. Te devuelve un **token** con esta forma: `123456789:AAH...`. Guárdalo, es secreto.

### 2.2 Crear el grupo y meter al bot

1. Crea un grupo en Telegram con las personas del proyecto.
2. Añade el bot al grupo como miembro.
3. **Escribe en el grupo el mensaje `/start@tu_bot`** (con el `@` del bot).

   > **Ojo — el fallo más común:** los bots tienen *privacy mode* activo por
   > defecto y **solo ven los mensajes que los mencionan o son comandos**. Si
   > escribes un "hola" normal, el bot no lo ve y el paso siguiente devuelve vacío.

### 2.3 Obtener el ID del grupo

Con tu token, ejecuta:

```bash
curl -s "https://api.telegram.org/bot<TU_TOKEN>/getUpdates" | grep -o '"chat":{"id":[-0-9]*' | head
```

Busca el número que empieza con **guion** (los grupos son negativos, típicamente
`-100...`). Ese es tu `TELEGRAM_CHAT_ID`.

### 2.4 Guardar las credenciales

Se guardan **fuera del repo**, en `/etc/medicinedepot/alerts.env` (permisos `600`,
solo root). El archivo ya existe con los campos vacíos:

```bash
ssh ionos "sed -i 's|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=\"123456789:AAH...\"|; \
                   s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=\"-1001234567890\"|' \
           /etc/medicinedepot/alerts.env"
```

> 🔒 **El token nunca va al repo.** Por eso vive en `/etc/`, no en
> `/opt/medicinedepot-odoo19-migration/`. Si alguna vez se filtra, revócalo en
> @BotFather con `/revoke`.

### 2.5 Probar

```bash
# Mensaje de prueba directo
ssh ionos '. /etc/medicinedepot/alerts.env && curl -s -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" -d "text=Prueba de alertas MedicineDepot ✅"'

# Simular una caída real: fuerza el estado a FALLO y corre el healthcheck
ssh ionos 'echo "FAIL 0" > /var/lib/medicinedepot-healthcheck/endpoint_Odoo_Dev && \
           /opt/medicinedepot-odoo19-migration/scripts/healthcheck.sh'
# Debe llegar un mensaje de RECUPERADO al grupo.
```

---

## 3. Mantenimiento

- **Ver el log completo:** `tail -f /var/log/medicinedepot-healthcheck.log`
- **Reiniciar el estado de alertas** (p. ej. tras mantenimiento planificado):
  `rm -f /var/lib/medicinedepot-healthcheck/*`
- **Silenciar temporalmente** (ventana de mantenimiento): vaciar `TELEGRAM_CHAT_ID`
  en `/etc/medicinedepot/alerts.env`; el healthcheck sigue registrando en el log.
- **Cambiar la frecuencia del recordatorio:** `REPEAT_AFTER_CYCLES` en el script
  (12 = un recordatorio cada ~65 min).
- **Respaldo del script anterior:** `/root/config-backups/healthcheck.sh.orig-20260731`

### Cosas que pueden romperlo

- **Si el grupo pasa a supergrupo**, el `chat_id` **cambia**. Habría que repetir §2.3.
  Síntoma: dejan de llegar mensajes sin ningún error visible.
- **Si sacas al bot del grupo**, la API responde error y el script lo ignora en
  silencio (`|| true`, para que un fallo de Telegram nunca tumbe el healthcheck).
  Conviene probar con §2.5 después de cualquier cambio en el grupo.
- **El script no está versionado en git todavía** (aparece como `??` en
  `git status`). Entra en el lote de rescate a git pendiente.
