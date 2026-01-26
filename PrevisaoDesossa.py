import streamlit as st
import pandas as pd
import gspread # Importação correta para o gspread

# --- CONFIGURAÇÃO DA API ---
PLANILHA_NOME = "Dados_Desossa" 

def conectar_google_drive():
    try:
        # Se estiver no Streamlit Cloud usando Secrets
        if "gcp_service_account" in st.secrets:
            secrets_dict = dict(st.secrets["gcp_service_account"])
            # Limpeza da chave privada (ajuste comum para o Streamlit Cloud)
            if "-----BEGIN PRIVATE KEY-----" not in secrets_dict["private_key"]:
                pk = secrets_dict["private_key"].replace('\\n', '\n')
                secrets_dict["private_key"] = pk
            
            client = gspread.service_account_from_dict(secrets_dict)
            return client
        else:
            # Caso esteja rodando localmente com o arquivo JSON
            return gspread.service_account(filename="google_secret.json")
    except Exception as e:
        st.error(f"Erro na conexão com o Google Drive: {e}")
        return None

# --- PERCENTUAIS DE REFERÊNCIA ---
PERCENTUAIS_SUINO = {
    "Pernil": 0.26,
    "Paleta": 0.15,
    "Lombo": 0.13,
    "Barriga": 0.13,
    "Costela": 0.09,
    "Copa/Sobrepaleta": 0.07,
    "Recortes/Gordura": 0.12,
    "Pés/Rabo/Orelha": 0.05
}

def main():
    st.set_page_config(page_title="Apuração de Desossa", layout="wide")
    st.title("🥩 Sistema de Apuração de Desossa")

    tipo_mp = st.selectbox("Escolha o tipo de matéria-prima:", ["Selecione", "Bovino", "Suíno"])

    if tipo_mp == "Suíno":
        st.subheader("Módulo Suíno: Projeção de Desossa")
        
        peso_carcaca = st.number_input("Peso Total da Carcaça (kg):", min_value=0.0, step=0.1)

        if peso_carcaca > 0:
            st.markdown("### 📊 Projeção Estimada de Cortes")
            
            dados_projecao = []
            for corte, perc in PERCENTUAIS_SUINO.items():
                peso_estimado = peso_carcaca * perc
                dados_projecao.append({
                    "Corte": corte, 
                    "Percentual": f"{int(perc*100)}%", 
                    "Peso Estimado (kg)": round(peso_estimado, 3)
                })
            
            df_projecao = pd.DataFrame(dados_projecao)
            st.table(df_projecao)

            if st.button("Salvar Apuração no Google Drive"):
                gc = conectar_google_drive()
                if gc:
                    try:
                        # Abre a planilha e a aba específica (crie a aba 'Suinos' na sua planilha)
                        sh = gc.open(PLANILHA_NOME)
                        worksheet = sh.worksheet("Suinos")
                        
                        # Prepara a linha (Data formatada + Peso Total + Pesos de cada corte)
                        data_atual = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
                        pesos_cortes = [round(peso_carcaca * p, 2) for p in PERCENTUAIS_SUINO.values()]
                        nova_linha = [data_atual, peso_carcaca] + pesos_cortes
                        
                        # Adiciona a linha ao final da planilha
                        worksheet.append_row(nova_linha)
                        st.success(f"✅ Dados salvos com sucesso na aba 'Suinos' da planilha '{PLANILHA_NOME}'!")
                    except gspread.exceptions.WorksheetNotFound:
                        st.error("Erro: A aba 'Suinos' não foi encontrada na planilha.")
                    except Exception as e:
                        st.error(f"Erro ao salvar dados: {e}")

    elif tipo_mp == "Bovino":
        st.info("Módulo Bovino em desenvolvimento.")

if __name__ == "__main__":
    main()
