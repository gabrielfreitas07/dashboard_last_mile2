pip install matplotlib
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    st.title("Análise de Desempenho Last Mile")

    # Sidebar
    st.sidebar.header("Carregar arquivos")
    uploaded_csv = st.sidebar.file_uploader("Monitoramento da pontualidade (CSV)", type=["csv"])
    uploaded_csv2 = st.sidebar.file_uploader("Pedido de logistica (CSV)", type=["csv"])

    if uploaded_csv is not None:
        # Carregar dados do arquivo CSV
        data = pd.read_csv(uploaded_csv)

        if uploaded_csv2 is not None:
            # Carregar dados do arquivo Excel
            csv_data2 = pd.read_csv(uploaded_csv2, usecols=['Número do Waybill','CEP do destinatário', 'Cidade do destinatário'])

            # Mesclar os dados do Excel com o CSV existente
            data = data.merge(csv_data2, left_on='Número do Waybill', right_on='Número do Waybill', how='left')
        
        transform_table = {'SÃO PAULO': 'SP'}

        def transform_estado(estado):
            estado = estado.strip().upper()  # Remover espaços em branco e converter para maiúsculas
            if len(estado) > 2:  # Verificar se o estado possui mais de duas letras
                # Aplicar a tabela de transformação
                return transform_table.get(estado, estado)  # Retorna o valor da tabela ou o próprio estado se não estiver na tabela
            return estado
        data['estado'] = data['estado'].apply(transform_estado)
        
        #data['CEP do destinatário'] = data['CEP do destinatário'].astype(int)
        data['CEP do destinatário'] = data['CEP do destinatário'].astype(str).apply(lambda x: x.split('.')[0].zfill(8) if pd.notnull(x) else x)
        data['Cabeça de CEP'] = data['CEP do destinatário'].apply(lambda x: x[:3])
                              
        cep = st.sidebar.multiselect('Cabeça de CEP', data['Cabeça de CEP'].unique().tolist(), default=None)
        iata = st.sidebar.multiselect('Ponto previsto de entrega', data['Ponto previsto de entrega'].unique().tolist(), default=None)
        uf = st.sidebar.multiselect('Estado', data['estado'].unique().tolist(), default=None)
        cliente = st.sidebar.multiselect('Nome do cliente', data['Nome do cliente'].unique().tolist(), default=None)

        # Aplicar filtro dinâmico
        if cep:
            data = data[data['Cabeça de CEP'].isin(cep)]
        if iata:
            data = data[data['Ponto previsto de entrega'].isin(iata)]
        if uf:
            data = data[data['estado'].isin(uf)]
        if cliente:
            data = data[data['Nome do cliente'].isin(cliente)]
        
        # Converter colunas para datetime
        date_time_columns = ['Hora do status mais recente', 'Tempo de criação de pedido', 'Hora de Saída da Encomenda',
                             'Tempo de recolha', 'tempo de inbound em armazém de transferência', 'tempo de carregamento',
                             'Tempo de descarregamento', 'tempo de inbound no ponto', 'Horário de Entrega do Ponto',
                             'Tempo de assinatura', 'Primeiro prazo de entrega', 'Horário em que deve ser entregue',
                             'tempo de outbound  em armazém de transferência']
        data[date_time_columns] = data[date_time_columns].apply(pd.to_datetime)

        # Criar coluna 'Due Week' com o número da semana no ano
        data['Due Week'] = data['Horário em que deve ser entregue'].dt.isocalendar().week

        # Extrair apenas a data da coluna 'Hora de Saída da Encomenda'
        data['Int Shipped'] = data['Hora de Saída da Encomenda'].dt.date

        # Extrair apenas a data da coluna 'Tempo de recolha'
        data['Int Coleta'] = data['Tempo de recolha'].dt.date

        # Calcular a diferença em horas entre 'Tempo de recolha' e 'Hora de Saída da Encomenda'
        data['Tempo de coleta'] = (data['Tempo de recolha'] - data['Hora de Saída da Encomenda']).dt.total_seconds() / 3600

        # Criar coluna 'Int Rec HUB' com base na condição
        data['Int Rec HUB'] = data['tempo de inbound em armazém de transferência'].apply(lambda x: "Não recebido" if pd.isnull(x) else "Recebido")

        # Calcular a diferença em horas entre 'tempo de inbound em armazém de transferência' e 'Hora de Saída da Encomenda'
        data['T INBOUND'] = data.apply(lambda row: (row['tempo de inbound em armazém de transferência'] - row['Hora de Saída da Encomenda']).total_seconds() / 3600 if pd.notnull(row['tempo de inbound em armazém de transferência']) else "", axis=1)

        # Criar coluna 'Int inicio transferencia' com base na condição
        data['Int inicio transferencia'] = data['tempo de carregamento'].apply(lambda x: "Não processado" if pd.isnull(x) else x.date())

        data['T HUB'] = data.apply(lambda row: round(((row['tempo de outbound  em armazém de transferência'] - row['tempo de inbound em armazém de transferência']).total_seconds() / 3600), 0) if pd.notnull(row['tempo de outbound  em armazém de transferência']) else "Não processado", axis=1)

        # Calcular a diferença de data entre 'Int ENTREGA LM' e 'Int REC LM'
        data['Tempo LM'] = (data['Tempo de assinatura'] - data['tempo de inbound no ponto']).dt.days.apply(lambda x: "D0" if x < 1 else ("D1" if x >= 1 else ("D2" if x <= 2 else ("Acima de D2" if x > 2 else ("Em aberto" if pd.isnull(x) else "")))))
        
        # Calcular a diferença em horas entre 'tempo de inbound em armazém de transferência' e 'Hora de Saída da Encomenda'
        data['inbound'] = ((data['tempo de inbound em armazém de transferência'] - data['Hora de Saída da Encomenda']).dt.total_seconds() / 3600).round(1)

        # Calcular a diferença em horas entre 'tempo de carregamento' e 'tempo de inbound em armazém de transferência'
        data['hub'] = ((data['tempo de carregamento'] - data['tempo de inbound em armazém de transferência']).dt.total_seconds() / 3600).round(1)

        # Calcular a diferença em horas entre 'tempo de inbound no ponto' e 'tempo de carregamento'
        data['transferencia'] = ((data['tempo de inbound no ponto'] - data['tempo de carregamento']).dt.total_seconds() / 3600).round(1)

        # Calcular a diferença em horas entre 'Tempo de assinatura' e 'tempo de inbound no ponto'
        data['lm'] = ((data['Tempo de assinatura'] - data['tempo de inbound no ponto']).dt.total_seconds() / 3600).round(1)

        # Calcular a soma das diferenças entre 'inbound' e 'lm'
        data['soma_inbound_lm'] = (data['inbound'] + data['lm']).round(1)

        data['Analise entrega'] = (data['Horário em que deve ser entregue'] - data['Tempo de assinatura']).apply(lambda x: "Late" if x.days < 0 else "On time" if x.days >= 0 and not pd.isnull(x) else "Em aberto")
        status = st.sidebar.multiselect('Analise entrega',data['Analise entrega'].unique().tolist(), default = None)
        if status:
            data = data[data['Analise entrega'].isin(status)]
        
        data2 = data
        novo_nome_colunas = {
                'Tempo de criação de pedido': '1 - Criado',
                'Hora de Saída da Encomenda': '2 - Liberado',
                'Tempo de recolha': '3 - Coletado',
                'tempo de inbound em armazém de transferência': '4 - Recebido HUB',
                'tempo de outbound  em armazém de transferência': '5 - Processado',
                'tempo de carregamento': '6 - Transferido',
                'Tempo de descarregamento': '7 - Dercarga',
                'tempo de inbound no ponto': '8 - Recebido LM',
                'Horário de Entrega do Ponto': '9 - Em rota',
                'Tempo de assinatura': 'Entregue'
            }
        data2.rename(columns=novo_nome_colunas, inplace=True)
        
        caixa_dagua = pd.pivot_table(data2, 
                             index=['estado', 'Ponto previsto de entrega'],
                             values=['1 - Criado', '2 - Liberado', '3 - Coletado', '4 - Recebido HUB', '5 - Processado', '6 - Transferido', '7 - Dercarga', '8 - Recebido LM', '9 - Em rota','Entregue'], 
                             aggfunc=pd.Series.nunique, 
                             margins=True,
                             margins_name='Total')
        st.subheader("Tabela monitoramento caixa d'agua:")
        st.write(caixa_dagua)
        
        pivot_table = pd.pivot_table(data, index='Ponto previsto de entrega', 
                                     columns='Tempo LM', 
                                     values='Número do Waybill', 
                                     aggfunc=pd.Series.nunique, 
                                     margins=True,
                                     margins_name='Total')
        
        tabela_dinamica2 = pd.pivot_table(data, values='Número do Waybill',
                                  index=['Ponto previsto de entrega'],
                                  columns=['Tempo LM'],
                                  aggfunc=pd.Series.nunique,
                                  margins=True,
                                  margins_name='Total')
        tabela_dinamica_incrementada = tabela_dinamica2.cumsum(axis=1)
        ultimo_valor_por_linha = tabela_dinamica_incrementada.iloc[:, -1]
        tabela_dinamica_percentage2 = tabela_dinamica_incrementada.div(ultimo_valor_por_linha, axis=0) * 200
        tabela_dinamica_percentage2 = tabela_dinamica_percentage2.drop(columns=['Total'])
        tabela_dinamica_percentage2 = tabela_dinamica_percentage2.round(1)
        tabela_dinamica_percentage2 = tabela_dinamica_percentage2.astype(str) + '%'
        tabela_dinamica_percentage2 = tabela_dinamica_percentage2.replace('nan%', None)
        
        pivot_table2 = pd.pivot_table(data, index='Status do Waybill',  
                                     values='Número do Waybill', 
                                     aggfunc=pd.Series.nunique, 
                                     margins=True,
                                     margins_name='Total')
        pivot_table3 = pd.pivot_table(data, index='T HUB',  
                                     values='Número do Waybill', 
                                     aggfunc=pd.Series.nunique, 
                                     margins=True,
                                     margins_name='Total')
        pivot_table3.index = pivot_table3.index.round(0)
        pivot_table3.index = pivot_table3.index.astype(str) + ' hrs'
        pivot_table4 = pd.pivot_table(data, index='Ponto previsto de entrega',  
                                      columns= 'Analise entrega',
                                     values='Número do Waybill', 
                                     aggfunc=pd.Series.nunique, 
                                     margins=True,
                                     margins_name='Total')
        pivot_table_percentage = pivot_table4.div(pivot_table4['Total'], axis=0) * 100
        pivot_table_percentage = pivot_table_percentage.drop(columns=['Total'])
        pivot_table_percentage = pivot_table_percentage.round(1)
        pivot_table_percentage = pivot_table_percentage.astype(str) + '%'
        pivot_table_percentage = pivot_table_percentage.replace('nan%', None)

        pivot_table5 = pd.pivot_table(data, index='Int Shipped', 
                                     columns='Int Coleta', 
                                     values='Número do Waybill', 
                                     aggfunc=pd.Series.nunique, 
                                     margins=True,
                                     margins_name='Total')

        st.subheader("Shipped x Coleta:")
        st.write(pivot_table5)
        
        # Organizar as tabelas lado a lado
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Volume de entregas:")
            st.write(pivot_table)
        with col2:
            st.subheader("Porcentagem de entregas:")
            st.write(tabela_dinamica_percentage2)
        
        col3,col4 = st.columns(2)
        with col3:
            st.subheader("Status pedido:")
            st.write(pivot_table2)
        with col4:   
            st.subheader("Tempo no HUB:")
            st.write(pivot_table3)
        col5,col6 = st.columns(2)
        with col5:
            st.subheader("Analise entrega:")
            st.write(pivot_table4)
        with col6:
            st.subheader("Analise entrega %:")
            st.write(pivot_table_percentage)

        # Filtrar os dados de acordo com as condições especificadas
        filtered_data = data[data['Status do Waybill'].isin(['A recolher', 'Transbordo para armazenamento', 'Coletados', 'Objeto colatdo em LM'])]

        # Plotar gráfico de barras comparando 'Não recebidos' com o resto
        st.subheader("Volume por Cabeça de CEP")
        counts = data['Cabeça de CEP'].value_counts()
        st.bar_chart(counts)
        
        # Plotar gráfico de barras comparando 'Não recebidos' com o resto
        st.subheader("Status ofensores")
        counts = filtered_data['Status do Waybill'].value_counts()
        st.bar_chart(counts)
        
        # Exibir os dados carregados com as novas colunas
        st.subheader("Conjunto de dados:")
        st.write(data)
        
if __name__ == "__main__":
    main()
