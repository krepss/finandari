import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="Finanças Casal", layout="wide", page_icon="💰")

# ✅ SEU REPOSITÓRIO
GITHUB_REPO = "krepss/finandari"
ARQUIVO_CSV = "dados.csv"

# --- 2. FUNÇÕES (GITHUB) ---
def get_github_repo():
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except:
        st.error("ERRO: Token do GitHub não encontrado.")
        return None
    g = Github(token)
    return g.get_repo(GITHUB_REPO)

def ler_dados():
    try:
        repo = get_github_repo()
        if not repo: return pd.DataFrame()
        contents = repo.get_contents(ARQUIVO_CSV)
        csv_data = contents.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(csv_data))
    except:
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor"])

def salvar_dataframe_no_git(df_novo_completo):
    repo = get_github_repo()
    if not repo: return False
    novo_conteudo = df_novo_completo.to_csv(index=False)
    try:
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(ARQUIVO_CSV, "Update Streamlit", novo_conteudo, contents.sha)
        return True
    except:
        try:
            repo.create_file(ARQUIVO_CSV, "Create CSV", novo_conteudo)
            return True
        except Exception as e:
            st.error(f"Erro Git: {e}")
            return False

# --- 3. BARRA LATERAL (PREVISÃO DE RENDA) ---
with st.sidebar:
    st.header("🔮 Previsão de Renda")
    st.markdown("Defina quanto entra esse mês para calcularmos a sobra.")
    
    # Inputs para Salário e Extras
    salario_fixo = st.number_input("Salário Mensal (Casal)", min_value=0.0, value=5000.00, step=100.0)
    renda_extra = st.number_input("Extras / Por fora", min_value=0.0, value=0.0, step=50.0)
    
    receita_prevista_total = salario_fixo + renda_extra
    
    st.divider()
    st.metric("💰 Caixa Total Previsto", f"R$ {receita_prevista_total:,.2f}")
    st.info("👆 Mude esses valores conforme o mês.")

# --- 4. INTERFACE PRINCIPAL ---
st.title("💰 Finanças do Casal")

tab1, tab2, tab3 = st.tabs(["📊 Visão Geral & Metas", "✍️ Lançar Manual", "📂 Importar Nubank"])

# === ABA 1: DASHBOARD COM PREVISÃO ===
with tab1:
    df = ler_dados()
    
    if not df.empty:
        # Tratamento
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
        
        # Filtro de Mês
        lista_meses = sorted(df['mes_ano'].unique(), reverse=True)
        # Seleciona o primeiro mês da lista (o mais atual) automaticamente
        mes_atual_padrao = lista_meses[0] if len(lista_meses) > 0 else None
        
        col_filtro, col_msg = st.columns([1, 3])
        with col_filtro:
            mes_escolhido = st.selectbox("📅 Analisar Mês:", lista_meses, index=0)
        
        # Aplica filtro
        df_filtrado = df[df['mes_ano'] == mes_escolhido]
        
        # Cálculos do REALIZADO (O que está no CSV)
        gastos_reais = df_filtrado[df_filtrado['tipo'] == 'SAIDA']['valor'].sum()
        entradas_reais = df_filtrado[df_filtrado['tipo'] == 'ENTRADA']['valor'].sum()
        
        # Cálculos de PROJEÇÃO (Previsão - Gastos)
        sobra_projetada = receita_prevista_total - gastos_reais
        
        # --- CARTÕES DE SAÚDE FINANCEIRA ---
        st.subheader(f"Resumo de {mes_escolhido}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💸 Gastos Totais (CSV)", f"R$ {gastos_reais:,.2f}", delta_color="inverse")
        c2.metric("💰 Renda Prevista (Lateral)", f"R$ {receita_prevista_total:,.2f}", help="Soma do Salário + Extras configurados na barra lateral")
        
        # Lógica da cor do Saldo
        cor_saldo = "normal" if sobra_projetada > 0 else "inverse"
        c3.metric("invisivel", "invisivel", label_visibility="hidden") # Hack para alinhar
        c3.metric("🔮 Sobra Projetada (Livre)", f"R$ {sobra_projetada:,.2f}", delta=f"{sobra_projetada:,.2f}", delta_color=cor_saldo)

        # BARRA DE PROGRESSO DO ORÇAMENTO
        st.markdown("### 🚦 Comprometimento da Renda")
        if receita_prevista_total > 0:
            porcentagem_gasta = (gastos_reais / receita_prevista_total)
            porcentagem_visual = min(porcentagem_gasta, 1.0) # Trava em 100% pro visual não quebrar
            
            # Cor da barra
            cor_barra = "green"
            msg_barra = "Tudo sob controle! 👍"
            if porcentagem_gasta > 0.70: 
                cor_barra = "orange"
                msg_barra = "Atenção! Cuidado com os gastos. ⚠️"
            if porcentagem_gasta > 0.90: 
                cor_barra = "red"
                msg_barra = "PERIGO! Você está quase estourando o orçamento. 🚨"
                
            st.progress(porcentagem_visual)
            st.caption(f"Você já consumiu **{porcentagem_gasta*100:.1f}%** da sua renda prevista. {msg_barra}")
        
        st.divider()
        
        # Gráficos e Tabelas (Código anterior mantido)
        col1, col2 = st.columns([1, 1])
        with col1:
            if gastos_reais > 0:
                st.subheader("Para onde foi o dinheiro?")
                df_saida = df_filtrado[df_filtrado['tipo'] == 'SAIDA']
                fig = px.donut(df_saida, values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem gastos neste mês.")
                
        with col2:
            st.subheader("Extrato Detalhado")
            st.dataframe(
                df_filtrado[['data', 'descricao', 'categoria', 'valor']].sort_values('data', ascending=False), 
                use_container_width=True, hide_index=True,
                column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")}
            )
    else:
        st.info("Sem dados. Comece importando uma fatura!")

# === ABA 2: LANÇAMENTO MANUAL ===
with tab2:
    st.header("Novo Gasto Avulso")
    with st.form("form_manual", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        data = col_a.date_input("Data", datetime.now())
        descricao = col_b.text_input("Descrição")
        categoria = st.selectbox("Categoria", ["Mercado", "Lazer", "Casa", "Transporte", "Saúde", "Contas Fixas", "Outros"])
        valor = st.number_input("Valor R$", min_value=0.0, step=0.01, format="%.2f")
        
        if st.form_submit_button("Salvar"):
            nova = pd.DataFrame([{"data": data.strftime("%Y-%m-%d"), "descricao": descricao, "categoria": categoria, "quem": "Casal", "tipo": "SAIDA", "valor": valor}])
            df_atual = ler_dados()
            df_final = pd.concat([df_atual, nova], ignore_index=True)
            with st.spinner("Salvando..."):
                if salvar_dataframe_no_git(df_final): st.success("Salvo!"); st.rerun()

# === ABA 3: IMPORTAR NUBANK ===
with tab3:
    st.header("📂 Importar Fatura")
    st.markdown("Arraste o CSV do Nubank aqui.")
    uploaded = st.file_uploader("Arquivo CSV", type="csv")

    if uploaded:
        try:
            df_nb = pd.read_csv(uploaded)
            novos = []
            for _, row in df_nb.iterrows():
                try: d_fmt = pd.to_datetime(row['date']).strftime("%Y-%m-%d")
                except: d_fmt = datetime.now().strftime("%Y-%m-%d")
                
                cat_nb = str(row.get('category', '')).title()
                tit = str(row.get('title', '')).title()
                if 'Pagamento' in tit and 'Fatura' in tit: continue 
                
                cat = "Outros"
                if any(x in cat_nb or x in tit for x in ['Transporte', 'Uber', '99', 'Posto']): cat = 'Transporte'
                elif any(x in cat_nb or x in tit for x in ['Mercado', 'Supermercado', 'Assai', 'Atacadao']): cat = 'Mercado'
                elif any(x in cat_nb or x in tit for x in ['Restaurante', 'Ifood', 'Burger', 'Pizza']): cat = 'Lazer'
                elif any(x in cat_nb or x in tit for x in ['Serviços', 'Netflix', 'Streaming']): cat = 'Contas Fixas'
                elif any(x in cat_nb or x in tit for x in ['Saúde', 'Farmacia', 'Drogasil']): cat = 'Saúde'

                novos.append({"data": d_fmt, "descricao": tit, "categoria": cat, "tipo": "SAIDA", "valor": float(row['amount'])})
            
            df_previa = pd.DataFrame(novos)
            if not df_previa.empty:
                df_previa['data'] = pd.to_datetime(df_previa['data'])
                st.info("Confira os dados abaixo:")
                df_edit = st.data_editor(df_previa, hide_index=True, num_rows="dynamic", column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})
                
                if st.button("✅ Confirmar Importação"):
                    df_edit['quem'] = "Casal"
                    df_edit['data'] = df_edit['data'].dt.strftime("%Y-%m-%d")
                    df_final = pd.concat([ler_dados(), df_edit], ignore_index=True).drop_duplicates(subset=['data', 'descricao', 'valor'])
                    with st.spinner("Salvando..."):
                        if salvar_dataframe_no_git(df_final): st.success("Importado!"); st.rerun()
            else: st.warning("Nenhum dado válido.")
        except Exception as e: st.error(f"Erro no CSV: {e}")
