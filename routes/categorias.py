from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Categoria

categorias_bp = Blueprint('categorias', __name__)

@categorias_bp.route('/')
def listar():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    return render_template('categorias/listar.html', categorias=categorias)

@categorias_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        if not nombre:
            flash('El nombre de la categoría es obligatorio', 'danger')
            return redirect(url_for('categorias.crear'))
        if Categoria.query.filter_by(nombre=nombre).first():
            flash('Ya existe una categoría con ese nombre', 'danger')
            return redirect(url_for('categorias.crear'))
        categoria = Categoria(nombre=nombre)
        db.session.add(categoria)
        db.session.commit()
        flash('Categoría creada exitosamente', 'success')
        return redirect(url_for('categorias.listar'))
    return render_template('categorias/editar.html', categoria=None)

@categorias_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    categoria = Categoria.query.get_or_404(id)
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        if not nombre:
            flash('El nombre es obligatorio', 'danger')
            return redirect(url_for('categorias.editar', id=id))
        existente = Categoria.query.filter_by(nombre=nombre).first()
        if existente and existente.id != id:
            flash('Ya existe otra categoría con ese nombre', 'danger')
            return redirect(url_for('categorias.editar', id=id))
        categoria.nombre = nombre
        db.session.commit()
        flash('Categoría actualizada', 'success')
        return redirect(url_for('categorias.listar'))
    return render_template('categorias/editar.html', categoria=categoria)

@categorias_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    categoria = Categoria.query.get_or_404(id)
    if categoria.productos:
        flash('No se puede eliminar una categoría con productos asociados', 'danger')
        return redirect(url_for('categorias.listar'))
    db.session.delete(categoria)
    db.session.commit()
    flash('Categoría eliminada', 'success')
    return redirect(url_for('categorias.listar'))

@categorias_bp.route('/api')
def api_listar():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    return jsonify([{'id': c.id, 'nombre': c.nombre} for c in categorias])