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

# --- 2. FUNÇÕES DE CONEXÃO (GITHUB) ---
def get_github_repo():
    """Conecta ao GitHub usando o Token secreto"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except:
        st.error("ERRO: Token do GitHub não encontrado.")
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
        return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor"])

def salvar_dataframe_no_git(df_novo_completo):
    """Salva os dados no GitHub (Sobrescreve o CSV)"""
    repo = get_github_repo()
    if not repo: return False
    
    # Garante formatação de data para string YYYY-MM-DD
    if 'data' in df_novo_completo.columns:
        try:
            df_novo_completo['data'] = pd.to_datetime(df_novo_completo['data']).dt.strftime("%Y-%m-%d")
        except:
            pass

    novo_conteudo = df_novo_completo.to_csv(index=False)
    
    try:
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(ARQUIVO_CSV, "Update via Streamlit", novo_conteudo, contents.sha)
        return True
    except:
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
    
    salario_fixo = st.number_input("Salários (Soma)", min_value=0.0, value=5000.00, step=100.0)
    renda_extra = st.number_input("Renda Extra / Freelas", min_value=0.0, value=0.0, step=50.0)
    
    receita_prevista_total = salario_fixo + renda_extra
    
    st.divider()
    st.metric("💰 Caixa Total Previsto", f"R$ {receita_prevista_total:,.2f}")

# --- 4. INTERFACE PRINCIPAL ---
st.title("💰 Finanças do Casal")

# ADICIONEI A ABA 4 AQUI EMBAIXO 👇
tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "✍️ Lançar Manual", "📂 Importar Nubank", "🔧 Ajustes / Excluir"])

# === ABA 1: DASHBOARD ===
with tab1:
    df = ler_dados()
    
    if not df.empty:
        df['valor'] = pd.to_numeric(df['valor'])
        df['data'] = pd.to_datetime(df['data'])
        df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
        
        lista_meses = sorted(df['mes_ano'].unique(), reverse=True)
        col_filtro, col_vazia = st.columns([1, 3])
        with col_filtro:
            mes_escolhido = st.selectbox("📅 Analisar Mês:", lista_meses, index=0)
        
        df_filtrado = df[df['mes_ano'] == mes_escolhido]
        
        gastos_reais = df_filtrado[df_filtrado['tipo'] == 'SAIDA']['valor'].sum()
        sobra_projetada = receita_prevista_total - gastos_reais
        
        st.subheader(f"Resumo de {mes_escolhido}")
        c1, c2, c3 = st.columns(3)
        c1.metric("💸 Gastos (CSV)", f"R$ {gastos_reais:,.2f}", delta_color="inverse")
        c2.metric("💰 Renda Prevista", f"R$ {receita_prevista_total:,.2f}")
        
        cor_saldo = "normal" if sobra_projetada >= 0 else "inverse"
        c3.metric("🔮 Sobra Projetada", f"R$ {sobra_projetada:,.2f}", delta_color=cor_saldo)

        st.markdown("### 🚦 Saúde do Mês")
        if receita_prevista_total > 0:
            porcentagem_gasta = (gastos_reais / receita_prevista_total)
            porcentagem_visual = max(0.0, min(porcentagem_gasta, 1.0))
            
            msg_barra = "Tudo tranquilo! 👍"
            if porcentagem_gasta > 0.70: msg_barra = "Atenção ⚠️"
            if porcentagem_gasta > 0.90: msg_barra = "PERIGO 🚨"
            if porcentagem_gasta > 1.0:  msg_barra = "ESTOUROU O ORÇAMENTO 💸"
            
            st.progress(porcentagem_visual)
            st.caption(f"Você consumiu **{porcentagem_gasta*100:.1f}%** da renda prevista. {msg_barra}")
        
        st.divider()
        
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
        st.info("Nenhum dado encontrado.")

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
                "quem": "Casal",
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
    st.markdown("Arraste o CSV do Nubank.")
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
                    df_edit['quem'] = "Casal"
                    df_edit['data'] = df_edit['data'].dt.strftime("%Y-%m-%d")
                    df_final = pd.concat([ler_dados(), df_edit], ignore_index=True).drop_duplicates(subset=['data', 'descricao', 'valor'])
                    with st.spinner("Salvando no GitHub..."):
                        if salvar_dataframe_no_git(df_final): st.success("Importado com sucesso!"); st.rerun()
            else: st.warning("Nenhum dado válido.")
        except Exception as e: st.error(f"Erro no CSV: {e}")

# === ABA 4: AJUSTES E EXCLUSÃO (NOVA!) ===
with tab4:
    st.header("🔧 Gerenciamento de Dados")
    st.markdown("Aqui você pode corrigir lançamentos errados ou apagar dados antigos.")
    
    df_manutencao = ler_dados()
    
    if not df_manutencao.empty:
        # Tratamento
        df_manutencao['data'] = pd.to_datetime(df_manutencao['data'])
        df_manutencao['valor'] = pd.to_numeric(df_manutencao['valor'])
        
        st.subheader("1. Editor Completo (Corrigir ou Apagar Linhas)")
        st.info("Para excluir: Selecione a linha clicando na caixa à esquerda e aperte a tecla DELETE (ou clique na lixeira no celular). Depois clique em Salvar.")
        
        # Tabela Editável com opção de deletar
        df_editado_final = st.data_editor(
            df_manutencao,
            num_rows="dynamic", # Permite adicionar e remover linhas
            use_container_width=True,
            column_config={
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "categoria": st.column_config.SelectboxColumn("Categoria", options=["Mercado", "Lazer", "Casa", "Transporte", "Saúde", "Contas Fixas", "Outros"]),
                "tipo": st.column_config.SelectboxColumn("Tipo", options=["SAIDA", "ENTRADA"])
            },
            key="editor_manutencao"
        )
        
        if st.button("💾 Salvar Alterações na Tabela"):
            with st.spinner("Atualizando banco de dados..."):
                if salvar_dataframe_no_git(df_editado_final):
                    st.success("Tabela atualizada com sucesso!")
                    st.rerun()

        st.divider()

        # ZONA DE PERIGO (Exclusão em Massa)
        with st.expander("🚨 Zona de Perigo (Exclusões em Massa)"):
            st.warning("Cuidado! Essas ações não podem ser desfeitas.")
            
            c_del1, c_del2 = st.columns(2)
            
            # Opção 1: Apagar um mês inteiro
            with c_del1:
                st.subheader("Apagar Mês Específico")
                df_manutencao['mes_ano'] = df_manutencao['data'].dt.strftime('%Y-%m')
                meses_disponiveis = sorted(df_manutencao['mes_ano'].unique(), reverse=True)
                
                if meses_disponiveis:
                    mes_para_apagar = st.selectbox("Escolha o mês para apagar:", meses_disponiveis)
                    if st.button(f"🗑️ Excluir tudo de {mes_para_apagar}"):
                        # Filtra mantendo apenas o que NÃO é do mês escolhido
                        df_limpo = df_manutencao[df_manutencao['mes_ano'] != mes_para_apagar]
                        # Remove a coluna auxiliar antes de salvar
                        df_limpo = df_limpo.drop(columns=['mes_ano'])
                        
                        with st.spinner("Apagando mês..."):
                            if salvar_dataframe_no_git(df_limpo):
                                st.success(f"Dados de {mes_para_apagar} excluídos!")
                                st.rerun()
            
            # Opção 2: Reset Total
            with c_del2:
                st.subheader("Reset de Fábrica")
                check_seguranca = st.checkbox("Tenho certeza que quero apagar TODOS os dados.")
                
                if st.button("💣 APAGAR TUDO") and check_seguranca:
                    df_vazio = pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor"])
                    with st.spinner("Formatando sistema..."):
                        if salvar_dataframe_no_git(df_vazio):
                            st.success("Banco de dados zerado!")
                            st.rerun()
    else:
        st.info("O banco de dados está vazio.")
