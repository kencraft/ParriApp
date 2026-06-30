from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, JornadaLaboral, Pedido
from datetime import datetime

jornadas_bp = Blueprint('jornadas', __name__)

@jornadas_bp.route('/iniciar', methods=['POST'])
def iniciar():
    activa = JornadaLaboral.query.filter_by(activa=True).first()
    if activa:
        flash('Ya hay una jornada laboral activa', 'warning')
        return redirect(url_for('index'))
    jornada = JornadaLaboral()
    db.session.add(jornada)
    db.session.commit()
    flash('Jornada laboral iniciada', 'success')
    return redirect(url_for('index'))

@jornadas_bp.route('/cerrar')
def cerrar_form():
    jornada = JornadaLaboral.query.filter_by(activa=True).first()
    if not jornada:
        flash('No hay una jornada laboral activa', 'warning')
        return redirect(url_for('index'))
    pedidos_abiertos = Pedido.query.filter_by(estado='abierto').count()
    return render_template('jornadas/cerrar.html', jornada=jornada, pedidos_abiertos=pedidos_abiertos)

@jornadas_bp.route('/cerrar', methods=['POST'])
def cerrar():
    jornada = JornadaLaboral.query.filter_by(activa=True).first()
    if not jornada:
        flash('No hay una jornada laboral activa', 'warning')
        return redirect(url_for('index'))
    pedidos_abiertos = Pedido.query.filter_by(estado='abierto').count()
    if pedidos_abiertos > 0:
        flash(f'No se puede cerrar la jornada: hay {pedidos_abiertos} pedido(s) pendiente(s) de pago', 'danger')
        return redirect(url_for('jornadas.cerrar_form'))
    jornada.fecha_fin = datetime.now()
    jornada.activa = False
    db.session.commit()
    flash('Jornada laboral cerrada correctamente', 'success')
    return redirect(url_for('index'))