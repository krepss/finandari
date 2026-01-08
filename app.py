import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Finanças Git", layout="wide")

# NOME DO SEU REPOSITÓRIO (Mude isto!)
# Formato: "usuario/repositorio"
GITHUB_REPO = "krepss/finandari" 
ARQUIVO_CSV = "dados.csv"

# --- FUNÇÕES DE CONEXÃO COM GITHUB ---
def get_github_repo():
    # Pega o token dos segredos do Streamlit
    token = st.secrets["GITHUB_TOKEN"]
    g = Github(token)
    return g.get_repo(GITHUB_REPO)

def ler_dados():
    try:
        repo = get_github_repo()
        # Tenta pegar o arquivo
        contents = repo.get_contents(ARQUIVO_CSV)
        # Decodifica o CSV que vem do Git
        csv_data = contents.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_data))
    except:
        # Se o arquivo não existe, retorna DataFrame vazio
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor"])

def salvar_no_git(nova_linha_dict):
    repo = get_github_repo()
    
    # 1. Tenta ler o arquivo atual
    try:
        contents = repo.get_contents(ARQUIVO_CSV)
        df_atual = pd.read_csv(StringIO(contents.decoded_content.decode("utf-8")))
        
        # Adiciona a nova linha
        df_novo = pd.concat([df_atual, pd.DataFrame([nova_linha_dict])], ignore_index=True)
        
        # Converte para CSV string
        novo_conteudo = df_novo.to_csv(index=False)
        
        # FAZ O UPDATE NO GITHUB (Commit)
        repo.update_file(
            path=ARQUIVO_CSV,
            message="Nova transação via Streamlit",
            content=novo_conteudo,
            sha=contents.sha # Precisamos do SHA para provar que estamos editando a versão certa
        )
        return True
    
    except Exception as e:
        # Se o arquivo não existe, cria um novo (Create)
        df_novo = pd.DataFrame([nova_linha_dict])
        novo_conteudo = df_novo.to_csv(index=False)
        
        try:
            repo.create_file(
                path=ARQUIVO_CSV,
                message="Primeira transação - Criando arquivo",
                content=novo_conteudo
            )
            return True
        except Exception as erro_criacao:
            st.error(f"Erro ao salvar: {erro_criacao}")
            return False

# --- INTERFACE ---
st.title("💰 Finanças do Casal (CSV no Git)")

# --- BARRA LATERAL ---
st.sidebar.header("💸 Lançar Gasto")
with st.sidebar.form("form_git", clear_on_submit=True):
    data = st.date_input("Data", datetime.now())
    descricao = st.text_input("Descrição")
    categoria = st.selectbox("Categoria", ["Mercado", "Lazer", "Casa", "Salário", "Outros"])
    quem = st.selectbox("Quem?", ["Ele", "Ela"])
    tipo = st.radio("Tipo", ["SAIDA", "ENTRADA"])
    valor = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
    
    submitted = st.form_submit_button("Salvar no Git")
    
    if submitted:
        nova_transacao = {
            "data": data.strftime("%Y-%m-%d"),
            "descricao": descricao,
            "categoria": categoria,
            "quem": quem,
            "tipo": tipo,
            "valor": valor
        }
        
        with st.spinner("Conectando ao GitHub... (Isso leva uns 3 segs)"):
            sucesso = salvar_no_git(nova_transacao)
            if sucesso:
                st.success("Salvo e Comitado! 🚀")
                st.rerun() # Recarrega a página para mostrar o dado novo

# --- DASHBOARD ---
df = ler_dados()

if not df.empty:
    # Converter tipos
    df['valor'] = pd.to_numeric(df['valor'])
    
    # Métricas
    entrada = df[df['tipo'] == 'ENTRADA']['valor'].sum()
    saida = df[df['tipo'] == 'SAIDA']['valor'].sum()
    saldo = entrada - saida
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Entradas", f"R$ {entrada:.2f}")
    c2.metric("Saídas", f"R$ {saida:.2f}")
    c3.metric("Saldo", f"R$ {saldo:.2f}")
    
    st.divider()
    
    # Tabela e Gráfico
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Extrato")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with col2:
        if saida > 0:
            st.subheader("Gastos")
            df_saida = df[df['tipo'] == 'SAIDA']
            fig = px.donut(df_saida, values='valor', names='categoria', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado no CSV ainda. Faça o primeiro lançamento!")
