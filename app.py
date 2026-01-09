import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime
import time # <--- NOVO: Para a mensagem de confirmação não sumir rápido

# --- 1. CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="Finanças do Casal", layout="wide", page_icon="💰")

# ✅ SEU REPOSITÓRIO
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
        
        # Correção de colunas antigas
        if 'origem' not in df.columns:
            df['origem'] = 'Manual'
        if 'quem' not in df.columns:
            df['quem'] = 'Casal'
            
        return df
    except:
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor", "origem"])

def salvar_dataframe_no_git(df_novo_completo):
    repo = get_github_repo()
    novo_conteudo = df_novo_completo.to_csv(index=False)
    try:
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(path=ARQUIVO_CSV, message="Update via App", content=novo_conteudo, sha=contents.sha)
        return True
    except:
        try:
            repo.create_file(path=ARQUIVO_CSV, message="Init", content=novo_conteudo)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
            return False

# --- 3. INTERFACE ---
st.title("💰 Finanças do Casal")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "✍️ Lançar Manual", "📂 Importar Arquivos"])

# === ABA 1: DASHBOARD ===
with tab1:
    df = ler_dados()
    if not df.empty:
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        
        entrada = df[df['tipo'] == 'ENTRADA']['valor'].sum()
        saida = df[df['tipo'] == 'SAIDA']['valor'].sum()
        saldo = entrada - saida
        
        total_nubank = df[(df['tipo'] == 'SAIDA') & (df['origem'] == 'Nubank')]['valor'].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entradas", f"R$ {entrada:,.2f}")
        c2.metric("Saídas", f"R$ {saida:,.2f}")
        c3.metric("Saldo", f"R$ {saldo:,.2f}")
        c4.metric("🟣 Nubank", f"R$ {total_nubank:,.2f}")
        
        st.divider()
        col1, col2 = st.columns([1, 1])
        with col1:
            if saida > 0:
                st.subheader("Categorias")
                # Gráfico de Pizza (Donut)
                fig = px.pie(df[df['tipo'] == 'SAIDA'], values='valor', names='categoria', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem gastos.")
        with col2:
            st.subheader("Extrato")
            st.dataframe(df.sort_values('data', ascending=False), use_container_width=True, hide_index=True)
            
        st.divider()
        with st.expander("🚨 Zona de Perigo"):
            if st.button("🗑️ APAGAR TUDO"):
                empty_df = pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor", "origem"])
                if salvar_dataframe_no_git(empty_df):
                    st.success("Limpo!")
                    time.sleep(2) # Espera 2s para você ler
                    st.rerun()
    else:
        st.info("Sem dados.")

# === ABA 2: LANÇAMENTO MANUAL ===
with tab2:
    st.header("Novo Gasto")
    with st.form("form_manual", clear_on_submit=True):
        c1, c2 = st.columns(2)
        data = c1.date_input("Data", datetime.now())
        descricao = c2.text_input("Descrição")
        categoria = st.selectbox("Categoria", ["Mercado", "Lazer", "Casa", "Salário", "Transporte", "Saúde", "Contas Fixas", "Outros"])
        quem = st.selectbox("Quem?", ["Casal", "Ele", "Ela"])
        tipo = st.radio("Tipo", ["SAIDA", "ENTRADA"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
        
        if st.form_submit_button("Salvar"):
            novo = pd.DataFrame([{
                "data": data.strftime("%Y-%m-%d"), "descricao": descricao, "categoria": categoria,
                "quem": quem, "tipo": tipo, "valor": valor, "origem": "Manual"
            }])
            df_final = pd.concat([ler_dados(), novo], ignore_index=True)
            
            with st.spinner("Salvando..."):
                if salvar_dataframe_no_git(df_final):
                    st.success("✅ Gasto salvo com sucesso!")
                    time.sleep(1.5) # <--- O SEGREDO: Espera 1.5s
                    st.rerun()

# === ABA 3: IMPORTAÇÃO (NUBANK E PLANILHA) ===
with tab3:
    st.header("📂 Importar Arquivos")
    
    # SELETOR DE MODELO
    modelo = st.radio("Qual o modelo do arquivo?", ["Nubank (Fatura CSV)", "Planilha Anual (Meses nas colunas)"], horizontal=True)
    
    uploaded_file = st.file_uploader("Solte o CSV aqui", type="csv")

    if uploaded_file is not None:
        try:
            novos_dados = []
            
            # --- MODELO 1: NUBANK ---
            if modelo == "Nubank (Fatura CSV)":
                df_raw = pd.read_csv(uploaded_file)
                for _, row in df_raw.iterrows():
                    try:
                        dt = pd.to_datetime(row['date']).strftime("%Y-%m-%d")
                    except:
                        dt = datetime.now().strftime("%Y-%m-%d")
                        
                    desc = str(row.get('title', '')).title()
                    cat = str(row.get('category', '')).title()
                    
                    if 'Pagamento' in desc or 'Pagamento' in cat: continue
                    
                    cat_final = "Outros"
                    if 'Uber' in desc or 'Transporte' in cat: cat_final = 'Transporte'
                    elif 'Mercado' in cat or 'Assai' in desc: cat_final = 'Mercado'
                    elif 'Ifood' in desc or 'Restaurante' in cat: cat_final = 'Lazer'
                    elif 'Netflix' in desc: cat_final = 'Contas Fixas'
                    
                    novos_dados.append({
                        "data": dt, "descricao": desc, "categoria": cat_final,
                        "tipo": "SAIDA", "valor": abs(float(row['amount'])), "origem": "Nubank"
                    })

            # --- MODELO 2: PLANILHA ANUAL ---
            elif modelo == "Planilha Anual (Meses nas colunas)":
                df_raw = pd.read_csv(uploaded_file)
                
                # Pega o ano da primeira coluna
                ano = df_raw.columns[0]
                df_raw = df_raw.rename(columns={ano: 'descricao'})
                df_raw = df_raw[df_raw['descricao'] != 'TOTAL']
                
                df_melted = df_raw.melt(id_vars=['descricao'], var_name='mes', value_name='valor_str')
                
                mapa_mes = {'JAN':'01','FEV':'02','MAR':'03','ABR':'04','MAI':'05','JUN':'06',
                            'JUL':'07','AGO':'08','SET':'09','OUT':'10','NOV':'11','DEZ':'12'}
                
                for _, row in df_melted.iterrows():
                    val_str = str(row['valor_str'])
                    if val_str == 'nan' or val_str == '': continue
                    val_limpo = val_str.replace('R$','').replace('.','').replace(',','.').strip()
                    try:
                        valor_float = float(val_limpo)
                    except:
                        continue
                        
                    if valor_float > 0:
                        mes_num = mapa_mes.get(row['mes'], '01')
                        data_final = f"{ano}-{mes_num}-10"
                        
                        novos_dados.append({
                            "data": data_final, "descricao": row['descricao'],
                            "categoria": "Contas Fixas", "tipo": "SAIDA",
                            "valor": valor_float, "origem": f"Planilha {ano}"
                        })

            # --- EXIBIÇÃO DA PRÉVIA ---
            df_previa = pd.DataFrame(novos_dados)
            
            if not df_previa.empty:
                df_previa['data'] = pd.to_datetime(df_previa['data'])
                
                st.info(f"Foram encontrados {len(df_previa)} lançamentos.")
                st.metric("Total a Importar", f"R$ {df_previa['valor'].sum():,.2f}")
                
                df_editado = st.data_editor(
                    df_previa,
                    column_config={
                        "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                    },
                    hide_index=True,
                    num_rows="dynamic"
                )
                
                if st.button("✅ Confirmar Importação"):
                    df_editado['quem'] = "Casal"
                    if 'origem' not in df_editado.columns:
                        df_editado['origem'] = "Importado"
                    df_editado['data'] = df_editado['data'].dt.strftime("%Y-%m-%d")
                    
                    df_final = pd.concat([ler_dados(), df_editado], ignore_index=True)
                    df_final = df_final.drop_duplicates(subset=['data', 'descricao', 'valor'])
                    
                    with st.spinner("Enviando dados..."):
                        if salvar_dataframe_no_git(df_final):
                            st.success("✅ Importação concluída com sucesso!")
                            time.sleep(2) # <--- Espera 2s para você comemorar
                            st.rerun()
            else:
                st.warning("Nenhum dado válido encontrado.")
                
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
