from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Mozo

mozos_bp = Blueprint('mozos', __name__)

@mozos_bp.route('/')
def listar():
    mozos = Mozo.query.order_by(Mozo.nombre).all()
    return render_template('mozos/listar.html', mozos=mozos)

@mozos_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()
        if not nombre:
            flash('El nombre es obligatorio', 'danger')
            return redirect(url_for('mozos.crear'))
        mozo = Mozo(nombre=nombre, telefono=telefono)
        db.session.add(mozo)
        db.session.commit()
        flash('Mozo creado exitosamente', 'success')
        return redirect(url_for('mozos.listar'))
    return render_template('mozos/editar.html', mozo=None)

@mozos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    mozo = Mozo.query.get_or_404(id)
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        if not nombre:
            flash('El nombre es obligatorio', 'danger')
            return redirect(url_for('mozos.editar', id=id))
        mozo.nombre = nombre
        mozo.telefono = request.form.get('telefono', '').strip()
        mozo.activo = 'activo' in request.form
        db.session.commit()
        flash('Mozo actualizado', 'success')
        return redirect(url_for('mozos.listar'))
    return render_template('mozos/editar.html', mozo=mozo)

@mozos_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    mozo = Mozo.query.get_or_404(id)
    db.session.delete(mozo)
    db.session.commit()
    flash('Mozo eliminado', 'success')
    return redirect(url_for('mozos.listar'))