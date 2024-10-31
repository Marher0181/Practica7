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
            empleados_collection.insert_one({
                "NombreEmpleado": row["Nombre"],
                "SalarioBruto": salario_bruto,
                "SalarioNeto": salario_neto
            }) 

        return redirect(url_for('get_empleados'))
    else:
        return "Tipo inválido"

def calcular_salario_neto(salario_bruto):
    deduccion_igss = salario_bruto * 0.0483

    if salario_bruto < 30000:
        isr = salario_bruto * 0.05
    else:
        isr = 1500 + ((salario_bruto - 30000) * 0.07)

    salario_neto = salario_bruto - deduccion_igss - isr
    
    return round(salario_neto, 2)

@app.route('/empleados/nuevo', methods=['GET', 'POST'])
def crear_empleado():
    if request.method == 'POST':
        nombre = request.form['nombre']
        salario_hora = float(request.form['salario_hora'])
        horas_trabajadas = int(request.form['horas_trabajadas'])
        
        salario_bruto = salario_hora * horas_trabajadas
        salario_neto = calcular_salario_neto(salario_bruto)
        
        empleado = {
            "NombreEmpleado": nombre,
            "SalarioBruto": salario_bruto,
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

        empleados_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "NombreEmpleado": nombre,
                "SalarioBruto": salario_bruto,
                "SalarioNeto": salario_neto
            }}
        )
        return redirect(url_for('get_empleados'))

    return render_template('editar_empleado.html', empleado=empleado)

@app.route('/empleados/eliminar/<string:id>', methods=['POST'])
def eliminar_empleado(id):
    empleados_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('get_empleados'))

@app.route('/usuarios/nuevo', methods=['POST'])
def crear_usuario():
    nuevo_usuario = request.form['new_username']
    nueva_contrasena = request.form['new_password']

    if not nuevo_usuario or not nueva_contrasena:
        flash('Todos los campos son obligatorios.')
        return redirect(url_for('home'))

    if usuarios_collection.find_one({'nombre': nuevo_usuario}):
        flash('El nombre de usuario ya existe. Elige otro.')
        return redirect(url_for('home'))

    hashed_password = generate_password_hash(nueva_contrasena)

    # Insertar el nuevo usuario en la base de datos
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
    hashed_password = generate_password_hash(contrasena)  # Cifrar la nueva contraseña
    usuarios_collection.update_one({"_id": ObjectId(id)}, {"$set": {'nombre': nombre, 'contrasena': hashed_password}})
    return redirect(url_for('home'))

@app.route('/usuarios/eliminar/<string:id>', methods=['POST'])
def eliminar_usuario(id):
    usuarios_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
