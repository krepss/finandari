import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="Finanças Casal", layout="wide", page_icon="💰")

# ✅ SEU REPOSITÓRIO CONFIGURADO
GITHUB_REPO = "krepss/finandari"
ARQUIVO_CSV = "dados.csv"

# --- 2. FUNÇÕES DE CONEXÃO COM GITHUB ---
def get_github_repo():
    """Conecta ao GitHub usando o Token secreto"""
    # Tenta pegar dos segredos (Nuvem) ou procura localmente se não achar
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except:
        st.error("ERRO: Token do GitHub não encontrado. Configure o secrets.toml")
        return None
        
    g = Github(token)
    return g.get_repo(GITHUB_REPO)

def ler_dados():
    """Baixa o CSV do GitHub e transforma em Tabela"""
    try:
        repo = get_github_repo()
        if not repo: return pd.DataFrame()
        
        contents = repo.get_contents(ARQUIVO_CSV)
        csv_data = contents.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_data))
    except:
        # Se arquivo não existe, retorna tabela vazia com as colunas certas
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor"])

def salvar_dataframe_no_git(df_novo_completo):
    """Sobrescreve o CSV no GitHub com os dados atualizados"""
    repo = get_github_repo()
    if not repo: return False
    
    # Converte para CSV texto
    novo_conteudo = df_novo_completo.to_csv(index=False)
    
    try:
        # Tenta atualizar arquivo existente
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(
            path=ARQUIVO_CSV,
            message="Atualização via App Streamlit",
            content=novo_conteudo,
            sha=contents.sha
        )
        return True
    except:
        # Se não existe, cria um novo
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

# --- 3. INTERFACE DO SISTEMA ---
st.title("💰 Finanças do Casal")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "✍️ Lançar Manual", "📂 Importar Nubank"])

# === ABA 1: DASHBOARD COM FILTRO ===
with tab1:
    st.header("📊 Visão Geral")
    df = ler_dados()
    
    if not df.empty:
        # Tratamento de tipos
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        
        # Cria coluna auxiliar para o filtro (Ex: 2024-01)
        df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
        
        # Filtro de Mês
        lista_meses = sorted(df['mes_ano'].unique(), reverse=True)
        lista_meses.insert(0, "Todos")
        
        col_filtro, col_vazia = st.columns([1, 3])
        with col_filtro:
            mes_escolhido = st.selectbox("📅 Filtrar por Mês:", lista_meses)
        
        # Aplica o filtro
        if mes_escolhido != "Todos":
            df_filtrado = df[df['mes_ano'] == mes_escolhido]
        else:
            df_filtrado = df

        # Cálculos
        entrada = df_filtrado[df_filtrado['tipo'] == 'ENTRADA']['valor'].sum()
        saida = df_filtrado[df_filtrado['tipo'] == 'SAIDA']['valor'].sum()
        saldo = entrada - saida
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Entradas", f"R$ {entrada:,.2f}")
        c2.metric("Saídas", f"R$ {saida:,.2f}")
        c3.metric("Saldo do Período", f"R$ {saldo:,.2f}", delta_color="normal")
        
        st.divider()
        
        # Gráfico e Tabela
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if saida > 0:
                st.subheader("Para onde foi o dinheiro?")
                df_saida = df_filtrado[df_filtrado['tipo'] == 'SAIDA']
                fig = px.donut(
                    df_saida, 
                    values='valor', 
                    names='categoria', 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Sem gastos em {mes_escolhido}.")
                
        with col2:
            st.subheader("Extrato")
            st.dataframe(
                df_filtrado[['data', 'descricao', 'categoria', 'valor', 'quem']].sort_values('data', ascending=False), 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                }
            )
    else:
        st.info("Nenhum dado encontrado. Faça seu primeiro lançamento!")

# === ABA 2: LANÇAMENTO MANUAL ===
with tab2:
    st.header("Novo Gasto Avulso")
    with st.form("form_manual", clear_on_submit=True):
        col_form1, col_form2 = st.columns(2)
        
        data = col_form1.date_input("Data", datetime.now())
        descricao = col_form2.text_input("Descrição (Ex: Padaria)")
        
        categoria = st.selectbox("Categoria", ["Mercado", "Lazer", "Casa", "Salário", "Transporte", "Saúde", "Contas Fixas", "Outros"])
        quem = st.selectbox("Quem?", ["Casal", "Ele", "Ela"])
        tipo = st.radio("Tipo", ["SAIDA", "ENTRADA"], horizontal=True)
        valor = st.number_input("Valor R$", min_value=0.0, step=0.01, format="%.2f")
        
        if st.form_submit_button("Salvar Manualmente"):
            nova_linha = pd.DataFrame([{
                "data": data.strftime("%Y-%m-%d"),
                "descricao": descricao,
                "categoria": categoria,
                "quem": quem,
                "tipo": tipo,
                "valor": valor
            }])
            
            df_atual = ler_dados()
            df_final = pd.concat([df_atual, nova_linha], ignore_index=True)
            
            with st.spinner("Enviando para o GitHub..."):
                if salvar_dataframe_no_git(df_final):
                    st.success("Salvo com sucesso!")
                    st.rerun()

# === ABA 3: IMPORTAR NUBANK (CORRIGIDO) ===
with tab3:
    st.header("📂 Importar Fatura Nubank")
    st.markdown("Arraste o arquivo CSV. O sistema classifica tudo e salva como 'Casal'.")
    
    uploaded_file = st.file_uploader("Solte o CSV aqui", type="csv")

    if uploaded_file is not None:
        try:
            df_nubank = pd.read_csv(uploaded_file)
            novos_dados = []
            
            for index, row in df_nubank.iterrows():
                # Tratamento de Data
                try:
                    data_obj = pd.to_datetime(row['date'])
                    data_formatada = data_obj.strftime("%Y-%m-%d")
                except:
                    data_formatada = datetime.now().strftime("%Y-%m-%d")

                # Categorização Automática
                cat_nubank = str(row.get('category', '')).title()
                titulo = str(row.get('title', '')).title()
                
                # Ignora Pagamento de Fatura
                if 'Pagamento' in titulo and 'Fatura' in titulo: continue 

                cat_sugerida = "Outros"
                if 'Transporte' in cat_nubank or 'Uber' in titulo or '99' in titulo or 'Posto' in titulo:
                    cat_sugerida = 'Transporte'
                elif 'Mercado' in cat_nubank or 'Supermercado' in cat_nubank or 'Assai' in titulo or 'Atacadao' in titulo:
                    cat_sugerida = 'Mercado'
                elif 'Restaurante' in cat_nubank or 'Ifood' in titulo or 'Burger' in titulo or 'Pizza' in titulo:
                    cat_sugerida = 'Lazer'
                elif 'Serviços' in cat_nubank or 'Streaming' in cat_nubank or 'Netflix' in titulo:
                    cat_sugerida = 'Contas Fixas'
                elif 'Saúde' in cat_nubank or 'Farmacia' in titulo or 'Drogasil' in titulo:
                    cat_sugerida = 'Saúde'

                novos_dados.append({
                    "data": data_formatada,
                    "descricao": titulo,
                    "categoria": cat_sugerida,
                    "tipo": "SAIDA",
                    "valor": float(row['amount'])
                })
            
            df_previa = pd.DataFrame(novos_dados)

            if not df_previa.empty:
                # 🛠️ CORREÇÃO IMPORTANTE: Converte para data real pro editor funcionar
                df_previa['data'] = pd.to_datetime(df_previa['data'])

                st.info("👇 Confira e edite se necessário.")

                df_editado = st.data_editor(
                    df_previa,
                    column_config={
                        "categoria": st.column_config.SelectboxColumn("Categoria", width="medium", options=["Mercado", "Lazer", "Casa", "Transporte", "Saúde", "Contas Fixas", "Outros"], required=True),
                        "descricao": st.column_config.TextColumn("Descrição"),
                        "valor": st.column_config.NumberColumn("Valor R$", format="R$ %.2f"),
                        "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "tipo": st.column_config.TextColumn("Tipo", disabled=True)
                    },
                    hide_index=True,
                    num_rows="dynamic"
                )
                
                st.divider()

                if st.button("✅ Confirmar Importação"):
                    # Define 'Casal' pra tudo
                    df_editado['quem'] = "Casal"
                    # Converte data de volta pra texto pra salvar no CSV
                    df_editado['data'] = df_editado['data'].dt.strftime("%Y-%m-%d")

                    df_atual = ler_dados()
                    df_final = pd.concat([df_atual, df_editado], ignore_index=True)
                    df_final = df_final.drop_duplicates(subset=['data', 'descricao', 'valor'])
                    
                    with st.spinner("Salvando no Git..."):
                        if salvar_dataframe_no_git(df_final):
                            st.success(f"Sucesso! {len(df_editado)} gastos salvos.")
                            st.rerun()
            else:
                st.warning("Nenhuma transação válida encontrada.")
            
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")
