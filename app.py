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
        try:
            contents = repo.get_contents(ARQUIVO_CSV)
            csv_data = contents.decoded_content.decode("utf-8")
            df = pd.read_csv(StringIO(csv_data))
            
            if 'origem' not in df.columns: df['origem'] = 'Manual'
            if 'quem' not in df.columns: df['quem'] = 'Casal'
            
            if not df.empty:
                df['data'] = pd.to_datetime(df['data'], format='mixed', errors='coerce')
                df = df.dropna(subset=['data'])
            return df
        except Exception as e:
            if "404" in str(e): return pd.DataFrame(columns=["data", "descricao", "categoria", "quem", "tipo", "valor", "origem"])
            else: st.error(f"⚠️ Erro GitHub: {e}"); return None
    except Exception as e: st.error(f"⚠️ Erro Crítico: {e}"); return None

def salvar_dataframe_no_git(df_novo_completo):
    repo = get_github_repo()
    if not df_novo_completo.empty:
        try: df_novo_completo['data'] = pd.to_datetime(df_novo_completo['data']).dt.strftime("%Y-%m-%d")
        except: pass
    novo_conteudo = df_novo_completo.to_csv(index=False)
    try:
        contents = repo.get_contents(ARQUIVO_CSV)
        repo.update_file(path=ARQUIVO_CSV, message="Update via App", content=novo_conteudo, sha=contents.sha)
        return True
    except:
        try: repo.create_file(path=ARQUIVO_CSV, message="Init", content=novo_conteudo); return True
        except Exception as e: st.error(f"Erro Salvar: {e}"); return False

# --- 3. INTERFACE ---
st.title("💰 Finanças do Casal")
df = ler_dados()
if df is None: st.stop()

# ==========================================
# 🟣 BARRA LATERAL (FILTROS)
# ==========================================
st.sidebar.header("🔍 Filtros & Ajustes")

# --- 1. FILTRO DE FONTE (NOVIDADE!) ---
# Aqui você separa o que é Nubank, Manual, Planilha, etc.
st.sidebar.subheader("Separar por Origem")
lista_origens = sorted(df['origem'].unique()) if not df.empty else ["Manual", "Nubank"]
# Por padrão, seleciona tudo
filtro_origem = st.sidebar.multiselect(
    "Mostrar dados de:", 
    options=lista_origens, 
    default=lista_origens
)

# --- 2. FILTRO DE MÊS ---
st.sidebar.subheader("Período")
mes_selecionado = "Todos"
if not df.empty:
    df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
    lista_meses = sorted(df['mes_ano'].unique(), reverse=True)
    mes_selecionado = st.sidebar.selectbox("Mês:", ["Todos"] + list(lista_meses))

# --- 3. METAS ---
st.sidebar.divider()
with st.sidebar.expander("🎯 Configurar Metas (Budget)"):
    meta_mercado = st.number_input("Mercado", value=1500.0, step=50.0)
    meta_lazer = st.number_input("Lazer", value=800.0, step=50.0)
    meta_transporte = st.number_input("Transporte", value=500.0, step=50.0)
    meta_fixas = st.number_input("Contas Fixas", value=2000.0, step=50.0)
    meta_casa = st.number_input("Casa", value=500.0, step=50.0)
    metas = {"Mercado": meta_mercado, "Lazer": meta_lazer, "Transporte": meta_transporte, "Contas Fixas": meta_fixas, "Casa": meta_casa}

# --- 4. BACKUP ---
st.sidebar.divider()
csv_csv = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button("📥 Baixar Backup", csv_csv, 'financas_backup.csv', 'text/csv')

# --- 5. GERADOR DE RENDA ---
st.sidebar.divider()
with st.sidebar.expander("💸 Gerar Renda Recorrente"):
    with st.form("form_receita"):
        rec_desc = st.text_input("Descrição", "Salário")
        rec_valor = st.number_input("Valor", min_value=0.0, step=100.0)
        rec_dia = st.number_input("Dia", 1, 31, 5)
        rec_meses = st.slider("Meses", 1, 12, 12)
        if st.form_submit_button("Gerar"):
            df_atual = ler_dados()
            if df_atual is not None:
                lista = []
                now = datetime.now()
                for i in range(rec_meses):
                    y, m = now.year, now.month + i
                    while m > 12: m -= 12; y += 1
                    try: dt = f"{y}-{m:02d}-{rec_dia:02d}"; pd.to_datetime(dt)
                    except: dt = f"{y}-{m:02d}-28"
                    lista.append({"data": dt, "descricao": rec_desc, "categoria": "Salário", "quem": "Casal", "tipo": "ENTRADA", "valor": rec_valor, "origem": "Previsão"})
                df_final = pd.concat([df_atual, pd.DataFrame(lista)], ignore_index=True)
                if salvar_dataframe_no_git(df_final): st.sidebar.success("Gerado!"); time.sleep(1.5); st.rerun()

# ==========================================
# APLICAÇÃO DOS FILTROS
# ==========================================
# Primeiro filtra a Origem (Nubank vs Outros)
if filtro_origem:
    df_visualizacao = df[df['origem'].isin(filtro_origem)]
else:
    df_visualizacao = df # Se o usuário tirar tudo, mostra tudo pra não bugar

# Depois filtra o Mês
if mes_selecionado != "Todos":
    df_visualizacao = df_visualizacao[df_visualizacao['mes_ano'] == mes_selecionado]

# ==========================================
# ÁREA PRINCIPAL
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "✍️ Lançar", "📂 Importar", "📝 Gestão de Lançamentos"])

# === ABA 1: DASHBOARD ===
with tab1:
    if not df_visualizacao.empty:
        entrada = df_visualizacao[df_visualizacao['tipo'] == 'ENTRADA']['valor'].sum()
        saida = df_visualizacao[df_visualizacao['tipo'] == 'SAIDA']['valor'].sum()
        saldo = entrada - saida
        
        taxa_poupanca = 0
        if entrada > 0: taxa_poupanca = (saldo / entrada) * 100
        
        c_poup = "off"; m_poup = "Neutro"
        if taxa_poupanca >= 20: c_poup="normal"; m_poup="🔥 Excelente! (>20%)"
        elif taxa_poupanca > 0: c_poup="off"; m_poup="👍 Positivo"
        else: c_poup="inverse"; m_poup="⚠️ Atenção"

        st.caption(f"Período: **{mes_selecionado}** | Origens: **{', '.join(filtro_origem)}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entradas", f"R$ {entrada:,.2f}")
        c2.metric("Saídas", f"R$ {saida:,.2f}")
        c3.metric("Saldo", f"R$ {saldo:,.2f}")
        c4.metric("💰 Poupança", f"{taxa_poupanca:.1f}%", delta=m_poup, delta_color=c_poup)
        
        st.divider()

        # METAS (Só aparecem se houver saídas)
        if saida > 0:
            st.subheader("🎯 Metas (Budget)")
            gastos_cat = df_visualizacao[df_visualizacao['tipo']=='SAIDA'].groupby('categoria')['valor'].sum()
            col_m1, col_m2 = st.columns(2)
            for i, (cat, teto) in enumerate(metas.items()):
                gasto = gastos_cat.get(cat, 0.0)
                pct = min(gasto / teto, 1.0) if teto > 0 else 0
                col = col_m1 if i % 2 == 0 else col_m2
                with col:
                    st.write(f"**{cat}**")
                    st.progress(pct)
                    resta = teto - gasto
                    if resta >= 0: st.caption(f"Resta: R$ {resta:,.2f}")
                    else: st.caption(f":red[Estourou R$ {abs(resta):,.2f}!]")
            st.divider()

        # GRÁFICO DE EVOLUÇÃO
        st.subheader("📈 Evolução")
        # Usa o df filtrado pela origem, mas agrupado por mês
        df_evo = df[df['origem'].isin(filtro_origem)].groupby(['mes_ano', 'tipo'])['valor'].sum().reset_index()
        fig = px.bar(df_evo, x='mes_ano', y='valor', color='tipo', barmode='group', color_discrete_map={'ENTRADA': '#00CC96', 'SAIDA': '#EF553B'})
        st.plotly_chart(fig, use_container_width=True)

        # PIZZA E EXTRATO
        c_graf, c_tab = st.columns([1,1])
        with c_graf:
            if saida > 0:
                # Gráfico de Rosca por Categoria
                st.subheader("Por Categoria")
                fig_p = px.pie(df_visualizacao[df_visualizacao['tipo']=='SAIDA'], values='valor', names='categoria', hole=0.5)
                st.plotly_chart(fig_p, use_container_width=True)
                
                # NOVO: Gráfico de Barras por Origem (Para ver quanto é Nubank vs Outros)
                st.subheader("Por Origem")
                fig_o = px.bar(df_visualizacao[df_visualizacao['tipo']=='SAIDA'], x='origem', y='valor', color='origem')
                st.plotly_chart(fig_o, use_container_width=True)
                
        with c_tab:
            st.subheader("Extrato Detalhado")
            st.dataframe(df_visualizacao[['data', 'descricao', 'valor', 'categoria', 'origem']].sort_values('data', ascending=False), use_container_width=True, hide_index=True)
            
    else: st.info("Sem dados com estes filtros.")

# === ABA 2: LANÇAR ===
with tab2:
    st.header("Novo Lançamento")
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        dt = c1.date_input("Data", datetime.now())
        desc = c2.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Mercado", "Lazer", "Casa", "Salário", "Transporte", "Saúde", "Contas Fixas", "Outros", "Investimento"])
        quem = st.selectbox("Quem", ["Casal", "Ele", "Ela"])
        tipo = st.radio("Tipo", ["SAIDA", "ENTRADA"], horizontal=True)
        val = st.number_input("Valor", min_value=0.0, step=0.01)
        if st.form_submit_button("Salvar"):
            df_cur = ler_dados()
            if df_cur is not None:
                new = pd.DataFrame([{"data": dt.strftime("%Y-%m-%d"), "descricao": desc, "categoria": cat, "quem": quem, "tipo": tipo, "valor": val, "origem": "Manual"}])
                if salvar_dataframe_no_git(pd.concat([df_cur, new], ignore_index=True)): st.success("Salvo!"); time.sleep(1.5); st.rerun()

# === ABA 3: IMPORTAR ===
with tab3:
    st.header("📂 Importar")
    mod = st.radio("Tipo:", ["Nubank (CSV)", "Planilha Anual"], horizontal=True)
    upl = st.file_uploader("CSV", type="csv")
    if upl:
        try:
            ls = []
            if mod == "Nubank (CSV)":
                raw = pd.read_csv(upl)
                for _, r in raw.iterrows():
                    try: d = pd.to_datetime(r['date']).strftime("%Y-%m-%d")
                    except: d = datetime.now().strftime("%Y-%m-%d")
                    t, c = str(r.get('title','')).title(), str(r.get('category','')).title()
                    if 'Pagamento' in t or 'Pagamento' in c: continue
                    cat_f = "Outros"
                    if 'Uber' in t or 'Transporte' in c: cat_f='Transporte'
                    elif 'Mercado' in c or 'Assai' in t: cat_f='Mercado'
                    elif 'Ifood' in t or 'Restaurante' in c: cat_f='Lazer'
                    elif 'Netflix' in t: cat_f='Contas Fixas'
                    ls.append({"data": d, "descricao": t, "categoria": cat_f, "tipo": "SAIDA", "valor": abs(float(r['amount'])), "origem": "Nubank"})
            elif mod == "Planilha Anual":
                raw = pd.read_csv(upl)
                ano = raw.columns[0]; raw = raw.rename(columns={ano:'desc'}); raw=raw[raw['desc']!='TOTAL']
                melt = raw.melt(id_vars=['desc'], var_name='m', value_name='v')
                m_map = {'JAN':'01','FEV':'02','MAR':'03','ABR':'04','MAI':'05','JUN':'06','JUL':'07','AGO':'08','SET':'09','OUT':'10','NOV':'11','DEZ':'12'}
                for _, r in melt.iterrows():
                    v_str = str(r['v'])
                    if v_str in ['nan','']: continue
                    try: v_flt = float(v_str.replace('R$','').replace('.','').replace(',','.').strip())
                    except: continue
                    if v_flt > 0: ls.append({"data": f"{ano}-{m_map.get(r['m'],'01')}-10", "descricao": r['desc'], "categoria": "Contas Fixas", "tipo": "SAIDA", "valor": v_flt, "origem": f"Planilha {ano}"})
            
            df_p = pd.DataFrame(ls)
            if not df_p.empty:
                df_p['data'] = pd.to_datetime(df_p['data'], format='mixed', errors='coerce')
                st.info(f"{len(df_p)} itens."); ed = st.data_editor(df_p, hide_index=True)
                if st.button("Confirmar"):
                    cur = ler_dados()
                    if cur is not None:
                        ed['quem']="Casal"; 
                        if 'origem' not in ed.columns: ed['origem']="Importado"
                        ed['data']=ed['data'].dt.strftime("%Y-%m-%d")
                        fin = pd.concat([cur, ed], ignore_index=True).drop_duplicates(subset=['data','descricao','valor'])
                        if salvar_dataframe_no_git(fin): st.success("Feito!"); time.sleep(2); st.rerun()
            else: st.warning("Nada encontrado.")
        except Exception as e: st.error(f"Erro: {e}")

# === ABA 4: GESTÃO ===
with tab4:
    st.header("📝 Gestão de Lançamentos")
    df_completo = ler_dados()
    if df_completo is not None and not df_completo.empty:
        df_completo['mes_ano'] = pd.to_datetime(df_completo['data']).dt.strftime('%Y-%m')
        
        # FILTROS DA GESTÃO
        with st.expander("🔍 Filtros de Busca", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            f_mes = c1.selectbox("Mês", ["Todos"] + list(sorted(df_completo['mes_ano'].unique(), reverse=True)))
            f_cat = c2.multiselect("Categoria", sorted(df_completo['categoria'].unique()))
            # NOVO FILTRO DE ORIGEM AQUI TAMBÉM
            f_ori = c3.multiselect("Origem (Nubank/Manual)", sorted(df_completo['origem'].unique()))
            f_txt = c4.text_input("Buscar Texto")
        
        df_fil = df_completo.copy()
        if f_mes != "Todos": df_fil = df_fil[df_fil['mes_ano'] == f_mes]
        if f_cat: df_fil = df_fil[df_fil['categoria'].isin(f_cat)]
        if f_ori: df_fil = df_fil[df_fil['origem'].isin(f_ori)] # Aplica filtro de origem
        if f_txt: df_fil = df_fil[df_fil['descricao'].str.contains(f_txt, case=False, na=False) | df_fil['origem'].str.contains(f_txt, case=False, na=False)]
        df_fil = df_fil.sort_values('data', ascending=False)

        st.caption(f"Exibindo {len(df_fil)} lançamentos.")
        df_ed = st.data_editor(
            df_fil,
            column_config={
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "mes_ano": None
            },
            num_rows="dynamic", use_container_width=True, height=500
        )
        
        st.write("---")
        if st.button("💾 SALVAR ALTERAÇÕES", type="primary"):
            idx_exibidos = df_fil.index
            df_resto = df_completo.drop(idx_exibidos)
            df_final_save = pd.concat([df_resto, df_ed], ignore_index=True).sort_values('data', ascending=False)
            if 'mes_ano' in df_final_save.columns: df_final_save = df_final_save.drop(columns=['mes_ano'])

            with st.spinner("Atualizando..."):
                if salvar_dataframe_no_git(df_final_save): st.success("✅ Sucesso!"); time.sleep(2); st.rerun()
    else: st.warning("Vazio.")
