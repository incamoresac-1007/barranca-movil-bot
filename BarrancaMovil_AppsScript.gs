
/**
 * Barranca Móvil - Receptor Google Sheets
 * Deploy: Extensiones > Apps Script > Implementar > Nueva implementación > Aplicación web
 * Acceso: Cualquiera con el enlace
 */
const SHEET_NAMES = {
  servicios: 'SERVICIOS',
  identidades: 'IDENTIDADES',
  encomiendas: 'ENCOMIENDAS',
  turismo: 'TURISMO',
  conductores: 'CONDUCTORES',
  alertas: 'ALERTAS'
};

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents || '{}');
    const action = payload.action || 'upsert_servicio';
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    if (action === 'upsert_servicio') {
      upsertById_(ss.getSheetByName(SHEET_NAMES.servicios), 'ID_SERVICIO', mapServicio_(payload.data || payload));
    } else if (action === 'add_identidad') {
      appendByHeaders_(ss.getSheetByName(SHEET_NAMES.identidades), mapIdentidad_(payload.data || payload));
    } else if (action === 'upsert_encomienda') {
      upsertById_(ss.getSheetByName(SHEET_NAMES.encomiendas), 'ID_SERVICIO', mapEncomienda_(payload.data || payload));
    } else if (action === 'upsert_turismo') {
      upsertById_(ss.getSheetByName(SHEET_NAMES.turismo), 'ID_SERVICIO', mapTurismo_(payload.data || payload));
    } else if (action === 'add_alerta') {
      appendByHeaders_(ss.getSheetByName(SHEET_NAMES.alertas), mapAlerta_(payload.data || payload));
    } else if (action === 'update_conductor') {
      upsertById_(ss.getSheetByName(SHEET_NAMES.conductores), 'TELEFONO', payload.data || payload);
    } else {
      throw new Error('Acción no soportada: ' + action);
    }

    return json_({ ok: true, action, timestamp: new Date().toISOString() });
  } catch (err) {
    return json_({ ok: false, error: String(err), timestamp: new Date().toISOString() });
  }
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function headerMap_(sheet) {
  const headers = sheet.getRange(4, 1, 1, sheet.getLastColumn()).getValues()[0];
  const map = {};
  headers.forEach((h, i) => map[String(h).trim()] = i + 1);
  return map;
}

function appendByHeaders_(sheet, obj) {
  const map = headerMap_(sheet);
  const row = new Array(sheet.getLastColumn()).fill('');
  Object.keys(obj).forEach(k => {
    if (map[k]) row[map[k] - 1] = obj[k];
  });
  sheet.appendRow(row);
}

function upsertById_(sheet, idHeader, obj) {
  const map = headerMap_(sheet);
  const idCol = map[idHeader];
  if (!idCol) throw new Error('No existe columna ID: ' + idHeader);

  const id = obj[idHeader];
  if (!id) throw new Error('Falta ' + idHeader);

  const last = sheet.getLastRow();
  let rowIndex = -1;

  if (last >= 5) {
    const ids = sheet.getRange(5, idCol, last - 4, 1).getValues().flat();
    const pos = ids.findIndex(x => String(x) === String(id));
    if (pos >= 0) rowIndex = pos + 5;
  }

  if (rowIndex < 0) {
    appendByHeaders_(sheet, obj);
  } else {
    Object.keys(obj).forEach(k => {
      if (map[k]) sheet.getRange(rowIndex, map[k]).setValue(obj[k]);
    });
  }
}

function mapServicio_(d) {
  return {
    ID_SERVICIO: d.id_servicio || d.ID_SERVICIO,
    FECHA: d.fecha || new Date(),
    HORA: d.hora || Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'HH:mm'),
    ESTADO: d.estado || '',
    TIPO_SERVICIO: d.tipo_servicio || d.tipo || '',
    CANAL: d.canal || '',
    CLIENTE: d.cliente || d.nombre || '',
    TELEFONO: d.telefono || '',
    DNI_CLIENTE: d.dni_cliente || '',
    ORIGEN: d.origen || d.recojo || '',
    DESTINO: d.destino || '',
    REFERENCIA_ORIGEN: d.referencia_origen || '',
    REFERENCIA_DESTINO: d.referencia_destino || '',
    RUTA: d.ruta || '',
    CONDUCTOR: d.conductor || '',
    PLACA: d.placa || '',
    TELEFONO_CONDUCTOR: d.telefono_conductor || '',
    PAGO: d.pago || '',
    TARIFA: d.tarifa || '',
    PRIORIDAD: d.prioridad || '',
    ALERTA: d.alerta || '',
    OBSERVACION: d.observacion || '',
    ULTIMA_ACTUALIZACION: new Date(),
    HORA_CONFIRMACION: d.hora_confirmacion || '',
    HORA_ASIGNACION: d.hora_asignacion || '',
    MINUTOS_ESPERA: d.minutos_espera || ''
  };
}

function mapIdentidad_(d) {
  return {
    ID_SERVICIO: d.id_servicio || '',
    TIPO_SERVICIO: d.tipo_servicio || '',
    ROL: d.rol || '',
    NOMBRE: d.nombre || '',
    DNI: d.dni || '',
    TELEFONO: d.telefono || '',
    VALIDADO: d.validado || 'PENDIENTE',
    OBSERVACION: d.observacion || '',
    FECHA_REGISTRO: new Date(),
    CANAL_ORIGEN: d.canal || ''
  };
}

function mapEncomienda_(d) {
  return {
    ID_SERVICIO: d.id_servicio || '',
    DESCRIPCION: d.descripcion || '',
    CANTIDAD_BULTOS: d.cantidad_bultos || '',
    TIPO_CARGA: d.tipo_carga || '',
    PESO_UNITARIO_KG: d.peso_unitario_kg || '',
    PESO_TOTAL_KG: d.peso_total_kg || '',
    FOTO_RECIBIDA: d.foto_recibida || '',
    RIESGO: d.riesgo || '',
    CUIDADO_ESPECIAL: d.cuidado_especial || '',
    VALIDACION_OPERADOR: d.validacion_operador || '',
    DESTINATARIO: d.destinatario || '',
    DNI_DESTINATARIO: d.dni_destinatario || '',
    OBSERVACION: d.observacion || '',
    ULTIMA_ACTUALIZACION: new Date()
  };
}

function mapTurismo_(d) {
  return {
    ID_SERVICIO: d.id_servicio || '',
    DESTINO_TURISTICO: d.destino_turistico || d.destino || '',
    MODALIDAD: d.modalidad || '',
    FECHA_TOUR: d.fecha_tour || d.fecha || '',
    HORA_RECOJO: d.hora_recojo || '',
    CANTIDAD_PERSONAS: d.cantidad_personas || d.personas || '',
    TIPO_GRUPO: d.tipo_grupo || '',
    PASAJEROS_RESUMEN: d.pasajeros_resumen || '',
    DNI_COMPLETO: d.dni_completo || '',
    PRECIO_REFERENCIAL: d.precio_referencial || '',
    NOTA_RUTA: d.nota_ruta || '',
    CONDUCTOR: d.conductor || '',
    PLACA: d.placa || '',
    ESTADO: d.estado || '',
    OBSERVACION: d.observacion || ''
  };
}

function mapAlerta_(d) {
  return {
    ID_ALERTA: d.id_alerta || ('AL-' + Date.now()),
    ID_SERVICIO: d.id_servicio || '',
    FECHA_HORA: new Date(),
    TIPO_ALERTA: d.tipo_alerta || '',
    PRIORIDAD: d.prioridad || 'MEDIA',
    DESCRIPCION: d.descripcion || '',
    REQUIERE_ACCION: d.requiere_accion || 'SI',
    ESTADO_ALERTA: d.estado_alerta || 'ABIERTA',
    RESPONSABLE: d.responsable || 'Operador',
    CIERRE: ''
  };
}
