from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Pedido, Pago, Mesa, JornadaLaboral, Configuracion
from datetime import datetime

pagos_bp = Blueprint('pagos', __name__)

@pagos_bp.route('/cobrar/<int:pedido_id>')
def cobrar(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.estado != 'abierto':
        flash('Este pedido ya está cerrado', 'warning')
        return redirect(url_for('pedidos.mesa', mesa_id=pedido.mesa_id) if pedido.tipo == 'mesa' else url_for('pedidos.mostrador'))
    if pedido.tipo == 'mesa' and not pedido.preticket_impreso:
        flash('Debe imprimir la pre-cuenta antes de cobrar', 'warning')
        return redirect(url_for('pedidos.mesa', mesa_id=pedido.mesa_id))
    if not pedido.detalles:
        flash('No hay productos en el pedido', 'warning')
        return redirect(url_for('pedidos.mesa', mesa_id=pedido.mesa_id) if pedido.tipo == 'mesa' else url_for('pedidos.mostrador'))
    return render_template('pagos/cobrar.html', pedido=pedido)

@pagos_bp.route('/cobrar/<int:pedido_id>/procesar', methods=['POST'])
def procesar(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.estado != 'abierto':
        flash('Este pedido ya está cerrado', 'warning')
        return redirect(url_for('pedidos.mesa', mesa_id=pedido.mesa_id) if pedido.tipo == 'mesa' else url_for('pedidos.mostrador'))
    metodo = request.form.get('metodo_pago')
    monto_recibido = request.form.get('monto_recibido', type=float)
    if not metodo:
        flash('Debe seleccionar un método de pago', 'danger')
        return redirect(url_for('pagos.cobrar', pedido_id=pedido_id))
    if monto_recibido is None or monto_recibido < pedido.total:
        flash('El monto ingresado debe ser igual o mayor al total del cobro', 'danger')
        return redirect(url_for('pagos.cobrar', pedido_id=pedido_id))
    if metodo != 'efectivo':
        monto_recibido = pedido.total
    jornada = JornadaLaboral.query.filter_by(activa=True).first()
    vuelto = round(monto_recibido - pedido.total, 2) if (monto_recibido and monto_recibido >= pedido.total) else 0.0
    pago = Pago(
        pedido_id=pedido.id,
        monto=pedido.total,
        monto_recibido=monto_recibido,
        vuelto=vuelto,
        metodo_pago=metodo,
        jornada_id=jornada.id if jornada else None
    )
    db.session.add(pago)
    if pedido.tipo == 'mesa':
        mesa = Mesa.query.get(pedido.mesa_id)
        if mesa:
            mesa.estado = 'libre'
    pedido.estado = 'cerrado'
    db.session.commit()
    flash('Pago registrado exitosamente', 'success')
    return redirect(url_for('pagos.comprobante', pago_id=pago.id))

@pagos_bp.route('/comprobante/<int:pago_id>')
def comprobante(pago_id):
    pago = Pago.query.get_or_404(pago_id)
    mensaje_ticket = Configuracion.obtener('mensaje_ticket', 'Gracias por su visita')
    return render_template('pagos/comprobante.html', pago=pago, mensaje_ticket=mensaje_ticket)

@pagos_bp.route('/historial')
def historial():
    pagos = Pago.query.order_by(Pago.fecha_hora.desc()).all()
    return render_template('pagos/historial.html', pagos=pagos)