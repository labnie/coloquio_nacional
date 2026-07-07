/**
 * Código de Google Apps Script para recibir los registros del formulario
 * (formulario_registro.html) y guardarlos en una Google Sheet, además de
 * mandarte un correo de notificación por cada envío.
 *
 * ─────────────────────────────────────────────────────────────
 * CÓMO CONFIGURARLO (una sola vez):
 * ─────────────────────────────────────────────────────────────
 * 1. Crea una Google Sheet nueva (sheets.google.com → En blanco).
 *    En la fila 1, agrega estos encabezados (opcional pero recomendado):
 *    Fecha | Clave_DGES | Escuela | Estado | Programa | Contacto | Correo | Enlaces
 *
 * 2. En esa misma Sheet: Extensiones → Apps Script.
 *
 * 3. Borra el contenido de "Code.gs" y pega TODO este archivo.
 *
 * 4. Reemplaza la línea que dice:
 *        var CORREO_NOTIFICACION = 'tpineda.labnie@normales.mx';
 *    con tu correo real.
 *
 * 5. Guarda (ícono de disquete o Ctrl+S).
 *
 * 6. Haz clic en "Desplegar" (Deploy) → "Nueva implementación" (New deployment).
 *    - Tipo: "Aplicación web" (Web app)
 *    - Ejecutar como: "Yo" (tu cuenta)
 *    - Quién tiene acceso: "Cualquier usuario" (Anyone)
 *    - Haz clic en "Desplegar". Google te pedirá autorizar permisos —
 *      es normal que aparezca una pantalla de advertencia ("Google no ha
 *      verificado esta app"); haz clic en "Configuración avanzada" →
 *      "Ir a [nombre del proyecto] (no seguro)" → "Permitir". Es tu propio
 *      script, así que es seguro autorizarlo.
 *
 * 7. Copia la URL que termina en "/exec" que te da al desplegar.
 *
 * 8. Pega esa URL en formulario_registro.html, en la constante
 *    APPS_SCRIPT_URL (al inicio del <script>).
 *
 * 9. Si más adelante actualizas este código, tienes que volver a
 *    "Desplegar" → "Gestionar implementaciones" → editar (ícono de lápiz)
 *    → "Nueva versión" → Desplegar, para que los cambios surtan efecto.
 * ─────────────────────────────────────────────────────────────
 */

var CORREO_NOTIFICACION = 'tpineda.labnie@normales.mx';

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var params = e.parameter;

    var clave = params.clave || '';
    var escuela = params.escuela || '';
    var estado = params.estado || '';
    var programa = params.programa || '';
    var contacto = params.contacto || '';
    var correo = params.correo || '';
    var enlaces = params.enlaces || '';

    sheet.appendRow([new Date(), clave, escuela, estado, programa, contacto, correo, enlaces]);

    if (CORREO_NOTIFICACION && CORREO_NOTIFICACION.indexOf('@') > -1) {
      var asunto = 'Nuevo registro de experiencia radial: ' + escuela;
      var cuerpo =
        'Se recibió un nuevo registro en el mapa de Redes Radiales Normalistas.\n\n' +
        'Escuela: ' + escuela + ' (' + clave + ')\n' +
        'Estado: ' + estado + '\n' +
        'Programa: ' + programa + '\n' +
        'Contacto: ' + contacto + '\n' +
        'Correo: ' + correo + '\n' +
        'Enlaces: ' + enlaces + '\n\n' +
        'Revisa la hoja de cálculo para ver todos los registros.';
      MailApp.sendEmail(CORREO_NOTIFICACION, asunto, cuerpo);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'ok' }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Función de prueba: selecciónala en el menú desplegable de arriba (junto
 * al botón ▶) y haz clic en "Ejecutar" para simular un envío de prueba sin
 * necesidad del formulario real. Revisa la hoja y tu correo después.
 */
function pruebaManual() {
  var fakeEvent = {
    parameter: {
      clave: 'test01',
      escuela: 'Escuela de Prueba',
      estado: 'Estado de Prueba',
      programa: 'Programa de Prueba',
      contacto: 'Alguien probando',
      correo: 'prueba@ejemplo.com',
      enlaces: 'Spotify: https://open.spotify.com/show/prueba'
    }
  };
  doPost(fakeEvent);
}
