from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Producto, Categoria

productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/')
def listar():
    productos = Producto.query.join(Categoria).order_by(Categoria.nombre, Producto.nombre).all()
    return render_template('productos/listar.html', productos=productos)

@productos_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        precio = request.form.get('precio', type=float)
        categoria_id = request.form.get('categoria_id', type=int)
        if not nombre:
            flash('El nombre es obligatorio', 'danger')
            return redirect(url_for('productos.crear'))
        if precio is None or precio < 0:
            flash('El precio debe ser un número válido', 'danger')
            return redirect(url_for('productos.crear'))
        if not categoria_id:
            flash('Debe seleccionar una categoría', 'danger')
            return redirect(url_for('productos.crear'))
        if not Categoria.query.get(categoria_id):
            flash('La categoría seleccionada no existe', 'danger')
            return redirect(url_for('productos.crear'))
        producto = Producto(nombre=nombre, precio=precio, categoria_id=categoria_id)
        db.session.add(producto)
        db.session.commit()
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('productos.listar'))
    return render_template('productos/editar.html', producto=None, categorias=categorias)

@productos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    producto = Producto.query.get_or_404(id)
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        precio = request.form.get('precio', type=float)
        categoria_id = request.form.get('categoria_id', type=int)
        if not nombre:
            flash('El nombre es obligatorio', 'danger')
            return redirect(url_for('productos.editar', id=id))
        if precio is None or precio < 0:
            flash('El precio debe ser un número válido', 'danger')
            return redirect(url_for('productos.editar', id=id))
        if not categoria_id or not Categoria.query.get(categoria_id):
            flash('Debe seleccionar una categoría válida', 'danger')
            return redirect(url_for('productos.editar', id=id))
        producto.nombre = nombre
        producto.precio = precio
        producto.categoria_id = categoria_id
        producto.activo = 'activo' in request.form
        db.session.commit()
        flash('Producto actualizado', 'success')
        return redirect(url_for('productos.listar'))
    return render_template('productos/editar.html', producto=producto, categorias=categorias)

@productos_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado', 'success')
    return redirect(url_for('productos.listar'))

@productos_bp.route('/api')
def api_listar():
    categoria_id = request.args.get('categoria_id', type=int)
    query = Producto.query.filter_by(activo=True)
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    productos = query.order_by(Producto.nombre).all()
    return jsonify([{
        'id': p.id,
        'nombre': p.nombre,
        'precio': p.precio,
        'categoria': p.categoria
    } for p in productos])