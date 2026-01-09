import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="Finanças do Casal", layout="wide", page_icon="💰")

# ✅ SEU REPOSITÓRIO CORRETO
GITHUB_REPO = "krepss/finandari" 
ARQUIVO_CSV = "dados.csv"

# --- 2. FUNÇÕES DE CONEXÃO COM GITHUB ---
def get_github_repo():
    token = st.secrets["GITHUB_TOKEN"]
    g = Github(token)
    return g.get_repo(GITHUB_REPO)

def ler_dados():
    try:
        repo = get_github_repo()
        contents = repo.get_contents(ARQUIVO_CSV)
        csv_data = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(csv_data))
        
        # --- CORREÇÃO AUTOMÁTICA DE COLUNAS ---
        # Garante que o sistema não quebre se tiver dados antigos faltando colunas
        if 'origem' not in df.columns:
            df['origem'] = 'Manual'
        if 'quem' not in df.columns:
            df['quem'] = 'Casal'
            
        return df
    except:
        # Retorna vazio se não existir arquivo ainda
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor", "origem"])

def salvar_dataframe_no_git(df_novo_completo):
    repo = get_github_repo()
    novo_conteudo = df_novo_completo.to_csv(index=False)
    
    try:
        # Tenta atualizar
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(
            path=ARQUIVO_CSV,
            message="Atualização via App Streamlit",
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

# --- 3. INTERFACE ---
st.title("💰 Finanças do Casal")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "✍️ Lançar Manual", "📂 Importar Nubank"])

# === ABA 1: DASHBOARD ===
with tab1:
    df = ler_dados()
    
    if not df.empty:
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        
        # Cálculos
        entrada = df[df['tipo'] == 'ENTRADA']['valor'].sum()
        saida = df[df['tipo'] == 'SAIDA']['valor'].sum()
        saldo = entrada - saida
        
        # Cálculo: SÓ NUBANK
        total_nubank = df[
            (df['tipo'] == 'SAIDA') & 
            (df['origem'] == 'Nubank')
        ]['valor'].sum()

        # Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entradas", f"R$ {entrada:,.2f}")
        c2.metric("Saídas Totais", f"R$ {saida:,.2f}")
        c3.metric("Saldo Geral", f"R$ {saldo:,.2f}")
        c4.metric("🟣 Só Nubank", f"R$ {total_nubank:,.2f}", help="Soma dos CSVs importados")
        
        st.divider()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if saida > 0:
                st.subheader("Gastos por Categoria")
                df_saida = df[df['tipo'] == 'SAIDA']
                fig = px.donut(df_saida, values='valor', names='categoria', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem saídas registradas.")
                
        with col2:
            st.subheader("Extrato Detalhado")
            st.dataframe(
                df[['data', 'descricao', 'valor', 'categoria', 'origem']].sort_values('data', ascending=False), 
                use_container_width=True, 
                hide_index=True
            )
            
        # --- ZONA DE PERIGO (RESET) ---
        st.divider()
        with st.expander("🚨 Zona de Perigo (Limpar Dados)"):
            st.warning("Cuidado: Isso apaga o arquivo CSV lá no GitHub para sempre.")
            if st.button("🗑️ APAGAR TODOS OS DADOS"):
                # Cria um DataFrame vazio e salva por cima
                empty_df = pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor", "origem"])
                if salvar_dataframe_no_git(empty_df):
                    st.success("Tudo limpo! Começando do zero.")
                    st.rerun()
    else:
        st.info("Nenhum dado encontrado. Use as abas para começar.")

# === ABA 2: LANÇAMENTO MANUAL ===
with tab2:
    st.header("Novo Gasto Avulso")
    with st.form("form_manual", clear_on_submit=True):
        col_form1, col_form2 = st.columns(2)
        data = col_form1.date_input("Data", datetime.now())
        descricao = col_form2.text_input("Descrição")
        
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
                "valor": valor,
                "origem": "Manual"
            }])
            
            df_atual = ler_dados()
            df_final = pd.concat([df_atual, nova_linha], ignore_index=True)
            
            with st.spinner("Enviando para o Git..."):
                if salvar_dataframe_no_git(df_final):
                    st.success("Salvo!")
                    st.rerun()

# === ABA 3: IMPORTAR NUBANK ===
with tab3:
    st.header("📂 Importar Fatura Nubank")
    st.markdown("Arraste o arquivo CSV aqui. O sistema soma a fatura e classifica os gastos.")
    
    uploaded_file = st.file_uploader("Solte o arquivo CSV aqui", type="csv")

    if uploaded_file is not None:
        try:
            df_nubank = pd.read_csv(uploaded_file)
            novos_dados = []
            
            for index, row in df_nubank.iterrows():
                # Tratamento Data
                try:
                    data_obj = pd.to_datetime(row['date'])
                    data_formatada = data_obj.strftime("%Y-%m-%d")
                except:
                    data_formatada = datetime.now().strftime("%Y-%m-%d")

                # Tratamento Texto
                cat_nubank = str(row.get('category', '')).title()
                titulo = str(row.get('title', '')).title()
                
                # Ignora pagamento de fatura
                if 'Pagamento' in titulo and 'Fatura' in titulo:
                    continue 

                # Categorização Automática
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
                # ✅ FIX DO ERRO DE DATA (RESET DE TIPO)
                df_previa['data'] = pd.to_datetime(df_previa['data'])
                # --------------------------------------

                total_fatura = df_previa['valor'].sum()
                
                c_total, c_aviso = st.columns([1, 2])
                c_total.metric("Valor Fatura", f"R$ {total_fatura:,.2f}")
                c_aviso.info(f"{len(df_previa)} itens encontrados.")
                
                st.divider()

                # Tabela Editável
                df_editado = st.data_editor(
                    df_previa,
                    column_config={
                        "categoria": st.column_config.SelectboxColumn(
                            "Categoria",
                            width="medium",
                            options=["Mercado", "Lazer", "Casa", "Transporte", "Saúde", "Contas Fixas", "Outros"],
                            required=True
                        ),
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
                    # Preenche campos automáticos
                    df_editado['quem'] = "Casal"
                    df_editado['origem'] = "Nubank"
                    # Converte data de volta para Texto para salvar no CSV limpo
                    df_editado['data'] = df_editado['data'].dt.strftime("%Y-%m-%d")

                    df_atual = ler_dados()
                    
                    # Junta e remove duplicatas
                    df_final = pd.concat([df_atual, df_editado], ignore_index=True)
                    df_final = df_final.drop_duplicates(subset=['data', 'descricao', 'valor'])
                    
                    with st.spinner("Salvando no Git..."):
                        if salvar_dataframe_no_git(df_final):
                            st.success(f"Fatura importada com sucesso!")
                            st.rerun()
            else:
                st.warning("O arquivo não contém gastos válidos.")
            
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")
