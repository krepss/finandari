import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Finanças do Casal", layout="wide")

# NOME DO SEU REPOSITÓRIO
GITHUB_REPO = "klebs/financas-casal"  # <--- CONFIRA SE ESTÁ CERTO
ARQUIVO_CSV = "dados.csv"

# --- FUNÇÕES DE CONEXÃO COM GITHUB ---
def get_github_repo():
    token = st.secrets["GITHUB_TOKEN"]
    g = Github(token)
    return g.get_repo(GITHUB_REPO)

def ler_dados():
    try:
        repo = get_github_repo()
        contents = repo.get_contents(ARQUIVO_CSV)
        csv_data = contents.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_data))
    except:
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor"])

def salvar_dataframe_no_git(df_novo_completo):
    """
    Salva o DataFrame inteiro de volta no Git.
    Usado tanto para lançamentos manuais quanto para importação em massa.
    """
    repo = get_github_repo()
    novo_conteudo = df_novo_completo.to_csv(index=False)
    
    try:
        # Tenta atualizar arquivo existente
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(
            path=ARQUIVO_CSV,
            message="Atualização via Streamlit (Lote/Manual)",
            content=novo_conteudo,
            sha=contents.sha
        )
        return True
    except:
        # Se não existe, cria
        try:
            repo.create_file(
                path=ARQUIVO_CSV,
                message="Criando arquivo inicial",
                content=novo_conteudo
            )
            return True
        except Exception as e:
            st.error(f"Erro ao salvar no Git: {e}")
            return False

# --- INTERFACE ---
st.title("💰 Finanças do Casal")

# Abas para separar Manual de Importação
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "✍️ Lançar Manual", "📂 Importar Nubank"])

# --- ABA 1: DASHBOARD ---
with tab1:
    df = ler_dados()
    
    if not df.empty:
        # Converter tipos
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        
        # Filtros de Mês (Opcional, mas útil)
        mes_atual = datetime.now().month
        
        # Métricas
        entrada = df[df['tipo'] == 'ENTRADA']['valor'].sum()
        saida = df[df['tipo'] == 'SAIDA']['valor'].sum()
        saldo = entrada - saida
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Entradas", f"R$ {entrada:,.2f}")
        c2.metric("Saídas", f"R$ {saida:,.2f}")
        c3.metric("Saldo Geral", f"R$ {saldo:,.2f}")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Extrato")
            st.dataframe(df.sort_values('data', ascending=False), use_container_width=True, hide_index=True)
            
        with col2:
            if saida > 0:
                st.subheader("Gastos por Categoria")
                df_saida = df[df['tipo'] == 'SAIDA']
                fig = px.donut(df_saida, values='valor', names='categoria', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado.")

# --- ABA 2: LANÇAMENTO MANUAL ---
with tab2:
    st.header("Novo Gasto Avulso")
    with st.form("form_manual", clear_on_submit=True):
        data = st.date_input("Data", datetime.now())
        descricao = st.text_input("Descrição")
        categoria = st.selectbox("Categoria", ["Mercado", "Lazer", "Casa", "Salário", "Transporte", "Outros"])
        quem = st.selectbox("Quem?", ["Ele", "Ela"])
        tipo = st.radio("Tipo", ["SAIDA", "ENTRADA"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
        
        if st.form_submit_button("Salvar Manualmente"):
            nova_linha = pd.DataFrame([{
                "data": data.strftime("%Y-%m-%d"),
                "descricao": descricao,
                "categoria": categoria,
                "quem": quem,
                "tipo": tipo,
                "valor": valor
            }])
            
            # Carrega o atual, junta com o novo e salva
            df_atual = ler_dados()
            df_final = pd.concat([df_atual, nova_linha], ignore_index=True)
            
            with st.spinner("Enviando para o GitHub..."):
                if salvar_dataframe_no_git(df_final):
                    st.success("Salvo!")
                    st.rerun()

# --- ABA 3: IMPORTAR NUBANK ---
with tab3:
    st.header("Importar Fatura (CSV)")
    st.markdown("Baixe o CSV no app do Nubank e solte aqui.")
    
    uploaded_file = st.file_uploader("Escolha o arquivo CSV", type="csv")
    
    # Configurações extras para a importação
    col_config1, col_config2 = st.columns(2)
    quem_import = col_config1.selectbox("De quem é essa fatura?", ["Ele", "Ela"], key="quem_csv")
    categoria_padrao = col_config2.selectbox("Categoria Padrão (se não soubermos)", ["Outros", "Mercado", "Lazer"], key="cat_csv")

    if uploaded_file is not None:
        try:
            # 1. Lê o CSV do Nubank
            # O Nubank geralmente usa vírgula como separador, mas pode variar.
            df_nubank = pd.read_csv(uploaded_file)
            
            # Mostra uma prévia para o usuário ver se leu certo
            st.write("Prévia do arquivo do Nubank:", df_nubank.head())
            
            # 2. Processa os dados para o formato do nosso App
            # O Nubank geralmente tem colunas: date, category, title, amount
            
            novos_dados = []
            
            for index, row in df_nubank.iterrows():
                # Tenta normalizar a data (Nubank vem YYYY-MM-DD ou DD/MM/YYYY dependendo da versão)
                try:
                    data_formatada = pd.to_datetime(row['date']).strftime("%Y-%m-%d")
                except:
                    data_formatada = datetime.now().strftime("%Y-%m-%d")

                # Lógica simples de Categoria (Tenta usar a do Nubank ou a padrão)
                cat_nubank = str(row.get('category', '')).title() # Tenta pegar categoria do Nubank
                
                # Mapeamento básico (Opcional: Melhore isso com o tempo)
                cat_final = categoria_padrao
                if 'Transporte' in cat_nubank or 'Uber' in str(row['title']):
                    cat_final = 'Transporte'
                elif 'Mercado' in cat_nubank or 'Supermercado' in cat_nubank:
                    cat_final = 'Mercado'
                elif 'Restaurante' in cat_nubank or 'Ifood' in str(row['title']):
                    cat_final = 'Lazer'
                
                novos_dados.append({
                    "data": data_formatada,
                    "descricao": row['title'], # Nubank chama de title
                    "categoria": cat_final,
                    "quem": quem_import,
                    "tipo": "SAIDA", # Fatura de cartão é sempre saída
                    "valor": float(row['amount']) # Nubank já manda positivo
                })
            
            df_novos = pd.DataFrame(novos_dados)
            
            st.subheader("Serão importados:")
            st.dataframe(df_novos)
            
            if st.button("Confirmar Importação"):
                df_atual = ler_dados()
                
                # Junta tudo
                df_final = pd.concat([df_atual, df_novos], ignore_index=True)
                
                # Remove duplicatas exatas para não importar 2x a mesma coisa
                df_final = df_final.drop_duplicates(subset=['data', 'descricao', 'valor', 'quem'])
                
                with st.spinner("Salvando montanha de dados no Git..."):
                    if salvar_dataframe_no_git(df_final):
                        st.success(f"{len(df_novos)} transações importadas com sucesso!")
                        st.rerun()
                        
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}. Verifique se é um CSV do Nubank válido.")
