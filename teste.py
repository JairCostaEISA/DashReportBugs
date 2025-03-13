import pyodbc
import pandas as pd
import streamlit as st
import plotly.express as px

# Configuração inicial da página
st.set_page_config(
    page_title="Gestão de Defeitos",    # Título da aba do navegador
    page_icon="📊",                     # Ícone da aba do navegador
    layout="wide",                      # Layout: 'centered' ou 'wide' >> layout da página como "wide" (amplo), permitindo que os GRAFICOS OU DataFrame ocupe mais espaço.
    initial_sidebar_state="expanded"    # 'auto', 'expanded', 'collapsed' >> se o sidebar vem expandido ou fechado
    )


# Conteúdo do aplicativo / Titulo da pagina
st.title("DEP3.1 - Report Bugs")

# SERVER = '172.22.0.120'
# DATABASE = 'eisa_pr2014_vivo_aceitacao_db'
# USERNAME = 'qc_minerva'
# PASSWORD = 'qc2014minerva'

# conexaoBaseQC = f'DRIVER={{SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

# Acessando as credenciais do banco de dados a partir do arquivo secrets.toml
host = st.secrets["database"]["host"]
user = st.secrets["database"]["user"]
password = st.secrets["database"]["password"]
dbname = st.secrets["database"]["dbname"]

# Criando a string de conexão para o SQL Server
conexaoBaseQC = f'DRIVER={{SQL Server}};SERVER={host};DATABASE={dbname};UID={user};PWD={password}'

# conexao = pyodbc.connect(conexaoBaseQC)
# print("Conexao Bem Sucedida")
try:
    conexao = pyodbc.connect(conexaoBaseQC)
    print("Conexão Bem Sucedida")
except pyodbc.Error as e:
    st.error("Erro ao conectar ao banco de dados. Verifique as configurações.")
    st.stop()  # Para a execução do aplicativo


Consulta_SQL = """
WITH Reabertura AS (
SELECT
	l.au_entity_id AS BG_BUG_ID_REABERTURA,
	-- Renomeie para evitar conflito
        CONVERT(DATE,
	MAX(l.AU_TIME)) AS DATA_REABERTURA
FROM
	td.audit_log l
JOIN td.audit_properties p
        ON
	l.au_action_id = p.ap_action_id
WHERE
	p.AP_FIELD_NAME = 'BG_USER_03'
	AND p.AP_PROPERTY_NAME = 'Status_Vivo'
	AND p.AP_OLD_VALUE = 'A espera de ReTeste'
	AND p.AP_NEW_VALUE = 'Reopen'
GROUP BY
	l.au_entity_id
)
-- Agora a CTE Reabertura é usada diretamente na consulta principal
SELECT
	BG_DETECTION_DATE AS ABERTURA,
	LEFT(BG_USER_01,
	CHARINDEX('-',
	BG_USER_01) - 1) AS ID_VIVO,
	BG_BUG_ID AS ID_EISA,
	SUBSTRING(BG_USER_01, CHARINDEX('-', BG_USER_01, CHARINDEX('-', BG_USER_01) + 1) + 1, LEN(BG_USER_01)) AS PROJETO,
	BG_USER_42 AS BLOCO_REQUISITO,
	BG_DETECTION_VERSION AS RELEASE,
	BG_USER_06 AS ESTEIRA,
	BG_USER_15 AS CNs,
	BG_USER_10 AS PREVISAO,
	BG_USER_35 AS COMENTARIOS,
	BG_USER_08 AS PACKAGE,
	BG_SUMMARY AS SUMMARY,
	BG_RESPONSIBLE AS ASSIGNED_TO,
	BG_USER_09 AS RESPONSIBLE,
	BG_USER_20 AS REQUIREMENT,
	BG_STATUS AS STATUS_EISA,
	BG_USER_03 AS STATUS_VIVO,
	BG_USER_13 AS CAUSA_DO_DEFEITO,
	BG_USER_31 AS MOTIVO_REJEIÇÃO,
	BG_USER_10 AS ANSWER_DATE,
	BG_USER_05 AS TYPE,
	BG_USER_32 AS CONTADOR_REOPEN,
	BG_USER_34 AS CONTADOR_FIXED,
	BG_USER_33 AS CONTADOR_REJECTED,
	BG_USER_41 AS DATA_CORREÇÃO,
	BG_USER_38 AS DATA_DEVOLUÇÃO_EISA,
	BG_USER_22 AS SLA,
	BG_USER_40 AS INTERNAL_FRONT,
	BG_USER_24 AS SERVIÇO,
	BG_USER_25 AS AMBIENTE,
	BG_USER_26 AS MODULO,
	BG_USER_37 AS SISTEMA_CORRECAO,
	R.DATA_REABERTURA,
	-- Referência da CTE aqui
	DATEDIFF(DAY, R.DATA_REABERTURA, GETDATE()) AS AGEING_REABERTURA
	-- Referência da CTE aqui
FROM
	TD.BUG b
LEFT JOIN Reabertura R
	-- Usando a CTE 'Reabertura' com alias 'R'
    ON
	b.BG_BUG_ID = R.BG_BUG_ID_REABERTURA
	-- Corrigido para o alias correto
WHERE
	BG_DETECTED_BY IN ('pticketuser')
	AND BG_DETECTION_DATE >= '2025-01-01 00:00:00.000'
	AND (BG_DETECTION_VERSION LIKE '%v25.%'
		OR BG_DETECTION_VERSION LIKE '%v17.%')
ORDER BY
	ABERTURA,
	PROJETO DESC;
"""

# Executando a consulta
dadosGerais = pd.read_sql(Consulta_SQL, conexao)

# Usando o método replace para substituir / personalizar os PROJETOS exemplo :"BSS Pré-pago (Valentina)" por "Valentina"
dadosGerais['PROJETO'] = dadosGerais['PROJETO'].replace('BSS Pré-pago (Valentina)', 'Valentina')
dadosGerais['PROJETO'] = dadosGerais['PROJETO'].replace('Tributário', 'NFCOM')
dadosGerais['PROJETO'] = dadosGerais['PROJETO'].replace('Estruturante', 'Pandora')

# Usando o método replace para substituir / personalizar as ESTEIRAS 
dadosGerais['ESTEIRA'] = dadosGerais['ESTEIRA'].replace('QA1 Vivo Homologação', 'QA1')
dadosGerais['ESTEIRA'] = dadosGerais['ESTEIRA'].replace('QA2 Vivo Homologação', 'QA2')
dadosGerais['ESTEIRA'] = dadosGerais['ESTEIRA'].replace('QA3 Vivo Homologação', 'QA3')
dadosGerais['ESTEIRA'] = dadosGerais['ESTEIRA'].replace('QA4 Vivo Homologação', 'QA3')

# Convertendo as colunas para formato datetime sem usar strftime
dadosGerais['ABERTURA'] = pd.to_datetime(dadosGerais['ABERTURA'], errors='coerce')
dadosGerais['DATA_DEVOLUÇÃO_EISA'] = pd.to_datetime(dadosGerais['DATA_DEVOLUÇÃO_EISA'], errors='coerce')


# ✅ Criando um estado para evitar reset dos filtros
if "dados_atualizados" not in st.session_state:
    st.session_state.dados_atualizados = False

# Armazenando o intervalo de data inicial no session_state, caso ainda não tenha sido armazenado
if "data_inicio_inicial" not in st.session_state:
    st.session_state.data_inicio_inicial = pd.to_datetime("2025-01-02")  # Definindo o valor inicial
if "data_fim_inicial" not in st.session_state:
    st.session_state.data_fim_inicial = pd.to_datetime("2025-03-11")  # Definindo o valor inicial

# ✅ Adicionar botão de reexecução sem resetar os filtros
if st.button("Atualizar Dados"):
    # # Resetando o filtro de data para os valores iniciais
    # st.session_state.data_inicio = st.session_state.data_inicio_inicial  # Definindo o valor inicial
    # st.session_state.data_fim = st.session_state.data_fim_inicial  # Definindo o valor inicial
    
    st.session_state.dados_atualizados = True
    st.rerun()  # Reexecuta a aplicação sem resetar os outros filtros    

# # 🔹 Inicializando os valores no session_state **antes** da criação dos widgets
# if "data_inicio" not in st.session_state:
#     st.session_state.data_inicio = st.session_state.data_inicio_inicial  # Usando o valor inicial de data_inicio

# if "data_fim" not in st.session_state:
#     st.session_state.data_fim = st.session_state.data_fim_inicial  # Usando o valor inicial de data_fim


if "status_vivo" not in st.session_state:
    st.session_state.status_vivo = [
        status for status in dadosGerais["STATUS_VIVO"].unique()
        if status not in ('A espera de ReTeste', 'Nao Aplicavel')
    ]

if "status_eisa" not in st.session_state:
    st.session_state.status_eisa = [
        status for status in ["New", "Open", "Reopen", "In Analysis", "Rejected", "Fixed"]
        if status in dadosGerais["STATUS_EISA"].unique()
    ]

if "projeto" not in st.session_state:
    st.session_state.projeto = [
        projetos for projetos in ["NFCOM", "Pandora", "Regressão", "Valentina"]
        if projetos in dadosGerais["PROJETO"].unique()
    ]

if "release" not in st.session_state:
    st.session_state.release = list(dadosGerais["RELEASE"].unique()[-6:])  # Pega as últimas 6 releases

if "responsible" not in st.session_state: 
    st.session_state.responsible = [
        responsible for responsible in ["Desenvolvimento - Construção", "Desenvolvimento - Big Data", "Desenvolvimento - Integração", "Desenvolvimento - Plataforma", "Gestão de Defeitos", "Gestão de Projetos", "Implantação e Ambientes NGIN e Smarts", "Implantação e Ambientes RM", "Parametrização RM", "PPs e Parametrizações NGIN e Smarts", "Projetos Especiais", "Arquitetura e Requisitos"]
        if responsible in dadosGerais["RESPONSIBLE"].unique()
    ]

if "esteira" not in st.session_state:
    st.session_state.esteira = [
        esteiras for esteiras in ["QA1", "QA2", "QA3", "QA4"]
        if esteiras in dadosGerais["ESTEIRA"].unique()
    ]

# Sidebar de filtros
st.sidebar.title("Filtros")

# 🔹 Criando widgets de filtro sem sobrescrever manualmente o session_state
status_vivo = st.sidebar.multiselect(
    "Status VIVO:",
    options=dadosGerais["STATUS_VIVO"].unique(),
    default=st.session_state.status_vivo,  
    key="status_vivo"
)

status_eisa = st.sidebar.multiselect(
    "Status EISA",
    options=dadosGerais["STATUS_EISA"].unique(),
    default=st.session_state.status_eisa,  
    key="status_eisa"
)

projeto = st.sidebar.multiselect(
    "Projeto:",
    options=dadosGerais["PROJETO"].unique(),
    default=st.session_state.projeto,  
    key="projeto"
)

esteira = st.sidebar.multiselect(
    "Esteira:",
    options=dadosGerais["ESTEIRA"].unique(),
    default=st.session_state.esteira,  
    key="esteira"
)

release = st.sidebar.multiselect(
    "Releases:",
    options=dadosGerais["RELEASE"].unique(),
    default=st.session_state.release,  
    key="release"
)

responsible = st.sidebar.multiselect(
    "Frentes_EISA:",
    options=dadosGerais["RESPONSIBLE"].unique(),
    default=st.session_state.responsible,  # Define o valor padrão a partir do session_state
    key="responsible"
)

# # Atualizando o filtro de data com os valores do session_state
# data_inicio, data_fim = st.sidebar.date_input(
#     "Selecione o intervalo de datas", 
#     [st.session_state.data_inicio, st.session_state.data_fim]  # Usando os valores atualizados do session_state
# )

# # Atualizando o session_state com os valores selecionados
# st.session_state.data_inicio = data_inicio
# st.session_state.data_fim = data_fim

# Se os parametros default dos sidebars sejam comentados --- Os filtros deixaram de ser independentes
# Então se não comentar
# E aparecerá a mensagem na primeira abertura da pagina --- The widget with key "status_vivo" was created with a default value but also had its value set via the Session State API. (O widget com chave "status_vivo" foi criado com um valor padrão, mas também tinha seu valor definido através da API do estado da sessão.)

# Se comentar ...  
# Removi o parâmetro default de todos os widgets, pois os valores agora serão gerenciados diretamente pelo session_state.
# Necessario apenas manter o key para garantir que os valores sejam armazenados e recuperados corretamente do session_state.

# 🔹 NÃO MODIFICAR O session_state APÓS OS WIDGETS ⛔

# 🔹 Aplicando os filtros ao dataframe
df_filtro = dadosGerais[
    (dadosGerais["STATUS_VIVO"].isin(st.session_state.status_vivo)) &
    (dadosGerais["STATUS_EISA"].isin(st.session_state.status_eisa)) &
    (dadosGerais["PROJETO"].isin(st.session_state.projeto)) &
    (dadosGerais["RELEASE"].isin(st.session_state.release)) &
    (dadosGerais["RESPONSIBLE"].isin(st.session_state.responsible)) &
    (dadosGerais["ESTEIRA"].isin(st.session_state.esteira))
    # (dadosGerais["ABERTURA"] >= pd.to_datetime(st.session_state.data_inicio)) &  # Filtrando pela data de início
    # (dadosGerais["ABERTURA"] <= pd.to_datetime(st.session_state.data_fim))       # Filtrando pela data de fim
].reset_index(drop=True)

# # Adicionando o botão de "Sair" na sidebar
# if st.sidebar.button("Sair"):
#     st.session_state.logged_in = False  # Altera o estado para não logado
#     st.session_state.current_page = "login"  # Redireciona para a tela de login
#     st.rerun()  # Recarrega a página para ir para o login

#########################################################################################################################################################################################

# Criando um dicionário de cores personalizadas para cada responsável
cores_responsaveis = {
    "Arq Dev e Requisitos": "#1f77b4",  # Azul médio
    "Desenvolvimento - Big Data": "#ff7f0e",  # Laranja vibrante
    "Desenvolvimento - Construção": "#2ca02c",  # Verde médio
    "Desenvolvimento - Integração": "#d62728",  # Vermelho suave
    "Desenvolvimento - Plataforma": "#9467bd",  # Roxo elegante
    "Desenvolvimento - RM": "#8c564b",  # Marrom quente
    "Gestão de Defeitos": "#e377c2",  # Rosa suave
    "Gestão de Projetos": "#7f7f7f",  # Cinza neutro
    "Implantação e Ambientes NGIN e Smarts": "#bcbd22",  # Verde amarelado
    "Implantação e Ambientes RM": "#17becf",  # Azul turquesa
    "Parametrização RM": "#f4a261",  # Pêssego
    "PostGA/DU": "#e76f51",  # Laranja queimado
    "PPs e Parametrizações NGIN e Smarts": "#2a9d8f",  # Verde esmeralda
    "Projetos Especiais": "#264653",  # Azul petróleo
    "Qualidade NGIN e automação": "#f94144",  # Vermelho intenso
    "Qualidade RM e Smarts": "#90be6d",  # Verde claro
    "Serviços e BackOffice": "#577590",  # Azul acinzentado
    "Smart Offers": "#f9c74f",  # Amarelo vibrante
    "Suporte e Automação RM": "#f3722c"  # Laranja forte
}

# Agrupando os dados pelo campo 'RESPONSIBLE' para contagem de defeitos
count_data = df_filtro.groupby('RESPONSIBLE').size().reset_index(name='Qtd_Defeitos')

# Criando o gráfico Treemap
grafico1 = px.treemap(
    count_data,
    path=['RESPONSIBLE'],  # Definindo a estrutura do Treemap com base no campo 'RESPONSIBLE'
    values='Qtd_Defeitos',  # O tamanho de cada bloco será baseado na quantidade de defeitos
    color='RESPONSIBLE',  # Define a coloração pelo campo 'RESPONSIBLE'
    color_discrete_map=cores_responsaveis,  # Aplica o dicionário de cores
    title='Qtd. por Responsável EISA'
)

# Ajustando os detalhes do gráfico
grafico1.update_traces(
    textinfo='label+value',  # Exibe o rótulo e o valor dentro dos blocos
    textposition='middle center',  # Posição do texto no centro do bloco
    textfont=dict(family='Arial', size=15, weight='bold')  # Definindo a fonte como negrito, tamanho
)

grafico1.update_layout(
    legend_title="Responsável EISA",  # Título da legenda
    xaxis_title=None,  # Remove o título do eixo X (não aplicável em treemaps)
    yaxis_title=None,  # Remove o título do eixo Y (não aplicável em treemaps)
    showlegend=True  # Exibe a legenda
)

#################################################################################################################################################################################################

count_data = df_filtro.groupby('PROJETO').size().reset_index(name='Qtd_Defeitos') # Agrupamento os responsaveis ... pelo campo PROJETOS para contagem através do "".size""
                                                                                    # reset_index(name='Qtd_Defeitos'): Entre " " cria um novo DataFrame, e atribui um nome a nova coluna que contém a contagem de defeitos, chamada de 'Qtd_Defeitos'.
grafico2 = px.pie(
    count_data,
    title='Qtd. por PROJETOS',
    values='Qtd_Defeitos',
    names='PROJETO'
    )
        
        
grafico2.update_traces(
    textinfo='label + value',  # Adiciona os valores da contagem como texto
    textposition='auto',       # Posiciona o texto dentro das barras = > ('auto' ou 'inside' ou outside)
    textfont=dict(size=15)  # Define o tamanho da fonte para os valores (ajuste o tamanho conforme necessário)
    )

#################################################################################################################################################################################################

cores_esteiras = {
    "QA1": "#2ca02c",  # Verde médio
    "QA2": "#f9c74f",  # Amarelo vibrante
    "QA3": "#8c564b",  # Marrom quente
    "QA4": "#d62728"  # Vermelho suave
}

# Agrupando os dados pelo campo 'ESTEIRA' para contagem de defeitos
count_data = df_filtro.groupby('ESTEIRA').size().reset_index(name='Qtd_Defeitos')

# Criando o gráfico de rosca
grafico3 = px.pie(
    count_data,
    title='Qtd. por ESTEIRA',
    values='Qtd_Defeitos',
    color='ESTEIRA',  # Aplica a coloração pelo campo 'ESTEIRA'
    color_discrete_map=cores_esteiras,  # Aplica o dicionário de cores
    names='ESTEIRA'
)

# Definindo o tamanho do buraco no meio para criar o efeito de rosca
grafico3.update_traces(
    textinfo='label + value',  # Exibe o rótulo e o valor dentro do gráfico
    textposition='auto',       # Posiciona o texto automaticamente
    textfont=dict(size=15),    # Define o tamanho da fonte
    hole=0.5                   # Cria o buraco no centro, valor entre 0 (sem buraco) e 1 (buraco total)
)

#################################################################################################################################################################################################

count_data = df_filtro.groupby('STATUS_EISA').size().reset_index(name='Qtd_Defeitos') # Agrupamento os responsaveis ... pelo campo RESPONSIBLE para contagem através do "".size""
                                                                                    # reset_index(name='Qtd_Defeitos'): Entre " " cria um novo DataFrame, e atribui um nome a nova coluna que contém a contagem de defeitos, chamada de 'Qtd_Defeitos'.
grafico4 = px.bar(
    count_data,
    x='STATUS_EISA',
    y='Qtd_Defeitos',
    title='Qtd. por STATUS_EISA',
    color='STATUS_EISA',
    text='Qtd_Defeitos'
)
                
grafico4.update_traces(
    textposition='auto',  # Posicionar o texto automaticamente
    insidetextanchor='middle',  # Alinha o texto verticalmente no centro
    textfont=dict(size=15)  # Define o tamanho da fonte para os valores (ajuste o tamanho conforme necessário)
)

grafico4.update_layout(
    legend_title="STATUS_EISA",  # Alterar o título da legenda
    xaxis_title=None,  # Remove o título do eixo X
    yaxis_title=None,  # Remove o título do eixo Y
    yaxis=dict(showticklabels=False),  # Remove os rótulos dos ticks do eixo Y
    xaxis=dict(showticklabels=True),  # Remove os rótulos dos ticks do eixo X
)

###############################################################################################################################################################################

# 🔹 Exibir a contagem de defeitos após a aplicação do filtro
st.info(f"🔹 No momento temos {df_filtro.shape[0]} defeitos na nossa chave EISA")

###############################################################################################################################################################################

andamento = df_filtro[
    (df_filtro["STATUS_EISA"].isin(["Open", "Reopen", "New", "In Analysis", "RFI - Request for Information"]))& 
    (df_filtro["STATUS_VIVO"].isin([status for status in dadosGerais["STATUS_VIVO"].unique() if status not in ('A espera de ReTeste', 'Nao Aplicavel')]))
].shape[0]

aguardando_instalacao = df_filtro[
    (df_filtro["STATUS_VIVO"].isin(["Aguardando instalação em LAB", "Aguardando Instalação QA"]))].shape[0]

assistido_desblindagem = df_filtro[
    (df_filtro["STATUS_VIVO"].isin(["Aguardando teste assistido", "Aguardando desblindagem"]))].shape[0]

reject = df_filtro[
    (df_filtro["STATUS_EISA"].isin(["Rejected"])) & 
    (df_filtro["STATUS_VIVO"].isin([status for status in dadosGerais["STATUS_VIVO"].unique() if status not in ('A espera de ReTeste', 'Nao Aplicavel')]))
].shape[0]

fixed = df_filtro[
    (df_filtro["STATUS_EISA"].isin(["Fixed"])) & 
    (df_filtro["STATUS_VIVO"].isin([status for status in dadosGerais["STATUS_VIVO"].unique() if status not in ('A espera de ReTeste', 'Nao Aplicavel')]))
].shape[0]

# st.header("Status Geral")

col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])  # O valor 1 indica que todas as colunas terão a mesma largura
with col1:
    st.metric('🔍 Em Análise', andamento)
with col2:
    st.metric('❌ Rejects', reject)
with col3:
    st.metric('✔️ Fixeds', fixed)
with col4:
    st.metric('🔧 Aguardando Instalação em LAB/QA', aguardando_instalacao)
with col5:
    st.metric('💻 Aguardando Teste Assistido / Desblindagem', assistido_desblindagem)

###############################################################################################################################################################################

# 🔹 Contando defeitos com previsão válida (não vazia e sem espaços) dentro do df_filtro
total_com_previsao = df_filtro["PREVISAO"].dropna().astype(str).str.strip().ne("").sum()

# 🔹 Exibindo a contagem com st.info()
st.info(f"🔹 Total de defeitos com previsão: **{total_com_previsao}**")

###############################################################################################################################################################################

df_filtro["DIAS_ABERTURA"] = (pd.Timestamp.today() - df_filtro["ABERTURA"]).dt.days

# Obtendo contagens corretamente
qtd_1_dia = (df_filtro["DIAS_ABERTURA"] <= 1).sum()
qtd_2_dias = (df_filtro["DIAS_ABERTURA"] == 2).sum()
qtd_3_dias = (df_filtro["DIAS_ABERTURA"] == 3).sum()
qtd_4_dias = (df_filtro["DIAS_ABERTURA"] == 4).sum()
qtd_5_ou_mais = (df_filtro["DIAS_ABERTURA"] >= 5).sum()  # Corrigido

# Criando métricas com cinco colunas
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("📅 1 Dia", qtd_1_dia)
col2.metric("⏳ 2 Dias", qtd_2_dias)
col3.metric("🔥 3 Dias", qtd_3_dias)
col4.metric("⚡ 4 Dias", qtd_4_dias)
col5.metric("🚨 5+ Dias", qtd_5_ou_mais)

###############################################################################################################################################################################

# st.header("Dashboards")

with st.container():

    # st.plotly_chart(grafico1, use_container_width=True)

    col4, col5, col6 = st.columns(3)
    col7, col8 = st.columns(2)

with col4:
    st.plotly_chart(grafico2, use_container_width=True)
with col5:
    st.plotly_chart(grafico3, use_container_width=True)
with col6:
    st.plotly_chart(grafico4, use_container_width=True)

st.plotly_chart(grafico1, use_container_width=True)

