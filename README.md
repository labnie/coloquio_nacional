# Redes Radiales Normalistas

Visor interactivo y formulario de registro para el Coloquio Nacional de
Experiencias Radiales en comunidades normalistas.

## Estructura del proyecto

```
mapa_experiencias_radiales.html   ← el mapa (ábrelo directo en el navegador)
formulario_registro.html          ← formulario de registro (vista previa de diseño)
catalogo_escuelas.csv             ← las 259 escuelas normales con su Clave DGES,
                                     para que los normalistas encuentren su clave
actualizar_desde_formulario.py    ← integra respuestas del Google Form a los datos
regenerar_mapa.py                 ← vuelve a embeber los datos actualizados en el mapa
data/                             ← datos fuente (GeoJSON) — no se editan a mano
```

Ambos archivos HTML son autónomos: no dependen de ninguna carpeta extra
(css/js/imágenes), solo cargan Leaflet y las fuentes desde internet (CDN).
Para publicarlos basta con subir estos archivos tal cual a la raíz de tu
repositorio de GitHub Pages.

## 1. Publicar en GitHub Pages

1. Crea un repositorio nuevo en GitHub.
2. Sube todo el contenido de esta carpeta a la raíz del repositorio.
3. En **Settings → Pages**, elige la rama `main` y la carpeta `/ (root)`.
4. Tu sitio quedará en `https://TU-USUARIO.github.io/TU-REPO/mapa_experiencias_radiales.html`
   (o renombra ese archivo a `index.html` para que cargue directo en la raíz).

## 2. Formulario para que los normalistas alimenten el mapa

El mapa ya incluye un botón "Registra la experiencia radial de tu escuela"
que enlaza a `formulario_registro.html`. Ese archivo es por ahora una
vista previa de diseño — para que envíe datos de verdad, sigue estos pasos:

### 2.1 Crear el Google Form

Crea un formulario de Google con estas preguntas exactas (los nombres deben
coincidir con lo que espera el script; puedes cambiarlos, pero entonces
ajusta CSV_COLUMNS al inicio de actualizar_desde_formulario.py):

| Pregunta del formulario | Tipo         | Notas |
|---|---|---|
| Clave_DGES        | Texto corto | Deben buscar su clave en catalogo_escuelas.csv (259 escuelas) |
| Nombre_programa   | Texto corto | Nombre del programa/podcast de radio |
| Contacto          | Texto corto | Nombre de quien reporta |
| Correo_e          | Texto corto | Opcional |
| Enlaces           | Párrafo     | Uno o varios enlaces separados por " \| ", ej: "Spotify: https://... \| YouTube: https://..." |

En el formulario, ve a Respuestas → ícono de Sheets para crear la hoja de
cálculo que recibirá las respuestas. También puedes activar
Respuestas → ⋮ → "Recibir notificaciones por correo de nuevas respuestas"
para que te avisen a tu correo en cada envío.

Comparte catalogo_escuelas.csv con los normalistas para que encuentren su
clave DGES antes de llenar el formulario.

### 2.2 Revisar e integrar las respuestas

1. En la Google Sheet de respuestas: Archivo → Descargar → Valores separados por comas (.csv).
2. Guarda ese archivo como respuestas_formulario.csv en esta misma carpeta.
3. Corre:
   ```
   python3 actualizar_desde_formulario.py
   ```
   Esto actualiza data/Experiencias_radiales_DGESUM_2.js — te dice cuántas
   experiencias son nuevas, cuántas se actualizaron, y qué claves no
   encontró (revísalas a mano).
4. Corre:
   ```
   python3 regenerar_mapa.py
   ```
   Esto vuelve a incrustar los datos actualizados dentro de
   mapa_experiencias_radiales.html (el mapa no lee data/ en vivo, así que
   este paso es necesario para que los cambios se vean).
5. Sube los cambios (git push) para publicarlos.

Reglas del script actualizar_desde_formulario.py:
- Si la escuela ya tenía una experiencia registrada, el nuevo programa,
  contacto y enlaces se agregan a lo existente (no se borra nada).
- Si la escuela no tenía experiencia registrada pero sí existe en las 259
  normales del catálogo, se crea un punto nuevo usando su ubicación real.
- Si la clave no existe en el catálogo, la respuesta se ignora y se
  reporta para que la revises.

## 3. Conectar el formulario con diseño propio (formulario_registro.html)

Este formulario ya está preparado para enviar datos reales a una Google
Sheet mediante Google Apps Script (que además puede notificarte por
correo en cada envío, sin depender de servicios externos).

1. Abre `apps_script_backend.gs` — trae las instrucciones completas paso a
   paso dentro del propio archivo (crear la Sheet, pegar el código en
   Apps Script, poner tu correo, desplegar como aplicación web).
2. Al terminar el despliegue, copia la URL que termina en `/exec`.
3. Abre `formulario_registro.html`, busca la línea:
   ```
   const APPS_SCRIPT_URL = 'PEGA_AQUI_TU_URL_DE_APPS_SCRIPT';
   ```
   y reemplázala con tu URL real.
4. Sube el cambio (`git push`). Ya podrás recibir registros reales,
   guardados en tu Google Sheet y notificados a tu correo.

Si prefieres usar el Google Form simple en su lugar (sin este formulario
con diseño propio), sigue la sección 2 de este README.
