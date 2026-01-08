import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS (Tudo aqui!) ---
st.set_page_config(page_title="Finanças do Casal", layout="wide")

# Função para conectar no banco (cria sozinho se não existir)
def get_connection():
    conn = sqlite3.connect('financas_streamlit.db')
    return conn

# Cria a tabela na primeira vez que rodar
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            descricao TEXT,
            categoria TEXT,
            quem TEXT,
            tipo TEXT,
            valor REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db() # Roda a criação do banco

# --- 2. BARRA LATERAL (Inserir Dados) ---
st.sidebar.header("💸 Nova Transação")

with st.sidebar.form("form_transacao", clear_on_submit=True):
    data = st.date_input("Data")
    descricao = st.text_input("Descrição (Ex: Pizza)")
    categoria = st.selectbox("Categoria", ["Mercado", "Lazer", "Contas Fixas", "Investimento", "Salário"])
    quem = st.selectbox("Quem?", ["Ele", "Ela"])
    tipo = st.radio("Tipo", ["SAIDA", "ENTRADA"])
    valor = st.number_input("Valor R$", min_value=0.0, step=0.01, format="%.2f")
    
    submitted = st.form_submit_button("Salvar")
    
    if submitted:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transacoes (data, descricao, categoria, quem, tipo, valor)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data, descricao, categoria, quem, tipo, valor))
        conn.commit()
        conn.close()
        st.sidebar.success("Lançado!")

# --- 3. DADOS E DASHBOARD ---
st.title("💰 Finanças do Casal")

# Ler dados do banco
conn = get_connection()
df = pd.read_sql("SELECT * FROM transacoes", conn)
conn.close()

if not df.empty:
    # Converter coluna de data
    df['data'] = pd.to_datetime(df['data'])
    df = df.sort_values(by='data', ascending=False)

    # Métricas
    total_entrada = df[df['tipo'] == 'ENTRADA']['valor'].sum()
    total_saida = df[df['tipo'] == 'SAIDA']['valor'].sum()
    saldo = total_entrada - total_saida

    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas", f"R$ {total_entrada:,.2f}", delta_color="normal")
    col2.metric("Saídas", f"R$ {total_saida:,.2f}", delta_color="inverse")
    col3.metric("Saldo Final", f"R$ {saldo:,.2f}")

    st.divider()

    # Layout: Gráfico na esquerda, Tabela na direita
    col_graf, col_tab = st.columns([1, 1])

    with col_graf:
        st.subheader("Para onde foi o dinheiro?")
        # Filtra só as saídas para o gráfico
        df_saidas = df[df['tipo'] == 'SAIDA']
        if not df_saidas.empty:
            fig = px.donut(df_saidas, values='valor', names='categoria', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Cadastre saídas para ver o gráfico.")

    with col_tab:
        st.subheader("Extrato")
        # Mostra tabela bonitinha
        st.dataframe(
            df[['data', 'descricao', 'categoria', 'quem', 'tipo', 'valor']],
            hide_index=True,
            use_container_width=True
        )
        
        # Botão para limpar banco (opcional)
        if st.button("Limpar Todos os Dados"):
            conn = get_connection()
            conn.execute("DELETE FROM transacoes")
            conn.commit()
            conn.close()
            st.rerun()

else:
    st.info("👈 Use a barra lateral para adicionar sua primeira transação!")
