from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Configuracion

configuracion_bp = Blueprint('configuracion', __name__, url_prefix='/configuracion')

@configuracion_bp.route('/', methods=['GET', 'POST'])
def editar():
    if request.method == 'POST':
        mensaje_ticket = request.form.get('mensaje_ticket', '').strip()
        Configuracion.establecer('mensaje_ticket', mensaje_ticket)
        flash('Configuración guardada correctamente', 'success')
        return redirect(url_for('configuracion.editar'))
    mensaje_ticket = Configuracion.obtener('mensaje_ticket', 'Gracias por su visita')
    return render_template('configuracion/editar.html', mensaje_ticket=mensaje_ticket)
