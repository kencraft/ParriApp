import os
from flask import Flask, render_template, request, flash, redirect, url_for
from models import db, Mesa, Pedido, Pago, Configuracion
from routes.mesas import mesas_bp
from routes.mozos import mozos_bp
from routes.productos import productos_bp
from routes.pedidos import pedidos_bp
from routes.pagos import pagos_bp
from routes.categorias import categorias_bp
from routes.jornadas import jornadas_bp
from routes.configuracion import configuracion_bp
from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'parri-restaurant-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parri.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

app.register_blueprint(mesas_bp, url_prefix='/mesas')
app.register_blueprint(mozos_bp, url_prefix='/mozos')
app.register_blueprint(productos_bp, url_prefix='/productos')
app.register_blueprint(pedidos_bp, url_prefix='/pedidos')
app.register_blueprint(pagos_bp, url_prefix='/pagos')
app.register_blueprint(categorias_bp, url_prefix='/categorias')
app.register_blueprint(jornadas_bp, url_prefix='/jornadas')
app.register_blueprint(configuracion_bp, url_prefix='/configuracion')

@app.route('/')
def index():
    from models import JornadaLaboral
    jornada_activa = JornadaLaboral.query.filter_by(activa=True).first()
    mesas = Mesa.query.order_by(Mesa.numero).all()
    mesas_data = []
    for m in mesas:
        pedido_activo = None
        mozo_nombre = None
        if m.estado == 'ocupada':
            pedido_activo = Pedido.query.filter_by(mesa_id=m.id, estado='abierto').first()
            if pedido_activo and pedido_activo.mozo:
                mozo_nombre = pedido_activo.mozo.nombre
        mesas_data.append({
            'id': m.id,
            'numero': m.numero,
            'estado': m.estado,
            'comensales': m.comensales,
            'mozo': mozo_nombre,
            'preticket_impreso': pedido_activo.preticket_impreso if pedido_activo else False
        })
    mesas_ocupadas = sum(1 for m in mesas if m.estado == 'ocupada')
    mesas_libres = sum(1 for m in mesas if m.estado == 'libre')
    if jornada_activa:
        pedidos_hoy = Pedido.query.filter(
            Pedido.jornada_id == jornada_activa.id,
            Pedido.estado == 'cerrado'
        ).count()
        total_hoy = db.session.query(db.func.sum(Pago.monto)).filter(
            Pago.jornada_id == jornada_activa.id
        ).scalar() or 0
    else:
        pedidos_hoy = 0
        total_hoy = 0
    total_comensales = db.session.query(db.func.coalesce(db.func.sum(Mesa.comensales), 0)).filter(
        Mesa.estado == 'ocupada'
    ).scalar() or 0
    return render_template('index.html',
        mesas=mesas_data,
        mesas_ocupadas=mesas_ocupadas,
        mesas_libres=mesas_libres,
        pedidos_hoy=pedidos_hoy,
        total_hoy=total_hoy,
        total_comensales=total_comensales,
        jornada_activa=jornada_activa
    )

@app.route('/resumen')
def resumen():
    from models import JornadaLaboral
    jornada_id = request.args.get('jornada_id', type=int)
    jornada = None
    if jornada_id:
        jornada = JornadaLaboral.query.get(jornada_id)
    if not jornada:
        jornada = JornadaLaboral.query.filter_by(activa=True).first()
    if not jornada:
        jornada = JornadaLaboral.query.order_by(JornadaLaboral.id.desc()).first()
    if not jornada:
        flash('No hay jornadas registradas para mostrar', 'warning')
        return redirect(url_for('index'))
    todas_jornadas = JornadaLaboral.query.order_by(JornadaLaboral.id.desc()).all()
    pedidos_jornada = Pedido.query.filter(
        Pedido.jornada_id == jornada.id,
        Pedido.estado == 'cerrado'
    ).all()
    total_ventas = db.session.query(db.func.sum(Pago.monto)).filter(
        Pago.jornada_id == jornada.id
    ).scalar() or 0
    pagos_por_metodo = db.session.query(
        Pago.metodo_pago, db.func.sum(Pago.monto), db.func.count(Pago.id)
    ).filter(
        Pago.jornada_id == jornada.id
    ).group_by(Pago.metodo_pago).all()
    total_comensales = db.session.query(db.func.coalesce(db.func.sum(Mesa.comensales), 0)).filter(
        Mesa.id.in_(db.session.query(Pedido.mesa_id).filter(
            Pedido.jornada_id == jornada.id,
            Pedido.estado == 'cerrado',
            Pedido.mesa_id.isnot(None)
        ))
    ).scalar() or 0
    cantidad_pedidos = len(pedidos_jornada)
    mensaje_ticket = Configuracion.obtener('mensaje_ticket', 'Gracias por su visita')
    return render_template('resumen.html',
        jornada=jornada,
        todas_jornadas=todas_jornadas,
        total_ventas=total_ventas,
        pagos_por_metodo=pagos_por_metodo,
        total_comensales=total_comensales,
        cantidad_pedidos=cantidad_pedidos,
        mensaje_ticket=mensaje_ticket
    )

@app.route('/jornadas')
def listar_jornadas():
    from models import JornadaLaboral
    jornadas = JornadaLaboral.query.order_by(JornadaLaboral.id.desc()).all()
    return render_template('jornadas/listar.html', jornadas=jornadas)

@app.template_filter('currency')
def currency_filter(value):
    if value is None:
        return '$0,00'
    s = f'{value:,.2f}'
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'${s}'

@app.template_filter('qty')
def qty_filter(value):
    if value is None:
        return '0'
    try:
        val = float(value)
        if val.is_integer():
            return str(int(val))
        return f'{val:.3f}'.rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return str(value)

with app.app_context():
    db.create_all()
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE pagos ADD COLUMN monto_recibido FLOAT"))
            conn.commit()
    except Exception:
        pass
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE pagos ADD COLUMN vuelto FLOAT"))
            conn.commit()
    except Exception:
        pass
    try:
        with db.engine.connect() as conn:
            info = conn.execute(db.text("PRAGMA table_info(detalles_pedido)")).fetchall()
            for col in info:
                if col[1] == 'cantidad' and 'INT' in str(col[2]).upper():
                    conn.execute(db.text("""
                        CREATE TABLE detalles_pedido_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            pedido_id INTEGER NOT NULL,
                            producto_id INTEGER NOT NULL,
                            cantidad REAL NOT NULL DEFAULT 1.0,
                            precio_unitario REAL NOT NULL,
                            notas VARCHAR(200),
                            FOREIGN KEY(pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
                            FOREIGN KEY(producto_id) REFERENCES productos(id)
                        )
                    """))
                    conn.execute(db.text("INSERT INTO detalles_pedido_new (id, pedido_id, producto_id, cantidad, precio_unitario, notas) SELECT id, pedido_id, producto_id, cantidad, precio_unitario, notas FROM detalles_pedido"))
                    conn.execute(db.text("DROP TABLE detalles_pedido"))
                    conn.execute(db.text("ALTER TABLE detalles_pedido_new RENAME TO detalles_pedido"))
                    conn.commit()
                    break
    except Exception as e:
        print("Migration error:", e)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)