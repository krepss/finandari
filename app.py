import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime
import time

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
        
        # Correção de colunas e tipos
        if 'origem' not in df.columns: df['origem'] = 'Manual'
        if 'quem' not in df.columns: df['quem'] = 'Casal'
        
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            
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

df = ler_dados()

# ==========================================
# 🟣 BARRA LATERAL: FILTROS E GERADOR DE RECEITA
# ==========================================
st.sidebar.header("🔍 Filtros")

# 1. Filtro de Mês
mes_selecionado = "Todos"
if not df.empty:
    df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
    lista_meses = sorted(df['mes_ano'].unique(), reverse=True)
    mes_selecionado = st.sidebar.selectbox("Mês:", ["Todos"] + list(lista_meses))

# 2. FERRAMENTA DE PREVISÃO DE SALÁRIO (NOVA!)
st.sidebar.divider()
st.sidebar.header("📅 Previsão de Receita")
with st.sidebar.expander("Gerar Renda Recorrente"):
    st.caption("Cria lançamentos futuros automaticamente.")
    with st.form("form_receita"):
        rec_desc = st.text_input("Descrição", "Salário Mensal")
        rec_valor = st.number_input("Valor R$", min_value=0.0, step=100.0)
        rec_dia = st.number_input("Dia do Recebimento", min_value=1, max_value=31, value=5)
        rec_meses = st.slider("Repetir por quantos meses?", 1, 12, 12)
        
        if st.form_submit_button("Gerar Entradas"):
            lista_receitas = []
            data_atual = datetime.now()
            
            # Loop para gerar os meses
            for i in range(rec_meses):
                # Lógica simples para avançar meses
                ano_atual = data_atual.year
                mes_atual = data_atual.month + i
                
                # Ajusta se virar o ano (mês 13 vira mês 1 do ano seguinte)
                while mes_atual > 12:
                    mes_atual -= 12
                    ano_atual += 1
                
                try:
                    # Tenta criar a data (cuidado com dia 31 em fevereiro)
                    data_lan = f"{ano_atual}-{mes_atual:02d}-{rec_dia:02d}"
                    # Validação simples de data
                    pd.to_datetime(data_lan) 
                except:
                    # Se der erro (ex: dia 30 de fev), joga pro dia 28
                    data_lan = f"{ano_atual}-{mes_atual:02d}-28"

                lista_receitas.append({
                    "data": data_lan,
                    "descricao": rec_desc,
                    "categoria": "Salário",
                    "quem": "Casal",
                    "tipo": "ENTRADA", # Importante: É Entrada!
                    "valor": rec_valor,
                    "origem": "Previsão Automática"
                })
            
            df_receitas = pd.DataFrame(lista_receitas)
            df_final = pd.concat([df, df_receitas], ignore_index=True)
            
            if salvar_dataframe_no_git(df_final):
                st.sidebar.success(f"{rec_meses} entradas geradas!")
                time.sleep(1.5)
                st.rerun()

# ==========================================
# LÓGICA DE FILTRAGEM
# ==========================================
if mes_selecionado != "Todos":
    df_visualizacao = df[df['mes_ano'] == mes_selecionado]
else:
    df_visualizacao = df

# ==========================================
# ÁREA PRINCIPAL
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "✍️ Lançar Gasto/Ganho", "📂 Importar CSV"])

# === ABA 1: DASHBOARD ===
with tab1:
    if not df_visualizacao.empty:
        entrada = df_visualizacao[df_visualizacao['tipo'] == 'ENTRADA']['valor'].sum()
        saida = df_visualizacao[df_visualizacao['tipo'] == 'SAIDA']['valor'].sum()
        saldo = entrada - saida
        
        total_nubank = df_visualizacao[(df_visualizacao['tipo'] == 'SAIDA') & (df_visualizacao['origem'] == 'Nubank')]['valor'].sum()

        st.caption(f"Período: **{mes_selecionado}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entradas (Previstas/Reais)", f"R$ {entrada:,.2f}")
        c2.metric("Saídas", f"R$ {saida:,.2f}")
        c3.metric("Saldo", f"R$ {saldo:,.2f}", delta_color="normal")
        c4.metric("🟣 Fatura Nubank", f"R$ {total_nubank:,.2f}")
        
        st.divider()
        col1, col2 = st.columns([1, 1])
        with col1:
            if saida > 0:
                st.subheader("Gastos por Categoria")
                fig = px.pie(df_visualizacao[df_visualizacao['tipo'] == 'SAIDA'], values='valor', names='categoria', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem gastos neste período.")
        with col2:
            st.subheader("Extrato")
            # Mostra 'origem' para você ver o que é Salário Automático
            st.dataframe(df_visualizacao[['data', 'descricao', 'valor', 'tipo', 'origem']].sort_values('data', ascending=False), use_container_width=True, hide_index=True)
            
        st.divider()
        with st.expander("🚨 Zona de Perigo"):
            if st.button("🗑️ APAGAR TUDO"):
                empty_df = pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor", "origem"])
                if salvar_dataframe_no_git(empty_df):
                    st.success("Limpo!")
                    time.sleep(2)
                    st.rerun()
    else:
        st.info("Nenhum dado. Use a barra lateral para gerar receitas ou as abas para lançar gastos.")

# === ABA 2: LANÇAMENTO MANUAL ===
with tab2:
    st.header("Novo Lançamento (Gasto ou Ganho)")
    with st.form("form_manual", clear_on_submit=True):
        c1, c2 = st.columns(2)
        data = c1.date_input("Data", datetime.now())
        descricao = c2.text_input("Descrição")
        categoria = st.selectbox("Categoria", ["Mercado", "Lazer", "Casa", "Salário", "Transporte", "Saúde", "Contas Fixas", "Outros", "Investimento"])
        quem = st.selectbox("Quem?", ["Casal", "Ele", "Ela"])
        tipo = st.radio("Tipo", ["SAIDA", "ENTRADA"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f")
        
        if st.form_submit_button("Salvar"):
            novo = pd.DataFrame([{
                "data": data.strftime("%Y-%m-%d"), "descricao": descricao, "categoria": categoria,
                "quem": quem, "tipo": tipo, "valor": valor, "origem": "Manual"
            }])
            df_final = pd.concat([df, novo], ignore_index=True)
            
            with st.spinner("Salvando..."):
                if salvar_dataframe_no_git(df_final):
                    st.success("✅ Salvo com sucesso!")
                    time.sleep(1.5)
                    st.rerun()

# === ABA 3: IMPORTAÇÃO ===
with tab3:
    st.header("📂 Importar Arquivos")
    modelo = st.radio("Modelo:", ["Nubank (CSV)", "Planilha Anual (Colunas = Meses)"], horizontal=True)
    uploaded_file = st.file_uploader("Solte o CSV aqui", type="csv")

    if uploaded_file is not None:
        try:
            novos_dados = []
            # --- Lógica Nubank ---
            if modelo == "Nubank (CSV)":
                df_raw = pd.read_csv(uploaded_file)
                for _, row in df_raw.iterrows():
                    try: dt = pd.to_datetime(row['date']).strftime("%Y-%m-%d")
                    except: dt = datetime.now().strftime("%Y-%m-%d")
                    
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

            # --- Lógica Planilha Anual ---
            elif modelo == "Planilha Anual (Colunas = Meses)":
                df_raw = pd.read_csv(uploaded_file)
                ano = df_raw.columns[0]
                df_raw = df_raw.rename(columns={ano: 'descricao'})
                df_raw = df_raw[df_raw['descricao'] != 'TOTAL']
                df_melted = df_raw.melt(id_vars=['descricao'], var_name='mes', value_name='valor_str')
                
                mapa_mes = {'JAN':'01','FEV':'02','MAR':'03','ABR':'04','MAI':'05','JUN':'06',
                            'JUL':'07','AGO':'08','SET':'09','OUT':'10','NOV':'11','DEZ':'12'}
                
                for _, row in df_melted.iterrows():
                    val_str = str(row['valor_str'])
                    if val_str == 'nan' or val_str == '': continue
                    try: valor_float = float(val_str.replace('R$','').replace('.','').replace(',','.').strip())
                    except: continue
                    
                    if valor_float > 0:
                        mes_num = mapa_mes.get(row['mes'], '01')
                        novos_dados.append({
                            "data": f"{ano}-{mes_num}-10", "descricao": row['descricao'],
                            "categoria": "Contas Fixas", "tipo": "SAIDA",
                            "valor": valor_float, "origem": f"Planilha {ano}"
                        })

            # --- Salvar ---
            df_previa = pd.DataFrame(novos_dados)
            if not df_previa.empty:
                df_previa['data'] = pd.to_datetime(df_previa['data'])
                st.info(f"{len(df_previa)} itens encontrados.")
                df_editado = st.data_editor(df_previa, column_config={"data":st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "valor":st.column_config.NumberColumn("Valor", format="R$ %.2f")}, hide_index=True, num_rows="dynamic")
                
                if st.button("✅ Confirmar"):
                    df_editado['quem'] = "Casal"
                    if 'origem' not in df_editado.columns: df_editado['origem'] = "Importado"
                    df_editado['data'] = df_editado['data'].dt.strftime("%Y-%m-%d")
                    df_final = pd.concat([df, df_editado], ignore_index=True)
                    df_final = df_final.drop_duplicates(subset=['data', 'descricao', 'valor'])
                    
                    with st.spinner("Salvando..."):
                        if salvar_dataframe_no_git(df_final):
                            st.success("✅ Importado!")
                            time.sleep(2)
                            st.rerun()
            else: st.warning("Nada encontrado.")
        except Exception as e: st.error(f"Erro: {e}")
