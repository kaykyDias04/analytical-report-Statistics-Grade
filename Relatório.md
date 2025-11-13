## 📊 Relatório Analítico: Desempenho Operacional e Financeiro do E-commerce

## Sumário Executivo

O presente relatório visa fornecer à direção do e-commerce brasileiro uma análise estatística robusta sobre o desempenho operacional e financeiro. A análise exploratória e inferencial revelou achados acionáveis cruciais para a otimização de processos e aumento da rentabilidade.

## 🎯 Achados Acionáveis Chave:

1.  **Oportunidade de Conversão de Pagamento:** A taxa de cancelamento varia significativamente entre os métodos de pagamento. O método **[Método de Pagamento com Maior Taxa de Cancelamento]** apresenta uma taxa de cancelamento de **[X]%**, sugerindo a necessidade de revisão dos fluxos de confirmação e checkout específicos para este método.

2.  **Risco Logístico Regional:** A performance logística não é uniforme. A região **[Região com Maior Taxa de Atraso]** registra a maior taxa de atraso nas entregas, impactando a satisfação do cliente. O lead time médio nesta região é de **[Y] dias**, excedendo a média nacional.

3.  **Potencial de Rentabilidade:** O Take-rate de frete (P_Service/Total) tem uma média de **[Z]%**, indicando que o custo do frete é uma parcela significativa da receita total. A otimização dos custos logísticos ou a revisão da política de frete pode impactar diretamente a margem de lucro.

4.  **Sazonalidade de Vendas:** O mês de **[Mês de Pico de Vendas]** demonstrou o pico de vendas, com **[W]%** do volume anual, o que deve guiar o planejamento de estoque e campanhas promocionais.

---

## 🛠️ Dados & Método

### Fontes de Dados e Joins

A análise foi conduzida a partir de cinco fontes de dados (arquivos CSV) que representam o modelo dimensional do e-commerce: `FACT_Orders`, `DIM_Delivery`, `DIM_Customer`, `DIM_Shopping` e `DIM_Products`. Os dados foram carregados e integrados utilizando a biblioteca Pandas em Python, com agregação por `Id` (Pedido) para criar a Analytical Base Table (ABT).

### Qualidade e Preparação dos Dados

O processo de Data Cleaning incluiu a padronização de strings, conversão de tipos de dados (datas e numéricos) e tratamento de valores nulos.

### Tratamento de Datas

> Durante a limpeza de dados, foram identificados **328 pedidos** onde a data de entrega (`D_Date`) era anterior à data do pedido (`Order_Date`). Por representarem um erro de registro fisicamente impossível, esses 328 registros foram removidos dos DataFrames `df_abt` e `df_entregues`. Toda a análise subsequente (EDA, Inferência) foi realizada sobre a base de dados tratada, garantindo a integridade dos cálculos de prazo e atraso.

### Estratégia de Outliers

A identificação de outliers foi realizada usando a regra IQR (Intervalo Interquartil) para as principais métricas financeiras e logísticas.

* **Ticket Médio (Total):** Foram identificados **[X] pedidos ([Y]%)** como outliers (acima de R$ [Z]).
    * **Tratamento: Manutenção.** Estes são pedidos legítimos de alto valor (receita real) e não um erro de dados. Removê-los distorceria a receita total. A análise de média (como o Ticket Médio) está ciente de sua influência, e a mediana será usada como uma métrica de tendência central mais robusta.

* **Prazo de Entrega (Lead Time):** Foram identificadas **[A] entregas ([B]%)** como outliers (ex: acima de [C] dias ou abaixo de [D] dias).
    * **Tratamento: Manutenção com Flag.** Esses outliers representam falhas logísticas reais (ou entregas surpreendentemente rápidas). Eles não serão removidos, pois são cruciais para entender os piores cenários da operação.

### Feature Engineering (KPIs)

As seguintes métricas de negócio foram criadas como features para a análise:

* `delivery_delay_days` (Atraso)
* `delivery_lead_time` (Prazo de Entrega)
* `is_late` (Flag de Atraso)
* `is_confirmed` (Flag de Conversão)
* `freight_share` (Take-rate de Frete)
* `discount_perc` (Desconto Médio Percentual)

---

## 📈 Análise Exploratória de Dados (EDA)

### Distribuição e Tendência Central

A análise descritiva das principais métricas financeiras e logísticas revelou:

| Métrica | Média | Mediana | Desvio Padrão |
| :--- | :--- | :--- | :--- |
| **Ticket Médio (R$)** | [Valor Médio] | [Valor Mediano] | [Desvio Padrão] |
| **Prazo de Entrega (dias)** | [Valor Médio] | [Valor Mediano] | [Desvio Padrão] |
| **Desconto Médio (%)** | [Valor Médio] | [Valor Mediano] | [Desvio Padrão] |

A distribuição do Ticket Médio, conforme o histograma gerado, é **[Descrição da Distribuição, ex: assimétrica à direita]**, o que justifica a decisão de usar a mediana como métrica robusta de tendência central.

### Performance Logística por Serviço

A performance de entrega, medida pela taxa de atraso (`is_late`), varia conforme o tipo de serviço contratado:

| Serviço | Taxa de Atraso (%) | Prazo Médio (dias) |
| :--- | :--- | :--- |
| Standard | [Taxa Atraso] | [Prazo Médio] |
| Same-Day | [Taxa Atraso] | [Prazo Médio] |
| Scheduled | [Taxa Atraso] | [Prazo Médio] |

O serviço **[Serviço com Melhor Performance]** demonstra a melhor performance em termos de pontualidade.

### Sazonalidade e Geográfica

A análise de séries temporais por mês/ano identificou o pico de vendas em **[Mês de Pico]**. A análise geográfica por Região e UF indica que a Região **[Região de Pior Performance]** apresenta o maior desafio logístico.

---

## 🔬 Inferência Estatística

Foram calculados Intervalos de Confiança (IC) de 95% para as principais métricas, fornecendo estimativas robustas para a direção:

* **IC 95% para Ticket Médio:** O ticket médio real da população de pedidos está, com 95% de confiança, entre **R$ [Limite Inferior]** e **R$ [Limite Superior]**.

* **IC 95% para Proporção de Atraso:** A proporção real de pedidos atrasados está, com 95% de confiança, entre **[Limite Inferior]%** e **[Limite Superior]%**.
