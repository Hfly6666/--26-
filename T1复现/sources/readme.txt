Disclosure plan
We agree with immediate disclosure of code and data with publication. 
Data description (experiment)
Dataset "df_test.csv": 
Dataset description: a subset of data (3000 SKUs) that used for testing the various inventory replenishment model performance in the offline experiment.
Dataset dictionary: 
“SKU”: disguised SKU ID
“demand_mean”: average demand of the SKU
“demand_std”: standard deviation of demand of the SKU
“review_period”: item review period 
“vendor_vlt_mean”: average vendor lead time 
“vendor_vlt_std”: standard deviation of vendor lead time 
“initial_stock”: initial inventory level
“demand_hist”: historical demand 
“OPT_pred”: offline optimal solution given the realized demand and vlt in the test period
“E2E_RNN_pred”: replenishment quantity predicted by the proposed E2E model
“gbm_pred_pred”: replenishment quantity predicted by the LightGBM model
“sf_rnn”: demand forecasting series outputted by the proposed E2E model
“vlt”: vlt forecast outputted by the proposed E2E model
The original dataset has the same dictionaries.
Disguise process: desensitization of the SKU ID. We also randomly sample a subset of 3000 SKU from the original dataset because the original dataset is too large to disclose. 
Datasets “order_e2e_post_500.csv”, “order_e2e_post_500.csv”, “order_e2e_post_500.csv” and “order_e2e_post_500.csv”.
Dataset description: “order_e2e_post_500.csv” and “order_e2e_post_500.csv” include post- and pre- experiment results, respectively, for a subset of the treatment group (500 SKU-DC pairs). “order_e2e_post_500.csv” and “order_e2e_post_500.csv” include post- and pre- experiment results, respectively, for a subset (500 SKU-DC pairs) of the control group. Note that the control group has been selected from all candidate SKU-DC pairs in the same category by propensity score matching.
Data dictionary: 
“sku_dc_pair_index”: desensitized index for each of the (SKU, DC) pair
“complete_tm”: order complete time
“order_amount”: order amount (replenishment quantities)
“test_inv”: inventory curve within test period
“test_demand”: demand observations within test period
“ave_demand”: average demand
“ave_inv”: average inventory level
“vlt”: vendor lead time
“vlt_num”: extracted value of vendor lead time
Dataset dictionaries of original datasets:
Two columns “SKU_id”:  SKU ID and “DC”: distribution center ID instead of “sku_dc_pair_index”.
Other columns are the same as the disguised dataset
Disguise process: The sku_dc_pair_index has been desensitized to disguise the original SKU name and DC ID. We randomly sampled 500 (SKU,DC) pairs for the treatment group because the original dataset is too large to be disclosed.
Dataset “control_demand_vlt.csv”：
Dataset discerption:  These (SKU, DC) pairs are all candidate pairs that can be selected as the control group. The propensity score matching are performed on this dataset to select a control group to reduce the potential selection bias.
Dataset dictionary:
Index: (SKU, DC) pair index
“ave_demand”: average demand
“vlt_num”: vendor lead time value 
Dataset dictionaries of original datasets:
Two additional columns “SKU_id”:  SKU ID and “DC”: distribution center ID 
Other columns are the same as the disguised dataset
Disguise process: we desensitized the original SKU name and DC ID and give each (SKU, DC) pair an index. 
Data description (model)
Dataset "rdc_sales_1320.csv": 
Dataset description: a disguised example data set (5 SKU-DC pairs) for daily sales. 
Dataset dictionary: 
“row”: disguised SKU-DC ID (format: SKU_ID#DC_ID)
Other than “row”, the following columns represents daily sales data. The index of each column was converted to date-time format in “data_parser.py”.
The original dataset has the same dictionaries.
Disguise process: desensitization of the SKU ID and DC ID. We also randomly sample a subset of 5 SKU from the original dataset to give an example. 
Dataset “stock.csv”:
Dataset description: “stock.csv” is a disguised example data set for stock levels in the warehouse. 
Data dictionary: 
“item_sku_id”: disguised SKU-DC ID (format: SKU_ID#DC_ID)
Other than “row”, the following columns represents daily stock-level data. Each column is indexed with date. 
The original dataset includes longer record of stock level. The provided data set is trimmed to one month. 
Disguise process: desensitization of the SKU ID and DC ID. 2 SKUs are randomly picked from the original dataset and is trimmed to be one-month long.
Dataset “vlt_2019_0305.csv”：
Dataset discerption: a disguised example dataset for vendor lead time. 
Dataset dictionary:
“item_sku_id”: disguised SKU- ID 
“int_org_num”: disguised DC-ID
“pur_bill_id”: purchase bill ID.
“create_tm” and “complete_tm”: create time and complete time.
“vlt_actual”: actual vendor lead time (equals to complete time – create time).
“actual_pur_qtty”: actual purchase quantity.
“item_first_cate_cd”, “item_second_cate_cd”, “item_third_cate_cd”: item first, second, and third category ID.
“brand_code”: brand code.
“create_day_of_week”: create day of the week.
Disguised volumn names for three groups of features: item dimension information (e.g. weight, height, length), item-wise and vendor-wise historical VLT statistics (e.g. averaged VLT over certain time window, standard deviation of VLT ), statistics of item historical purchase quantities (e.g. averaged purchase quantity over certain time windows).
Dataset dictionaries of original datasets:
More column corresponding to item dimension information, item-wise and vendor-wise historical VLT statistics. The column names should be consistent with “VLT_FEA” defined in config/config.py
Other columns are the same as the disguised dataset
Disguise process: we desensitized the original SKU name and DC ID and remove confidential column names. The data set contains on SKU-DC pair as an example. 
