# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC Claims and Membership Recon By Year

# COMMAND ----------

# DBTITLE 1,Physician Table Totals By First Service Year (Aligned)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_202607 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202607,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202607
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_202607
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_202512 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202512,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202512
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_202512
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_202410 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202410,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202410
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_202410
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_202310 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202310,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202310
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_202310
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2022 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2022,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2022
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2022
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2021 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2021,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2021
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2021
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2020 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2020,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2020
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2020
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2019 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2019,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2019
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2019
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2018 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2018,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2018
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2018
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2017 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2017,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2017
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2017
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2016 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2016,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2016
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2016
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC   CREATE OR REPLACE TEMPORARY TABLE summ_2015 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2015,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2015
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2015
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_2014 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2014,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2014
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_pr_f_2014
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_fnl = 'N'
# MAGIC   AND service_code not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_202607
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_202512
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_202410
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM
# MAGIC       summ_202310
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2022
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2021
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2020
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2019
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2018
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2017
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2016
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2015
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       fst_srvc_year,
# MAGIC       fst_srvc_month
# MAGIC     FROM summ_2014
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE summ_combined AS
# MAGIC SELECT Base.component,
# MAGIC Base.fst_srvc_year,
# MAGIC SUM(coalesce(summ_2014.net_pd_amt_2014,0)) as net_pd_amt_2014,
# MAGIC SUM(coalesce(summ_2015.net_pd_amt_2015,0)) as net_pd_amt_2015,
# MAGIC SUM(coalesce(summ_2016.net_pd_amt_2016,0)) as net_pd_amt_2016,
# MAGIC SUM(coalesce(summ_2017.net_pd_amt_2017,0)) as net_pd_amt_2017,
# MAGIC SUM(coalesce(summ_2018.net_pd_amt_2018,0)) as net_pd_amt_2018,
# MAGIC SUM(coalesce(summ_2019.net_pd_amt_2019,0)) as net_pd_amt_2019,
# MAGIC SUM(coalesce(summ_2020.net_pd_amt_2020,0)) as net_pd_amt_2020,
# MAGIC SUM(coalesce(summ_2021.net_pd_amt_2021,0)) as net_pd_amt_2021,
# MAGIC SUM(coalesce(summ_2022.net_pd_amt_2022,0)) as net_pd_amt_2022,
# MAGIC SUM(coalesce(summ_202310.net_pd_amt_202310,0)) as net_pd_amt_202310,
# MAGIC SUM(coalesce(summ_202410.net_pd_amt_202410,0)) as net_pd_amt_202410,
# MAGIC SUM(coalesce(summ_202512.net_pd_amt_202512,0)) as net_pd_amt_202512,
# MAGIC SUM(coalesce(summ_202607.net_pd_amt_202607,0)) as net_pd_amt_202607,
# MAGIC SUM(coalesce(summ_2014.allw_amt_2014,0)) as allw_amt_2014,
# MAGIC SUM(coalesce(summ_2015.allw_amt_2015,0)) as allw_amt_2015,
# MAGIC SUM(coalesce(summ_2016.allw_amt_2016,0)) as allw_amt_2016,
# MAGIC SUM(coalesce(summ_2017.allw_amt_2017,0)) as allw_amt_2017,
# MAGIC SUM(coalesce(summ_2018.allw_amt_2018,0)) as allw_amt_2018,
# MAGIC SUM(coalesce(summ_2019.allw_amt_2019,0)) as allw_amt_2019,
# MAGIC SUM(coalesce(summ_2020.allw_amt_2020,0)) as allw_amt_2020,
# MAGIC SUM(coalesce(summ_2021.allw_amt_2021,0)) as allw_amt_2021,
# MAGIC SUM(coalesce(summ_2022.allw_amt_2022,0)) as allw_amt_2022,
# MAGIC SUM(coalesce(summ_202310.allw_amt_202310,0)) as allw_amt_202310,
# MAGIC SUM(coalesce(summ_202410.allw_amt_202410,0)) as allw_amt_202410,
# MAGIC SUM(coalesce(summ_202512.allw_amt_202512,0)) as allw_amt_202512,
# MAGIC SUM(coalesce(summ_202607.allw_amt_202607,0)) as allw_amt_202607
# MAGIC FROM summ_combined_1 as Base
# MAGIC LEFT JOIN summ_2014 as summ_2014
# MAGIC     on Base.component = summ_2014.component
# MAGIC         and Base.fst_srvc_month = summ_2014.fst_srvc_month
# MAGIC LEFT JOIN summ_2015 as summ_2015
# MAGIC     on Base.component = summ_2015.component
# MAGIC         and Base.fst_srvc_month = summ_2015.fst_srvc_month
# MAGIC LEFT JOIN summ_2016 as summ_2016
# MAGIC     on Base.component = summ_2016.component
# MAGIC         and Base.fst_srvc_month = summ_2016.fst_srvc_month
# MAGIC LEFT JOIN summ_2017 as summ_2017
# MAGIC     on Base.component = summ_2017.component
# MAGIC         and Base.fst_srvc_month = summ_2017.fst_srvc_month
# MAGIC LEFT JOIN summ_2018 as summ_2018
# MAGIC     on Base.component = summ_2018.component
# MAGIC         and Base.fst_srvc_month = summ_2018.fst_srvc_month
# MAGIC LEFT JOIN summ_2019 as summ_2019
# MAGIC     on Base.component = summ_2019.component
# MAGIC         and Base.fst_srvc_month = summ_2019.fst_srvc_month
# MAGIC LEFT JOIN summ_2020 as summ_2020
# MAGIC     on Base.component = summ_2020.component
# MAGIC         and Base.fst_srvc_month = summ_2020.fst_srvc_month
# MAGIC LEFT JOIN summ_2021 as summ_2021
# MAGIC     on Base.component = summ_2021.component
# MAGIC         and Base.fst_srvc_month = summ_2021.fst_srvc_month
# MAGIC LEFT JOIN summ_2022 as summ_2022
# MAGIC     on Base.component = summ_2022.component
# MAGIC         and Base.fst_srvc_month = summ_2022.fst_srvc_month
# MAGIC LEFT JOIN summ_202310 as summ_202310
# MAGIC     on Base.component = summ_202310.component
# MAGIC         and Base.fst_srvc_month = summ_202310.fst_srvc_month
# MAGIC LEFT JOIN summ_202410 as summ_202410
# MAGIC     on Base.component = summ_202410.component
# MAGIC         and Base.fst_srvc_month = summ_202410.fst_srvc_month
# MAGIC LEFT JOIN summ_202512 as summ_202512
# MAGIC     on Base.component = summ_202512.component
# MAGIC         and Base.fst_srvc_month = summ_202512.fst_srvc_month
# MAGIC LEFT JOIN summ_202607 as summ_202607
# MAGIC     on Base.component = summ_202607.component
# MAGIC         and Base.fst_srvc_month = summ_202607.fst_srvc_month
# MAGIC GROUP BY Base.component,
# MAGIC Base.fst_srvc_year;
# MAGIC
# MAGIC Select * from summ_combined order by component,
# MAGIC fst_srvc_year

# COMMAND ----------

# DBTITLE 1,OAH Migration Source Filter Impact (glxy_pr_f_202607)
# MAGIC %sql
# MAGIC -- Impact of migration_source NOT IN ('OAH') filter
# MAGIC -- Base: denial_fnl = 'N' AND service_code NOT IN ('PR_CLM_DNL','PR_DWNADJ_DNL')
# MAGIC SELECT
# MAGIC   fst_srvc_year,
# MAGIC   SUM(net_pd_amt_fnl)                                                        AS total_net_pd,
# MAGIC   SUM(CASE WHEN migration_source IN ('OAH') THEN net_pd_amt_fnl ELSE 0 END) AS oah_net_pd_excluded,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN migration_source IN ('OAH') THEN net_pd_amt_fnl ELSE 0 END)
# MAGIC         / NULLIF(SUM(net_pd_amt_fnl), 0), 2)                                AS oah_net_pd_pct,
# MAGIC   SUM(allw_amt_fnl)                                                          AS total_allw_amt,
# MAGIC   SUM(CASE WHEN migration_source IN ('OAH') THEN allw_amt_fnl ELSE 0 END)   AS oah_allw_excluded,
# MAGIC   ROUND(100.0 * SUM(CASE WHEN migration_source IN ('OAH') THEN allw_amt_fnl ELSE 0 END)
# MAGIC         / NULLIF(SUM(allw_amt_fnl), 0), 2)                                  AS oah_allw_pct
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_pr_f_202607
# MAGIC WHERE denial_fnl = 'N'
# MAGIC   AND service_code NOT IN ('PR_CLM_DNL', 'PR_DWNADJ_DNL')
# MAGIC GROUP BY fst_srvc_year
# MAGIC ORDER BY fst_srvc_year

# COMMAND ----------

# DBTITLE 1,Outpatient Table Totals By Early Service Year (Aligned)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_202607 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202607,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202607
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202607
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_202512 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202512,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202512
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202512
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_202410 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202410,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202410
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202410
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_202310 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202310,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202310
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202310
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2022 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2022,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2022
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2022
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2021 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2021,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2021
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2021
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2020 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2020,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2020
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2020
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2019 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2019,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2019
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2019
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2018 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2018,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2018
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2018
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2017 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2017,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2017
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2017
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2016 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2016,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2016
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2016
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC   CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2015 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2015,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2015
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2015
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_2014 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2014,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2014
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2014
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_202607
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_202512
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_202410
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_202310
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2022
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2021
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2020
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2019
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2018
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2017
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2016
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2015
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM op_erly_summ_2014
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_erly_summ_combined AS
# MAGIC SELECT Base.component,
# MAGIC Base.erly_srvc_year,
# MAGIC SUM(coalesce(summ_2014.net_pd_amt_2014,0)) as net_pd_amt_2014,
# MAGIC SUM(coalesce(summ_2015.net_pd_amt_2015,0)) as net_pd_amt_2015,
# MAGIC SUM(coalesce(summ_2016.net_pd_amt_2016,0)) as net_pd_amt_2016,
# MAGIC SUM(coalesce(summ_2017.net_pd_amt_2017,0)) as net_pd_amt_2017,
# MAGIC SUM(coalesce(summ_2018.net_pd_amt_2018,0)) as net_pd_amt_2018,
# MAGIC SUM(coalesce(summ_2019.net_pd_amt_2019,0)) as net_pd_amt_2019,
# MAGIC SUM(coalesce(summ_2020.net_pd_amt_2020,0)) as net_pd_amt_2020,
# MAGIC SUM(coalesce(summ_2021.net_pd_amt_2021,0)) as net_pd_amt_2021,
# MAGIC SUM(coalesce(summ_2022.net_pd_amt_2022,0)) as net_pd_amt_2022,
# MAGIC SUM(coalesce(summ_202310.net_pd_amt_202310,0)) as net_pd_amt_202310,
# MAGIC SUM(coalesce(summ_202410.net_pd_amt_202410,0)) as net_pd_amt_202410,
# MAGIC SUM(coalesce(summ_202512.net_pd_amt_202512,0)) as net_pd_amt_202512,
# MAGIC SUM(coalesce(summ_202607.net_pd_amt_202607,0)) as net_pd_amt_202607,
# MAGIC SUM(coalesce(summ_2014.allw_amt_2014,0)) as allw_amt_2014,
# MAGIC SUM(coalesce(summ_2015.allw_amt_2015,0)) as allw_amt_2015,
# MAGIC SUM(coalesce(summ_2016.allw_amt_2016,0)) as allw_amt_2016,
# MAGIC SUM(coalesce(summ_2017.allw_amt_2017,0)) as allw_amt_2017,
# MAGIC SUM(coalesce(summ_2018.allw_amt_2018,0)) as allw_amt_2018,
# MAGIC SUM(coalesce(summ_2019.allw_amt_2019,0)) as allw_amt_2019,
# MAGIC SUM(coalesce(summ_2020.allw_amt_2020,0)) as allw_amt_2020,
# MAGIC SUM(coalesce(summ_2021.allw_amt_2021,0)) as allw_amt_2021,
# MAGIC SUM(coalesce(summ_2022.allw_amt_2022,0)) as allw_amt_2022,
# MAGIC SUM(coalesce(summ_202310.allw_amt_202310,0)) as allw_amt_202310,
# MAGIC SUM(coalesce(summ_202410.allw_amt_202410,0)) as allw_amt_202410,
# MAGIC SUM(coalesce(summ_202512.allw_amt_202512,0)) as allw_amt_202512,
# MAGIC SUM(coalesce(summ_202607.allw_amt_202607,0)) as allw_amt_202607
# MAGIC FROM op_erly_summ_combined_1 as Base
# MAGIC LEFT JOIN op_erly_summ_2014 as summ_2014
# MAGIC     on Base.component = summ_2014.component
# MAGIC         and Base.erly_srvc_month = summ_2014.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2015 as summ_2015
# MAGIC     on Base.component = summ_2015.component
# MAGIC         and Base.erly_srvc_month = summ_2015.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2016 as summ_2016
# MAGIC     on Base.component = summ_2016.component
# MAGIC         and Base.erly_srvc_month = summ_2016.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2017 as summ_2017
# MAGIC     on Base.component = summ_2017.component
# MAGIC         and Base.erly_srvc_month = summ_2017.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2018 as summ_2018
# MAGIC     on Base.component = summ_2018.component
# MAGIC         and Base.erly_srvc_month = summ_2018.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2019 as summ_2019
# MAGIC     on Base.component = summ_2019.component
# MAGIC         and Base.erly_srvc_month = summ_2019.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2020 as summ_2020
# MAGIC     on Base.component = summ_2020.component
# MAGIC         and Base.erly_srvc_month = summ_2020.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2021 as summ_2021
# MAGIC     on Base.component = summ_2021.component
# MAGIC         and Base.erly_srvc_month = summ_2021.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_2022 as summ_2022
# MAGIC     on Base.component = summ_2022.component
# MAGIC         and Base.erly_srvc_month = summ_2022.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_202310 as summ_202310
# MAGIC     on Base.component = summ_202310.component
# MAGIC         and Base.erly_srvc_month = summ_202310.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_202410 as summ_202410
# MAGIC     on Base.component = summ_202410.component
# MAGIC         and Base.erly_srvc_month = summ_202410.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_202512 as summ_202512
# MAGIC     on Base.component = summ_202512.component
# MAGIC         and Base.erly_srvc_month = summ_202512.erly_srvc_month
# MAGIC LEFT JOIN op_erly_summ_202607 as summ_202607
# MAGIC     on Base.component = summ_202607.component
# MAGIC         and Base.erly_srvc_month = summ_202607.erly_srvc_month
# MAGIC GROUP BY Base.component,
# MAGIC Base.erly_srvc_year;
# MAGIC
# MAGIC Select * from op_erly_summ_combined order by component,
# MAGIC erly_srvc_year

# COMMAND ----------

# DBTITLE 1,Inpatient Table Totals By Admit Year (Aligned 2018+)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_202607 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202607,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202607
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202607
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_202512 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202512,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202512
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202512
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_202410 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202410,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202410
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202410
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_202310 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202310,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202310
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202310
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2022 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2022,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2022
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2022
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2021 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2021,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2021
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2021
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2020 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2020,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2020
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2020
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2019 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2019,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2019
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2019
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2018 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2018,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2018
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2018
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2017 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2017,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2017
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2017
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2016 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2016,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2016
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2016
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2015 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2015,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2015
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2015
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_2014 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   extract(YEAR FROM admit_start_dt) as admit_year,
# MAGIC   admit_yr_month as admit_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2014,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2014
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2014
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC   AND denial_f = 'N'
# MAGIC   AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   admit_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   component,
# MAGIC   admit_year,
# MAGIC   admit_month
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_202607
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_202512
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_202410
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_202310
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2022
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2021
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2020
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2019
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2018
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2017
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2016
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2015
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       component,
# MAGIC       admit_year,
# MAGIC       admit_month
# MAGIC     FROM
# MAGIC       ip_admit_summ_2014
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_admit_summ_combined AS
# MAGIC SELECT
# MAGIC   Base.component,
# MAGIC   Base.admit_year,
# MAGIC   SUM(coalesce(summ_2014.net_pd_amt_2014, 0)) as net_pd_amt_2014,
# MAGIC   SUM(coalesce(summ_2015.net_pd_amt_2015, 0)) as net_pd_amt_2015,
# MAGIC   SUM(coalesce(summ_2016.net_pd_amt_2016, 0)) as net_pd_amt_2016,
# MAGIC   SUM(coalesce(summ_2017.net_pd_amt_2017, 0)) as net_pd_amt_2017,
# MAGIC   SUM(coalesce(summ_2018.net_pd_amt_2018, 0)) as net_pd_amt_2018,
# MAGIC   SUM(coalesce(summ_2019.net_pd_amt_2019, 0)) as net_pd_amt_2019,
# MAGIC   SUM(coalesce(summ_2020.net_pd_amt_2020, 0)) as net_pd_amt_2020,
# MAGIC   SUM(coalesce(summ_2021.net_pd_amt_2021, 0)) as net_pd_amt_2021,
# MAGIC   SUM(coalesce(summ_2022.net_pd_amt_2022, 0)) as net_pd_amt_2022,
# MAGIC   SUM(coalesce(summ_202310.net_pd_amt_202310, 0)) as net_pd_amt_202310,
# MAGIC   SUM(coalesce(summ_202410.net_pd_amt_202410, 0)) as net_pd_amt_202410,
# MAGIC   SUM(coalesce(summ_202512.net_pd_amt_202512, 0)) as net_pd_amt_202512,
# MAGIC   SUM(coalesce(summ_202607.net_pd_amt_202607, 0)) as net_pd_amt_202607,
# MAGIC   SUM(coalesce(summ_2014.allw_amt_2014, 0)) as allw_amt_2014,
# MAGIC   SUM(coalesce(summ_2015.allw_amt_2015, 0)) as allw_amt_2015,
# MAGIC   SUM(coalesce(summ_2016.allw_amt_2016, 0)) as allw_amt_2016,
# MAGIC   SUM(coalesce(summ_2017.allw_amt_2017, 0)) as allw_amt_2017,
# MAGIC   SUM(coalesce(summ_2018.allw_amt_2018, 0)) as allw_amt_2018,
# MAGIC   SUM(coalesce(summ_2019.allw_amt_2019, 0)) as allw_amt_2019,
# MAGIC   SUM(coalesce(summ_2020.allw_amt_2020, 0)) as allw_amt_2020,
# MAGIC   SUM(coalesce(summ_2021.allw_amt_2021, 0)) as allw_amt_2021,
# MAGIC   SUM(coalesce(summ_2022.allw_amt_2022, 0)) as allw_amt_2022,
# MAGIC   SUM(coalesce(summ_202310.allw_amt_202310, 0)) as allw_amt_202310,
# MAGIC   SUM(coalesce(summ_202410.allw_amt_202410, 0)) as allw_amt_202410,
# MAGIC   SUM(coalesce(summ_202512.allw_amt_202512, 0)) as allw_amt_202512,
# MAGIC   SUM(coalesce(summ_202607.allw_amt_202607, 0)) as allw_amt_202607
# MAGIC FROM
# MAGIC   ip_admit_summ_combined_1 as Base
# MAGIC     LEFT JOIN ip_admit_summ_2014 as summ_2014
# MAGIC       on Base.component = summ_2014.component
# MAGIC       and Base.admit_month = summ_2014.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2015 as summ_2015
# MAGIC       on Base.component = summ_2015.component
# MAGIC       and Base.admit_month = summ_2015.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2016 as summ_2016
# MAGIC       on Base.component = summ_2016.component
# MAGIC       and Base.admit_month = summ_2016.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2017 as summ_2017
# MAGIC       on Base.component = summ_2017.component
# MAGIC       and Base.admit_month = summ_2017.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2018 as summ_2018
# MAGIC       on Base.component = summ_2018.component
# MAGIC       and Base.admit_month = summ_2018.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2019 as summ_2019
# MAGIC       on Base.component = summ_2019.component
# MAGIC       and Base.admit_month = summ_2019.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2020 as summ_2020
# MAGIC       on Base.component = summ_2020.component
# MAGIC       and Base.admit_month = summ_2020.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2021 as summ_2021
# MAGIC       on Base.component = summ_2021.component
# MAGIC       and Base.admit_month = summ_2021.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_2022 as summ_2022
# MAGIC       on Base.component = summ_2022.component
# MAGIC       and Base.admit_month = summ_2022.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_202310 as summ_202310
# MAGIC       on Base.component = summ_202310.component
# MAGIC       and Base.admit_month = summ_202310.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_202410 as summ_202410
# MAGIC       on Base.component = summ_202410.component
# MAGIC       and Base.admit_month = summ_202410.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_202512 as summ_202512
# MAGIC       on Base.component = summ_202512.component
# MAGIC       and Base.admit_month = summ_202512.admit_month
# MAGIC     LEFT JOIN ip_admit_summ_202607 as summ_202607
# MAGIC       on Base.component = summ_202607.component
# MAGIC       and Base.admit_month = summ_202607.admit_month
# MAGIC GROUP BY
# MAGIC   Base.component,
# MAGIC   Base.admit_year;
# MAGIC
# MAGIC Select
# MAGIC   *
# MAGIC from
# MAGIC   ip_admit_summ_combined
# MAGIC order by
# MAGIC   component,
# MAGIC   admit_year

# COMMAND ----------

# DBTITLE 1,Rx Totals By Service Year (Aligned)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE rx_summ_curr AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   year(date_of_service) as service_year,
# MAGIC   year(date_of_service)*100+month(date_of_service) as service_month,
# MAGIC   SUM(coalesce(tadm_net_pd,0)) as net_pd_amt_curr,
# MAGIC   SUM(coalesce(tadm_allowed,0)) as allw_amt_curr,
# MAGIC   SUM(coalesce(rbt_billed_amt,0)+coalesce(rebate_accrual,0)) as rebates_curr,
# MAGIC   SUM(coalesce(rebate_accrual,0)) as rebate_accrual_curr,
# MAGIC   SUM(coalesce(rbt_billed_amt,0)) as rbt_billed_amt_curr
# MAGIC FROM
# MAGIC   prod_tadm.mard.m1_claims_f
# MAGIC WHERE
# MAGIC   tadm_global_cap = 'NA'
# MAGIC 	and migration_source <> 'OAH'
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   service_year,
# MAGIC   service_month
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   service_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE rx_summ_2020 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   year(date_of_service) as service_year,
# MAGIC   year(date_of_service)*100+month(date_of_service) as service_month,
# MAGIC   SUM(coalesce(tadm_net_pd,0)) as net_pd_amt_2020,
# MAGIC   SUM(coalesce(tadm_allowed,0)) as allw_amt_2020,
# MAGIC   SUM(0+coalesce(rebate_accrual,0)) as rebates_2020,
# MAGIC   SUM(coalesce(rebate_accrual,0)) as rebate_accrual_2020,
# MAGIC   SUM(0) as rbt_billed_amt_2020
# MAGIC FROM
# MAGIC   prod_tadm.mard.m1_claims_2020_f
# MAGIC WHERE
# MAGIC   tadm_global_cap = 'NA'
# MAGIC 	and migration_source <> 'OAH'
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   service_year,
# MAGIC   service_month
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   service_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE rx_summ_2019 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   year(date_of_service) as service_year,
# MAGIC   year(date_of_service)*100+month(date_of_service) as service_month,
# MAGIC   SUM(coalesce(tadm_net_pd,0)) as net_pd_amt_2019,
# MAGIC   SUM(coalesce(tadm_allowed,0)) as allw_amt_2019,
# MAGIC   SUM(0+coalesce(rebate_accrual,0)) as rebates_2019,
# MAGIC   SUM(coalesce(rebate_accrual,0)) as rebate_accrual_2019,
# MAGIC   SUM(0) as rbt_billed_amt_2019
# MAGIC FROM
# MAGIC   prod_tadm.mard.m1_claims_2019_f
# MAGIC WHERE
# MAGIC   tadm_global_cap = 'NA'
# MAGIC 	and migration_source <> 'OAH'
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   service_year,
# MAGIC   service_month
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   service_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE rx_summ_2018 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   year(date_of_service) as service_year,
# MAGIC   year(date_of_service)*100+month(date_of_service) as service_month,
# MAGIC   SUM(coalesce(tadm_net_pd,0)) as net_pd_amt_2018,
# MAGIC   SUM(coalesce(tadm_allowed,0)) as allw_amt_2018,
# MAGIC   SUM(0+coalesce(rebate_accrual,0)) as rebates_2018,
# MAGIC   SUM(coalesce(rebate_accrual,0)) as rebate_accrual_2018,
# MAGIC   SUM(0) as rbt_billed_amt_2018
# MAGIC FROM
# MAGIC   prod_tadm.mard.m1_claims_2018_f
# MAGIC WHERE
# MAGIC   tadm_global_cap = 'NA'
# MAGIC 	and migration_source <> 'OAH'
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   service_year,
# MAGIC   service_month
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   service_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE rx_summ_2017 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   year(date_of_service) as service_year,
# MAGIC   year(date_of_service)*100+month(date_of_service) as service_month,
# MAGIC   SUM(coalesce(tadm_net_pd,0)) as net_pd_amt_2017,
# MAGIC   SUM(coalesce(tadm_allowed,0)) as allw_amt_2017,
# MAGIC   SUM(0+coalesce(rebate_accrual,0)) as rebates_2017,
# MAGIC   SUM(coalesce(rebate_accrual,0)) as rebate_accrual_2017,
# MAGIC   SUM(0) as rbt_billed_amt_2017
# MAGIC FROM
# MAGIC   prod_tadm.mard.m1_claims_2017_f
# MAGIC WHERE
# MAGIC   tadm_global_cap = 'NA'
# MAGIC 	and migration_source <> 'OAH'
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   service_year,
# MAGIC   service_month
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   service_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE rx_summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   /*component,*/
# MAGIC   service_year,
# MAGIC   service_month
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       service_year,
# MAGIC       service_month
# MAGIC     FROM rx_summ_curr
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       service_year,
# MAGIC       service_month
# MAGIC     FROM rx_summ_2020
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       service_year,
# MAGIC       service_month
# MAGIC     FROM rx_summ_2019
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       service_year,
# MAGIC       service_month
# MAGIC     FROM rx_summ_2018
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       service_year,
# MAGIC       service_month
# MAGIC     FROM rx_summ_2017
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE rx_summ_combined AS
# MAGIC SELECT /*Base.component,*/
# MAGIC Base.service_year,
# MAGIC SUM(coalesce(rx_summ_2017.net_pd_amt_2017,0)) as net_pd_amt_2017,
# MAGIC SUM(coalesce(rx_summ_2018.net_pd_amt_2018,0)) as net_pd_amt_2018,
# MAGIC SUM(coalesce(rx_summ_2019.net_pd_amt_2019,0)) as net_pd_amt_2019,
# MAGIC SUM(coalesce(rx_summ_2020.net_pd_amt_2020,0)) as net_pd_amt_2020,
# MAGIC SUM(coalesce(rx_summ_curr.net_pd_amt_curr,0)) as net_pd_amt_curr,
# MAGIC SUM(coalesce(rx_summ_2017.allw_amt_2017,0)) as allw_amt_2017,
# MAGIC SUM(coalesce(rx_summ_2018.allw_amt_2018,0)) as allw_amt_2018,
# MAGIC SUM(coalesce(rx_summ_2019.allw_amt_2019,0)) as allw_amt_2019,
# MAGIC SUM(coalesce(rx_summ_2020.allw_amt_2020,0)) as allw_amt_2020,
# MAGIC SUM(coalesce(rx_summ_curr.allw_amt_curr,0)) as allw_amt_curr,
# MAGIC SUM(coalesce(rx_summ_2017.rebates_2017,0)) as rebates_2017,
# MAGIC SUM(coalesce(rx_summ_2018.rebates_2018,0)) as rebates_2018,
# MAGIC SUM(coalesce(rx_summ_2019.rebates_2019,0)) as rebates_2019,
# MAGIC SUM(coalesce(rx_summ_2020.rebates_2020,0)) as rebates_2020,
# MAGIC SUM(coalesce(rx_summ_curr.rebates_curr,0)) as rebates_curr,
# MAGIC SUM(coalesce(rx_summ_2017.rebate_accrual_2017,0)) as rebate_accrual_2017,
# MAGIC SUM(coalesce(rx_summ_2018.rebate_accrual_2018,0)) as rebate_accrual_2018,
# MAGIC SUM(coalesce(rx_summ_2019.rebate_accrual_2019,0)) as rebate_accrual_2019,
# MAGIC SUM(coalesce(rx_summ_2020.rebate_accrual_2020,0)) as rebate_accrual_2020,
# MAGIC SUM(coalesce(rx_summ_curr.rebate_accrual_curr,0)) as rebate_accrual_curr,
# MAGIC SUM(coalesce(rx_summ_2017.rbt_billed_amt_2017,0)) as rbt_billed_amt_2017,
# MAGIC SUM(coalesce(rx_summ_2018.rbt_billed_amt_2018,0)) as rbt_billed_amt_2018,
# MAGIC SUM(coalesce(rx_summ_2019.rbt_billed_amt_2019,0)) as rbt_billed_amt_2019,
# MAGIC SUM(coalesce(rx_summ_2020.rbt_billed_amt_2020,0)) as rbt_billed_amt_2020,
# MAGIC SUM(coalesce(rx_summ_curr.rbt_billed_amt_curr,0)) as rbt_billed_amt_curr
# MAGIC FROM rx_summ_combined_1 as Base
# MAGIC LEFT JOIN rx_summ_2017 as rx_summ_2017
# MAGIC     on /*Base.component = rx_summ_2017.component
# MAGIC         and*/ Base.service_month = rx_summ_2017.service_month
# MAGIC LEFT JOIN rx_summ_2018 as rx_summ_2018
# MAGIC     on /*Base.component = rx_summ_2018.component
# MAGIC         and*/ Base.service_month = rx_summ_2018.service_month
# MAGIC LEFT JOIN rx_summ_2019 as rx_summ_2019
# MAGIC     on /*Base.component = rx_summ_2019.component
# MAGIC         and*/ Base.service_month = rx_summ_2019.service_month
# MAGIC LEFT JOIN rx_summ_2020 as rx_summ_2020
# MAGIC     on /*Base.component = rx_summ_2020.component
# MAGIC         and*/ Base.service_month = rx_summ_2020.service_month
# MAGIC LEFT JOIN rx_summ_curr as rx_summ_curr
# MAGIC     on /*Base.component = rx_summ_curr.component
# MAGIC         and*/ Base.service_month = rx_summ_curr.service_month
# MAGIC GROUP BY /*Base.component,*/
# MAGIC Base.service_year;
# MAGIC
# MAGIC Select * from rx_summ_combined order by /*component,*/
# MAGIC service_year

# COMMAND ----------

# DBTITLE 1,Membership Totals By Financial Year (Aligned)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_202607 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_202607
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_202607
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_202512 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_202512
# MAGIC FROM prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_202512
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_202410 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_202410
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_202410
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_202310 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_202310
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_202310
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2022 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2022
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2022
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2021 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2021
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2021
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2020 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2020
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2020
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2019 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2019
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2019
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2018 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2018
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2018
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2017 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2017
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2017
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2016 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2016
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2016
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2015 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2015
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2015
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_2014 AS
# MAGIC SELECT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH,
# MAGIC   SUM(FIN_MEMBER_CNT) AS FIN_MEMBER_CNT_2014
# MAGIC FROM
# MAGIC   prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2014
# MAGIC WHERE
# MAGIC   migration_source <> ('OAH')
# MAGIC 	AND global_cap = 'NA'
# MAGIC 	AND fin_source_name = 'COSMOS'
# MAGIC 	/*AND fin_tfm_product_new NOT IN ('PEOPLES HEALTH')*/
# MAGIC 	and sgr_source_name = 'COSMOS'
# MAGIC GROUP BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC ORDER BY
# MAGIC   /*component,*/
# MAGIC   FIN_INC_MONTH;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR,
# MAGIC   FIN_INC_MONTH
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_202607
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_202512
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_202410
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_202310
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2022
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2021
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2020
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2019
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2018
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2017
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2016
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2015
# MAGIC     UNION
# MAGIC     SELECT
# MAGIC       /*component,*/
# MAGIC       FIN_INC_YEAR,
# MAGIC       FIN_INC_MONTH
# MAGIC     FROM
# MAGIC       mbr_summ_2014
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE mbr_summ_combined AS
# MAGIC SELECT
# MAGIC   /*Base.component,*/
# MAGIC   Base.FIN_INC_YEAR,
# MAGIC   SUM(coalesce(summ_2014.FIN_MEMBER_CNT_2014, 0)) as FIN_MEMBER_CNT_2014,
# MAGIC   SUM(coalesce(summ_2015.FIN_MEMBER_CNT_2015, 0)) as FIN_MEMBER_CNT_2015,
# MAGIC   SUM(coalesce(summ_2016.FIN_MEMBER_CNT_2016, 0)) as FIN_MEMBER_CNT_2016,
# MAGIC   SUM(coalesce(summ_2017.FIN_MEMBER_CNT_2017, 0)) as FIN_MEMBER_CNT_2017,
# MAGIC   SUM(coalesce(summ_2018.FIN_MEMBER_CNT_2018, 0)) as FIN_MEMBER_CNT_2018,
# MAGIC   SUM(coalesce(summ_2019.FIN_MEMBER_CNT_2019, 0)) as FIN_MEMBER_CNT_2019,
# MAGIC   SUM(coalesce(summ_2020.FIN_MEMBER_CNT_2020, 0)) as FIN_MEMBER_CNT_2020,
# MAGIC   SUM(coalesce(summ_2021.FIN_MEMBER_CNT_2021, 0)) as FIN_MEMBER_CNT_2021,
# MAGIC   SUM(coalesce(summ_2022.FIN_MEMBER_CNT_2022, 0)) as FIN_MEMBER_CNT_2022,
# MAGIC   SUM(coalesce(summ_202310.FIN_MEMBER_CNT_202310, 0)) as FIN_MEMBER_CNT_202310,
# MAGIC   SUM(coalesce(summ_202410.FIN_MEMBER_CNT_202410, 0)) as FIN_MEMBER_CNT_202410,
# MAGIC   SUM(coalesce(summ_202512.FIN_MEMBER_CNT_202512, 0)) as FIN_MEMBER_CNT_202512,
# MAGIC   SUM(coalesce(summ_202607.FIN_MEMBER_CNT_202607, 0)) as FIN_MEMBER_CNT_202607
# MAGIC FROM
# MAGIC   mbr_summ_combined_1 as Base
# MAGIC     LEFT JOIN mbr_summ_2014 as summ_2014
# MAGIC       on /*Base.component = summ_2014.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2014.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2015 as summ_2015
# MAGIC       on /*Base.component = summ_2015.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2015.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2016 as summ_2016
# MAGIC       on /*Base.component = summ_2016.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2016.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2017 as summ_2017
# MAGIC       on /*Base.component = summ_2017.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2017.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2018 as summ_2018
# MAGIC       on /*Base.component = summ_2018.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2018.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2019 as summ_2019
# MAGIC       on /*Base.component = summ_2019.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2019.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2020 as summ_2020
# MAGIC       on /*Base.component = summ_2020.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2020.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2021 as summ_2021
# MAGIC       on /*Base.component = summ_2021.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2021.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_2022 as summ_2022
# MAGIC       on /*Base.component = summ_2022.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_2022.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_202310 as summ_202310
# MAGIC       on /*Base.component = summ_202310.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_202310.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_202410 as summ_202410
# MAGIC       on /*Base.component = summ_202410.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_202410.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_202512 as summ_202512
# MAGIC       on /*Base.component = summ_202512.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_202512.FIN_INC_MONTH
# MAGIC     LEFT JOIN mbr_summ_202607 as summ_202607
# MAGIC       on /*Base.component = summ_202607.component
# MAGIC       and*/ Base.FIN_INC_MONTH = summ_202607.FIN_INC_MONTH
# MAGIC GROUP BY
# MAGIC   /*Base.component,*/
# MAGIC   Base.FIN_INC_YEAR;
# MAGIC
# MAGIC Select
# MAGIC   *
# MAGIC from
# MAGIC   mbr_summ_combined
# MAGIC order by
# MAGIC   /*component,*/
# MAGIC   FIN_INC_YEAR

# COMMAND ----------

# MAGIC %md
# MAGIC Claims and Membership Recon By Year -- Not Aligned

# COMMAND ----------

# DBTITLE 1,Outpatient Table Totals By First Service Year (Not Aligned)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_202607 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202607,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202607
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202607
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_202512 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202512,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202512
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202512
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_202410 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202410,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202410
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202410
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_202310 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202310,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202310
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_202310
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2022 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2022,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2022
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2022
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2021 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2021,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2021
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2021
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2020 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2020,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2020
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2020
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2019 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2019,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2019
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2019
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2018 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2018,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2018
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2018
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2017 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2017,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2017
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2017
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2016 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2016,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2016
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2016
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC   CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2015 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2015,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2015
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2015
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_2014 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2014,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2014
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_op_f_2014
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND hce_service_code NOT IN ('OP_CLM_DNL','OP_DWNADJ_DNL')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_202607
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_202512
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_202410
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_202310
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2022
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2021
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2020
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2019
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2018
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2017
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2016
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2015
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM op_fst_summ_2014
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE op_fst_summ_combined AS
# MAGIC SELECT Base.component,
# MAGIC Base.fst_srvc_year,
# MAGIC SUM(coalesce(summ_2014.net_pd_amt_2014,0)) as net_pd_amt_2014,
# MAGIC SUM(coalesce(summ_2015.net_pd_amt_2015,0)) as net_pd_amt_2015,
# MAGIC SUM(coalesce(summ_2016.net_pd_amt_2016,0)) as net_pd_amt_2016,
# MAGIC SUM(coalesce(summ_2017.net_pd_amt_2017,0)) as net_pd_amt_2017,
# MAGIC SUM(coalesce(summ_2018.net_pd_amt_2018,0)) as net_pd_amt_2018,
# MAGIC SUM(coalesce(summ_2019.net_pd_amt_2019,0)) as net_pd_amt_2019,
# MAGIC SUM(coalesce(summ_2020.net_pd_amt_2020,0)) as net_pd_amt_2020,
# MAGIC SUM(coalesce(summ_2021.net_pd_amt_2021,0)) as net_pd_amt_2021,
# MAGIC SUM(coalesce(summ_2022.net_pd_amt_2022,0)) as net_pd_amt_2022,
# MAGIC SUM(coalesce(summ_202310.net_pd_amt_202310,0)) as net_pd_amt_202310,
# MAGIC SUM(coalesce(summ_202410.net_pd_amt_202410,0)) as net_pd_amt_202410,
# MAGIC SUM(coalesce(summ_202512.net_pd_amt_202512,0)) as net_pd_amt_202512,
# MAGIC SUM(coalesce(summ_202607.net_pd_amt_202607,0)) as net_pd_amt_202607,
# MAGIC SUM(coalesce(summ_2014.allw_amt_2014,0)) as allw_amt_2014,
# MAGIC SUM(coalesce(summ_2015.allw_amt_2015,0)) as allw_amt_2015,
# MAGIC SUM(coalesce(summ_2016.allw_amt_2016,0)) as allw_amt_2016,
# MAGIC SUM(coalesce(summ_2017.allw_amt_2017,0)) as allw_amt_2017,
# MAGIC SUM(coalesce(summ_2018.allw_amt_2018,0)) as allw_amt_2018,
# MAGIC SUM(coalesce(summ_2019.allw_amt_2019,0)) as allw_amt_2019,
# MAGIC SUM(coalesce(summ_2020.allw_amt_2020,0)) as allw_amt_2020,
# MAGIC SUM(coalesce(summ_2021.allw_amt_2021,0)) as allw_amt_2021,
# MAGIC SUM(coalesce(summ_2022.allw_amt_2022,0)) as allw_amt_2022,
# MAGIC SUM(coalesce(summ_202310.allw_amt_202310,0)) as allw_amt_202310,
# MAGIC SUM(coalesce(summ_202410.allw_amt_202410,0)) as allw_amt_202410,
# MAGIC SUM(coalesce(summ_202512.allw_amt_202512,0)) as allw_amt_202512,
# MAGIC SUM(coalesce(summ_202607.allw_amt_202607,0)) as allw_amt_202607
# MAGIC FROM op_fst_summ_combined_1 as Base
# MAGIC LEFT JOIN op_fst_summ_2014 as summ_2014
# MAGIC     on Base.component = summ_2014.component
# MAGIC         and Base.fst_srvc_month = summ_2014.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2015 as summ_2015
# MAGIC     on Base.component = summ_2015.component
# MAGIC         and Base.fst_srvc_month = summ_2015.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2016 as summ_2016
# MAGIC     on Base.component = summ_2016.component
# MAGIC         and Base.fst_srvc_month = summ_2016.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2017 as summ_2017
# MAGIC     on Base.component = summ_2017.component
# MAGIC         and Base.fst_srvc_month = summ_2017.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2018 as summ_2018
# MAGIC     on Base.component = summ_2018.component
# MAGIC         and Base.fst_srvc_month = summ_2018.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2019 as summ_2019
# MAGIC     on Base.component = summ_2019.component
# MAGIC         and Base.fst_srvc_month = summ_2019.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2020 as summ_2020
# MAGIC     on Base.component = summ_2020.component
# MAGIC         and Base.fst_srvc_month = summ_2020.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2021 as summ_2021
# MAGIC     on Base.component = summ_2021.component
# MAGIC         and Base.fst_srvc_month = summ_2021.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_2022 as summ_2022
# MAGIC     on Base.component = summ_2022.component
# MAGIC         and Base.fst_srvc_month = summ_2022.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_202310 as summ_202310
# MAGIC     on Base.component = summ_202310.component
# MAGIC         and Base.fst_srvc_month = summ_202310.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_202410 as summ_202410
# MAGIC     on Base.component = summ_202410.component
# MAGIC         and Base.fst_srvc_month = summ_202410.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_202512 as summ_202512
# MAGIC     on Base.component = summ_202512.component
# MAGIC         and Base.fst_srvc_month = summ_202512.fst_srvc_month
# MAGIC LEFT JOIN op_fst_summ_202607 as summ_202607
# MAGIC     on Base.component = summ_202607.component
# MAGIC         and Base.fst_srvc_month = summ_202607.fst_srvc_month
# MAGIC GROUP BY Base.component,
# MAGIC Base.fst_srvc_year;
# MAGIC
# MAGIC Select * from op_fst_summ_combined order by component,
# MAGIC fst_srvc_year

# COMMAND ----------

# DBTITLE 1,Inpatient Table Totals By First Service Year (Not Aligned)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_202607 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202607,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202607
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202607
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_202512 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202512,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202512
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202512
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_202410 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202410,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202410
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202410
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_202310 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202310,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202310
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202310
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2022 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2022,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2022
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2022
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2021 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2021,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2021
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2021
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2020 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2020,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2020
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2020
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2019 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2019,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2019
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2019
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2018 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2018,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2018
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2018
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2017 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2017,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2017
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2017
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2016 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2016,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2016
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2016
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC   CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2015 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2015,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2015
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2015
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_2014 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2014,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2014
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2014
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   fst_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   component,
# MAGIC   fst_srvc_year,
# MAGIC   fst_srvc_month
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_202607
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_202512
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_202410
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_202310
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2022
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2021
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2020
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2019
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2018
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2017
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2016
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2015
# MAGIC     UNION
# MAGIC     SELECT component, fst_srvc_year, fst_srvc_month
# MAGIC     FROM ip_fst_summ_2014
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_fst_summ_combined AS
# MAGIC SELECT Base.component,
# MAGIC Base.fst_srvc_year,
# MAGIC SUM(coalesce(summ_2014.net_pd_amt_2014,0)) as net_pd_amt_2014,
# MAGIC SUM(coalesce(summ_2015.net_pd_amt_2015,0)) as net_pd_amt_2015,
# MAGIC SUM(coalesce(summ_2016.net_pd_amt_2016,0)) as net_pd_amt_2016,
# MAGIC SUM(coalesce(summ_2017.net_pd_amt_2017,0)) as net_pd_amt_2017,
# MAGIC SUM(coalesce(summ_2018.net_pd_amt_2018,0)) as net_pd_amt_2018,
# MAGIC SUM(coalesce(summ_2019.net_pd_amt_2019,0)) as net_pd_amt_2019,
# MAGIC SUM(coalesce(summ_2020.net_pd_amt_2020,0)) as net_pd_amt_2020,
# MAGIC SUM(coalesce(summ_2021.net_pd_amt_2021,0)) as net_pd_amt_2021,
# MAGIC SUM(coalesce(summ_2022.net_pd_amt_2022,0)) as net_pd_amt_2022,
# MAGIC SUM(coalesce(summ_202310.net_pd_amt_202310,0)) as net_pd_amt_202310,
# MAGIC SUM(coalesce(summ_202410.net_pd_amt_202410,0)) as net_pd_amt_202410,
# MAGIC SUM(coalesce(summ_202512.net_pd_amt_202512,0)) as net_pd_amt_202512,
# MAGIC SUM(coalesce(summ_202607.net_pd_amt_202607,0)) as net_pd_amt_202607,
# MAGIC SUM(coalesce(summ_2014.allw_amt_2014,0)) as allw_amt_2014,
# MAGIC SUM(coalesce(summ_2015.allw_amt_2015,0)) as allw_amt_2015,
# MAGIC SUM(coalesce(summ_2016.allw_amt_2016,0)) as allw_amt_2016,
# MAGIC SUM(coalesce(summ_2017.allw_amt_2017,0)) as allw_amt_2017,
# MAGIC SUM(coalesce(summ_2018.allw_amt_2018,0)) as allw_amt_2018,
# MAGIC SUM(coalesce(summ_2019.allw_amt_2019,0)) as allw_amt_2019,
# MAGIC SUM(coalesce(summ_2020.allw_amt_2020,0)) as allw_amt_2020,
# MAGIC SUM(coalesce(summ_2021.allw_amt_2021,0)) as allw_amt_2021,
# MAGIC SUM(coalesce(summ_2022.allw_amt_2022,0)) as allw_amt_2022,
# MAGIC SUM(coalesce(summ_202310.allw_amt_202310,0)) as allw_amt_202310,
# MAGIC SUM(coalesce(summ_202410.allw_amt_202410,0)) as allw_amt_202410,
# MAGIC SUM(coalesce(summ_202512.allw_amt_202512,0)) as allw_amt_202512,
# MAGIC SUM(coalesce(summ_202607.allw_amt_202607,0)) as allw_amt_202607
# MAGIC FROM ip_fst_summ_combined_1 as Base
# MAGIC LEFT JOIN ip_fst_summ_2014 as summ_2014
# MAGIC     on Base.component = summ_2014.component
# MAGIC         and Base.fst_srvc_month = summ_2014.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2015 as summ_2015
# MAGIC     on Base.component = summ_2015.component
# MAGIC         and Base.fst_srvc_month = summ_2015.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2016 as summ_2016
# MAGIC     on Base.component = summ_2016.component
# MAGIC         and Base.fst_srvc_month = summ_2016.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2017 as summ_2017
# MAGIC     on Base.component = summ_2017.component
# MAGIC         and Base.fst_srvc_month = summ_2017.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2018 as summ_2018
# MAGIC     on Base.component = summ_2018.component
# MAGIC         and Base.fst_srvc_month = summ_2018.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2019 as summ_2019
# MAGIC     on Base.component = summ_2019.component
# MAGIC         and Base.fst_srvc_month = summ_2019.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2020 as summ_2020
# MAGIC     on Base.component = summ_2020.component
# MAGIC         and Base.fst_srvc_month = summ_2020.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2021 as summ_2021
# MAGIC     on Base.component = summ_2021.component
# MAGIC         and Base.fst_srvc_month = summ_2021.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_2022 as summ_2022
# MAGIC     on Base.component = summ_2022.component
# MAGIC         and Base.fst_srvc_month = summ_2022.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_202310 as summ_202310
# MAGIC     on Base.component = summ_202310.component
# MAGIC         and Base.fst_srvc_month = summ_202310.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_202410 as summ_202410
# MAGIC     on Base.component = summ_202410.component
# MAGIC         and Base.fst_srvc_month = summ_202410.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_202512 as summ_202512
# MAGIC     on Base.component = summ_202512.component
# MAGIC         and Base.fst_srvc_month = summ_202512.fst_srvc_month
# MAGIC LEFT JOIN ip_fst_summ_202607 as summ_202607
# MAGIC     on Base.component = summ_202607.component
# MAGIC         and Base.fst_srvc_month = summ_202607.fst_srvc_month
# MAGIC GROUP BY Base.component,
# MAGIC Base.fst_srvc_year;
# MAGIC
# MAGIC Select * from ip_fst_summ_combined order by component,
# MAGIC fst_srvc_year

# COMMAND ----------

# DBTITLE 1,Inpatient Table Totals By Early Service Year (Not Aligned)
# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_202607 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202607,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202607
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202607
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_202512 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202512,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202512
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202512
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_202410 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202410,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202410
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202410
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_202310 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_202310,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_202310
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202310
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2022 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2022,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2022
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2022
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2021 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2021,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2021
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2021
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2020 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2020,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2020
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2020
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2019 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2019,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2019
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2019
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2018 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2018,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2018
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2018
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2017 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2017,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2017
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2017
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2016 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2016,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2016
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2016
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC   CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2015 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2015,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2015
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2015
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_2014 AS
# MAGIC SELECT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month,
# MAGIC   SUM(net_pd_amt_fnl) as net_pd_amt_2014,
# MAGIC   SUM(allw_amt_fnl) as allw_amt_2014
# MAGIC FROM prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2014
# MAGIC WHERE
# MAGIC   migration_source NOT IN ('OAH')
# MAGIC     AND denial_f = 'N'
# MAGIC     AND tadm_admit_type NOT IN ('OTH')
# MAGIC GROUP BY
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC ORDER BY
# MAGIC   component,
# MAGIC   erly_srvc_month;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_combined_1 AS
# MAGIC SELECT DISTINCT
# MAGIC   component,
# MAGIC   erly_srvc_year,
# MAGIC   erly_srvc_month
# MAGIC FROM
# MAGIC   (
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_202607
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_202512
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_202410
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_202310
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2022
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2021
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2020
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2019
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2018
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2017
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2016
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2015
# MAGIC     UNION
# MAGIC     SELECT component, erly_srvc_year, erly_srvc_month
# MAGIC     FROM ip_erly_summ_2014
# MAGIC   ) as UnionBase;
# MAGIC
# MAGIC CREATE OR REPLACE TEMPORARY TABLE ip_erly_summ_combined AS
# MAGIC SELECT Base.component,
# MAGIC Base.erly_srvc_year,
# MAGIC SUM(coalesce(summ_2014.net_pd_amt_2014,0)) as net_pd_amt_2014,
# MAGIC SUM(coalesce(summ_2015.net_pd_amt_2015,0)) as net_pd_amt_2015,
# MAGIC SUM(coalesce(summ_2016.net_pd_amt_2016,0)) as net_pd_amt_2016,
# MAGIC SUM(coalesce(summ_2017.net_pd_amt_2017,0)) as net_pd_amt_2017,
# MAGIC SUM(coalesce(summ_2018.net_pd_amt_2018,0)) as net_pd_amt_2018,
# MAGIC SUM(coalesce(summ_2019.net_pd_amt_2019,0)) as net_pd_amt_2019,
# MAGIC SUM(coalesce(summ_2020.net_pd_amt_2020,0)) as net_pd_amt_2020,
# MAGIC SUM(coalesce(summ_2021.net_pd_amt_2021,0)) as net_pd_amt_2021,
# MAGIC SUM(coalesce(summ_2022.net_pd_amt_2022,0)) as net_pd_amt_2022,
# MAGIC SUM(coalesce(summ_202310.net_pd_amt_202310,0)) as net_pd_amt_202310,
# MAGIC SUM(coalesce(summ_202410.net_pd_amt_202410,0)) as net_pd_amt_202410,
# MAGIC SUM(coalesce(summ_202512.net_pd_amt_202512,0)) as net_pd_amt_202512,
# MAGIC SUM(coalesce(summ_202607.net_pd_amt_202607,0)) as net_pd_amt_202607,
# MAGIC SUM(coalesce(summ_2014.allw_amt_2014,0)) as allw_amt_2014,
# MAGIC SUM(coalesce(summ_2015.allw_amt_2015,0)) as allw_amt_2015,
# MAGIC SUM(coalesce(summ_2016.allw_amt_2016,0)) as allw_amt_2016,
# MAGIC SUM(coalesce(summ_2017.allw_amt_2017,0)) as allw_amt_2017,
# MAGIC SUM(coalesce(summ_2018.allw_amt_2018,0)) as allw_amt_2018,
# MAGIC SUM(coalesce(summ_2019.allw_amt_2019,0)) as allw_amt_2019,
# MAGIC SUM(coalesce(summ_2020.allw_amt_2020,0)) as allw_amt_2020,
# MAGIC SUM(coalesce(summ_2021.allw_amt_2021,0)) as allw_amt_2021,
# MAGIC SUM(coalesce(summ_2022.allw_amt_2022,0)) as allw_amt_2022,
# MAGIC SUM(coalesce(summ_202310.allw_amt_202310,0)) as allw_amt_202310,
# MAGIC SUM(coalesce(summ_202410.allw_amt_202410,0)) as allw_amt_202410,
# MAGIC SUM(coalesce(summ_202512.allw_amt_202512,0)) as allw_amt_202512,
# MAGIC SUM(coalesce(summ_202607.allw_amt_202607,0)) as allw_amt_202607
# MAGIC FROM ip_erly_summ_combined_1 as Base
# MAGIC LEFT JOIN ip_erly_summ_2014 as summ_2014
# MAGIC     on Base.component = summ_2014.component
# MAGIC         and Base.erly_srvc_month = summ_2014.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2015 as summ_2015
# MAGIC     on Base.component = summ_2015.component
# MAGIC         and Base.erly_srvc_month = summ_2015.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2016 as summ_2016
# MAGIC     on Base.component = summ_2016.component
# MAGIC         and Base.erly_srvc_month = summ_2016.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2017 as summ_2017
# MAGIC     on Base.component = summ_2017.component
# MAGIC         and Base.erly_srvc_month = summ_2017.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2018 as summ_2018
# MAGIC     on Base.component = summ_2018.component
# MAGIC         and Base.erly_srvc_month = summ_2018.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2019 as summ_2019
# MAGIC     on Base.component = summ_2019.component
# MAGIC         and Base.erly_srvc_month = summ_2019.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2020 as summ_2020
# MAGIC     on Base.component = summ_2020.component
# MAGIC         and Base.erly_srvc_month = summ_2020.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2021 as summ_2021
# MAGIC     on Base.component = summ_2021.component
# MAGIC         and Base.erly_srvc_month = summ_2021.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_2022 as summ_2022
# MAGIC     on Base.component = summ_2022.component
# MAGIC         and Base.erly_srvc_month = summ_2022.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_202310 as summ_202310
# MAGIC     on Base.component = summ_202310.component
# MAGIC         and Base.erly_srvc_month = summ_202310.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_202410 as summ_202410
# MAGIC     on Base.component = summ_202410.component
# MAGIC         and Base.erly_srvc_month = summ_202410.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_202512 as summ_202512
# MAGIC     on Base.component = summ_202512.component
# MAGIC         and Base.erly_srvc_month = summ_202512.erly_srvc_month
# MAGIC LEFT JOIN ip_erly_summ_202607 as summ_202607
# MAGIC     on Base.component = summ_202607.component
# MAGIC         and Base.erly_srvc_month = summ_202607.erly_srvc_month
# MAGIC GROUP BY Base.component,
# MAGIC Base.erly_srvc_year;
# MAGIC
# MAGIC Select * from ip_erly_summ_combined order by component,
# MAGIC erly_srvc_year
