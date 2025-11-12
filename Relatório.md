## Documentação da Estratégia de Outliers

A identificação de outliers foi realizada usando a regra IQR (Intervalo Interquartil).

Ticket Médio (Total): Foram identificados [X] pedidos ([Y]%) como outliers (acima de R$ [Z]).

Tratamento: Manutenção. Estes são pedidos legítimos de alto valor (receita real) e não um erro de dados. Removê-los distorceria a receita total. A análise de média (como o Ticket Médio) está ciente de sua influência, e a mediana será usada como uma métrica de tendência central mais robusta.

Prazo de Entrega (Lead Time): Foram identificadas [A] entregas ([B]%) como outliers (ex: acima de [C] dias ou abaixo de [D] dias).

Tratamento: Manutenção com Flag. Esses outliers representam falhas logísticas reais (ou entregas surpreendentemente rápidas). Eles não serão removidos, pois são cruciais para entender os piores cenários da operação.

## Documentação do Tratamento de Datas
 
Durante a limpeza de dados (Fase 2.1), foram identificados 328 pedidos onde a data de entrega (D_Date) era anterior à data do pedido (Order_Date).

Decisão de Tratamento: Por representarem um erro de registro fisicamente impossível, esses 328 registros foram removidos dos DataFrames df_abt e df_entregues. Toda a análise subsequente (EDA, Inferência) foi realizada sobre a base de dados tratada, garantindo a integridade dos cálculos de prazo e atraso.