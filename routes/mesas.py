from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Mesa

mesas_bp = Blueprint('mesas', __name__)

@mesas_bp.route('/')
def listar():
    mesas = Mesa.query.order_by(Mesa.numero).all()
    return render_template('mesas/listar.html', mesas=mesas)

@mesas_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        numero = request.form.get('numero', type=int)
        if not numero:
            flash('El número de mesa es obligatorio', 'danger')
            return redirect(url_for('mesas.crear'))
        if Mesa.query.filter_by(numero=numero).first():
            flash('Ya existe una mesa con ese número', 'danger')
            return redirect(url_for('mesas.crear'))
        mesa = Mesa(numero=numero)
        db.session.add(mesa)
        db.session.commit()
        flash('Mesa creada exitosamente', 'success')
        return redirect(url_for('mesas.listar'))
    return render_template('mesas/editar.html', mesa=None)

@mesas_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    mesa = Mesa.query.get_or_404(id)
    if request.method == 'POST':
        numero = request.form.get('numero', type=int)
        if not numero:
            flash('El número de mesa es obligatorio', 'danger')
            return redirect(url_for('mesas.editar', id=id))
        existente = Mesa.query.filter_by(numero=numero).first()
        if existente and existente.id != id:
            flash('Ya existe otra mesa con ese número', 'danger')
            return redirect(url_for('mesas.editar', id=id))
        mesa.numero = numero
        db.session.commit()
        flash('Mesa actualizada', 'success')
        return redirect(url_for('mesas.listar'))
    return render_template('mesas/editar.html', mesa=mesa)

@mesas_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    mesa = Mesa.query.get_or_404(id)
    db.session.delete(mesa)
    db.session.commit()
    flash('Mesa eliminada', 'success')
    return redirect(url_for('mesas.listar'))