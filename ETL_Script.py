# %%
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import scipy.stats as st
from statsmodels.stats.proportion import proportion_confint
import statsmodels.api as sm

# %%
df_orders = pd.read_csv('../analytical-report-Statistics-Grade/data/FACT_Orders.csv')
df_delivery = pd.read_csv('../analytical-report-Statistics-Grade/data/DIM_Delivery.csv')
df_customer = pd.read_csv('../analytical-report-Statistics-Grade/data/DIM_Customer.csv')
df_shopping = pd.read_csv('../analytical-report-Statistics-Grade/data/DIM_Shopping.csv')
df_products = pd.read_csv('../analytical-report-Statistics-Grade/data/DIM_Products.csv')


# %%
df_orders_kpi = df_orders[['Id', 'Discount', 'Subtotal', 'Purchase_Status']]
df_shopping_kpi = df_shopping[['Id', 'Quantity']]

df_elasticity = pd.merge(df_orders_kpi, df_shopping_kpi, on='Id', how='inner')


# %%
df_shopping['Product_Key'] = df_shopping['Item_ID'].str.split(',').str[1]

df_products['Product_Key'] = df_products['Product_Id'].str.split(',').str[1]

# %%
df_orders_agg = df_orders.groupby('Id').agg(
    Order_Date=('Order_Date', 'first'),
    payment=('Payment', 'first'),
    Purchase_Status=('Purchase_Status', 'first'),

    Subtotal=('Subtotal', 'sum'),
    Discount=('Discount', 'sum'),
    Total=('Total', 'sum')
).reset_index()

print(df_orders_agg.head())

# %%
df_abt = df_orders_agg.copy()

df_delivery_clean = df_delivery[['Id', 'Services', 'P_Sevice', 'D_Forecast', 'D_Date', 'Status']]
df_abt = pd.merge(df_abt, df_delivery_clean, on='Id', how='left')

df_customer_clean = df_customer[['Id', 'State', 'Region']]
df_abt = pd.merge(df_abt, df_customer_clean, on='Id', how='left')

df_abt = df_abt.rename(columns={
    'Id': 'order_id',
    'Order_Date': 'Order_Date',
    'payment': 'Payment_Method',
    'Purchase_Status': 'Purchase_Status',
    'Services': 'Service',
    'P_Sevice': 'P_Service', 
    'D_Forecast': 'D_Forecast',
    'D_Date': 'D_Date',
    'Status': 'Delivery_Status',
    'State': 'UF',
    'Region': 'Region'
})

# %%
df_items_base = df_shopping[['Id', 'Product_Key', 'Quantity', 'Price']]

df_products_clean = df_products[['Product_Key', 'Product_Name', 'Category', 'Subcategory']]
df_items_abt = pd.merge(df_items_base, df_products_clean, on='Product_Key', how='left')

df_items_abt = pd.merge(
    df_items_abt,
    df_orders_agg[['Id', 'Order_Date']],
    on='Id',
    how='left'
)

# %%
date_cols = ['Order_Date', 'D_Date', 'D_Forecast']
for col in date_cols:
    df_abt[col] = pd.to_datetime(df_abt[col], errors='coerce')

numeric_cols = ['Subtotal', 'Discount', 'Total', 'P_Service']
for col in numeric_cols:
    df_abt[col] = pd.to_numeric(df_abt[col], errors='coerce')


#  2. Limpeza de Strings

string_cols = ['Payment_Method', 'Purchase_Status', 'Service', 'Delivery_Status', 'UF', 'Region']
for col in string_cols:
    df_abt[col] = df_abt[col].astype(str).str.lower().str.strip()

df_abt = df_abt.replace('nan', np.nan)


# 3. Tratamento de Nulos (NA) 

# Para NAs numéricos (Subtotal, Discount, etc.), assumimos que 0 é
# o valor correto (ex: um pedido sem desconto terá NA do merge)
df_abt[numeric_cols] = df_abt[numeric_cols].fillna(0)

# Verificar integridade: Pedidos com Total 0
total_zero = (df_abt['Total'] == 0).sum()
print(f"Encontrados {total_zero} pedidos com Total R$ 0.00. (Revisar se necessário)")


# 4. Verificação de Duplicatas e Integridade 
dups = df_abt['order_id'].duplicated().sum()
if dups > 0:
    print(f"ALERTA: Encontradas {dups} duplicatas em 'order_id'. Removendo...")
    df_abt = df_abt.drop_duplicates(subset='order_id', keep='first')
else:
    print("Verificação de duplicatas: OK. 'order_id' é uma chave única.")

# Verificar integridade de datas (ex: entrega antes do pedido)
erros_data = (df_abt['D_Date'] < df_abt['Order_Date']).sum()
if erros_data > 0:
    print(f"ALERTA: Encontrados {erros_data} pedidos com data de entrega ANTES da data do pedido. (Revisar dados)")

df_entregues = df_abt[(df_abt['Delivery_Status'].isin(['entregue', 'atrasado'])) & (df_abt['D_Date'].notna())].copy()


# 1. Identificar as linhas com datas inconsistentes
indices_ruins = df_abt[df_abt['D_Date'] < df_abt['Order_Date']].index

print(f"--- Tratamento de Datas Inconsistentes ---")
print(f"Identificados {len(indices_ruins)} pedidos com D_Date < Order_Date.")

# 2. Decisão: Remover esses registros
# Guardamos os IDs removidos para referência
ids_removidos = df_abt.loc[indices_ruins, 'order_id'].tolist()
df_abt = df_abt.drop(indices_ruins)

# 3. ATUALIZAR o 'df_entregues' também
# (Garante que o df de entregas não contenha os IDs removidos)
df_entregues = df_entregues[~df_entregues['order_id'].isin(ids_removidos)].copy()

print(f"Tratamento: {len(indices_ruins)} registros removidos.")
print(f"Tamanho atual de 'df_abt': {len(df_abt)}")
print(f"Tamanho atual de 'df_entregues': {len(df_entregues)}")

print("\n--- Limpeza de Dados Concluída ---")

# %%
print("\n--- Iniciando Feature Engineering ---")

# 1. KPIs de Logística

if df_entregues.empty:
    print("ALERTA: Nenhum pedido encontrado com status 'entregue' ou 'atrasado'. A análise logística será pulada.")
else:
    # Tempo do pedido até a entrega
    df_entregues['delivery_lead_time_days'] = (df_entregues['D_Date'] - df_entregues['Order_Date']).dt.days

    # Atraso na entrega: Diferença da entrega vs. previsão
    # Negativo = chegou adiantado. Positivo = chegou atrasado.
    df_entregues['delivery_delay_days'] = (df_entregues['D_Date'] - df_entregues['D_Forecast']).dt.days

    # Flag de Atraso (KPI): 1 se atrasou, 0 se chegou no dia ou antes
    df_entregues['is_late'] = (df_entregues['delivery_delay_days'] > 0).astype(int)
    
    print(f"\n{len(df_entregues)} pedidos foram considerados 'entregues' para análise logística.")

# %%

# 2. KPIs de Negócio e Financeiros (na base principal df_abt)

# Flags de Status (KPIs de Conversão)
# (Baseado nos valores que vimos: 'confirmado', 'cancelado', 'em analise', 'processando')
df_abt['is_confirmed'] = (df_abt['Purchase_Status'] == 'confirmado').astype(int)
df_abt['is_canceled'] = (df_abt['Purchase_Status'] == 'cancelado').astype(int)

# KPIs Financeiros (KPIs de Rentabilidade)
# Take-rate de Frete: Quanto do Total do pedido é composto pelo frete
df_abt['freight_share'] = np.where(
    df_abt['Total'] > 0,
    df_abt['P_Service'] / df_abt['Total'],
    0
)

freight_share_means = df_abt[['freight_share']].mean()
formatted_freight_share = freight_share_means.map('{:.2%}'.format)

print("Qtd pedidos confirmados:", df_abt['is_confirmed'].sum())
print("\nQtd pedidos cancelados:", df_abt['is_canceled'].sum())
print("\nTake-rate de frete:", formatted_freight_share['freight_share'])

print("\n--- KPIs de Negócio e Financeiros Calculados ---")

# %%
# % de Desconto
df_abt['discount_perc'] = np.where(
    df_abt['Subtotal'] > 0,
    df_abt['Discount'] / df_abt['Subtotal'],
    0
)

df_elasticity['discount_perc'] = df_elasticity['Discount']

# Limpar o status de compra (padrão da Fase 2.1)
df_elasticity['Purchase_Status'] = df_elasticity['Purchase_Status'].astype(str).str.lower().str.strip()

# Filtra apenas por vendas confirmadas
df_analise = df_elasticity[df_elasticity['Purchase_Status'] == 'confirmado'].copy()

# Definir as faixas de desconto
bins = [-0.01, 0, 0.05, 0.1, 0.15, 0.2, 1] 
labels = ['0% (Sem Desconto)', '0.1% a 5%', '5.1% a 10%', '10.1% a 15%', '15.1% a 20%', '> 20%']

# Criar a coluna 'faixa_desconto'
df_analise['faixa_desconto'] = pd.cut(
    df_analise['discount_perc'], 
    bins=bins, 
    labels=labels,
    right=True
)

df_analise = df_analise.dropna(subset=['faixa_desconto'])

kpi_elasticidade = df_analise.groupby('faixa_desconto', observed=True)['Quantity'].mean().reset_index()

print("KPI: Quantidade Média Vendida por Faixa de Desconto")
print(kpi_elasticidade)

# %%
# Atributos de Sazonalidade (Agrupamento)
df_abt['order_month_year'] = df_abt['Order_Date'].dt.to_period('M') # Para séries temporais
df_abt['order_weekday'] = df_abt['Order_Date'].dt.day_name()      # Para análise de dia da semana


# %%
# Identificar outliers para o Ticket Médio (Total)
data_ticket = df_abt[df_abt['is_confirmed'] == 1]['Total']

Q1_ticket = data_ticket.quantile(0.25)
Q3_ticket = data_ticket.quantile(0.75)
IQR_ticket = Q3_ticket - Q1_ticket
limite_sup_ticket = Q3_ticket + (1.5 * IQR_ticket)
limite_inf_ticket = Q1_ticket - (1.5 * IQR_ticket)

## Quantificar os outliers
outliers_ticket = data_ticket[
    (data_ticket > limite_sup_ticket) | (data_ticket < limite_inf_ticket)
]

print(f"--- Análise de Outliers (Ticket Médio) ---")
print(f"Limite Superior (IQR): R$ {limite_sup_ticket:,.2f}")
print(f"Limite Inferior (IQR): R$ {limite_inf_ticket:,.2f}")
print(f"Total de Pedidos Confirmados: {len(data_ticket)}")
print(f"Pedidos considerados outliers: {len(outliers_ticket)} ({len(outliers_ticket) / len(data_ticket):.2%})")

# Identificar outliers para o Prazo de Entrega (Lead Time)
data_prazo = df_entregues['delivery_lead_time_days']

Q1_prazo = data_prazo.quantile(0.25)
Q3_prazo = data_prazo.quantile(0.75)
IQR_prazo = Q3_prazo - Q1_prazo
limite_sup_prazo = Q3_prazo + (1.5 * IQR_prazo)
limite_inf_prazo = Q1_prazo - (1.5 * IQR_prazo)

# Quantificar os outliers
outliers_prazo = data_prazo[
    (data_prazo > limite_sup_prazo) | (data_prazo < limite_inf_prazo)
]

print(f"\n--- Análise de Outliers (Prazo de Entrega) ---")
print(f"Limite Superior (IQR): {limite_sup_prazo:.2f} dias")
print(f"Limite Inferior (IQR): {limite_inf_prazo:.2f} dias")
print(f"Total de Pedidos Entregues: {len(data_prazo)}")
print(f"Entregas consideradas outliers: {len(outliers_prazo)} ({len(outliers_prazo) / len(data_prazo):.2%})")


# %%
# Médias de Prazo de Entrega por Serviço

print(f"{df_entregues[df_entregues['Service'] == 'standard']['delivery_lead_time_days'].mean():.2f}")
print(f"{df_entregues[df_entregues['Service'] == 'same-day']['delivery_lead_time_days'].mean():.2f}")
print(f"{df_entregues[df_entregues['Service'] == 'scheduled']['delivery_lead_time_days'].mean():.2f}")

# %%
# Médias de Prazo de Entrega por Região

print(f"{df_entregues[df_entregues['Region'] == 'norte']['delivery_lead_time_days'].mean():.2f}")
print(f"{df_entregues[df_entregues['Region'] == 'nordeste']['delivery_lead_time_days'].mean():.2f}")
print(f"{df_entregues[df_entregues['Region'] == 'sul']['delivery_lead_time_days'].mean():.2f}")
print(f"{df_entregues[df_entregues['Region'] == 'sudeste']['delivery_lead_time_days'].mean():.2f}")

print("--- Feature Engineering Concluída ---")

# %%
# 1. Identificar outliers para o Ticket Médio (Total)
data_ticket = df_abt[df_abt['is_confirmed'] == 1]['Total']

Q1_ticket = data_ticket.quantile(0.25)
Q3_ticket = data_ticket.quantile(0.75)
IQR_ticket = Q3_ticket - Q1_ticket
limite_sup_ticket = Q3_ticket + (1.5 * IQR_ticket)
limite_inf_ticket = Q1_ticket - (1.5 * IQR_ticket)

# 2. Quantificar os outliers
outliers_ticket = data_ticket[
    (data_ticket > limite_sup_ticket) | (data_ticket < limite_inf_ticket)
]

print(f"--- Análise de Outliers (Ticket Médio) ---")
print(f"Limite Superior (IQR): R$ {limite_sup_ticket:,.2f}")
print(f"Limite Inferior (IQR): R$ {limite_inf_ticket:,.2f}")
print(f"Total de Pedidos Confirmados: {len(data_ticket)}")
print(f"Pedidos considerados outliers: {len(outliers_ticket)} ({len(outliers_ticket) / len(data_ticket):.2%})")

# 3. Identificar outliers para o Prazo de Entrega (Lead Time)
data_prazo = df_entregues['delivery_lead_time_days']

Q1_prazo = data_prazo.quantile(0.25)
Q3_prazo = data_prazo.quantile(0.75)
IQR_prazo = Q3_prazo - Q1_prazo
limite_sup_prazo = Q3_prazo + (1.5 * IQR_prazo)
limite_inf_prazo = Q1_prazo - (1.5 * IQR_prazo)

# 4. Quantificar os outliers
outliers_prazo = data_prazo[
    (data_prazo > limite_sup_prazo) | (data_prazo < limite_inf_prazo)
]

print(f"\n--- Análise de Outliers (Prazo de Entrega) ---")
print(f"Limite Superior (IQR): {limite_sup_prazo:.2f} dias")
print(f"Limite Inferior (IQR): {limite_inf_prazo:.2f} dias")
print(f"Total de Pedidos Entregues: {len(data_prazo)}")
print(f"Entregas consideradas outliers: {len(outliers_prazo)} ({len(outliers_prazo) / len(data_prazo):.2%})")

print("\n--- Feature Engineering Concluída ---")

# %%
# 1. Análise Univariada (Distribuição dos KPIs)

print("\n--- Iniciando Análise Exploratória ---")
sns.set_style("whitegrid")

# %%
# Histograma do Ticket Médio (Total)
plt.figure(figsize=(10, 5))
sns.histplot(df_abt[df_abt['is_confirmed']==1]['Total'], kde=True, bins=50)
plt.title('Distribuição do Ticket Médio (Pedidos Confirmados)')
plt.ylabel('Contagem de Pedidos')
plt.xlabel('Valor Total do Pedido (R$)')
plt.show()
# 


# %%
# Histograma do Prazo de Entrega (Lead Time)
if not df_entregues.empty:
    plt.figure(figsize=(12, 5))
    dados_filtrados = df_entregues[df_entregues['delivery_lead_time_days'] > 0]['delivery_lead_time_days']
    
    sns.histplot(dados_filtrados, kde=True, bins=30)
    plt.title('Distribuição do Prazo de Entrega (em dias)')
    plt.ylabel('Contagem de Pedidos')
    plt.xlabel('Dias desde o Pedido até a Entrega')
    plt.xticks(range(0, dados_filtrados.max(), 10))
    plt.show()


# %%
# Histograma do Atraso
if not df_entregues.empty:
    plt.figure(figsize=(12, 5))
    sns.histplot(df_entregues['delivery_delay_days'], kde=False, bins=15)
    plt.title('Distribuição do Atraso (dias)')
    plt.ylabel('Contagem de Pedidos')
    plt.xlabel('Dias (Negativo=Adiantado, Positivo=Atrasado)')
    plt.show()



# %%
# 2. Análise de Sazonalidade (Séries Temporais)

# Receita (Total) ao longo do tempo

receita_mensal = df_abt[df_abt['is_confirmed']==1].groupby('order_month_year')['Total'].sum().reset_index()
receita_mensal['order_month_year_str'] = receita_mensal['order_month_year'].astype(str)

plt.figure(figsize=(12, 6))
sns.lineplot(data=receita_mensal, x='order_month_year_str', y='Total', marker="o")
plt.title('Receita Mensal (Pedidos Confirmados)')
plt.xlabel('Quinzena')
plt.ylabel('Receita Total (R$)')
plt.show()

# %%
# 3. Análise de KPIs de Logística (Por Segmento)

# Taxa de Atraso por Serviço (Service)
if not df_entregues.empty:
    plt.figure(figsize=(10, 5))
    taxa_atraso_servico = df_entregues.groupby('Service')['is_late'].mean().reset_index()
    
    ax = sns.barplot(
        data=taxa_atraso_servico.sort_values('is_late', ascending=False), 
        x='Service', 
        y='is_late',
        color='steelblue'
    )
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(
            f'{height:.1%}', 
            (p.get_x() + p.get_width() / 2., height), 
            ha='center', 
            va='center', 
            xytext=(0, 9), 
            textcoords='offset points',
            fontsize=11,
            fontweight='bold'
        )

    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))

    plt.title('Taxa Média de Atraso por Tipo de Serviço')
    plt.xlabel('Tipo de Serviço')
    plt.ylabel('Taxa de Atraso') 
    
    sns.despine(left=True, bottom=True)
    plt.show()


# %%
# Taxa de Atraso por Região (Region)

if not df_entregues.empty:
    plt.figure(figsize=(10, 5))
    taxa_atraso_regiao = df_entregues.groupby('Region')['is_late'].mean().reset_index()
    
    ax = sns.barplot(
        data=taxa_atraso_regiao.sort_values('is_late', ascending=False), 
        x='Region', 
        y='is_late',
        color='steelblue'
    )
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(
            f'{height:.1%}', 
            (p.get_x() + p.get_width() / 2., height), 
            ha='center', 
            va='center', 
            xytext=(0, 9), 
            textcoords='offset points',
            fontsize=11,
            fontweight='bold'
        )

    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))

    plt.title('Taxa Média de Atraso por Região')
    plt.xlabel('Regiões')
    plt.ylabel('Taxa de Atraso (% de Pedidos)') 
    
    sns.despine(left=True, bottom=True)
    plt.show()



# %%

# 4. Análise de Pagamento e Conversão  

# Status de Pagamento por Método
plt.figure(figsize=(12, 6))


sns.countplot(data=df_abt, x='Payment_Method', hue='Purchase_Status')

plt.title('Contagem de Status de Pedido por Método de Pagamento')
plt.ylabel('Contagem de Pedidos')
plt.xlabel('Método de Pagamento')
plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)
plt.tight_layout()
plt.show()


# %%

# Taxa de Cancelamento por Método de Pagamento
taxa_cancel_pagto = df_abt.groupby('Payment_Method')['is_canceled'].mean().reset_index()
plt.figure(figsize=(12, 6))
ax = sns.barplot(
    data=taxa_cancel_pagto.sort_values('is_canceled', ascending=False), 
    x='Payment_Method', 
    y='is_canceled')

for p in ax.patches:
    height = p.get_height()
    ax.annotate(
        f'{height:.1%}', 
        (p.get_x() + p.get_width() / 2., height), 
        ha='center', 
        va='center', 
        xytext=(0, 9), 
        textcoords='offset points',
        fontsize=11,
        fontweight='bold'
    )

ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
plt.title('Taxa de Cancelamento por Método de Pagamento')
plt.xlabel('Método de Pagamento')
plt.ylabel('Taxa de Cancelamento')
sns.despine(left=True, bottom=True)
plt.tight_layout()
plt.show()


# %%
# Análise de Elasticidade de Preço (Desconto vs. Quantidade Vendida)

plt.figure(figsize=(12, 7))

# Usamos 'seagreen' como uma cor sugestiva (dinheiro)
ax = sns.barplot(
    data=kpi_elasticidade, 
    x='faixa_desconto', 
    y='Quantity',
    color='seagreen'
)

# Adicionar rótulos de dados
for p in ax.patches:
    height = p.get_height()
    # '{:.2f}' formata o número com 2 casas decimais (ex: "1.25")
    ax.annotate(
        f'{height:.2f}', 
        (p.get_x() + p.get_width() / 2., height), 
        ha='center', 
        va='center', 
        xytext=(0, 9), 
        textcoords='offset points',
        fontsize=11,
        fontweight='bold'
    )

plt.title('Quantidade Média Vendida por Faixa de Desconto')
plt.xlabel('Faixa de Desconto (%)')
plt.ylabel('Quantidade Média por Item Vendido')
plt.xticks(rotation=45, ha='right')
sns.despine(left=True, bottom=True)
plt.tight_layout()
plt.show()


# %%
print("\n--- Iniciando Inferência Estatística ---")

def get_ic_mean(data, confidence=0.95):
    if len(data) < 2:
        return (np.nan, np.nan)
    n = len(data)
    mean = data.mean()
    sem = st.sem(data)
    ic = st.t.interval(confidence=confidence, df=n-1, loc=mean, scale=sem)
    return ic

# IC de Proporção (usando método 'wilson')
def get_ic_proportion(data, confidence=0.95):
    n_total = len(data)
    if n_total == 0:
        return (np.nan, np.nan)
    n_success = data.sum()
    ic = proportion_confint(count=n_success, nobs=n_total, alpha=(1-confidence), method='wilson')
    return ic

resultados_inferencia = {}

# 1. IC 95% para Ticket Médio
# Usamos apenas pedidos confirmados para o Ticket Médio
data_ticket = df_abt[df_abt['is_confirmed']==1]['Total']
ic_ticket = get_ic_mean(data_ticket)
resultados_inferencia['Ticket Medio'] = {
    'Média': data_ticket.mean(),
    'IC 95%': ic_ticket
}

# 2. IC 95% para Prazo Médio de Entrega
if not df_entregues.empty:
    data_prazo = df_entregues['delivery_lead_time_days']
    ic_prazo = get_ic_mean(data_prazo)
    resultados_inferencia['Prazo Médio Entrega (dias)'] = {
        'Média': data_prazo.mean(),
        'IC 95%': ic_prazo
    }

# 3. IC 95% para Taxa de Atraso (Geral)
if not df_entregues.empty:
    data_atraso = df_entregues['is_late']
    ic_atraso = get_ic_proportion(data_atraso)
    resultados_inferencia['Taxa de Atraso (Geral)'] = {
        'Proporção': data_atraso.mean(),
        'IC 95%': ic_atraso
    }

# 4. IC 95% para Taxa de Cancelamento (Geral)
data_cancel = df_abt['is_canceled']
ic_cancel = get_ic_proportion(data_cancel)
resultados_inferencia['Taxa de Cancelamento (Geral)'] = {
    'Proporção': data_cancel.mean(),
    'IC 95%': ic_cancel
}

# Tabela de Resultados
print("\n--- Resultados Finais: Intervalos de Confiança (95%) ---")

for kpi, values in resultados_inferencia.items():
    media_ou_prop = "Média" if "Média" in values else "Proporção"

    prefixo = ""
    
    if kpi == 'Ticket Medio':
        fmt = ".2f"
        prefixo = "R$ "
    elif kpi == 'Prazo Médio Entrega (dias)':
        fmt = ".1f" 
    else:
        fmt = ".2%" 

    print(f"\nKPI: {kpi}")

    print(f"  {prefixo}{media_ou_prop}: {values[media_ou_prop]:{fmt}}")
    print(f"  IC 95%: ({prefixo}{values['IC 95%'][0]:{fmt}}, {prefixo}{values['IC 95%'][1]:{fmt}})")



# %%
