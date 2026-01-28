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
            client = gspread.service_account_from_dict(secrets_dict)
            return client
        else:
            return gspread.service_account(filename="google_secret.json")
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return None

# --- PERCENTUAIS DE REFERÊNCIA (PADRÃO AMERICANO) ---
PERCENTUAIS_SUINO = {
    "Pernil": 0.26, "Paleta": 0.15, "Lombo": 0.13, "Barriga": 0.13,
    "Costela": 0.09, "Copa_Sobrepaleta": 0.07, "Recortes": 0.12, "Miudezas": 0.05
}

def main():
    st.set_page_config(page_title="Gestão de Desossa", layout="wide")
    
    menu = st.sidebar.selectbox("Navegação", ["Lançar Desossa", "Consultar Histórico e Totais", "Saldo Disponível"])

    if menu == "Lançar Desossa":
        st.title("🥩 Lançamento de Apuração (Padrão Decimal)")
        tipo_mp = st.selectbox("Tipo de Matéria-Prima:", ["Selecione", "Suíno"])

        if tipo_mp == "Suíno":
            # O number_input do Streamlit já trabalha com ponto decimal nativamente
            peso_carcaca = st.number_input("Peso Total da Carcaça (kg):", min_value=0.0, step=0.1, format="%.2f")
            
            if peso_carcaca > 0:
                st.markdown("### 📊 Projeção de Cortes")
                dados_projecao = [{"Corte": c, "Peso (kg)": round(peso_carcaca * p, 2)} for c, p in PERCENTUAIS_SUINO.items()]
                st.table(pd.DataFrame(dados_projecao))

                if st.button("Salvar no Google Drive"):
                    gc = conectar_google_drive()
                    if gc:
                        try:
                            sh = gc.open(PLANILHA_NOME)
                            worksheet = sh.worksheet("Suinos")
                            data_atual = pd.Timestamp.now().strftime("%d/%m/%Y")
                            
                            # Gerando pesos garantindo que são floats (padrão americano)
                            pesos = [round(peso_carcaca * p, 2) for p in PERCENTUAIS_SUINO.values()]
                            
                            # O gspread envia o float para a planilha. 
                            # Se sua planilha estiver em Português, o Google Sheets pode converter para vírgula visualmente, 
                            # mas o valor armazenado será numérico.
                            linha_para_salvar = [data_atual, float(peso_carcaca)] + pesos
                            worksheet.append_row(linha_para_salvar, value_input_option='RAW')
                            
                            st.success("✅ Dados salvos com sucesso no padrão numérico!")
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    elif menu == "Consultar Histórico e Totais":
        st.title("🔍 Consulta e Saldo de Estoque")
        gc = conectar_google_drive()
        
        if gc:
            try:
                sh = gc.open(PLANILHA_NOME)
                worksheet = sh.worksheet("Suinos")
                dados = worksheet.get_all_records()
                
                if not dados:
                    st.warning("Nenhum dado encontrado na planilha.")
                else:
                    df = pd.DataFrame(dados)

                    # --- LIMPEZA E CONVERSÃO DOS DADOS ---
                    # Remove vírgulas caso existam e força conversão para float
                    for col in df.columns:
                        if col != "Data":
                            df[col] = df[col].astype(str).str.replace(',', '.')
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

                    # --- EXIBIÇÃO DE TOTAIS ---
                    st.subheader("📦 Saldo Total Acumulado (kg)")
                    
                    # Definimos as colunas de cortes baseadas no seu cabeçalho da imagem
                    colunas_cortes = ["Pernil", "Paleta", "Lombo", "Barriga", "Costela", "Copa_Sobrepaleta", "Recortes", "Miudezas"]
                    
                    # Soma apenas se a coluna existir no DataFrame
                    colunas_existentes = [c for c in colunas_cortes if c in df.columns]
                    totais = df[colunas_existentes].sum()

                    cols = st.columns(4)
                    for i, (corte, valor) in enumerate(totais.items()):
                        # Exibição visual com ponto para milhar e vírgula para decimal (estilo BR) 
                        # ou mantenha ponto se preferir 100% padrão americano: f"{valor:.2f} kg"
                        cols[i % 4].metric(corte, f"{valor:,.2f} kg".replace(',', 'X').replace('.', ',').replace('X', '.'))

                    st.divider()
                    st.subheader("📜 Histórico de Pesagens")
                    # No dataframe mostramos o padrão americano puro para conferência
                    st.dataframe(df, use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao processar dados: {e}")
                
     elif menu == "Saldo Disponível":
        st.title("📊 Disponibilidade de Venda (ATP)")
        gc = conectar_google_drive()
        
        if gc:
            try:
                with st.spinner('Consolidando saldos de múltiplas fontes...'):
                    # 1. BUSCAR PRODUÇÃO (DADOS DESOSSA)
                    sh_desossa = gc.open(PLANILHA_NOME).worksheet("Suinos")
                    df_desossa = pd.DataFrame(sh_desossa.get_all_records())
                    # Limpeza padrão americano conforme alinhamos
                    for col in df_desossa.columns[2:]:
                        df_desossa[col] = pd.to_numeric(df_desossa[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    total_producao = df_desossa.iloc[:, 2:].sum()
    
                    # 2. BUSCAR ESTOQUE FÍSICO (PRODUTO ACABADO)
                    # Baseado no código de estoque que você enviou
                    sh_estoque = gc.open(PLANILHA_ESTOQUE_NOME).worksheet("ESTOQUETotal")
                    df_est = pd.DataFrame(sh_estoque.get_all_records())
                    df_est['KG'] = pd.to_numeric(df_est['KG'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    
                    # Agrupamos o estoque físico pela coluna 'MATÉRIA-PRIMA' que já existe no seu sistema
                    total_estoque_fisico = df_est.groupby('MATÉRIA-PRIMA')['KG'].sum()
    
                    # 3. BUSCAR PEDIDOS PENDENTES + DICIONÁRIO
                    sh_pedidos = gc.open(PLANILHA_PEDIDOS_NOME)
                    df_ped = pd.DataFrame(sh_pedidos.worksheet("pedidos").get_all_records())
                    df_dic = pd.DataFrame(sh_pedidos.worksheet("produtos").get_all_records())
    
                    # Faz o Procv (Merge) entre pedidos e o dicionário para saber a qual matéria-prima o produto pertence
                    df_ped_vinculado = pd.merge(df_ped[df_ped['status'] == 'pendente'], 
                                                df_dic[['descricao', 'materia_prima_vinculo']], 
                                                left_on='produto', right_on='descricao', how='left')
                    
                    df_ped_vinculado['peso'] = pd.to_numeric(df_ped_vinculado['peso'], errors='coerce').fillna(0)
                    total_pedidos = df_ped_vinculado.groupby('materia_prima_vinculo')['peso'].sum()
    
                # 4. EXIBIÇÃO DO DASHBOARD
                colunas_dashboard = ["Pernil", "Paleta", "Lombo", "Barriga", "Costela", "Copa_Sob", "Recortes", "Miudezas"]
                cols = st.columns(4)
                
                for i, item in enumerate(colunas_dashboard):
                    # Cálculo: (Produção Estimada + Estoque Físico) - Pedidos Pendentes
                    v_prod = total_producao.get(item, 0.0)
                    v_est  = total_estoque_fisico.get(item.upper(), 0.0) # Ajuste para bater Maiúsculas se necessário
                    v_ped  = total_pedidos.get(item, 0.0)
                    
                    saldo_final = (v_prod + v_est) - v_ped
                    
                    cor_metrica = "normal" if saldo_final > 0 else "inverse"
                    
                    with cols[i % 4]:
                        st.metric(f"📦 {item}", f"{saldo_final:,.2f} kg".replace(',', 'X').replace('.', ',').replace('X', '.'), 
                                  delta=f"Disponível", delta_color=cor_metrica)
                        
                        # Detalhes expansíveis para conferência
                        with st.expander("Ver composição"):
                            st.write(f"➕ Produção: {v_prod:,.2f} kg")
                            st.write(f"➕ Est. Físico: {v_est:,.2f} kg")
                            st.write(f"➖ Pedidos: {v_ped:,.2f} kg")
    
            except Exception as e:
                st.error(f"Erro ao cruzar dados: {e}")
            
if __name__ == "__main__":
    main()
