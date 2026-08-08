from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Pedido, DetallePedido, Mesa, Mozo, Producto, JornadaLaboral, Configuracion
from datetime import datetime

pedidos_bp = Blueprint('pedidos', __name__)

@pedidos_bp.route('/')
def listar():
    pedidos = Pedido.query.order_by(Pedido.fecha_hora.desc()).all()
    return render_template('pedidos/listar.html', pedidos=pedidos)

@pedidos_bp.route('/mesa/<int:mesa_id>')
def mesa(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    pedido = Pedido.query.filter_by(mesa_id=mesa_id, estado='abierto').first()
    mozos = Mozo.query.filter_by(activo=True).all()
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    return render_template('pedidos/mesa.html', mesa=mesa, pedido=pedido, mozos=mozos, productos=productos)

@pedidos_bp.route('/mesa/<int:mesa_id>/abrir', methods=['POST'])
def abrir(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    if mesa.estado == 'ocupada':
        flash('La mesa ya está ocupada', 'warning')
        return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))
    mozo_id = request.form.get('mozo_id', type=int)
    comensales = request.form.get('comensales', type=int)
    jornada = JornadaLaboral.query.filter_by(activa=True).first()
    pedido = Pedido(mesa_id=mesa_id, mozo_id=mozo_id, tipo='mesa', jornada_id=jornada.id if jornada else None)
    if comensales and comensales > 0:
        mesa.comensales = comensales
    mesa.estado = 'ocupada'
    db.session.add(pedido)
    db.session.commit()
    flash('Mesa abierta', 'success')
    return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))

@pedidos_bp.route('/mesa/<int:mesa_id>/editar', methods=['POST'])
def editar_mesa(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    pedido = Pedido.query.filter_by(mesa_id=mesa_id, estado='abierto').first()
    if not pedido:
        flash('No hay un pedido abierto en esta mesa', 'danger')
        return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))
    mozo_id = request.form.get('mozo_id', type=int)
    comensales = request.form.get('comensales', type=int)
    if mozo_id:
        pedido.mozo_id = mozo_id
    if comensales is not None and comensales > 0:
        mesa.comensales = comensales
    elif comensales is not None:
        mesa.comensales = None
    pedido.preticket_impreso = False
    db.session.commit()
    flash('Datos actualizados', 'success')
    return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))

@pedidos_bp.route('/mesa/<int:mesa_id>/agregar', methods=['POST'])
def agregar(mesa_id):
    pedido = Pedido.query.filter_by(mesa_id=mesa_id, estado='abierto').first()
    if not pedido:
        flash('No hay un pedido abierto en esta mesa', 'danger')
        return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))
    producto_id = request.form.get('producto_id', type=int)
    cantidad = request.form.get('cantidad', 1.0, type=float)
    precio_custom = request.form.get('precio_unitario', type=float)
    notas = request.form.get('notas', '').strip()
    if not producto_id:
        flash('Debe seleccionar un producto', 'danger')
        return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))
    if cantidad is None or cantidad <= 0:
        flash('La cantidad debe ser mayor a 0', 'danger')
        return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))
    producto = Producto.query.get_or_404(producto_id)
    precio_unitario = precio_custom if (precio_custom is not None and precio_custom >= 0) else producto.precio
    detalle = DetallePedido(
        pedido_id=pedido.id,
        producto_id=producto_id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        notas=notas
    )
    db.session.add(detalle)
    db.session.flush()
    pedido.calcular_total()
    pedido.preticket_impreso = False
    db.session.commit()
    flash('Producto agregado', 'success')
    return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))

@pedidos_bp.route('/detalle/<int:detalle_id>/editar', methods=['POST'])
def editar_detalle(detalle_id):
    detalle = DetallePedido.query.get_or_404(detalle_id)
    pedido = detalle.pedido
    cantidad = request.form.get('cantidad', detalle.cantidad, type=float)
    precio_custom = request.form.get('precio_unitario', type=float)
    notas = request.form.get('notas', '').strip()
    if cantidad is None or cantidad <= 0:
        flash('La cantidad debe ser mayor a 0', 'danger')
        return redirect(url_for('pedidos.mesa_mostrador', pedido_id=pedido.id) if pedido.tipo == 'mostrador' else url_for('pedidos.mesa', mesa_id=pedido.mesa_id))
    detalle.cantidad = cantidad
    if precio_custom is not None and precio_custom >= 0:
        detalle.precio_unitario = precio_custom
    if 'notas' in request.form:
        detalle.notas = notas
    db.session.flush()
    pedido.calcular_total()
    pedido.preticket_impreso = False
    db.session.commit()
    flash('Item actualizado', 'success')
    return redirect(url_for('pedidos.mesa_mostrador', pedido_id=pedido.id) if pedido.tipo == 'mostrador' else url_for('pedidos.mesa', mesa_id=pedido.mesa_id))

@pedidos_bp.route('/detalle/<int:detalle_id>/eliminar', methods=['POST'])
def eliminar_detalle(detalle_id):
    detalle = DetallePedido.query.get_or_404(detalle_id)
    pedido = detalle.pedido
    db.session.delete(detalle)
    db.session.flush()
    pedido.calcular_total()
    pedido.preticket_impreso = False
    db.session.commit()
    flash('Item eliminado', 'success')
    if pedido.tipo == 'mostrador':
        return redirect(url_for('pedidos.mesa_mostrador', pedido_id=pedido.id))
    return redirect(url_for('pedidos.mesa', mesa_id=pedido.mesa_id))

@pedidos_bp.route('/mesa/<int:mesa_id>/preticket')
def preticket(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    pedido = Pedido.query.filter_by(mesa_id=mesa_id, estado='abierto').first()
    if not pedido:
        flash('No hay pedido abierto', 'warning')
        return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))
    if not pedido.detalles:
        return redirect(url_for('pedidos.mesa', mesa_id=mesa_id))
    pedido.preticket_impreso = True
    db.session.commit()
    mensaje_ticket = Configuracion.obtener('mensaje_ticket', 'Gracias por su visita')
    return render_template('pedidos/preticket.html', mesa=mesa, pedido=pedido, mensaje_ticket=mensaje_ticket)

@pedidos_bp.route('/mostrador')
def mostrador():
    pedido = Pedido.query.filter_by(tipo='mostrador', estado='abierto').first()
    if not pedido:
        jornada = JornadaLaboral.query.filter_by(activa=True).first()
        pedido = Pedido(tipo='mostrador', jornada_id=jornada.id if jornada else None)
        db.session.add(pedido)
        db.session.commit()
    return redirect(url_for('pedidos.mesa_mostrador', pedido_id=pedido.id))

@pedidos_bp.route('/mostrador/<int:pedido_id>')
def mesa_mostrador(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.tipo != 'mostrador':
        flash('Pedido inválido', 'danger')
        return redirect(url_for('pedidos.mostrador'))
    mozos = Mozo.query.filter_by(activo=True).all()
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    return render_template('pedidos/mesa.html', mesa=None, pedido=pedido, mozos=mozos, productos=productos, mostrador=True)

@pedidos_bp.route('/mostrador/<int:pedido_id>/agregar', methods=['POST'])
def agregar_mostrador(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.tipo != 'mostrador':
        flash('Pedido inválido', 'danger')
        return redirect(url_for('pedidos.mostrador'))
    producto_id = request.form.get('producto_id', type=int)
    cantidad = request.form.get('cantidad', 1.0, type=float)
    precio_custom = request.form.get('precio_unitario', type=float)
    notas = request.form.get('notas', '').strip()
    if not producto_id:
        flash('Debe seleccionar un producto', 'danger')
        return redirect(url_for('pedidos.mesa_mostrador', pedido_id=pedido_id))
    if cantidad is None or cantidad <= 0:
        flash('La cantidad debe ser mayor a 0', 'danger')
        return redirect(url_for('pedidos.mesa_mostrador', pedido_id=pedido_id))
    producto = Producto.query.get_or_404(producto_id)
    precio_unitario = precio_custom if (precio_custom is not None and precio_custom >= 0) else producto.precio
    detalle = DetallePedido(
        pedido_id=pedido.id,
        producto_id=producto_id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        notas=notas
    )
    db.session.add(detalle)
    db.session.flush()
    pedido.calcular_total()
    pedido.preticket_impreso = False
    db.session.commit()
    flash('Producto agregado', 'success')
    return redirect(url_for('pedidos.mesa_mostrador', pedido_id=pedido_id))

@pedidos_bp.route('/mostrador/<int:pedido_id>/pagar')
def pagar_mostrador(pedido_id):
    return redirect(url_for('pagos.cobrar', pedido_id=pedido_id))