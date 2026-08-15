import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Categoria, Producto

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def leer_csv(nombre):
    ruta = os.path.join(BASE_DIR, nombre)
    with open(ruta, encoding='cp1252') as f:
        return list(csv.DictReader(f, delimiter=';'))


with app.app_context():
    db.drop_all()
    db.create_all()

    cat_rows = leer_csv('categorias.csv')
    mapa_categoria = {}
    for c in cat_rows:
        nombre = c['name'].strip()
        obj = Categoria(nombre=nombre)
        db.session.add(obj)
        db.session.flush()
        mapa_categoria[c['rubro_id']] = obj.id

    prod_rows = leer_csv('productos.csv')
    importados = 0
    for p in prod_rows:
        nombre = p['name'].strip()
        precio_str = p['price'].strip().replace(',', '.')
        try:
            precio = float(precio_str)
        except ValueError:
            print(f'Precio invalido para {nombre}: {p["price"]}')
            continue
        rubro_id = p['rubro_id'].strip()
        categoria_id = mapa_categoria.get(rubro_id)
        if categoria_id is None:
            print(f'Categoria no encontrada para {nombre} (rubro_id={rubro_id})')
            continue
        db.session.add(Producto(nombre=nombre, precio=precio, categoria_id=categoria_id, activo=True))
        importados += 1

    db.session.commit()

    print(f'Categorias importadas: {len(mapa_categoria)}')
    print(f'Productos importados: {importados}')
    print(f'Total productos en BD: {Producto.query.count()}')
    print(f'Total categorias en BD: {Categoria.query.count()}')
