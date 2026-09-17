function doPost(e) {
  // 1. ACTIVAR EL CANDADO (Evita que dos personas entren al mismo tiempo)
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000); // Espera hasta 15 segundos si el servidor está ocupado
  } catch (err) {
    return ContentService.createTextOutput("Error: Servidor ocupado").setMimeType(ContentService.MimeType.TEXT);
  }

  try {
    var params = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    if (params.action == 'save_entry') {
      var stateSheet = ss.getSheetByName(params.env == "Producción" ? "State" : "State_Test");
      var dataSheet = ss.getSheetByName(params.sheet);

      if (!stateSheet) {
        return ContentService.createTextOutput(JSON.stringify({
          status: "ERROR",
          error: "No se encontro la hoja de estado buscada: '" + (params.env == "Producción" ? "State" : "State_Test") + "'"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      if (!dataSheet) {
        return ContentService.createTextOutput(JSON.stringify({
          status: "ERROR",
          error: "No se encontro la hoja de datos buscada: '" + params.sheet + "'",
          hojas_disponibles: ss.getSheets().map(function(s){ return s.getName(); })
        })).setMimeType(ContentService.MimeType.JSON);
      }

      // Calcular (sin confirmar todavia) cual seria el proximo numero
      var lastNum = parseInt(stateSheet.getRange(2, 1).getValue()) + 1;
      var lastRec = parseInt(stateSheet.getRange(2, 2).getValue()) + 1;
      var currentYear = new Date().getFullYear() % 100;
      var an = ("0000" + lastNum).slice(-4) + "/" + currentYear;

      var row = params.row;
      row[3] = an;       // Número de Análisis (índice 3)
      row[17] = lastRec; // Nº de Recepción real (índice 17)

      // IMPORTANTE: primero guardamos la fila. Recien si esto no tira error
      // confirmamos el numero en la hoja State. Asi, si algo falla ac
      // (se corta la conexion, error de Google, etc.), el numero NO se
      // consume y el proximo intento reutiliza el mismo, en vez de saltarlo.
      var lastRowAntes = dataSheet.getLastRow();
      dataSheet.appendRow(row);
      SpreadsheetApp.flush(); // Forzar que la escritura se confirme antes de seguir
      var lastRowDespues = dataSheet.getLastRow();

      // Recien ahora, con la fila ya guardada, confirmamos el contador
      stateSheet.getRange(2, 1).setValue(lastNum);
      stateSheet.getRange(2, 2).setValue(lastRec);
      stateSheet.getRange(2, 3).setValue(currentYear);
      SpreadsheetApp.flush();

      Logger.log("save_entry OK -> spreadsheetId=" + ss.getId() + " hoja=" + dataSheet.getName() + " lastRowAntes=" + lastRowAntes + " lastRowDespues=" + lastRowDespues + " row=" + JSON.stringify(row));

      // Devolver los números generados a la App para que los muestre en el rótulo
      // + info de diagnostico para confirmar en que hoja/planilla exacta escribio
      return ContentService.createTextOutput(JSON.stringify({
        status: "OK",
        analysis: an,
        reception: lastRec,
        debug_spreadsheetId: ss.getId(),
        debug_spreadsheetName: ss.getName(),
        debug_hoja: dataSheet.getName(),
        debug_lastRowAntes: lastRowAntes,
        debug_lastRowDespues: lastRowDespues
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // --- ACCIÓN PARA EL HISTORIAL ---
    if (params.action === "update_history") {
      var sheet = ss.getSheetByName(params.sheet);
      if (!sheet) {
        return ContentService.createTextOutput(JSON.stringify({ status: "Sheet not found" })).setMimeType(ContentService.MimeType.JSON);
      }
      sheet.clear();
      var rows = params.rows;
      sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
      return ContentService.createTextOutput(JSON.stringify({ status: "OK" })).setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(JSON.stringify({ status: "Acción desconocida: " + params.action })).setMimeType(ContentService.MimeType.JSON);

  } catch (fatalErr) {
    // Cualquier error no previsto: lo devolvemos como JSON en vez de dejar
    // que Apps Script tire una pagina de error generica (que el cliente
    // no puede interpretar y hace ver que "se cerro" la app).
    return ContentService.createTextOutput(JSON.stringify({
      status: "ERROR",
      error: "Excepcion no controlada: " + fatalErr.message
    })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    // Soltar el candado para que entre la siguiente petición
    lock.releaseLock();
  }
}
