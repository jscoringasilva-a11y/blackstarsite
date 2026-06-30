from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'blackstar-portal-secret-2026')

db = SQLAlchemy(app)

# ─── MODELS ───────────────────────────────────────────────────────────────────

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    senha_hash = db.Column(db.String(300), nullable=False)
    cnpj = db.Column(db.String(20))
    pasta_drive_id = db.Column(db.String(200))  # ID da pasta no Google Drive
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    senha_hash = db.Column(db.String(300), nullable=False)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


# ─── SEED ADMIN PADRÃO ──────────────────────────────────────────────────────

def seed_admin():
    if Admin.query.count() == 0:
        admin = Admin(email='admin@blackstarcontabilidade.com.br')
        admin.set_senha('blackstar2026')  # TROCAR DEPOIS!
        db.session.add(admin)
        db.session.commit()


# ─── AUTH HELPERS ─────────────────────────────────────────────────────────────

def cliente_logado():
    return session.get('cliente_id')

def admin_logado():
    return session.get('admin_id')


# ─── ROTAS PÚBLICAS ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login_cliente'))


# ─── LOGIN CLIENTE ────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login_cliente():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        cliente = Cliente.query.filter_by(email=email, ativo=True).first()
        if cliente and cliente.check_senha(senha):
            session['cliente_id'] = cliente.id
            session['cliente_nome'] = cliente.nome
            return redirect(url_for('painel_cliente'))
        else:
            flash('E-mail ou senha incorretos.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout_cliente():
    session.pop('cliente_id', None)
    session.pop('cliente_nome', None)
    return redirect(url_for('login_cliente'))


@app.route('/painel')
def painel_cliente():
    if not cliente_logado():
        return redirect(url_for('login_cliente'))

    cliente = Cliente.query.get(session['cliente_id'])

    # Documentos virão do Google Drive (placeholder por enquanto)
    documentos = obter_documentos_drive(cliente.pasta_drive_id) if cliente.pasta_drive_id else []

    return render_template('painel_cliente.html', cliente=cliente, documentos=documentos)


def obter_documentos_drive(pasta_id):
    """
    Placeholder - será substituído pela integração real com Google Drive API.
    Por enquanto retorna estrutura de exemplo.
    """
    if not pasta_id:
        return {}
    # TODO: integrar com Google Drive API
    return {
        'Balancetes': [],
        'Guias': [],
        'Holerites': [],
        'Notas Fiscais': []
    }


# ─── LOGIN ADMIN ──────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_senha(senha):
            session['admin_id'] = admin.id
            return redirect(url_for('painel_admin'))
        else:
            flash('E-mail ou senha incorretos.', 'error')

    return render_template('login_admin.html')


@app.route('/admin/logout')
def logout_admin():
    session.pop('admin_id', None)
    return redirect(url_for('login_admin'))


@app.route('/admin')
def painel_admin():
    if not admin_logado():
        return redirect(url_for('login_admin'))

    clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template('painel_admin.html', clientes=clientes)


@app.route('/admin/cliente/novo', methods=['POST'])
def novo_cliente():
    if not admin_logado():
        return redirect(url_for('login_admin'))

    nome = request.form.get('nome')
    email = request.form.get('email', '').strip().lower()
    senha = request.form.get('senha')
    cnpj = request.form.get('cnpj', '')
    pasta_drive_id = request.form.get('pasta_drive_id', '')

    if Cliente.query.filter_by(email=email).first():
        flash('Já existe um cliente com esse e-mail.', 'error')
        return redirect(url_for('painel_admin'))

    cliente = Cliente(nome=nome, email=email, cnpj=cnpj, pasta_drive_id=pasta_drive_id)
    cliente.set_senha(senha)
    db.session.add(cliente)
    db.session.commit()

    flash(f'Cliente {nome} criado com sucesso!', 'success')
    return redirect(url_for('painel_admin'))


@app.route('/admin/cliente/editar/<int:id>', methods=['POST'])
def editar_cliente(id):
    if not admin_logado():
        return redirect(url_for('login_admin'))

    cliente = Cliente.query.get_or_404(id)
    cliente.nome = request.form.get('nome')
    cliente.cnpj = request.form.get('cnpj', '')
    cliente.pasta_drive_id = request.form.get('pasta_drive_id', '')

    nova_senha = request.form.get('senha')
    if nova_senha:
        cliente.set_senha(nova_senha)

    db.session.commit()
    flash('Cliente atualizado!', 'success')
    return redirect(url_for('painel_admin'))


@app.route('/admin/cliente/desativar/<int:id>', methods=['POST'])
def desativar_cliente(id):
    if not admin_logado():
        return redirect(url_for('login_admin'))

    cliente = Cliente.query.get_or_404(id)
    cliente.ativo = not cliente.ativo
    db.session.commit()
    return redirect(url_for('painel_admin'))


@app.route('/admin/cliente/excluir/<int:id>', methods=['POST'])
def excluir_cliente(id):
    if not admin_logado():
        return redirect(url_for('login_admin'))

    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente removido.', 'success')
    return redirect(url_for('painel_admin'))


# ─── INIT ─────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    seed_admin()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
