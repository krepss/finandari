import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="Finanças Casal", layout="wide", page_icon="💰")

# ✅ SEU REPOSITÓRIO (Já atualizado)
GITHUB_REPO = "krepss/finandari"
ARQUIVO_CSV = "dados.csv"

# --- 2. FUNÇÕES DE CONEXÃO (GITHUB) ---
def get_github_repo():
    """Conecta ao GitHub usando o Token secreto"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except:
        # Se rodar local sem secrets.toml
        st.error("ERRO: Token do GitHub não encontrado. Configure o secrets.toml ou os Secrets da nuvem.")
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
        # Retorna tabela vazia se o arquivo não existir ainda
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor"])

def salvar_dataframe_no_git(df_novo_completo):
    """Salva os dados no GitHub (Sobrescreve o CSV)"""
    repo = get_github_repo()
    if not repo: return False
    
    # Garante que as datas sejam salvas como string simples (YYYY-MM-DD)
    # Isso evita problemas futuros de formatação
    if 'data' in df_novo_completo.columns:
         # Tenta converter para datetime e depois para string, se falhar, deixa como está
        try:
            df_novo_completo['data'] = pd.to_datetime(df_novo_completo['data']).dt.strftime("%Y-%m-%d")
        except:
            pass

    novo_conteudo = df_novo_completo.to_csv(index=False)
    
    try:
        # Atualiza arquivo existente
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(ARQUIVO_CSV, "Update via Streamlit", novo_conteudo, contents.sha)
        return True
    except:
        # Cria arquivo se não existir
        try:
            repo.create_file(ARQUIVO_CSV, "Create CSV", novo_conteudo)
            return True
        except Exception as e:
            st.error(f"Erro ao salvar no Git: {e}")
            return False

# --- 3. BARRA LATERAL (PREVISÃO ORÇAMENTÁRIA) ---
with st.sidebar:
    st.header("🔮 Planejamento")
    st.markdown("Quanto dinheiro entra este mês?")
    
    # Inputs numéricos
    salario_fixo = st.number_input("Salários (Soma)", min_value=0.0, value=5000.00, step=100.0)
    renda_extra = st.number_input("Renda Extra / Freelas", min_value=0.0, value=0.0, step=50.0)
    
    receita_prevista_total = salario_fixo + renda_extra
    
    st.divider()
    st.metric("💰 Caixa Total Previsto", f"R$ {receita_prevista_total:,.2f}")

# --- 4. INTERFACE PRINCIPAL ---
st.title("💰 Finanças do Casal")

tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "✍️ Lançar Manual", "📂 Importar Nubank"])

# === ABA 1: DASHBOARD COM CORREÇÃO DO ERRO ===
with tab1:
    df = ler_dados()
    
    if not df.empty:
        # Converte colunas para garantir cálculos certos
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
        
        # Filtro de Mês
        lista_meses = sorted(df['mes_ano'].unique(), reverse=True)
        col_filtro, col_vazia = st.columns([1, 3])
        with col_filtro:
            mes_escolhido = st.selectbox("📅 Analisar Mês:", lista_meses, index=0)
        
        # Aplica filtro
        df_filtrado = df[df['mes_ano'] == mes_escolhido]
        
        # Cálculos
        gastos_reais = df_filtrado[df_filtrado['tipo'] == 'SAIDA']['valor'].sum()
        sobra_projetada = receita_prevista_total - gastos_reais
        
        # Cartões
        st.subheader(f"Resumo de {mes_escolhido}")
        c1, c2, c3 = st.columns(3)
        c1.metric("💸 Gastos (CSV)", f"R$ {gastos_reais:,.2f}", delta_color="inverse")
        c2.metric("💰 Renda Prevista", f"R$ {receita_prevista_total:,.2f}")
        
        cor_saldo = "normal" if sobra_projetada >= 0 else "inverse"
        c3.metric("🔮 Sobra Projetada", f"R$ {sobra_projetada:,.2f}", delta_color=cor_saldo)

        # --- BARRA DE PROGRESSO BLINDADA (CORREÇÃO DO ERRO) ---
        st.markdown("### 🚦 Saúde do Mês")
        if receita_prevista_total > 0:
            porcentagem_gasta = (gastos_reais / receita_prevista_total)
            
            # O código abaixo impede que o número seja menor que 0 ou maior que 1
            # Isso resolve o erro "Progress Value has invalid value"
            porcentagem_visual = max(0.0, min(porcentagem_gasta, 1.0))
            
            msg_barra = "Tudo tranquilo! 👍"
            if porcentagem_gasta > 0.70: msg_barra = "Atenção ⚠️"
            if porcentagem_gasta > 0.90: msg_barra = "PERIGO 🚨"
            if porcentagem_gasta > 1.0:  msg_barra = "ESTOUROU O ORÇAMENTO 💸"
            
            st.progress(porcentagem_visual)
            st.caption(f"Você consumiu **{porcentagem_gasta*100:.1f}%** da renda prevista. {msg_barra}")
        # -----------------------------------------------------
        
        st.divider()
        
        # Gráficos e Tabela
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
        st.info("Nenhum dado encontrado. Use as abas para adicionar.")

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
            nova = pd.DataFrame([{
                "data": data.strftime("%Y-%m-%d"), 
                "descricao": descricao, 
                "categoria": categoria, 
                "quem": "Casal", # Padrão manual
                "tipo": "SAIDA", 
                "valor": valor
            }])
            df_atual = ler_dados()
            df_final = pd.concat([df_atual, nova], ignore_index=True)
            with st.spinner("Salvando no GitHub..."):
                if salvar_dataframe_no_git(df_final): st.success("Salvo!"); st.rerun()

# === ABA 3: IMPORTAR NUBANK ===
with tab3:
    st.header("📂 Importar Fatura")
    st.markdown("Arraste o CSV do Nubank. Tudo será classificado como 'Casal'.")
    uploaded = st.file_uploader("Arquivo CSV", type="csv")

    if uploaded:
        try:
            df_nb = pd.read_csv(uploaded)
            novos = []
            for _, row in df_nb.iterrows():
                try: d_fmt = pd.to_datetime(row['date']).strftime("%Y-%m-%d")
                except: d_fmt = datetime.now().strftime("%Y-%m-%d")
                
                # Tratamento de Strings
                cat_nb = str(row.get('category', '')).title()
                tit = str(row.get('title', '')).title()
                
                # Ignora pagamento de fatura
                if 'Pagamento' in tit and 'Fatura' in tit: continue 
                
                # Classificação Automática
                cat = "Outros"
                if any(x in cat_nb or x in tit for x in ['Transporte', 'Uber', '99', 'Posto']): cat = 'Transporte'
                elif any(x in cat_nb or x in tit for x in ['Mercado', 'Supermercado', 'Assai', 'Atacadao']): cat = 'Mercado'
                elif any(x in cat_nb or x in tit for x in ['Restaurante', 'Ifood', 'Burger', 'Pizza']): cat = 'Lazer'
                elif any(x in cat_nb or x in tit for x in ['Serviços', 'Netflix', 'Streaming']): cat = 'Contas Fixas'
                elif any(x in cat_nb or x in tit for x in ['Saúde', 'Farmacia', 'Drogasil']): cat = 'Saúde'

                novos.append({"data": d_fmt, "descricao": tit, "categoria": cat, "tipo": "SAIDA", "valor": float(row['amount'])})
            
            df_previa = pd.DataFrame(novos)
            if not df_previa.empty:
                # Converte para data real pro editor funcionar
                df_previa['data'] = pd.to_datetime(df_previa['data'])
                
                st.info("Confira os dados abaixo:")
                df_edit = st.data_editor(
                    df_previa, 
                    hide_index=True, 
                    num_rows="dynamic", 
                    column_config={
                        "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), 
                        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                    }
                )
                
                if st.button("✅ Confirmar Importação"):
                    # Prepara para salvar
                    df_edit['quem'] = "Casal"
                    # Converte data de volta para texto simples
                    df_edit['data'] = df_edit['data'].dt.strftime("%Y-%m-%d")
                    
                    df_final = pd.concat([ler_dados(), df_edit], ignore_index=True).drop_duplicates(subset=['data', 'descricao', 'valor'])
                    with st.spinner("Salvando no GitHub..."):
                        if salvar_dataframe_no_git(df_final): st.success("Importado com sucesso!"); st.rerun()
            else: st.warning("Nenhum dado válido encontrado no CSV.")
        except Exception as e: st.error(f"Erro no CSV: {e}")
