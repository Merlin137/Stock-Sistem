from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import pandas as pd
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO, StringIO
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'chave_secreta_123'

usuarios_cadastrados = [
    {'nome': 'Farmacia', 'senha': 'Farmacia@2025'},
    {'nome': 'Admin', 'senha': 'cerof@2025'},
    {'nome': 'Almox', 'senha': 'Almox@2025'},
    {'nome': 'Estagiario', 'senha': 'Kronos-10'}
]
def carregar_imagem_fundo():
    try:
        caminho = os.path.join('static', 'fundo.png')
        print(f"Tentando carregar imagem em: {os.path.abspath(caminho)}")
        return Image.open(caminho)
    except FileNotFoundError:
        print("Imagem fundo.png não encontrada.")
        return None

def imagem_to_base64(imagem):
    buffered = BytesIO()
    imagem.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def carregar_produtos():
    filepath = os.path.join('produtos.csv')
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['ID', 'Nome', 'Tipo', 'Grupo', 'Volume', 'Temperatura'])
        df.to_csv(filepath, index=False)
        return df

def carregar_estoque():
    filepath = os.path.join('estoque.csv')
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['ID_Produto', 'Lote', 'Validade', 'Fornecedor', 'Marca', 'NF', 'DataEmissaoNF', 'DataEntrega', 'Quantidade', 'ValorUnitario', 'ValorTotal'])
        df.to_csv(filepath, index=False)
        return df

def carregar_pedidos():
    filepath = os.path.join('pedidos.csv')
    try:
        return pd.read_csv(filepath, encoding='utf-8')
    except UnicodeDecodeError:
        return pd.read_csv(filepath, encoding='latin-1')
    except FileNotFoundError:
        df = pd.DataFrame(columns=['Codigo_Pedido', 'ID_Produto', 'Produto', 'Quantidade', 'Solicitante', 'Departamento', 'DataPedido', 'Status'])
        df.to_csv(filepath, index=False)
        return df

def carregar_saidas():
    filepath = os.path.join('saidas.csv')
    try:
        return pd.read_csv(filepath, encoding='utf-8')
    except UnicodeDecodeError:
        return pd.read_csv(filepath, encoding='latin-1')
    except FileNotFoundError:
        return pd.DataFrame(columns=['Produto', 'Lote', 'Fornecedor', 'Quantidade', 'Solicitante', 'Departamento', 'DataSaida'])

def salvar_estoque(df):
    df.to_csv(os.path.join('estoque.csv'), index=False)

def salvar_produtos(df):
    df.to_csv(os.path.join('produtos.csv'), index=False)

def formatar_data_brasil(data):
    if data is None or pd.isna(data):
        return 'N/A'
    if isinstance(data, str):
        try:
            data = datetime.strptime(data, '%Y-%m-%d')
        except ValueError:
            return data
    return data.strftime('%d/%m/%Y')

def obter_id_por_nome(df, nome):
    produto = df[df['Nome'] == nome]
    return produto.iloc[0]['ID'] if not produto.empty else None

def gerar_novo_id(df):
    return 1 if df.empty else df['ID'].max() + 1

def gerar_codigo_pedido():
    pedidos_df = carregar_pedidos()
    return f"PED{len(pedidos_df) + 1:06d}"

@app.context_processor
def inject_imagem_fundo():
    imagem_fundo = carregar_imagem_fundo()
    return dict(imagem_fundo=imagem_to_base64(imagem_fundo) if imagem_fundo else '')

def login_required(f):
    def wrap(*args, **kwargs):
        if 'logado' not in session or not session['logado']:
            flash('❌ Faça login para acessar essa página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Rotas de Autenticação
@app.route('/', methods=['GET', 'POST'])
def login():
    print(f"[INFO] Acessando a rota de login - Método: {request.method}")
    
    if 'logado' in session and session['logado']:
        print(f"[INFO] Usuário {session.get('usuario', 'desconhecido')} já logado, redirecionando para o menu")
        return redirect(url_for('menu'))
    
    if request.method == 'POST':
        usuario = request.form.get('usuario','').strip()
        senha = request.form.get('senha','').strip()
        
        print(f"[INFO] Tentativa de login - Usuário: {usuario}")
        
        if not usuario or not senha:
            flash('❌ Preencha todos os campos.', 'error')
            return render_template('login.html')
        
        usuario_encontrado = next((u for u in usuarios_cadastrados if u['nome'] == usuario and u['senha'] == senha), None)
        
        if usuario_encontrado:
            session['logado'] = True
            session['usuario'] = usuario
            print(f"[SUCCESS] Login bem-sucedido para o usuário: {usuario}")
            flash('✅ Login bem-sucedido!', 'success')
            return redirect(url_for('menu'))
        else:
            print(f"[ERROR] Falha no login - Credenciais inválidas para o usuário: {usuario}")
            flash('❌ Usuário ou senha incorretos.', 'error')
    
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    usuario = session.get('usuario', 'desconhecido')
    session.pop('logado', None)
    session.pop('usuario', None)
    print(f"[INFO] Logout realizado para o usuário: {usuario}")
    flash('✅ Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

# Rotas do Sistema
@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

@app.route('/consulta', methods=['GET', 'POST'])
@login_required
def consulta():
    produtos_df, estoque_df = carregar_produtos(), carregar_estoque()
    df = pd.merge(produtos_df, estoque_df, left_on='ID', right_on='ID_Produto', how='left') if not produtos_df.empty else pd.DataFrame()
    grupos = ["MATERIAL OFTALMO", "ANEL INTRAESTROMAL", "CONTROLADOS", "GRANDES VOLUMES", "LIOS", "MEDICAMENTOS GERAIS"]
    produtos = produtos_df['Nome'].unique().tolist() if not produtos_df.empty else []

    grupo = request.form.get('grupo', request.args.get('grupo', ''))
    produto = request.form.get('produto', request.args.get('produto', ''))
    nome = request.form.get('nome', request.args.get('nome', '')).strip().lower()

    if grupo in grupos:
        df = df[df['Grupo'] == grupo]
    if produto:
        df = df[df['Nome'] == produto]
    if nome:
        df = df[df['Nome'].str.lower().str.contains(nome, na=False)]

    if request.method == 'POST' and 'download' in request.form:
        buffer = StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return send_file(
            BytesIO(buffer.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"consulta_produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    tabela = df.to_html(index=False, classes="table", na_rep="N/A") if not df.empty else "<p>⚠️ Nenhum produto ou estoque cadastrado.</p>"
    return render_template('consulta.html', tabela=tabela, grupos=grupos, produtos=produtos,
                           grupo_selecionado=grupo, produto_selecionado=produto, nome_filtro=nome)

@app.route('/entrada', methods=['GET', 'POST'])
@login_required
def entrada():
    produtos_df, estoque_df = carregar_produtos(), carregar_estoque()
    nomes_cadastrados = produtos_df['Nome'].unique().tolist() + ["Outro"] if not produtos_df.empty else ["Outro"]

    if request.method == 'POST':
        try:
            nome_selecionado = request.form.get('nome_selecionado', '').strip()
            nome = request.form.get('nome', '').strip() if nome_selecionado == "Outro" else nome_selecionado
            if not nome:
                flash("❌ O campo 'Nome' é obrigatório.", 'error')
                return render_template('entrada.html', nomes_cadastrados=nomes_cadastrados)

            produto_existente = produtos_df[produtos_df['Nome'] == nome]
            if produto_existente.empty:
                id_produto = gerar_novo_id(produtos_df)
                novo_produto = {
                    'ID': id_produto,
                    'Nome': nome,
                    'Tipo': request.form.get('tipo', ''),
                    'Grupo': request.form.get('grupo', ''),
                    'Volume': float(request.form.get('volume', 0) or 0),
                    'Temperatura': request.form.get('temperatura', '')
                }
                produtos_df = pd.concat([produtos_df, pd.DataFrame([novo_produto])], ignore_index=True)
                salvar_produtos(produtos_df)
            else:
                id_produto = obter_id_por_nome(produtos_df, nome)

            entrada_data = {
                'ID_Produto': id_produto,
                'Lote': request.form.get('lote', '').strip(),
                'Validade': formatar_data_brasil(request.form.get('validade', '')),
                'Fornecedor': request.form.get('fornecedor', '').strip(),
                'Marca': request.form.get('marca', '').strip(),
                'NF': request.form.get('nf', '').strip(),
                'DataEmissaoNF': formatar_data_brasil(request.form.get('data_emissao_nf', '')),
                'DataEntrega': formatar_data_brasil(request.form.get('data_entrega', '')),
                'Quantidade': int(request.form.get('quantidade', 0) or 0),
                'ValorUnitario': float(request.form.get('valor_unitario', 0) or 0)
            }
            entrada_data['ValorTotal'] = entrada_data['Quantidade'] * entrada_data['ValorUnitario']

            campos_vazios = [k for k, v in entrada_data.items() if not v or (isinstance(v, (int, float)) and v <= 0)]
            if campos_vazios:
                flash(f"❌ Os seguintes campos são obrigatórios: {', '.join(campos_vazios)}", 'error')
            else:
                estoque_df = pd.concat([estoque_df, pd.DataFrame([entrada_data])], ignore_index=True)
                salvar_estoque(estoque_df)
                flash('✅ Entrada registrada com sucesso!', 'success')
                return redirect(url_for('entrada'))
        except ValueError as e:
            flash(f"❌ Erro nos valores inseridos: {str(e)}", 'error')
        except Exception as e:
            flash(f"❌ Erro ao registrar entrada: {str(e)}", 'error')

    return render_template('entrada.html', nomes_cadastrados=nomes_cadastrados)

@app.route('/saida', methods=['GET', 'POST'])
@login_required
def saida():
    produtos_df, estoque_df = carregar_produtos(), carregar_estoque()
    produtos = produtos_df['Nome'].unique().tolist() if not produtos_df.empty else []
    produto_selecionado = request.form.get('produto', '') if request.method == 'POST' else ''
    lotes_disponiveis = []

    if produto_selecionado:
        id_produto = obter_id_por_nome(produtos_df, produto_selecionado)
        if id_produto:
            lotes_disponiveis = estoque_df[estoque_df['ID_Produto'] == id_produto][['Lote', 'Quantidade']].to_dict('records')

    if request.method == 'POST' and 'lote' in request.form:
        try:
            saida_data = {
                'produto': request.form.get('produto', '').strip(),
                'lote': request.form.get('lote', '').strip(),
                'quantidade': int(request.form.get('quantidade', 0) or 0),
                'solicitante': request.form.get('solicitante', '').strip(),
                'departamento': request.form.get('departamento', '').strip(),
                'data_saida': formatar_data_brasil(datetime.now())
            }

            if not all([saida_data[k] for k in saida_data if k != 'data_saida']) or saida_data['quantidade'] <= 0:
                flash("❌ Todos os campos são obrigatórios e a quantidade deve ser maior que zero.", 'error')
                return render_template('saida.html', produtos=produtos, lotes_disponiveis=lotes_disponiveis, produto_selecionado=produto_selecionado)

            id_produto = obter_id_por_nome(produtos_df, saida_data['produto'])
            filtro = (estoque_df['ID_Produto'] == id_produto) & (estoque_df['Lote'] == saida_data['lote'])
            produto_lote = estoque_df[filtro]

            if not produto_lote.empty:
                index = produto_lote.index[0]
                if estoque_df.loc[index, 'Quantidade'] >= saida_data['quantidade']:
                    estoque_df.loc[index, 'Quantidade'] -= saida_data['quantidade']
                    msg = f"✅ {saida_data['quantidade']} unidades de {saida_data['produto']} (Lote: {saida_data['lote']}) retiradas."
                    if estoque_df.loc[index, 'Quantidade'] == 0:
                        estoque_df = estoque_df.drop(index)
                        msg = f"⚠️ Todas as unidades de {saida_data['produto']} (Lote: {saida_data['lote']}) foram retiradas."
                    saidas_df = carregar_saidas()
                    saidas_df = pd.concat([saidas_df, pd.DataFrame([saida_data])], ignore_index=True)
                    saidas_df.to_csv(os.path.join('saidas.csv'), index=False, encoding='utf-8')
                    salvar_estoque(estoque_df)
                    flash(msg, 'success')
                    return redirect(url_for('saida'))
                flash(f"❌ Quantidade insuficiente em estoque ({estoque_df.loc[index, 'Quantidade']} disponíveis).", 'error')
            else:
                flash("❌ Produto, lote ou fornecedor não encontrado.", 'error')
        except ValueError as e:
            flash(f"❌ Erro nos valores inseridos: {str(e)}", 'error')
        except Exception as e:
            flash(f"❌ Erro ao registrar saída: {str(e)}", 'error')

    return render_template('saida.html', produtos=produtos, lotes_disponiveis=lotes_disponiveis, produto_selecionado=produto_selecionado)

@app.route('/pedidos', methods=['GET', 'POST'])
@login_required
def pedidos():
    produtos_df = carregar_produtos()
    produtos = produtos_df['Nome'].unique().tolist() if not produtos_df.empty else []

    if request.method == 'POST':
        try:
            pedido_data = {
                'Codigo_Pedido': gerar_codigo_pedido(),
                'produto': request.form.get('produto', '').strip(),
                'quantidade': int(request.form.get('quantidade', 0) or 0),
                'solicitante': request.form.get('solicitante', '').strip(),
                'departamento': request.form.get('departamento', '').strip(),
                'data_pedido': formatar_data_brasil(datetime.now()),
                'status': "Pendente"
            }

            if not all([pedido_data[k] for k in pedido_data if k not in ['data_pedido', 'status', 'Codigo_Pedido']]) or pedido_data['quantidade'] <= 0:
                flash("❌ Todos os campos são obrigatórios e a quantidade deve ser maior que zero.", 'error')
                return render_template('pedidos.html', produtos=produtos)

            id_produto = obter_id_por_nome(produtos_df, pedido_data['produto'])
            if id_produto is None:
                flash("❌ Produto não encontrado.", 'error')
                return render_template('pedidos.html', produtos=produtos)

            pedidos_df = carregar_pedidos()
            pedido_data['ID_Produto'] = id_produto
            pedidos_df = pd.concat([pedidos_df, pd.DataFrame([pedido_data])], ignore_index=True)
            pedidos_df.to_csv(os.path.join('pedidos.csv'), index=False, encoding='utf-8')
            flash(f"✅ Pedido {pedido_data['Codigo_Pedido']} de {pedido_data['quantidade']} unidades de {pedido_data['produto']} registrado com sucesso!", 'success')
            return redirect(url_for('pedidos'))
        except ValueError as e:
            flash(f"❌ Erro nos valores inseridos: {str(e)}", 'error')
        except Exception as e:
            flash(f"❌ Erro ao registrar pedido: {str(e)}", 'error')

    tabela = "<p>⚠️ Nenhum pedido registrado até o momento.</p>"
    try:
        pedidos_df = carregar_pedidos()
        tabela = pedidos_df.to_html(index=False, classes="table", na_rep="N/A")
    except FileNotFoundError:
        pass

    return render_template('pedidos.html', produtos=produtos, tabela=tabela)

@app.route('/devolucao', methods=['GET', 'POST'])
@login_required
def devolucao():
    produtos_df, estoque_df = carregar_produtos(), carregar_estoque()
    produtos = produtos_df['Nome'].unique().tolist() if not produtos_df.empty else []
    produto_selecionado = request.form.get('produto', '') if request.method == 'POST' else ''
    lotes_disponiveis = []

    if produto_selecionado:
        id_produto = obter_id_por_nome(produtos_df, produto_selecionado)
        if id_produto:
            lotes_disponiveis = estoque_df[estoque_df['ID_Produto'] == id_produto][['Lote', 'Fornecedor', 'Quantidade']].to_dict('records')

    if request.method == 'POST' and 'lote' in request.form:
        try:
            devolucao_data = {
                'produto': request.form.get('produto', '').strip(),
                'lote': request.form.get('lote', '').strip(),
                'quantidade': int(request.form.get('quantidade', 0) or 0),
                'motivo': request.form.get('motivo', '').strip(),
                'devolvido_por': request.form.get('devolvido_por', '').strip(),
                'data_devolucao': formatar_data_brasil(datetime.now())
            }

            if not all([devolucao_data[k] for k in devolucao_data if k != 'data_devolucao']) or devolucao_data['quantidade'] <= 0:
                flash("❌ Todos os campos são obrigatórios e a quantidade deve ser maior que zero.", 'error')
                return render_template('devolucao.html', produtos=produtos, lotes_disponiveis=lotes_disponiveis, produto_selecionado=produto_selecionado)

            id_produto = obter_id_por_nome(produtos_df, devolucao_data['produto'])
            if id_produto is None:
                flash("❌ Produto não encontrado na lista de produtos.", 'error')
                return render_template('devolucao.html', produtos=produtos, lotes_disponiveis=lotes_disponiveis, produto_selecionado=produto_selecionado)

            filtro = (estoque_df['ID_Produto'] == id_produto) & (estoque_df['Lote'] == devolucao_data['lote'])
            produto_lote = estoque_df[filtro]

            if not produto_lote.empty:
                index = produto_lote.index[0]
                estoque_df.loc[index, 'Quantidade'] += devolucao_data['quantidade']
                flash(f"✅ Devolução de {devolucao_data['quantidade']} unidades de {devolucao_data['produto']} (Lote: {devolucao_data['lote']}) adicionada ao estoque existente.", 'success')
            else:
                produto_existente = estoque_df[estoque_df['ID_Produto'] == id_produto].iloc[0] if not estoque_df[estoque_df['ID_Produto'] == id_produto].empty else None
                nova_entrada = {
                    'ID_Produto': id_produto,
                    'Lote': devolucao_data['lote'],
                    'Validade': produto_existente['Validade'] if produto_existente is not None else 'N/A',
                    'Fornecedor': produto_existente['Fornecedor'] if produto_existente is not None else 'Desconhecido',
                    'Marca': produto_existente['Marca'] if produto_existente is not None else 'N/A',
                    'NF': produto_existente['NF'] if produto_existente is not None else 'N/A',
                    'DataEmissaoNF': produto_existente['DataEmissaoNF'] if produto_existente is not None else 'N/A',
                    'DataEntrega': produto_existente['DataEntrega'] if produto_existente is not None else devolucao_data['data_devolucao'],
                    'Quantidade': devolucao_data['quantidade'],
                    'ValorUnitario': produto_existente['ValorUnitario'] if produto_existente is not None else 0.0,
                    'ValorTotal': (produto_existente['ValorUnitario'] * devolucao_data['quantidade']) if produto_existente is not None else 0.0
                }
                estoque_df = pd.concat([estoque_df, pd.DataFrame([nova_entrada])], ignore_index=True)
                flash(f"✅ Devolução de {devolucao_data['quantidade']} unidades de {devolucao_data['produto']} (Lote: {devolucao_data['lote']}) adicionada como nova entrada no estoque.", 'success')

            salvar_estoque(estoque_df)

            devolucoes_df = pd.read_csv(os.path.join('devolucoes.csv')) if os.path.exists(os.path.join('devolucoes.csv')) else pd.DataFrame(columns=['Produto', 'Lote', 'Quantidade', 'Motivo', 'DevolvidoPor', 'DataDevolucao'])
            devolucoes_df = pd.concat([devolucoes_df, pd.DataFrame([devolucao_data])], ignore_index=True)
            devolucoes_df.to_csv(os.path.join('devolucoes.csv'), index=False, encoding='utf-8')
            return redirect(url_for('devolucao'))

        except ValueError as e:
            flash(f"❌ Erro nos valores inseridos: {str(e)}", 'error')
        except Exception as e:
            flash(f"❌ Erro ao registrar devolução: {str(e)}", 'error')

    return render_template('devolucao.html', produtos=produtos, lotes_disponiveis=lotes_disponiveis, produto_selecionado=produto_selecionado)

@app.route('/relatorio_saidas')
@login_required
def relatorio_saidas():
    saidas_df = carregar_saidas()
    tabela = saidas_df.to_html(index=False, classes="table", na_rep="N/A") if not saidas_df.empty else "<p>⚠️ Nenhuma saída registrada até o momento.</p>"
    return render_template('relatorio_saidas.html', tabela=tabela, saidas_df=saidas_df)

@app.route('/download_relatorio_saidas')
@login_required
def download_relatorio_saidas():
    saidas_df = carregar_saidas()
    if saidas_df.empty:
        flash("❌ Nenhum dado disponível para download.", 'error')
        return redirect(url_for('relatorio_saidas'))
    
    buffer = StringIO()
    saidas_df.to_csv(buffer, index=False, encoding='utf-8')
    buffer.seek(0)
    return send_file(
        BytesIO(buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"relatorio_saidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    print("Iniciando a aplicação Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000)
