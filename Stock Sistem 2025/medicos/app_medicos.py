from flask import Flask, render_template, request, redirect, url_for, flash, session
from PIL import Image
from io import BytesIO
import base64
import pandas as pd
from datetime import datetime
import os

# Configuração inicial
app = Flask(__name__, template_folder='templates')
app.secret_key = 'chave_secreta_medicos_456'

# Usuários médicos (hardcoded para exemplo)
MEDICOS = {
    'medico1': 'senha_medico1',
    'medico2': 'senha_medico2'
}

# Funções Auxiliares
def carregar_imagem_fundo():
    try:
        caminho = os.path.join('..', 'estoque', 'static', 'fundo.png')
        return Image.open(caminho)
    except FileNotFoundError:
        return None

def imagem_to_base64(imagem):
    if imagem is None:
        return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    buffered = BytesIO()
    imagem.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def carregar_produtos():
    filepath = os.path.join('..', 'estoque', 'produtos.csv')
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        return pd.DataFrame(columns=['ID', 'Nome', 'Tipo', 'Grupo', 'Volume', 'Temperatura'])

def carregar_pedidos():
    filepath = os.path.join('..', 'estoque', 'pedidos.csv')
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        return pd.DataFrame(columns=['Codigo_Pedido', 'ID_Produto', 'Produto', 'Quantidade', 'Solicitante', 'Departamento', 'DataPedido', 'Status'])

def formatar_data_brasil(data):
    return data.strftime('%d/%m/%Y')

def obter_id_por_nome(df, nome):
    produto = df[df['Nome'] == nome]
    return produto.iloc[0]['ID'] if not produto.empty else None

def gerar_codigo_pedido():
    pedidos_df = carregar_pedidos()
    return f"PED{len(pedidos_df) + 1:06d}"

# Injetar imagem de fundo em todos os templates
@app.context_processor
def inject_imagem_fundo():
    imagem_fundo = carregar_imagem_fundo()
    return dict(imagem_fundo=imagem_to_base64(imagem_fundo))

def login_required(f):
    def wrap(*args, **kwargs):
        if 'logado' not in session or not session['logado']:
            flash('❌ Faça login para acessar essa página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Rotas
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logado' in session and session['logado']:
        return redirect(url_for('fazer_pedido'))
    if request.method == 'POST':
        usuario = request.form.get('usuario', '')
        senha = request.form.get('senha', '')
        if usuario in MEDICOS and MEDICOS[usuario] == senha:
            session['logado'] = True
            session['usuario'] = usuario
            flash('✅ Login bem-sucedido!', 'success')
            return redirect(url_for('fazer_pedido'))
        flash('❌ Usuário ou senha incorretos.', 'error')
    return render_template('login_medicos.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logado', None)
    session.pop('usuario', None)
    flash('✅ Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/pedido', methods=['GET', 'POST'])
@login_required
def fazer_pedido():
    produtos_df = carregar_produtos()
    produtos = produtos_df['Nome'].unique().tolist() if not produtos_df.empty else []

    if request.method == 'POST':
        try:
            pedido_data = {
                'Codigo_Pedido': gerar_codigo_pedido(),
                'produto': request.form.get('produto', '').strip(),
                'quantidade': int(request.form.get('quantidade', 0)),
                'solicitante': session['usuario'],
                'departamento': 'Médico',
                'data_pedido': formatar_data_brasil(datetime.now()),
                'status': 'Pendente'
            }

            if not pedido_data['produto'] or pedido_data['quantidade'] <= 0:
                flash('❌ Produto e quantidade são obrigatórios e a quantidade deve ser maior que zero.', 'error')
                return render_template('fazer_pedido.html', produtos=produtos)

            id_produto = obter_id_por_nome(produtos_df, pedido_data['produto'])
            if id_produto is None:
                flash('❌ Produto não encontrado.', 'error')
                return render_template('fazer_pedido.html', produtos=produtos)

            filepath = os.path.join('..', 'estoque', 'pedidos.csv')
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write('Codigo_Pedido,ID_Produto,Produto,Quantidade,Solicitante,Departamento,DataPedido,Status\n')

            with open(filepath, 'a') as f:
                f.write(f"{pedido_data['Codigo_Pedido']},{id_produto},{pedido_data['produto']},{pedido_data['quantidade']},{pedido_data['solicitante']},{pedido_data['departamento']},{pedido_data['data_pedido']},{pedido_data['status']}\n")
            
            flash(f'✅ Pedido {pedido_data["Codigo_Pedido"]} de {pedido_data["quantidade"]} unidades de {pedido_data["produto"]} registrado com sucesso!', 'success')
            return redirect(url_for('fazer_pedido'))

        except ValueError as e:
            flash(f'❌ Erro nos valores inseridos: {str(e)}', 'error')
        except Exception as e:
            flash(f'❌ Erro ao registrar pedido: {str(e)}', 'error')

    return render_template('fazer_pedido.html', produtos=produtos)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, port=5001)