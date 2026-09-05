from flask import Blueprint, render_template, request, url_for, redirect, flash
from models import db, Pedido, DetallePedido, Pago, Producto, Mesa, JornadaLaboral, Categoria
from datetime import datetime, date, timedelta

estadisticas_bp = Blueprint('estadisticas', __name__)


@estadisticas_bp.route('/')
def index():
    modo = request.args.get('modo', 'jornada')
    jornada_id = request.args.get('jornada_id', type=int)
    fecha_desde_str = request.args.get('fecha_desde')
    fecha_hasta_str = request.args.get('fecha_hasta')
    producto_id = request.args.get('producto_id', type=int)

    todas_jornadas = JornadaLaboral.query.order_by(JornadaLaboral.id.desc()).all()

    # Determinar jornadas incluidas en el análisis
    jornada = None
    fecha_desde = None
    fecha_hasta = None
    if modo == 'jornada':
        if jornada_id:
            jornada = JornadaLaboral.query.get(jornada_id)
        if not jornada:
            jornada = JornadaLaboral.query.filter_by(activa=True).first()
        if not jornada:
            jornada = JornadaLaboral.query.order_by(JornadaLaboral.id.desc()).first()
        if not jornada:
            flash('No hay jornadas registradas para analizar', 'warning')
            return redirect(url_for('index'))
        jornadas_ids = [jornada.id]
        periodo_label = f'Jornada #{jornada.id} ({jornada.fecha_inicio.strftime("%d/%m/%Y")})'
    else:
        try:
            fecha_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date() if fecha_desde_str else None
        except (ValueError, TypeError):
            fecha_desde = None
        try:
            fecha_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date() if fecha_hasta_str else None
        except (ValueError, TypeError):
            fecha_hasta = None
        if not fecha_desde or not fecha_hasta:
            flash('Debe indicar ambas fechas del rango', 'danger')
            return redirect(url_for('estadisticas.index', modo='jornada'))
        if fecha_hasta < fecha_desde:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
        inicio_dt = datetime.combine(fecha_desde, datetime.min.time())
        fin_dt = datetime.combine(fecha_hasta, datetime.max.time())
        jornadas_rango = JornadaLaboral.query.filter(
            JornadaLaboral.fecha_inicio <= fin_dt,
            db.func.coalesce(JornadaLaboral.fecha_fin, datetime.now()) >= inicio_dt
        ).all()
        if not jornadas_rango:
            flash('No hay jornadas dentro del rango de fechas seleccionado', 'warning')
            return redirect(url_for('estadisticas.index', modo='jornada'))
        jornadas_ids = [j.id for j in jornadas_rango]
        periodo_label = f'{fecha_desde.strftime("%d/%m/%Y")} a {fecha_hasta.strftime("%d/%m/%Y")} ({len(jornadas_ids)} jornada(s))'

    # Pedidos cerrados y abiertos (en curso) dentro de las jornadas seleccionadas
    pedidos = Pedido.query.filter(
        Pedido.jornada_id.in_(jornadas_ids),
        Pedido.estado.in_(['cerrado', 'abierto'])
    ).all()
    pedido_ids = [p.id for p in pedidos]
    pedidos_cerrados_ids = [p.id for p in pedidos if p.estado == 'cerrado']
    pedidos_abiertos_ids = [p.id for p in pedidos if p.estado == 'abierto']

    # Totales generales: cobrado (pagos registrados) + pendiente (pedidos en curso)
    total_cobrado = 0
    if pedidos_cerrados_ids:
        total_cobrado = db.session.query(db.func.coalesce(db.func.sum(Pago.monto), 0)).filter(
            Pago.pedido_id.in_(pedidos_cerrados_ids)
        ).scalar() or 0
    total_pendiente = 0
    if pedidos_abiertos_ids:
        total_pendiente = db.session.query(
            db.func.coalesce(db.func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0)
        ).filter(DetallePedido.pedido_id.in_(pedidos_abiertos_ids)
        ).scalar() or 0
    total_ventas = total_cobrado + total_pendiente
    cantidad_pedidos = len(pedidos)
    cantidad_cerrados = len(pedidos_cerrados_ids)
    cantidad_abiertos = len(pedidos_abiertos_ids)
    mesas_pedidos_ids = [p.mesa_id for p in pedidos if p.mesa_id]
    if mesas_pedidos_ids:
        total_comensales = db.session.query(db.func.coalesce(db.func.sum(Mesa.comensales), 0)).filter(
            Mesa.id.in_(mesas_pedidos_ids)
        ).scalar() or 0
    else:
        total_comensales = 0

    # Top productos por cantidad vendida
    top_productos = []
    if pedido_ids:
        top_productos = db.session.query(
            Producto.nombre,
            db.func.sum(DetallePedido.cantidad),
            db.func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario)
        ).join(DetallePedido, DetallePedido.producto_id == Producto.id
        ).filter(DetallePedido.pedido_id.in_(pedido_ids)
        ).group_by(Producto.id
        ).order_by(db.func.sum(DetallePedido.cantidad).desc()
        ).limit(10).all()

    # Ventas por categoría (monto)
    ventas_categoria = []
    if pedido_ids:
        ventas_categoria = db.session.query(
            Categoria.nombre,
            db.func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario)
        ).join(Producto, Producto.categoria_id == Categoria.id
        ).join(DetallePedido, DetallePedido.producto_id == Producto.id
        ).filter(DetallePedido.pedido_id.in_(pedido_ids)
        ).group_by(Categoria.id
        ).order_by(db.func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario).desc()
        ).all()

    # Mostrador vs Mesas (monto desde detalles: incluye pedidos en curso)
    ventas_por_tipo = db.session.query(
        Pedido.tipo,
        db.func.coalesce(db.func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0),
        db.func.count(db.distinct(Pedido.id))
    ).join(DetallePedido, DetallePedido.pedido_id == Pedido.id
    ).filter(Pedido.jornada_id.in_(jornadas_ids), Pedido.estado.in_(['cerrado', 'abierto'])
    ).group_by(Pedido.tipo).all()

    # Evolución de ventas por día (desde detalles: incluye pedidos en curso)
    ventas_por_dia = db.session.query(
        db.func.date(Pedido.fecha_hora),
        db.func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario)
    ).join(DetallePedido, DetallePedido.pedido_id == Pedido.id
    ).filter(Pedido.jornada_id.in_(jornadas_ids), Pedido.estado.in_(['cerrado', 'abierto'])
    ).group_by(db.func.date(Pedido.fecha_hora)
    ).order_by(db.func.date(Pedido.fecha_hora)
    ).all() if pedido_ids else []

    # Producto específico
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    producto_info = None
    if producto_id and pedido_ids:
        prod = Producto.query.get(producto_id)
        if prod:
            cant_vendida = db.session.query(db.func.coalesce(db.func.sum(DetallePedido.cantidad), 0)).filter(
                DetallePedido.producto_id == producto_id,
                DetallePedido.pedido_id.in_(pedido_ids)
            ).scalar() or 0
            monto_vendido = db.session.query(db.func.coalesce(db.func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario), 0)).filter(
                DetallePedido.producto_id == producto_id,
                DetallePedido.pedido_id.in_(pedido_ids)
            ).scalar() or 0
            producto_info = {
                'nombre': prod.nombre,
                'cantidad': cant_vendida,
                'monto': monto_vendido
            }

    return render_template('estadisticas.html',
        modo=modo,
        jornada=jornada,
        todas_jornadas=todas_jornadas,
        fecha_desde=fecha_desde.strftime('%Y-%m-%d') if fecha_desde else '',
        fecha_hasta=fecha_hasta.strftime('%Y-%m-%d') if fecha_hasta else '',
        periodo_label=periodo_label,
        total_ventas=total_ventas,
        total_cobrado=total_cobrado,
        total_pendiente=total_pendiente,
        cantidad_pedidos=cantidad_pedidos,
        cantidad_cerrados=cantidad_cerrados,
        cantidad_abiertos=cantidad_abiertos,
        total_comensales=total_comensales,
        top_productos=top_productos,
        ventas_categoria=ventas_categoria,
        ventas_por_tipo=ventas_por_tipo,
        ventas_por_dia=ventas_por_dia,
        productos=productos,
        producto_id=producto_id,
        producto_info=producto_info
    )
