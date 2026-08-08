from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    productos = db.relationship('Producto', backref='categoria_obj', lazy=True)

    def __repr__(self):
        return self.nombre

class Mesa(db.Model):
    __tablename__ = 'mesas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    comensales = db.Column(db.Integer, nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='libre')
    pedidos = db.relationship('Pedido', backref='mesa', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'Mesa {self.numero}'

class Mozo(db.Model):
    __tablename__ = 'mozos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    activo = db.Column(db.Boolean, default=True)
    pedidos = db.relationship('Pedido', backref='mozo', lazy=True)

    def __repr__(self):
        return self.nombre

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    detalles = db.relationship('DetallePedido', backref='producto', lazy=True)

    @property
    def categoria(self):
        return self.categoria_obj.nombre if self.categoria_obj else ''

    def __repr__(self):
        return self.nombre

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=True)
    mozo_id = db.Column(db.Integer, db.ForeignKey('mozos.id'), nullable=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=True)
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)
    estado = db.Column(db.String(20), nullable=False, default='abierto')
    total = db.Column(db.Float, default=0.0)
    tipo = db.Column(db.String(20), nullable=False, default='mesa')
    preticket_impreso = db.Column(db.Boolean, default=False)
    detalles = db.relationship('DetallePedido', backref='pedido', lazy=True, cascade='all, delete-orphan')
    pagos = db.relationship('Pago', backref='pedido', lazy=True, cascade='all, delete-orphan')

    def calcular_total(self):
        self.total = sum(d.subtotal() for d in self.detalles)
        return self.total

    @property
    def detalles_agrupados(self):
        grupos = {}
        for d in self.detalles:
            key = d.producto_id
            if key in grupos:
                grupos[key]['cantidad'] += d.cantidad
                if d.notas and d.notas not in grupos[key]['notas_list']:
                    grupos[key]['notas_list'].append(d.notas)
            else:
                grupos[key] = {
                    'producto': d.producto,
                    'producto_id': d.producto_id,
                    'cantidad': d.cantidad,
                    'precio_unitario': d.precio_unitario,
                    'subtotal': 0,
                    'notas_list': [d.notas] if d.notas else []
                }
            grupos[key]['subtotal'] = grupos[key]['cantidad'] * grupos[key]['precio_unitario']
        result = []
        for g in grupos.values():
            g['notas'] = ', '.join(g['notas_list']) if g['notas_list'] else ''
            result.append(g)
        return result

    def __repr__(self):
        return f'Pedido #{self.id}'

class DetallePedido(db.Model):
    __tablename__ = 'detalles_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False, default=1.0)
    precio_unitario = db.Column(db.Float, nullable=False)
    notas = db.Column(db.String(200))

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __repr__(self):
        cant_str = str(int(self.cantidad)) if self.cantidad and float(self.cantidad).is_integer() else str(self.cantidad)
        return f'{cant_str}x {self.producto.nombre}'

class JornadaLaboral(db.Model):
    __tablename__ = 'jornadas'
    id = db.Column(db.Integer, primary_key=True)
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    activa = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'Jornada #{self.id} ({self.fecha_inicio.strftime("%d/%m/%Y")})'

class Configuracion(db.Model):
    __tablename__ = 'configuracion'
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(500), nullable=True)

    @classmethod
    def obtener(cls, clave, default=''):
        c = cls.query.filter_by(clave=clave).first()
        return c.valor if c else default

    @classmethod
    def establecer(cls, clave, valor):
        c = cls.query.filter_by(clave=clave).first()
        if c:
            c.valor = valor
        else:
            c = cls(clave=clave, valor=valor)
            db.session.add(c)
        db.session.commit()

    def __repr__(self):
        return f'{self.clave}={self.valor}'

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=True)
    monto = db.Column(db.Float, nullable=False)
    monto_recibido = db.Column(db.Float, nullable=True)
    vuelto = db.Column(db.Float, nullable=True)
    metodo_pago = db.Column(db.String(20), nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f'Pago ${self.monto} - {self.metodo_pago}'