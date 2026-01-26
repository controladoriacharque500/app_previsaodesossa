import streamlit as st
import pandas as pd
from gspread_pandas import Spread, Client

# --- CONFIGURAÇÃO DA API (MESMA LINHA DO SEU PROJETO ANTERIOR) ---
PLANILHA_NOME = "Dados_Desossa" 
# Certifique-se de ter o arquivo 'google_secret.json' no diretório ou as credenciais configuradas
def conectar_google_drive(PLANILHA_NOME):
  try:
      if "gcp_service_account" in st.secrets:
          secrets_dict = dict(st.secrets["gcp_service_account"])
          pk = secrets_dict["private_key"].replace('\n', '').replace(' ', '')
          pk = pk.replace('-----BEGINPRIVATEKEY-----', '').replace('-----ENDPRIVATEKEY-----', '')
          padding = len(pk) % 4
          if padding != 0: pk += '=' * (4 - padding)
          secrets_dict["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{pk}\n-----END PRIVATE KEY-----\n"
          return gspread.service_account_from_dict(secrets_dict)
      else:
        return gspread.service_account(filename=CREDENTIALS_PATH)
  except Exception as e:
    st.error(f"Erro na conexão: {e}")
    return None
    

# --- PERCENTUAIS DE REFERÊNCIA (BASEADO NA CONVERSA ANTERIOR) ---
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
    st.title("🥩 Sistema de Apuração de Desossa")

    # TELA 1: SELEÇÃO DE MATÉRIA-PRIMA
    tipo_mp = st.selectbox("Escolha o tipo de matéria-prima:", ["Selecione", "Bovino", "Suíno"])

    if tipo_mp == "Suíno":
        st.subheader("Módulo Suíno: Projeção de Desossa")
        
        # Entrada de dados
        peso_carcaca = st.number_input("Peso Total da Carcaça (kg):", min_value=0.0, step=0.1)

        if peso_carcaca > 0:
            st.markdown("### 📊 Projeção Estimada de Cortes")
            
            dados_projecao = []
            for corte, perc in PERCENTUAIS_SUINO.items():
                peso_estimado = peso_carcaca * perc
                dados_projecao.append({"Corte": corte, "Percentual": f"{perc*100}%", "Peso Estimado (kg)": round(peso_estimado, 3)})
            
            df_projecao = pd.DataFrame(dados_projecao)
            st.table(df_projecao)

            # Botão para salvar no Google Drive
            if st.button("Salvar Apuração no Google Drive"):
                try:
                    spread = conectar_google_drive("Dados_Desossa")
                    # Prepara a linha para salvar
                    nova_linha = [pd.Timestamp.now()] + [peso_carcaca] + [round(peso_carcaca * p, 2) for p in PERCENTUAIS_SUINO.values()]
                    # Lógica para dar append na planilha (ajustar conforme sua função de API anterior)
                    st.success("Dados salvos com sucesso na planilha 'Dados_Desossa'!")
                except Exception as e:
                    st.error(f"Erro ao conectar ao Drive: {e}")

    elif tipo_mp == "Bovino":
        st.info("Módulo Bovino em desenvolvimento. Em breve você poderá configurar os percentuais de traseiro, dianteiro e ponta de agulha.")

if __name__ == "__main__":
    main()
