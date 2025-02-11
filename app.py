from flask import Flask, jsonify, request, render_template
from datetime import datetime
from flask_cors import CORS

# Creamos la app y habilitamos CORS
app = Flask(__name__)
CORS(app)

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Definimos el alcance de permisos
SCOPE = [
   "https://spreadsheets.google.com/feeds",
   "https://www.googleapis.com/auth/drive"
]


# Intentamos obtener las credenciales desde la variable de entorno
credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if not credentials_json:
   CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
   client = gspread.authorize(CREDS)
else:
   # Convertimos la cadena JSON en un diccionario y creamos las credenciales
   creds_dict = json.loads(credentials_json)
   CREDS = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
   client = gspread.authorize(CREDS)
   # … (el resto del código que conecta con las hojas)
   
   # Intentamos leer la hoja "BASE DE DATOS" -> pestaña "Preguntas"
   try:
       sheet_preguntas = client.open("BASE DE DATOS").worksheet("Preguntas")
       datos = sheet_preguntas.get_all_records()
       print("Conexión exitosa a la hoja 'Preguntas'. Se han obtenido:")
   except Exception as e:
       print(f"Error conectando con Google Sheets: {e}")
       datos = []
# Para otras pestañas que usaremos (Respuestas, Subtipo, Usuarios):
def get_worksheet(nombre_hoja):
   """Pequeña función auxiliar para no repetir autorizar cada vez."""
   return client.open("BASE DE DATOS").worksheet(nombre_hoja)

def get_datos():
   return client.open("BASE DE DATOS").worksheet("Preguntas").get_all_records()

# ========= 2) RUTA PRINCIPAL DE PRUEBA =========
@app.route("/")
def home():
    return render_template("index.html")

# ========= 3) ENDPOINTS EXISTENTES (los dejamos o adaptamos) =========

@app.route("/preguntas", methods=["GET"])
def obtener_preguntas():
   """Devuelve todas las preguntas de la hoja, sin lógica adaptativa."""
   try:
       return jsonify({"status": "success", "datos": datos}), 200
   except Exception as e:
       return jsonify({"status": "error", "mensaje": str(e)}), 500

# @app.route("/iniciar_test", methods=["POST"])
# def iniciar_test():
#     """
#     Inicia el test devolviendo la primera pregunta.
#     """
#     try:
#         data = request.get_json(force=True)  # Force parsing JSON
#         print("Received data:", data)  # Debugging log

#         if not data or "usuario" not in data:
#             return jsonify({"status": "error", "message": "Falta el usuario"}), 400

#         usuario = data["usuario"]
#         testId = data.get("testId")

#         # Obtener la hoja de respuestas
#         respuestas_sheet = get_worksheet("Respuestas")
#         if not respuestas_sheet:
#             return jsonify({"status": "error", "message": "No se pudo acceder a la hoja de respuestas"}), 500

#         # Verificar si el testId ya existe
#         all_rows = respuestas_sheet.get_all_records()
        
#         # Obtener la primera pregunta
#         primera_pregunta, test_finalizado, _ = decidir_siguiente(usuario, testId)
#         print(f"Primera pregunta: {primera_pregunta}, Test finalizado: {test_finalizado}")

#         if primera_pregunta:
#             return jsonify({
#                 "status": "success",
#                 "siguiente_pregunta": primera_pregunta,
#                 "test_finalizado": test_finalizado
#             }), 200
#         else:
#             return jsonify({
#                 "status": "error",
#                 "message": "No se encontró una pregunta inicial.",
#                 "test_finalizado": False
#             }), 400

#     except Exception as e:
#         print("Error en iniciar_test:", str(e))  # Log the error
#         return jsonify({"status": "error", "message": str(e), "test_finalizado": False}), 500

# @app.route("/iniciar_test", methods=["POST"])

@app.route("/responder", methods=["POST"])
def registrar_respuesta_lineal():
    """
    Versión anterior de /responder que solo registra la respuesta en la hoja 'Respuestas'
    y no devuelve la siguiente pregunta. (Se deja por retrocompatibilidad).
    """
    try:
        data = request.json
        usuario = data.get("usuario")
        pregunta = data.get("id_pregunta")
        respuesta = data.get("respuesta")
        peso = data.get("peso", "")        
        subtipo_actual = data.get("subtipo_actual", "")
        # testId = data.get("testId", f"Test_{int(datetime.now().timestamp())}")
        testId = data.get("testId")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # when first loading, show first question   and   Increase id_pregunta
        id_pregunta = data.get("id_pregunta")
        if not id_pregunta:
            id_pregunta = 1
        else:
            id_pregunta += 1

        respuestas_sheet = get_worksheet("Respuestas")
        
        siguiente_pregunta = get_siguiente_pregunta(id_pregunta)
        siguiente_pregunta = {"id": id_pregunta, "Pregunta": siguiente_pregunta}
        
        if respuestas_sheet:
            # Log before appending the row to the sheet
            print(f"Appending row: [{testId}, {usuario}, {pregunta}, {respuesta}, {peso}, {subtipo_actual}, {timestamp}]")
            respuestas_sheet.append_row([
                testId,
                usuario,
                pregunta,
                respuesta,
                peso,
                subtipo_actual,
                timestamp
            ])
        else:
            print("⚠️ Error: respuestas_sheet is None or not accessible.")
        # Return success response
        return jsonify({"status": "success", "message": "Respuesta registrada correctamente",
                        "siguiente_pregunta": siguiente_pregunta}), 200
    except Exception as e:
        # Log the error for debugging
        print(f"❌ Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def get_siguiente_pregunta(id_pregunta):
    datos = get_datos()
    for row in datos:
        if row["Pregunta"] == id_pregunta:
            return row["Texto de la pregunta"]
    return None


# Otras rutas: registrar_usuario, actualizar_usuario, calcular_resultados...
@app.route("/registrar_usuario", methods=["POST"])
def registrar_usuario():
   try:
       data = request.json
       nombre = data.get("nombre")
       correo = data.get("correo", "")
       fecha_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

       id_usuario = f"Usuario_{int(datetime.now().timestamp())}"

       usuarios_sheet = get_worksheet("Usuarios")
       if usuarios_sheet:
           usuarios_sheet.append_row([
               id_usuario,
               f"{nombre}/{correo}",
               "En curso",
               fecha_inicio,
               "",
               "",
               "",
               ""
           ])

       return jsonify({"status": "success", "message": f"Usuario {id_usuario} registrado correctamente"}), 200
   except Exception as e:
       return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/actualizar_usuario", methods=["POST"])
def actualizar_usuario():
   try:
       data = request.json
       usuario = data.get("usuario")
       ultima_pregunta = data.get("ultima_pregunta", "")
       subtipo_actual = data.get("subtipo_actual", "")
       estado_test = data.get("estado_test", "En curso")

       usuarios_sheet = get_worksheet("Usuarios")
       if not usuarios_sheet:
           return jsonify({"status": "error", "message": "No se pudo acceder a la hoja Usuarios"}), 500

       registros = usuarios_sheet.get_all_records()
       encontrado = False
       for i, registro in enumerate(registros, start=2):
           if registro["Nombre/Correo Electrónico"] == usuario:
               usuarios_sheet.update(f"D{i}", ultima_pregunta)
               usuarios_sheet.update(f"E{i}", subtipo_actual)
               usuarios_sheet.update(f"F{i}", estado_test)
               encontrado = True
               break

       if not encontrado:
           return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

       return jsonify({"status": "success", "message": "Usuario actualizado correctamente"}), 200
   except Exception as e:
       return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/calcular_resultados", methods=["POST"])
def calcular_resultados():
   """
   Versión anterior que calcula resultados a partir de un array de respuestas.
   La dejamos tal cual, aunque en un test adaptativo podríamos usarla solo al final.
   """
   try:
       data = request.json
       respuestas = data.get("respuestas", [])

       # Acumular pesos por subtipo
       pesos_acumulados = {}
       for r in respuestas:
           intensidad = 1
           # Si la respuesta es "Si", podríamos interpretarla como 1, "No" como 0
           # o si es 1-5, parsear a int. Ajusta como prefieras.
           if isinstance(r["respuesta"], int):
               intensidad = r["respuesta"]
           elif str(r["respuesta"]).lower() in ["si", "sí", "yes"]:
               intensidad = 1
           else:
               intensidad = 0

           for subt in r["subtipos"]:
               if subt not in pesos_acumulados:
                   pesos_acumulados[subt] = 0
               pesos_acumulados[subt] += r["peso"] * (intensidad / 5.0)

       # Ordenar subtipos
       subtipos_ordenados = sorted(pesos_acumulados.items(), key=lambda x: x[1], reverse=True)
       subtipo_principal = subtipos_ordenados[0][0] if subtipos_ordenados else None

       # Leer hoja Subtipo para info adicional
       subtipo_sheet = get_worksheet("Subtipo")
       if subtipo_sheet:
           subtipo_data = subtipo_sheet.get_all_records()
       else:
           subtipo_data = []

       descripciones_subtipos = {
           row["Type Name"]: {
               "descripcion": row.get("Integracion ia", "No disponible."),
               "rasgos_clave": row.get("Rasgos Clave", "No disponible."),
               "virtudes": row.get("Virtudes", "No disponible."),
               "mecanismos_defensa": row.get("Mecanismo de defensa", "No disponible."),
               "motivacion_nuclear": row.get("Motivación", "No disponible."),
               "palabra_clave": row.get("Palabra Clave", "No disponible."),
           }
           for row in subtipo_data
       }

       datos_subtipo_principal = descripciones_subtipos.get(subtipo_principal, {
           "descripcion": "No disponible.",
           "rasgos_clave": "No disponible.",
           "virtudes": "No disponible.",
           "mecanismos_defensa": "No disponible.",
           "motivacion_nuclear": "No disponible.",
           "palabra_clave": "No disponible.",
       })

       # Filtrar preguntas que influyeron
       preguntas_influyentes = []
       for r in respuestas:
           if subtipo_principal in r["subtipos"]:
               preguntas_influyentes.append({
                   "pregunta": r["pregunta"],
                   "peso": r["peso"],
                   "respuesta": r["respuesta"]
               })

       return jsonify({
           "status": "success",
           "resultado": subtipo_principal,
           "descripcion": datos_subtipo_principal["descripcion"],
           "rasgos_clave": datos_subtipo_principal["rasgos_clave"],
           "virtudes": datos_subtipo_principal["virtudes"],
           "mecanismos_defensa": datos_subtipo_principal["mecanismos_defensa"],
           "motivacion_nuclear": datos_subtipo_principal["motivacion_nuclear"],
           "palabra_clave": datos_subtipo_principal["palabra_clave"],
           "pesos_acumulados": pesos_acumulados,
           "ranking": subtipos_ordenados,
           "preguntas_influyentes": preguntas_influyentes
       }), 200
   except Exception as e:
       return jsonify({"status": "error", "message": str(e)}), 500


# ========= 4) LÓGICA ADAPTATIVA =========
#
# Crearemos un nuevo endpoint: /siguiente_pregunta
# Cada vez que el usuario responda, guardamos la respuesta en "Respuestas"
# y decidimos la siguiente pregunta según la lógica solicitada:
#  - Primero "Eneatipo" (X preguntas)
#  - Luego "Específica" según el eneatipo más probable
#  - Si hay empates, "Discriminatorias".
#  - Terminamos cuando creemos que ya está claro (o se alcanza un número límite).

# @app.route("/siguiente_pregunta", methods=["POST"])
def siguiente_pregunta():
   """
   Endpoint adaptativo: Recibe la última respuesta, la registra,
   recalcula pesos parciales y devuelve la siguiente pregunta (o el resultado final).
   """
   try:
       data = request.json
       usuario = data.get("usuario", "Anonimo")
       testId = data.get("testId", f"Test_{int(datetime.now().timestamp())}")
       pregunta_id = data.get("pregunta_id")  # Ej: "Pregunta 1"
       respuesta_valor = data.get("respuesta")  # "Si", "No", "3", etc.
       # Nota: "peso" se puede extraer de la fila en la hoja "Preguntas"
       #   en función de la pregunta contestada.

       # 1) Guardar la respuesta (si hay pregunta_id y respuesta_valor)
       if pregunta_id and respuesta_valor is not None:
           # Buscar en 'datos' la fila con "Pregunta" == pregunta_id
           fila = next((f for f in datos if f["Pregunta"] == pregunta_id), None)
           if fila:
               peso_pregunta = float(fila.get("Peso", 1))
               # subtipos asociados -> "Eneatipo 1 conservacion, Eneatipo 2 social..."
               subtipos_asociados = fila.get("Subtipos asociados", "")
               # Tipo de Respuesta -> "Si/No" => interpretamos "Si"=1, "No"=0
               # o si es 1-5, parseamos int. A modo de ejemplo:
               tipo_resp = fila.get("Tipo de Respuesta", "Si/No")
              
               intensidad = 0
               # Convertir la respuesta a un factor numérico
               if tipo_resp.lower() in ["si/no", "si-no"]:
                   # si/no
                   if str(respuesta_valor).lower() in ["si", "sí", "yes", "1"]:
                       intensidad = 1
                   else:
                       intensidad = 0
               else:
                   # suponemos es 1-5
                   try:
                       intensidad = int(respuesta_valor)
                   except:
                       intensidad = 0  # fallback
              
               # Registrar en la hoja "Respuestas"
               respuestas_sheet = get_worksheet("Respuestas")
               if respuestas_sheet:
                   timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                   respuestas_sheet.append_row([
                       testId,
                       usuario,
                       pregunta_id,
                       respuesta_valor,  # la respuesta bruta
                       peso_pregunta,
                       "",  # subtipo_actual no lo usamos, lo calculamos
                       timestamp
                   ])
           else:
               print(f"No se encontró la fila de pregunta_id={pregunta_id} en la DB local 'datos'")

       # 2) Decidir la siguiente pregunta o si ya finalizamos
       #    Llamamos a una función helper que examina todas las respuestas
       #    del usuario y define qué preguntar a continuación.
       siguiente, test_finalizado, ranking_parcial = decidir_siguiente(usuario, testId)

       if test_finalizado:
           # Si finalizamos, podríamos devolver el ranking final,
           # un subtipo principal, etc.
           # O usar la antigua /calcular_resultados para un array?
           # Aquí haremos un calculo rápido sin pedir un array.
           resultado_json = calcular_resultados_parciales(usuario, testId, ranking_parcial)
           return jsonify(resultado_json), 200
       else:
           return jsonify({
               "status": "success",
               "test_finalizado": False,
               "siguiente_pregunta": siguiente,
               "testId": testId
           }), 200

   except Exception as e:
       return jsonify({"status": "error", "message": str(e)}), 500


def decidir_siguiente(usuario, testId):
   """
   Lógica adaptativa principal.
   1) Recolecta las respuestas del usuario en la hoja 'Respuestas'.
   2) Identifica cuántas preguntas de 'Eneatipo' ha respondido y su eneatipo más alto.
   3) Si no ha respondido X num de Eneatipo, pide la siguiente.
   4) Si ya tiene un eneatipo claro, pide 'Específica'.
   5) Si hay empates, pide 'Discriminatorias'.
   6) En algún punto, finaliza el test y devolvemos test_finalizado=True.
   """
   # Leer todas las respuestas de 'Respuestas' para este testId (y/o usuario)
   respuestas_sheet = get_worksheet("Respuestas")
   print(respuestas_sheet)
   
   if not respuestas_sheet:
       # Sin hoja, no podemos hacer lógica adaptativa real
       # Devolvemos la primera pregunta de Eneatipo, o finalizamos
       primera_eneatipo = next((x for x in datos if x.get("Categoría") == "Eneatipo"), None)
       return (formatear_pregunta(primera_eneatipo), False, {})
   all_rows = respuestas_sheet.get_all_records()
   # Filtramos solo las de testId y usuario
   resp_user = [
       r for r in all_rows
       if (r["Test ID"] == testId and str(r["Usuarios"]) == str(usuario))
   ]
   # PASO A: Calcular un ranking parcial a partir de sus respuestas
   ranking_parcial = calcular_ranking_parcial(resp_user)

   # PASO B: Contar cuántas de las que respondió son "Categoría=Eneatipo"
   #         y cuántas son "Específica" / "Discriminatorias", etc.
   # Podemos guiar nuestra lógica con el count de Eneatipo
   eneatipo_respondidas = 0
   for r in resp_user:
       # Hallar la fila en 'datos' con r["Pregunta contestada"]
       preg = next((x for x in datos if str(x["Pregunta"]) == str(r["Pregunta contestada"])), None)
       if preg and preg.get("Categoría") == "Eneatipo":
           eneatipo_respondidas += 1
   
   print("1111111111111111")
   # 2) Contar cuántas de las que respondió son "Específica" / "Discriminatorias", etc.
   # PASO C: Reglas de decisión
   # 1) Si eneatipo_respondidas < 3, pregunta otra de Eneatipo
   if eneatipo_respondidas < 3:
       # Buscar una pregunta de Eneatipo no contestada aún
       sig = buscar_pregunta_no_respondida("Eneatipo", usuario, testId)
       if sig:
           return (formatear_pregunta(sig), False, ranking_parcial)
       else:
           # No hay mas eneatipo sin responder, pasamos a la siguiente fase
           pass
   print("1111111111111111") 
   # 2) Si ya se respondieron >=3 eneatipo, vemos quién va ganando
   #    ranking_parcial = { "Eneatipo 1 conservacion": score, ... }
   #    Toma el top 1-2
   top = sorted(ranking_parcial.items(), key=lambda x: x[1], reverse=True)
   if not top:
       # Nadie? Pregunta Eneatipo random?
       sig = buscar_pregunta_no_respondida("Eneatipo", usuario, testId)
       if sig:
           return (formatear_pregunta(sig), False, ranking_parcial)
       else:
           # No hay, finalicemos forzadamente
           return (None, True, ranking_parcial)

   # El subtipo principal
   principal, score_principal = top[0]
   # Si hay un 2do
   if len(top) > 1:
       segundo, score_segundo = top[1]
   else:
       segundo, score_segundo = (None, 0)

   # Revisar si hay empate en los 2 primeros
   if segundo and abs(score_principal - score_segundo) < 0.5:
       # PREGUNTAS DISCRIMINATORIAS para esos subtipos
       sig = buscar_pregunta_discriminatoria([principal, segundo], usuario, testId)
       if sig:
           return (formatear_pregunta(sig), False, ranking_parcial)
       else:
           # No hay discriminatorias, finaliza
           return (None, True, ranking_parcial)
   else:
       # No hay empate. Asumimos que principal define el "Eneatipo X"
       # => siguiente pregunta "Específica" de ese Eneatipo, si no se han hecho
       sig = buscar_pregunta_especifica(principal, usuario, testId)
       if sig:
           return (formatear_pregunta(sig), False, ranking_parcial)
       else:
           # Si no hay mas específicas relevantes, terminamos
           return (None, True, ranking_parcial)


def buscar_pregunta_no_respondida(categoria, usuario, testId):
   """Devuelve la primera pregunta de 'datos' con esa categoría que el usuario no haya respondido."""
   respuestas_sheet = get_worksheet("Respuestas")
   if not respuestas_sheet:
       return None
   all_rows = respuestas_sheet.get_all_records()
   resp_user = [
       r for r in all_rows
       if (r["Test ID"] == testId and str(r["Usuario"]) == str(usuario))
   ]
   # IDs de preguntas ya respondidas
   respondidas_ids = {str(x["Pregunta contestada"]) for x in resp_user}

   for fila in datos:
       if fila.get("Categoría") == categoria:
           p_id = str(fila.get("Pregunta"))
           if p_id not in respondidas_ids:
               return fila
   return None

def buscar_pregunta_discriminatoria(lista_subtipos, usuario, testId):
   """
   Devuelve una pregunta de categoría Discriminatorias
   que discrimine entre los subtipos en 'lista_subtipos', si la hoja 'Subtipos asociados' coincide.
   """
   # Simplificado: buscamos una pregunta con categoría=Discriminatorias
   # y Subtipos asociados que contenga parte de la info
   respuestas_sheet = get_worksheet("Respuestas")
   if not respuestas_sheet:
       return None
   all_rows = respuestas_sheet.get_all_records()
   resp_user = [
       r for r in all_rows
       if (r["Test ID"] == testId and str(r["Usuario"]) == str(usuario))
   ]
   respondidas_ids = {str(x["Pregunta contestada"]) for x in resp_user}

   for fila in datos:
       if fila.get("Categoría") == "Discriminatorias":
           p_id = str(fila.get("Pregunta"))
           if p_id not in respondidas_ids:
               # Revisar si su "Subtipos asociados" coincide con los subtipos del top
               st = fila.get("Subtipos asociados", "")
               # Si contiene al menos uno de esos subtipos
               for s in lista_subtipos:
                   if s in st:
                       return fila
   return None

def buscar_pregunta_especifica(subtipo_principal, usuario, testId):
   """
   Devuelve una pregunta de categoría 'Específica' relacionada con el subtipo_principal
   (por ejemplo, si principal es 'Eneatipo 2 conservacion', buscamos esa coincidencia).
   """
   respuestas_sheet = get_worksheet("Respuestas")
   if not respuestas_sheet:
       return None
   all_rows = respuestas_sheet.get_all_records()
   resp_user = [
       r for r in all_rows
       if (r["Test ID"] == testId and str(r["Usuario"]) == str(usuario))
   ]
   respondidas_ids = {str(x["Pregunta contestada"]) for x in resp_user}

   for fila in datos:
       if fila.get("Categoría") == "Específica":
           p_id = str(fila.get("Pregunta"))
           if p_id not in respondidas_ids:
               # Check "Subtipos asociados"
               st = fila.get("Subtipos asociados", "")
               if subtipo_principal in st:
                   return fila
   return None

def formatear_pregunta(fila):
   """
   Devuelve un dict con 'id', 'Pregunta' y lo que necesites,
   a partir de la fila del sheet en 'datos'.
   """
   if not fila:
       return None
   return {
       "id": str(fila["Pregunta"]),
       "texto": fila.get("Texto de la pregunta", "Sin texto"),
       "categoria": fila.get("Categoría", ""),
       "tipo_respuesta": fila.get("Tipo de Respuesta", "Si/No")
   }

def calcular_ranking_parcial(resp_user):
   """
   Dado un listado de respuestas (filas de 'Respuestas') para un usuario+test,
   calculamos un dict { 'subtipo': puntuacion } temporal.
   - Para cada respuesta, miramos la pregunta en 'datos', sacamos 'Subtipos asociados', 'Peso'
   - Convertimos 'respuesta' en un factor (Si=1, No=0, o un int 1-5).
   - Suma a la puntuación de cada subtipo implicado.
   """
   subtipo_scores = {}
   datos = get_datos()

   for r in resp_user:
       pregunta_id = r["Preguntas"]
       respuesta_val = r["Respuesta"]
       peso = float(r["Peso Pregunta"]) if "Peso Pregunta" in r else float(r["Peso Pregunta "]) if "Peso Pregunta " in r else float(r.get("Peso", 1))

       # Buscar la fila en datos
       fila = next((x for x in datos if str(x["Pregunta"]) == str(pregunta_id)), None)
       print("22222222222", fila)
       if not fila:
           continue
       st_asociados = fila.get("Subtipos asociados", "")
       lista_st = [s.strip() for s in st_asociados.split(",")] if st_asociados else []
       # Convertir la respuesta a factor
       tipo_resp = fila.get("Tipo de Respuesta", "Si/No").lower()
       factor = 0
       if tipo_resp in ["si/no", "si-no"]:
           if str(respuesta_val).lower() in ["si", "sí", "yes", "1"]:
               factor = 1
           else:
               factor = 0
       else:
           # asume 1-5
           try:
               factor = int(respuesta_val)
           except:
               factor = 0

       # Sumar a cada subtipo
       # Podríamos normalizar "factor" con /5 si lo deseamos. Ej:
       for st in lista_st:
           if st not in subtipo_scores:
               subtipo_scores[st] = 0
           # Ej: sumamos peso*(factor/5) si es 1-5
           # o peso*(factor) si es si/no
           if tipo_resp in ["si/no", "si-no"]:
               subtipo_scores[st] += peso * factor
           else:
               # factor entre 1 y 5
               subtipo_scores[st] += (peso * (factor / 5.0))

   return subtipo_scores

def calcular_resultados_parciales(usuario, testId, ranking_parcial):
   """
   Cuando se finaliza el test, armamos un JSON con:
     - ranking ordenado
     - subtipo principal
     - posibilidad de añadir descripciones, etc.
   """
   # Ordenamos
   ordenado = sorted(ranking_parcial.items(), key=lambda x: x[1], reverse=True)
   subtipo_principal = ordenado[0][0] if ordenado else None

   # (Opcional) Podrías leer la hoja 'Subtipo' para más info
   subtipo_sheet = get_worksheet("Subtipo")
   if subtipo_sheet:
       subtipo_data = subtipo_sheet.get_all_records()
   else:
       subtipo_data = []

   descripciones_subtipos = {
       row["Type Name"]: {
           "descripcion": row.get("Integracion ia", "No disponible."),
           "rasgos_clave": row.get("Rasgos Clave", "No disponible."),
           "virtudes": row.get("Virtudes", "No disponible."),
           "mecanismos_defensa": row.get("Mecanismo de defensa", "No disponible."),
           "motivacion_nuclear": row.get("Motivación", "No disponible."),
           "palabra_clave": row.get("Palabra Clave", "No disponible."),
       }
       for row in subtipo_data
   }

   info_subtipo_principal = descripciones_subtipos.get(subtipo_principal, {
       "descripcion": "No disponible.",
       "rasgos_clave": "No disponible.",
       "virtudes": "No disponible.",
       "mecanismos_defensa": "No disponible.",
       "motivacion_nuclear": "No disponible.",
       "palabra_clave": "No disponible.",
   })

   return {
       "status": "success",
       "test_finalizado": True,
       "resultado": subtipo_principal,
       "ranking": ordenado,
       "descripcion": info_subtipo_principal["descripcion"],
       "rasgos_clave": info_subtipo_principal["rasgos_clave"],
       "virtudes": info_subtipo_principal["virtudes"],
       "mecanismos_defensa": info_subtipo_principal["mecanismos_defensa"],
       "motivacion_nuclear": info_subtipo_principal["motivacion_nuclear"],
       "palabra_clave": info_subtipo_principal["palabra_clave"]
   }


# ========= 5) EJECUCIÓN =========
if __name__ == "__main__":
   app.run(host="0.0.0.0", port=5000)

