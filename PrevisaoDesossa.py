import streamlit as st
import pandas as pd
import gspread

# --- CONFIGURAÇÃO DA API ---
PLANILHA_NOME = "Dados_Desossa" 
PLANILHA_ESTOQUE_NOME = "Estoque_industria_Analitico"
PLANILHA_PEDIDOS_NOME = "Mapa_de_Pedidos2"

def conectar_google_drive():
    try:
        if "gcp_service_account" in st.secrets:
            secrets_dict = dict(st.secrets["gcp_service_account"])
            if "-----BEGIN PRIVATE KEY-----" not in secrets_dict["private_key"]:
                pk = secrets_dict["private_key"].replace('\\n', '\n')
                secrets_dict["private_key"] = pk
            return gspread.service_account_from_dict(secrets_dict)
        else:
            return gspread.service_account(filename="google_secret.json")
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return None

# --- PERCENTUAIS DE REFERÊNCIA ---
PERCENTUAIS_SUINO = {
    "Pernil": 0.26, "Paleta": 0.15, "Lombo": 0.13, "Barriga": 0.13,
    "Costela": 0.09, "Copa_Sob": 0.07, "Recortes": 0.12, "Miudezas": 0.05
}

def main():
    st.set_page_config(page_title="Gestão da Cadeia de Suprimentos", layout="wide")
    menu = st.sidebar.selectbox("Navegação", ["Lançar Desossa", "Consultar Histórico e Totais", "Saldo Disponível"])

    # --- ABA: LANÇAR DESOSSA ---
    if menu == "Lançar Desossa":
        st.title("🥩 Lançamento de Apuração")
        tipo_mp = st.selectbox("Tipo de Matéria-Prima:", ["Selecione", "Suíno"])
        if tipo_mp == "Suíno":
            peso_carcaca = st.number_input("Peso Total da Carcaça (kg):", min_value=0.0, step=0.1, format="%.2f")
            if peso_carcaca > 0:
                st.markdown("### 📊 Projeção de Cortes")
                dados_projecao = [{"Corte": c, "Peso (kg)": round(peso_carcaca * p, 2)} for c, p in PERCENTUAIS_SUINO.items()]
                st.table(pd.DataFrame(dados_projecao))
                if st.button("Salvar no Google Drive"):
                    gc = conectar_google_drive()
                    if gc:
                        try:
                            sh = gc.open(PLANILHA_NOME).worksheet("Suinos")
                            data_atual = pd.Timestamp.now().strftime("%d/%m/%Y")
                            pesos = [round(peso_carcaca * p, 2) for p in PERCENTUAIS_SUINO.values()]
                            linha_para_salvar = [data_atual, float(peso_carcaca)] + pesos
                            sh.append_row(linha_para_salvar, value_input_option='RAW')
                            st.success("✅ Dados salvos com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    # --- ABA: CONSULTAR HISTÓRICO ---
    elif menu == "Consultar Histórico e Totais":
        st.title("🔍 Consulta e Saldo de Estoque")
        gc = conectar_google_drive()
        if gc:
            try:
                df = pd.DataFrame(gc.open(PLANILHA_NOME).worksheet("Suinos").get_all_records())
                if df.empty:
                    st.warning("Nenhum dado encontrado.")
                else:
                    for col in df.columns:
                        if col != "Data":
                            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
                    
                    st.subheader("📦 Saldo Total Acumulado (kg)")
                    colunas_cortes = list(PERCENTUAIS_SUINO.keys())
                    totais = df[[c for c in colunas_cortes if c in df.columns]].sum()
                    cols = st.columns(4)
                    for i, (corte, valor) in enumerate(totais.items()):
                        cols[i % 4].metric(corte, f"{valor:,.2f} kg".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    st.divider()
                    st.subheader("📜 Histórico de Pesagens")
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar dados: {e}")

    # --- ABA: SALDO DISPONÍVEL (CORRIGIDA) ---
    elif menu == "Saldo Disponível":
        st.title("📊 Disponibilidade de Venda (ATP)")
        gc = conectar_google_drive()
        if gc:
            try:
                with st.spinner('Cruzando referências de produtos e saldos...'):
                    # 1. PRODUÇÃO (DADOS DESOSSA)
                    df_desossa = pd.DataFrame(gc.open(PLANILHA_NOME).worksheet("Suinos").get_all_records())
                    for col in df_desossa.columns[2:]:
                        df_desossa[col] = pd.to_numeric(df_desossa[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    total_producao = df_desossa.iloc[:, 2:].sum()

                    # 2. CADASTRO DE PRODUTOS (DE-PARA CENTRAL)
                    sh_ped = gc.open(PLANILHA_PEDIDOS_NOME)
                    df_dic = pd.DataFrame(sh_ped.worksheet("produtos").get_all_records())
                    # Limpeza para garantir match: Maiúsculo e sem espaços
                    df_dic['descricao_limpa'] = df_dic['descricao'].astype(str).str.strip().str.upper()

                    # 3. ESTOQUE FÍSICO + VÍNCULO
                    df_est_raw = pd.DataFrame(gc.open(PLANILHA_ESTOQUE_NOME).worksheet("ESTOQUETotal").get_all_records())
                    df_est_raw['PRODUTO_LIMPO'] = df_est_raw['PRODUTO'].astype(str).str.strip().str.upper()
                    df_est_raw['KG'] = pd.to_numeric(df_est_raw['KG'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

                    df_est_vinculado = pd.merge(
                        df_est_raw, 
                        df_dic[['descricao_limpa', 'materia_prima_vinculo']], 
                        left_on='PRODUTO_LIMPO', 
                        right_on='descricao_limpa', 
                        how='left'
                    )
                    total_estoque_fisico = df_est_vinculado.groupby('materia_prima_vinculo')['KG'].sum()

                    # 4. PEDIDOS PENDENTES + VÍNCULO
                    df_ped = pd.DataFrame(sh_ped.worksheet("pedidos").get_all_records())
                    df_ped['prod_limpo'] = df_ped['produto'].astype(str).str.strip().str.upper()
                    
                    df_pend = pd.merge(
                        df_ped[df_ped['status'] == 'pendente'], 
                        df_dic[['descricao_limpa', 'materia_prima_vinculo']], 
                        left_on='prod_limpo', 
                        right_on='descricao_limpa', 
                        how='left'
                    )
                    df_pend['peso'] = pd.to_numeric(df_pend['peso'], errors='coerce').fillna(0)
                    total_pedidos = df_pend.groupby('materia_prima_vinculo')['peso'].sum()

                # 5. DASHBOARD
                colunas_dash = ["Pernil", "Paleta", "Lombo", "Barriga", "Costela", "Copa_Sob", "Recortes", "Miudezas"]
                cols = st.columns(4)
                
                for i, item in enumerate(colunas_dash):
                    v_prod = total_producao.get(item, 0.0)
                    v_est  = total_estoque_fisico.get(item, 0.0)
                    v_ped  = total_pedidos.get(item, 0.0)
                    
                    saldo_final = (v_prod + v_est) - v_ped
                    cor = "normal" if saldo_final > 0 else "inverse"
                    
                    with cols[i % 4]:
                        st.metric(
                            label=f"📦 {item}", 
                            value=f"{saldo_final:,.2f} kg".replace(',', 'X').replace('.', ',').replace('X', '.'), 
                            delta=f"Saldo ATP", 
                            delta_color=cor
                        )
                        with st.expander("Detalhes"):
                            st.write(f"Desossa: {v_prod:,.1f}kg")
                            st.write(f"Estoque: {v_est:,.1f}kg")
                            st.write(f"Pedidos: {v_ped:,.1f}kg")
            
            except Exception as e:
                st.error(f"Erro ao consolidar dados: {e}")

if __name__ == "__main__":
    main()
