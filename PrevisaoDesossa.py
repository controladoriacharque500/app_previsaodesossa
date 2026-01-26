import streamlit as st
import pandas as pd
import gspread

# --- CONFIGURAÇÃO DA API ---
PLANILHA_NOME = "Dados_Desossa" 
COLUNAS_SUINO = ["Data", "Peso_Total", "Pernil", "Paleta", "Lombo", "Barriga", "Costela", "Copa_Sobrepaleta", "Recortes", "Miudezas"]

def conectar_google_drive():
    try:
        if "gcp_service_account" in st.secrets:
            secrets_dict = dict(st.secrets["gcp_service_account"])
            if "-----BEGIN PRIVATE KEY-----" not in secrets_dict["private_key"]:
                pk = secrets_dict["private_key"].replace('\\n', '\n')
                secrets_dict["private_key"] = pk
            client = gspread.service_account_from_dict(secrets_dict)
            return client
        else:
            return gspread.service_account(filename="google_secret.json")
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return None

# --- PERCENTUAIS DE REFERÊNCIA ---
PERCENTUAIS_SUINO = {
    "Pernil": 0.26, "Paleta": 0.15, "Lombo": 0.13, "Barriga": 0.13,
    "Costela": 0.09, "Copa/Sobrepaleta": 0.07, "Recortes/Gordura": 0.12, "Pés/Rabo/Orelha": 0.05
}

def main():
    st.set_page_config(page_title="Gestão de Desossa", layout="wide")
    
    # --- MENU LATERAL ---
    menu = st.sidebar.selectbox("Navegação", ["Lançar Desossa", "Consultar Histórico e Totais"])

    if menu == "Lançar Desossa":
        st.title("🥩 Lançamento de Apuração")
        tipo_mp = st.selectbox("Tipo de Matéria-Prima:", ["Selecione", "Suíno", "Bovino"])

        if tipo_mp == "Suíno":
            peso_carcaca = st.number_input("Peso Total da Carcaça (kg):", min_value=0.0, step=0.1)
            if peso_carcaca > 0:
                st.markdown("### 📊 Projeção de Cortes")
                dados_projecao = [{"Corte": c, "Peso (kg)": round(peso_carcaca * p, 2)} for c, p in PERCENTUAIS_SUINO.items()]
                st.table(pd.DataFrame(dados_projecao))

                if st.button("Salvar no Google Drive"):
                    gc = conectar_google_drive()
                    if gc:
                        sh = gc.open(PLANILHA_NOME)
                        worksheet = sh.worksheet("Suinos")
                        data_atual = pd.Timestamp.now().strftime("%d/%m/%Y")
                        pesos = [round(peso_carcaca * p, 2) for p in PERCENTUAIS_SUINO.values()]
                        worksheet.append_row([data_atual, peso_carcaca] + pesos)
                        st.success("Dados salvos!")

    elif menu == "Consultar Histórico e Totais":
        st.title("🔍 Consulta e Saldo de Estoque")
        
        gc = conectar_google_drive()
        if gc:
            try:
                sh = gc.open(PLANILHA_NOME)
                worksheet = sh.worksheet("Suinos")
                
                # Transforma os dados da planilha em DataFrame Pandas
                dados = worksheet.get_all_records()
                if not dados:
                    st.warning("Nenhum dado encontrado na planilha.")
                else:
                    df = pd.DataFrame(dados)
                    
                    # --- ABA DE TOTAIS (RESUMO) ---
                    st.subheader("📦 Saldo Total Acumulado (Soma de todos os cortes)")
                    
                    # Seleciona as colunas de cortes (da terceira em diante)
                    colunas_cortes = df.columns[2:] 
                    totais = df[colunas_cortes].sum().reset_index()
                    totais.columns = ["Corte", "Total_Acumulado"] # Nome limpo para a coluna
                    
                    # Exibe os totais em colunas (estilo dashboard)
                    cols = st.columns(4)
                    for i, row in totais.iterrows():
                        # Aqui estava o erro! Agora usamos 'Total_Acumulado'
                        cols[i % 4].metric(row['Corte'], f"{row['Total_Acumulado']:.2f} kg")
                    
                    # Exibe os totais em colunas (estilo dashboard)
                    cols = st.columns(4)
                    for i, row in totais.iterrows():
                        cols[i % 4].metric(row['Corte'], f"{row['Total Acumulado (kg) Brandon']:.2f} kg")
                    
                    st.divider()
                    
                    # --- ABA DE HISTÓRICO ---
                    st.subheader("📜 Histórico de Pesagens")
                    st.dataframe(df, use_container_width=True)
                    
                    # Opção de download
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Baixar CSV", csv, "historico_desossa.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro ao carregar dados: {e}")

if __name__ == "__main__":
    main()
