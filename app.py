#Importaciones de librerias y bibliotecas para su uso
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from db import get_database
import csv
import io
from bson import ObjectId
from werkzeug.security import generate_password_hash

app = Flask(__name__)

app.secret_key = 'secreto123'

#Obtiene el resultado del metodo get_database, donde se hace la conexión a base de datos
db = get_database()

#En base a "db", la colección, empleados y usuarios es extraida
empleados_collection = db["Empleados"]
usuarios_collection = db["Usuarios"] 

#ruta que abre el login
@app.route('/')
def home():
    return render_template('login.html')

#Ruta donde se procesa el login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    #En este momento estoy manejando que si existe el usuario, entre, a pesar de no ser una buena practica, es
    #solo para fines de funcionalidad
    usuario = usuarios_collection.find_one({"nombre": username}) 

    if usuario:
        session['username'] = username 
        return redirect(url_for('get_empleados')) 
    else:
        return "Credenciales incorrectas", 401

#Deslogueo de la cuenta
@app.route('/logout')
def logout():
    session.pop('username', None)  
    return redirect(url_for('home'))

#Metodo de carga de CSV .html
@app.route('/upload')
def upload():
    return render_template('upload.html')

#En cuanto se carga el archivo y se presiona "Cargar archivo"
#comienza a ejecutarse eso
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    #Hace una pequeña validación en la cual, se valida si existe el archivo
    if 'file' not in request.files:
        return "No hay archivo"
    
    file = request.files['file']

    #Se verifica el nombre del archivo
    if file.filename == '':
        return "No seleccionó ningun archivo"
    
    #Valida si el archivo existe, y si exite, que termine con ".csv"
    if file and file.filename.endswith('.csv'):
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)

        #Lee el csv, y lo convierte en un diccionario
        csv_reader = csv.DictReader(stream)
        
        #recorre el diccionario
        for row in csv_reader:

            #Se procesan los datos, extrae salario por hora y horas trabajadas
            salario_bruto = float(row["Salario por Hora"]) * float(row["Horas Trabajadas"])

            #Calcula el salario Neto, en base al bruto
            salario_neto = calcular_salario_neto(salario_bruto)

            #Extrae el calculo del IGGS
            iggs = calcular_iggs(salario_bruto)

            #Extrae el calculo del ISR
            isr = calcular_isr(salario_bruto)

            #Inserta a la colección Empleados
            empleados_collection.insert_one({
                "NombreEmpleado": row["Nombre"],
                "SalarioPorHora": row["Salario por Hora"],
                "HorasTrabajadas": row["Horas Trabajadas"],
                "SalarioBruto": salario_bruto,
                "DeduccionesTotales": round(salario_bruto - salario_neto),
                "IGGS": iggs,
                "ISR": isr,
                "SalarioNeto": salario_neto
            }) 

        #Redirige a Empleados
        return redirect(url_for('get_empleados'))
    else:
        return "Tipo inválido"

def calcular_salario_neto(salario_bruto):

    #Se hace el calculo del IGGS
    deduccion_igss = salario_bruto * 0.0483

    #Calculo de ISR, en GT, si se gana más a 25,000 QTZ mes
    #El ISR, aumenta, de 1500, de importe fijo, y sobre el superhavit
    #Es el 7%
    if salario_bruto < 25000:
        isr = salario_bruto * 0.05
    else:
        isr = 1500 + ((salario_bruto - 30000) * 0.07)

    salario_neto = salario_bruto - deduccion_igss - isr
    
    return round(salario_neto, 2)

def calcular_iggs(salario_bruto):
    return round(salario_bruto * 0.0483)

def calcular_isr(salario_bruto):
    if salario_bruto < 25000:
        isr = salario_bruto * 0.05
    else:
        isr = 1500 + ((salario_bruto - 30000) * 0.07)

    return round(isr, 2)

#Añade un empleado nuevo, siguiendo el proceso y flujo del CSV
@app.route('/empleados/nuevo', methods=['GET', 'POST'])
def crear_empleado():
    if request.method == 'POST':
        nombre = request.form['nombre']
        salario_hora = float(request.form['salario_hora'])
        horas_trabajadas = int(request.form['horas_trabajadas'])
        
        salario_bruto = salario_hora * horas_trabajadas
        salario_neto = calcular_salario_neto(salario_bruto)
        iggs = calcular_iggs(salario_bruto)
        isr = calcular_isr(salario_bruto)
        empleado = {
            "NombreEmpleado": nombre,
            "SalarioPorHora": request.form['salario_hora'],
            "HorasTrabajadas": request.form['horas_trabajadas'],
            "SalarioBruto": salario_bruto,
            "DeduccionesTotales": round(salario_bruto - salario_neto),
            "IGGS": iggs,
            "ISR": isr,
            "SalarioNeto": salario_neto
        }
        
        empleados_collection.insert_one(empleado)
        return redirect(url_for('get_empleados'))
    return render_template('crear_empleado.html')

#Obtiene los empleados
@app.route('/empleados', methods=['GET'])
def get_empleados():
    empleados = list(empleados_collection.find())
    return render_template('empleados.html', empleados=empleados)

#Edita los empleados
@app.route('/empleados/editar/<string:id>', methods=['GET', 'POST'])
def editar_empleado(id):
    empleado = empleados_collection.find_one({"_id": ObjectId(id)})

    if request.method == 'POST':
        nombre = request.form['nombre']
        salario_hora = float(request.form['salario_hora'])
        horas_trabajadas = int(request.form['horas_trabajadas'])
        
        salario_bruto = salario_hora * horas_trabajadas
        salario_neto = calcular_salario_neto(salario_bruto)
        iggs = calcular_iggs(salario_bruto)
        isr = calcular_isr(salario_bruto)
        empleados_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "NombreEmpleado": nombre,
                "SalarioPorHora": request.form['salario_hora'],
                "HorasTrabajadas": request.form['horas_trabajadas'],
                "SalarioBruto": salario_bruto,
                "DeduccionesTotales": round(salario_bruto - salario_neto),
                "IGGS": iggs,
                "ISR": isr,
                "SalarioNeto": salario_neto
            }}
        )
        return redirect(url_for('get_empleados'))

    return render_template('editar_empleado.html', empleado=empleado)

#Elimina los empleados
@app.route('/empleados/eliminar/<string:id>', methods=['POST'])
def eliminar_empleado(id):
    empleados_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('get_empleados'))

#Obtiene usuarios
@app.route('/usuarios')
def usuarios():
    usuarios = list(usuarios_collection.find())
    return render_template('usuarios.html', usuarios=usuarios)

#Crea usuarios (Son necesarios para iniciar sesión)
@app.route('/usuarios/nuevo', methods=['POST'])
def crear_usuario():
    nuevo_usuario = request.form['nombre']
    nueva_contrasena = request.form['contrasena']

    if not nuevo_usuario or not nueva_contrasena:
        flash('Todos los campos son obligatorios.')
        return redirect(url_for('home'))

    if usuarios_collection.find_one({'nombre': nuevo_usuario}):
        flash('El nombre de usuario ya existe. Elige otro.')
        return redirect(url_for('home'))

    hashed_password = generate_password_hash(nueva_contrasena)

    usuarios_collection.insert_one({
        'nombre': nuevo_usuario,
        'contrasena': hashed_password
    })

    flash('Usuario creado exitosamente.')
    return redirect(url_for('home'))

#Edita usuariso previamente añadidos
@app.route('/usuarios/editar/<string:id>', methods=['POST'])
def editar_usuario(id):
    nombre = request.form['nombre']
    contrasena = request.form['contrasena']
    hashed_password = generate_password_hash(contrasena)
    usuarios_collection.update_one({"_id": ObjectId(id)}, {"$set": {'nombre': nombre, 'contrasena': hashed_password}})
    return redirect(url_for('home'))

#Se eliminan los usuarios
@app.route('/usuarios/eliminar/<string:id>', methods=['POST'])
def eliminar_usuario(id):
    usuarios_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('home'))

#Se hacen las estadisticas, con una consulta 
@app.route('/empleados/estadisticas', methods=['GET']) 
def estadisticas_empleados():
    pipeline = [
        {
            # Etapa de agrupación
            '$group': {
                '_id': None,  # Agrupamos todos los documentos en uno solo
                'total_horas': {'$sum': {'$toDouble': '$HorasTrabajadas'}},  # Suma total de horas trabajadas
                'total_salario_hora': {'$sum': {'$toDouble': '$SalarioPorHora'}},  # Suma total de salarios por hora
                'total_salario_bruto': {'$sum': {'$toDouble': '$SalarioBruto'}},  # Suma total de salarios brutos
                'total_salario_neto': {'$sum': {'$toDouble': '$SalarioNeto'}},  # Suma total de salarios netos
                'total_deducciones': {'$sum': {'$toDouble': '$DeduccionesTotales'}},  # Suma total de deducciones
                'total_iggs': {'$sum': {'$toDouble': '$IGGS'}},  # Suma total de IGGS
                'total_isr': {'$sum': {'$toDouble': '$ISR'}},  # Suma total de ISR
                'count': {'$sum': 1},  # Contamos el número total de empleados
                'salarios_neto': {'$push': {'$toDouble': '$SalarioNeto'}}  # Almacenamos todos los salarios netos en una lista
            }
        },
        {
            # Etapa de proyección para calcular promedios
            '$project': {
                'total_horas': 1,  # Mantiene el total de horas
                'promedio_horas': {'$divide': ['$total_horas', '$count']},  # Calcula el promedio de horas
                'total_salario_hora': 1,  # Mantiene el total de salario por hora
                'promedio_salario_hora': {'$divide': ['$total_salario_hora', '$count']},  # Promedio de salario por hora
                'total_salario_bruto': 1,  # Mantiene el total de salario bruto
                'promedio_salario_bruto': {'$divide': ['$total_salario_bruto', '$count']},  # Promedio de salario bruto
                'total_salario_neto': 1,  # Mantiene el total de salario neto
                'promedio_salario_neto': {'$divide': ['$total_salario_neto', '$count']},  # Promedio de salario neto
                'total_deducciones': 1,  # Mantiene el total de deducciones
                'deduccion_iggs_promedio': {'$divide': ['$total_iggs', '$count']},  # Promedio de deducción IGGS
                'deduccion_isr_promedio': {'$divide': ['$total_isr', '$count']},  # Promedio de deducción ISR
                'salarios_neto': 1  # Mantiene la lista de salarios netos
            }
        },
        {
            '$project': {
                'total_horas': 1,
                'promedio_horas': 1,
                'total_salario_hora': 1,
                'promedio_salario_hora': 1,
                'total_salario_bruto': 1,
                'promedio_salario_bruto': 1,
                'total_salario_neto': 1,
                'promedio_salario_neto': 1,
                'total_deducciones': 1,
                'deduccion_iggs_promedio': 1,
                'deduccion_isr_promedio': 1,
                'salario_mas_alto': {'$max': '$salarios_neto'},  # Salario más alto
                'salario_mas_bajo': {'$min': '$salarios_neto'},  # Salario más bajo
                'mediana_salario_neto': {
                    '$let': {
                        'vars': {
                            'sorted_salarios': {'$sortArray': {'input': '$salarios_neto', 'sortBy': 1}}  # Ordena la lista de salarios netos
                        },
                        'in': {
                            # Calcula la mediana
                            '$cond': {
                                'if': {'$eq': [{'$size': '$$sorted_salarios'}, 0]},  # Si no hay salarios
                                'then': 0,  # Mediana es 0
                                'else': {
                                    '$cond': {
                                        'if': {'$eq': [{'$mod': [{'$size': '$$sorted_salarios'}, 2]}, 0]},  # Si hay un número par de salarios
                                        'then': {'$avg': {
                                            '$slice': ['$$sorted_salarios', {'$divide': [{'$size': '$$sorted_salarios'}, 2]}, 2]  # Promedio de los dos salarios del medio
                                        }},
                                        'else': {'$arrayElemAt': ['$$sorted_salarios', {'$floor': {'$divide': [{'$size': '$$sorted_salarios'}, 2]}}]}  # Salario del medio si es impar
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    ]

    # Ejecuta la pipeline y convierte el resultado a una lista
    resultado = list(empleados_collection.aggregate(pipeline))

    # Si hay resultados, toma el primero; de lo contrario, establece valores por defecto
    if resultado:
        stats = resultado[0]
    else:
        stats = {
            'total_horas': 0,
            'promedio_horas': 0,
            'total_salario_hora': 0,
            'promedio_salario_hora': 0,
            'total_salario_bruto': 0,
            'promedio_salario_bruto': 0,
            'total_salario_neto': 0,
            'promedio_salario_neto': 0,
            'total_deducciones': 0,
            'deduccion_iggs_promedio': 0,
            'deduccion_isr_promedio': 0,
            'salario_mas_alto': 0,
            'salario_mas_bajo': 0,
            'mediana_salario_neto': 0
        }

    # Renderiza la plantilla con las estadísticas calculadas
    return render_template('estadisticas.html', **stats)

if __name__ == '__main__':
    app.run(debug=True)
