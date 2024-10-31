from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from db import get_database
import csv
import io
from bson import ObjectId
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = 'secreto123'

db = get_database()
empleados_collection = db["Empleados"]
usuarios_collection = db["Usuarios"] 

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    usuario = usuarios_collection.find_one({"nombre": username}) 

    if usuario:
        session['username'] = username 
        return redirect(url_for('get_empleados')) 
    else:
        return "Credenciales incorrectas", 401

@app.route('/logout')
def logout():
    session.pop('username', None)  
    return redirect(url_for('home'))

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return "No file part"
    
    file = request.files['file']

    if file.filename == '':
        return "No selected file"
    
    if file and file.filename.endswith('.csv'):
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        for row in csv_reader:
            print(row)
            salario_bruto = float(row["Salario por Hora"]) * float(row["Horas Trabajadas"])
            salario_neto = calcular_salario_neto(salario_bruto)
            iggs = calcular_iggs(salario_bruto)
            isr = calcular_isr(salario_bruto)
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

        return redirect(url_for('get_empleados'))
    else:
        return "Tipo inválido"

def calcular_salario_neto(salario_bruto):
    deduccion_igss = salario_bruto * 0.0483

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

@app.route('/empleados', methods=['GET'])
def get_empleados():
    empleados = list(empleados_collection.find())
    return render_template('empleados.html', empleados=empleados)

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

@app.route('/empleados/eliminar/<string:id>', methods=['POST'])
def eliminar_empleado(id):
    empleados_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('get_empleados'))

@app.route('/usuarios')
def usuarios():
    usuarios = list(usuarios_collection.find())
    return render_template('usuarios.html', usuarios=usuarios)

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

@app.route('/usuarios/editar/<string:id>', methods=['POST'])
def editar_usuario(id):
    nombre = request.form['nombre']
    contrasena = request.form['contrasena']
    hashed_password = generate_password_hash(contrasena)
    usuarios_collection.update_one({"_id": ObjectId(id)}, {"$set": {'nombre': nombre, 'contrasena': hashed_password}})
    return redirect(url_for('home'))

@app.route('/usuarios/eliminar/<string:id>', methods=['POST'])
def eliminar_usuario(id):
    usuarios_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('home'))

@app.route('/empleados/estadisticas', methods=['GET'])
def estadisticas_empleados():
    pipeline = [
        {
            '$group': {
                '_id': None,
                'total_horas': {'$sum': {'$toDouble': '$HorasTrabajadas'}},
                'total_salario_hora': {'$sum': {'$toDouble': '$SalarioPorHora'}},
                'total_salario_bruto': {'$sum': '$SalarioBruto'},
                'total_salario_neto': {'$sum': '$SalarioNeto'},
                'total_deducciones': {'$sum': '$DeduccionesTotales'},
                'total_iggs': {'$sum': '$IGGS'},
                'total_isr': {'$sum': '$ISR'},
                'count': {'$sum': 1}
            }
        },
        {
            '$project': {
                'total_horas': 1,
                'promedio_horas': {'$divide': ['$total_horas', '$count']},
                'total_salario_hora': 1,
                'promedio_salario_hora': {'$divide': ['$total_salario_hora', '$count']},
                'total_salario_bruto': 1,
                'promedio_salario_bruto': {'$divide': ['$total_salario_bruto', '$count']},
                'total_salario_neto': 1,
                'promedio_salario_neto': {'$divide': ['$total_salario_neto', '$count']},
                'total_deducciones': 1,
                'deduccion_iggs_promedio': {'$divide': ['$total_iggs', '$count']},
                'deduccion_isr_promedio': {'$divide': ['$total_isr', '$count']},
                'count': 1
            }
        }
    ]

    resultado = list(empleados_collection.aggregate(pipeline))

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
            'deduccion_isr_promedio': 0
        }

    total_horas = stats['total_horas']
    promedio_horas = stats['promedio_horas']
    total_salario_hora = stats['total_salario_hora']
    promedio_salario_hora = stats['promedio_salario_hora']
    total_salario_bruto = stats['total_salario_bruto']
    promedio_salario_bruto = stats['promedio_salario_bruto']
    total_salario_neto = stats['total_salario_neto']
    promedio_salario_neto = stats['promedio_salario_neto']
    total_deducciones = stats['total_deducciones']
    deduccion_iggs_promedio = stats['deduccion_iggs_promedio']
    deduccion_isr_promedio = stats['deduccion_isr_promedio']

    salarios_neto = list(empleados_collection.find({}, {'SalarioNeto': 1}))
    salarios_neto_lista = [float(emp['SalarioNeto']) for emp in salarios_neto]

    salario_mas_alto = max(salarios_neto_lista) if salarios_neto_lista else 0
    salario_mas_bajo = min(salarios_neto_lista) if salarios_neto_lista else 0

    salarios_neto_lista.sort()
    n = len(salarios_neto_lista)
    mediana_salario_neto = (salarios_neto_lista[n // 2] if n % 2 != 0 else 
                            (salarios_neto_lista[n // 2 - 1] + salarios_neto_lista[n // 2]) / 2) if salarios_neto_lista else 0

    return render_template('estadisticas.html', 
                           total_horas=total_horas,
                           promedio_horas=promedio_horas,
                           total_salario_hora=total_salario_hora,
                           promedio_salario_hora=promedio_salario_hora,
                           total_salario_bruto=total_salario_bruto,
                           promedio_salario_bruto=promedio_salario_bruto,
                           total_salario_neto=total_salario_neto,
                           promedio_salario_neto=promedio_salario_neto,
                           salario_mas_alto=salario_mas_alto,
                           salario_mas_bajo=salario_mas_bajo,
                           mediana_salario_neto=mediana_salario_neto,
                           deduccion_iggs_promedio=deduccion_iggs_promedio,
                           deduccion_isr_promedio=deduccion_isr_promedio
                           )

if __name__ == '__main__':
    app.run(debug=True)
