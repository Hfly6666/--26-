"""Build a self-contained Chinese HTML report from freshly computed artifacts."""
from pathlib import Path
import json,base64,html,hashlib,zipfile,shutil,sys
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
ROOT=Path(__file__).resolve().parent;R=ROOT/'results';O=ROOT/'output';F=O/'figures'
F.mkdir(parents=True,exist_ok=True)
for p in [Path('C:/Windows/Fonts/msyh.ttc'),Path('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')]:
 if p.exists():fontManager.addfont(str(p));plt.rcParams['font.family']=FontProperties(fname=str(p)).get_name();break
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,'figure.facecolor':'white','savefig.facecolor':'white'})
NAVY='#15364b';TEAL='#147c80';GOLD='#d7993d';RED='#b44e43';GRAY='#758899'
def load(n):return json.loads((R/n).read_text(encoding='utf-8'))
def esc(s):return html.escape(str(s))
def num(x,d=2):return f'{x:,.{d}f}'
def pv(x):return f'{x:.2e}' if x<.001 else f'{x:.4f}'
def table(headers,rows,caption=''):
 return '<div class="tablewrap"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+str(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def save(fig,name):
 fig.savefig(F/name,dpi=165,bbox_inches='tight');plt.close(fig)
def fig(name,cap):
 data=base64.b64encode((F/name).read_bytes()).decode();return f'<figure><img src="data:image/png;base64,{data}" alt="{esc(cap)}"><figcaption>{cap}</figcaption></figure>'
summary=pd.read_csv(R/'offline_author_summary.csv',index_col=0);methods=list(summary.columns)
labels={'OPT':'OPT（事后参考）','E2E_RNN':'E2E-RNN','Bm1':'BM1','Bm2':'BM2','Normal':'Normal','Gamma':'Gamma','gbm':'E2E-GBM'}
paper=np.array([[3022.60,3766.52,4207.09,4157.03,4576.05,4476.17,4017.82],[1925.70,2689.02,2502.55,2254.99,3369.21,2821.87,2109.93],[1096.91,1077.50,1704.54,1902.04,1206.84,1654.30,1907.89]])
forplot=['OPT','E2E-RNN','BM1','BM2','Normal','Gamma','E2E-GBM']
fig1,axs=plt.subplots(1,2,figsize=(12.6,4.4),sharey=True)
for ax,values,title in zip(axs,[paper,summary.to_numpy()],['论文图2：原始全量实验（文中报告）','本次重算：公开子样本（2607个SKU）']):
 x=np.arange(7);ax.bar(x,values[1],color=TEAL,label='持有成本');ax.bar(x,values[2],bottom=values[1],color=GOLD,label='缺货成本')
 for i,v in enumerate(values[0]):ax.text(i,v+55,f'{v:.0f}',ha='center',fontsize=9)
 ax.set_xticks(x,forplot,rotation=35,ha='right');ax.set_title(title,fontsize=12);ax.set_ylim(0,5250);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
axs[0].set_ylabel('平均累计成本（h=1，b=9）');axs[1].legend(frameon=False,loc='upper left');fig1.tight_layout();save(fig1,'01_offline_costs.png')
sens=load('offline_simulator_sensitivity.json');xx=np.arange(7)
fig2,ax=plt.subplots(figsize=(11.5,4.5))
for j,(key,label,c) in enumerate([('author_cost','作者口径',GRAY),('clip_negative_orders_cost','只将负订单截为0',TEAL),('include_initial_lead_window_cost','只补计首次到货前窗口',GOLD)]):
 ax.bar(xx+(j-1)*.25,[s[key] for s in sens],width=.24,label=label,color=c)
ax.set_xticks(xx,forplot);ax.set_ylabel('平均累计成本');ax.set_ylim(0,9000);ax.legend(frameon=False,ncol=3,loc='upper left');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True);fig2.tight_layout();save(fig2,'02_simulator_sensitivity.png')
boot=load('offline_bootstrap.json');fig3,ax=plt.subplots(figsize=(10,3.7))
y=np.arange(len(boot));v=np.array([x['reduction_pct'] for x in boot]);ci=np.array([x['reduction_ci'] for x in boot]);ax.errorbar(v,y,xerr=[v-ci[:,0],ci[:,1]-v],fmt='o',capsize=5,color=TEAL)
ax.set_yticks(y,[labels[x['baseline']] for x in boot]);ax.invert_yaxis();ax.axvline(0,color=GRAY,lw=1);ax.set_xlabel('E2E-RNN相对基准的平均成本降幅（%）及配对SKU bootstrap 95%区间');ax.grid(axis='x',alpha=.15);fig3.tight_layout();save(fig3,'03_bootstrap.png')
field=load('field_summary.json');horizon=load('field_horizon_audit.json');did=load('field_did.json')
fig4,axs=plt.subplots(1,2,figsize=(11.8,4.2));x=np.arange(4);keys=['e2e_pre','e2e_post','jd_pre','jd_post']
axs[0].bar(x,[field[k]['holding'] for k in keys],color=TEAL,label='持有');axs[0].bar(x,[field[k]['stockout'] for k in keys],bottom=[field[k]['holding'] for k in keys],color=GOLD,label='缺货')
axs[0].set_xticks(x,['E2E 前','E2E 后','对照 前','对照 后']);axs[0].set_ylabel('平均累计成本（作者口径）');axs[0].legend(frameon=False)
for g,c,l in [('e2e',TEAL,'E2E'),('jd',RED,'对照')]:
 vs=[field[f'{g}_{t}']['total'] for t in ['pre','post']];axs[1].plot([0,1],vs,'o-',color=c,label=l,lw=2)
 for i,v in enumerate(vs):axs[1].annotate(f'{v:.2f}',(i,v),xytext=(5,8),textcoords='offset points')
axs[1].set_xticks([0,1],['实验前','实验后']);axs[1].set_xlim(-.15,1.27);axs[1].set_ylabel('平均累计成本');axs[1].legend(frameon=False);axs[1].set_title('四组均值DiD = −1603.73')
for ax in axs:ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig4.tight_layout();save(fig4,'04_field_costs.png')
fig5,axs=plt.subplots(1,2,figsize=(11.8,3.8),sharey=True)
for ax,t,title in zip(axs,['pre','post'],['实验前','实验后']):
 for j,(g,c,l) in enumerate([('e2e',TEAL,'E2E'),('jd',GOLD,'对照')]):
  hist=horizon[f'{g}_{t}']['day_histogram'];days=np.arange(32);ax.bar(days+(j-.5)*.38,[hist.get(str(d),0) for d in days],width=.38,color=c,label=l)
 ax.set_title(title);ax.set_xlabel('作者实际计费天数 = 库存向量长度 − 1');ax.set_xlim(-1,32);ax.legend(frameon=False)
axs[0].set_ylabel('样本单位数');fig5.tight_layout();save(fig5,'05_observation_horizons.png')
matching=load('matching.json');fig6,ax=plt.subplots(figsize=(10,3.1))
for j,(sample,label,c,m) in enumerate([('candidate_pool','匹配前候选池',GRAY,'o'),('raw_covariate_nn','按作者原始协变量近邻',TEAL,'s'),('score_nn','补充：真正的倾向得分近邻',GOLD,'^')]):
 vals=[b['standardized_mean_difference'] for b in matching['balance'] if b['sample']==sample];ax.scatter(vals,np.arange(2)+(j-1)*.12,label=label,color=c,marker=m,s=50)
ax.axvline(0,color=GRAY,alpha=.6);ax.axvline(-.1,color=GRAY,ls=':',alpha=.5);ax.axvline(.1,color=GRAY,ls=':',alpha=.5);ax.set_yticks([0,1],['日均需求','提前期']);ax.set_xlabel('标准化均值差 SMD（分母固定为匹配前两组的合并标准差）');ax.set_ylim(-.5,1.5);ax.legend(frameon=False,loc='upper left',fontsize=9);fig6.tight_layout();save(fig6,'06_matching_balance.png')

offline_rows=[]
for i,m in enumerate(methods):
 vals=summary[m].to_numpy();offline_rows.append([labels[m],num(paper[0,i]),num(vals[0]),num(vals[1]),num(vals[2]),num(100*(vals[0]/summary['OPT'].iloc[0]-1))+'%'])
offline_table=table(['方法','论文图2全量总成本','公开样本总成本','公开样本持有','公开样本缺货','相对公开OPT增幅'],offline_rows,'表2　论文报告值与公开样本重算值（不同样本，不要求数值相等）')
bootstrap_table=table(['基准','RNN平均降幅','95%区间','RNN成本更低的SKU占比'],[[labels[b['baseline']],num(b['reduction_pct'])+'%',f"[{num(b['reduction_ci'][0])}%, {num(b['reduction_ci'][1])}%]",num(b['e2e_lower_sku_pct'])+'%'] for b in boot],'表3　2607个SKU配对抽样2000次，随机种子20261025')
audit=load('offline_semantic_audit.json')
sensitivity_table=table(['方法','作者总成本','负订单数 / 3000','只截断负订单','只补计首次提前期'],[[labels[s['method']],num(s['author_cost']),str(a['negative_orders']),num(s['clip_negative_orders_cost']),num(s['include_initial_lead_window_cost'])] for s,a in zip(sens,audit)],'表4　一次只改变一个评价口径；各敏感性分支均沿用其他原始逻辑')
metricnames={'holding':'持有成本','stockout':'缺货成本','total':'总成本','turnover':'库存天数指标','stockout_rate':'缺货比例'}
paperfield={'holding':[598.20,809.54,26.1],'stockout':[496.34,1027.93,51.7],'total':[1094.54,1837.47,40.4],'turnover':[18.59,20.39,8.8],'stockout_rate':[.17,.26,34.6]}
tt=load('field_ttests.json');reg=load('field_regressions.json')
field_table=table(['指标','论文处理 / 对照','公开处理 / 对照','公开样本降幅','双样本t检验p'],[[metricnames[t['metric']],f"{num(paperfield[t['metric']][0],4 if t['metric']=='stockout_rate' else 2)} / {num(paperfield[t['metric']][1],4 if t['metric']=='stockout_rate' else 2)}",f"{num(t['treatment_mean'],4 if t['metric']=='stockout_rate' else 2)} / {num(t['control_mean'],4 if t['metric']=='stockout_rate' else 2)}",num(t['reduction_pct'])+'%',pv(t['pooled_p'])] for t in tt],'表5　论文表2与公开现场样本（每组500）的实验后比较；成本权重不同，不能直接对数值')
regrows=[]
for m in metricnames:
 a,b,c=[next(t for t in reg if t['metric']==m and t['specification']==s) for s in ['notebook_no_intercept','paper_eq11_intercept','intercept_HC3']]
 regrows.append([metricnames[m],f"{num(a['e2e_coef'],4)} (p={pv(a['p'])})",f"{num(b['e2e_coef'],4)} (p={pv(b['p'])})",pv(c['p'])])
reg_table=table(['指标','作者笔记本：无常数项β','按论文式(11)：含常数项β','含常数项HC3的p'],regrows,'表6　同一公开样本、相同需求与提前期控制变量；不同回归规格')
did_table=table(['指标','E2E 前 → 后','对照 前 → 后','四组均值DiD','聚类95%区间'],[[metricnames[d['metric']],f"{num(d['e2e_pre'],4)} → {num(d['e2e_post'],4)}",f"{num(d['control_pre'],4)} → {num(d['control_post'],4)}",num(d['effect'],4),f"[{num(d['cluster_ci'][0],4)}, {num(d['cluster_ci'][1],4)}]"] for d in did],'表7　统一将库存天数截为非负的四组均值DiD；区间依赖“同组前后ID确为同一单位”的假设')
nbdid=load('field_notebook_did_audit.json')['did_tests']
did_replay_table=table(['指标','保存的旧p值','本次顺序重跑p值','本次原代码DiD均值差'],[[metricnames[d['metric']],esc(d['saved_output'].split('p =')[-1].strip()),pv(d['reexecuted_p']),num(d['reexecuted_effect'],4)] for d in nbdid],'表8　原笔记本DID单元格38/40/42/44/46（从0编号）的旧输出与本次执行；均值差不是t检验系数')
horizon_table=table(['样本','平均计费天数','计费天数范围','零计费天单位','总成本 / 总观察天','单位日成本的均值'],[[{'e2e_pre':'E2E 前','e2e_post':'E2E 后','jd_pre':'对照 前','jd_post':'对照 后'}[k],num(horizon[k]['mean_measured_days'],3),f"{horizon[k]['min_measured_days']}–{horizon[k]['max_measured_days']}",str(horizon[k]['zero_measured_days']),num(horizon[k]['total_cost_per_observed_day']),num(horizon[k]['unweighted_mean_unit_day_cost'])] for k in keys],'表10　不同观察时长审计；总观察天加权与单位日成本均值是两种不同统计量，后者排除零计费天单位')
matchtable=table(['样本','日均需求：处理 / 对照','日均需求SMD','提前期：处理 / 对照','提前期SMD'],[[label,f"{b[0]['treatment_mean']:.6f} / {b[0]['control_mean']:.6f}",f"{b[0]['standardized_mean_difference']:.6f}",f"{b[1]['treatment_mean']:.6f} / {b[1]['control_mean']:.6f}",f"{b[1]['standardized_mean_difference']:.6f}"] for sample,label in [('candidate_pool','匹配前'),('raw_covariate_nn','原始协变量近邻'),('released_control','已公布对照样本'),('score_nn','得分近邻（补充）')] for b in [[x for x in matching['balance'] if x['sample']==sample]]],'表9　匹配诊断；SMD只检验已观察的两项协变量')
normal=load('normal_equation_audit.json');theorem=load('theorem_validation.json');environment=load('environment.json');validation=load('field_validation.json');offlineaudit=load('offline_notebook_audit.json')
field_sens=load('field_sensitivity.json')
other_table=table(['现场成本计算分支','处理组后期总成本','对照组后期总成本','降幅','四组总成本DiD'],[[{'notebook':'作者口径 h=1,b=9','paper_h12_b88':'仅重计价 h=12,b=88','include_last_day':'包含库存向量末日 h=1,b=9'}[s['branch']],num(s['treatment_post']),num(s['control_post']),num(s['reduction_pct'])+'%',num(s['did'])] for s in field_sens if s['metric']=='total'],'表11　固定已实现库存轨迹的权重与末日敏感性；没有重新训练或重新决策')
daily_reduction=100*(1-horizon['e2e_post']['total_cost_per_observed_day']/horizon['jd_post']['total_cost_per_observed_day'])

CSS='''
:root{--ink:#203345;--navy:#15364b;--teal:#147c80;--line:#dce6eb;--muted:#607585;--pale:#f2f7f8;--gold:#ae701a}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;color:var(--ink);background:#edf2f5;line-height:1.85}a{color:var(--teal);text-underline-offset:3px}header{background:var(--navy);color:white;padding:55px max(5vw,24px) 45px}header .overline{letter-spacing:2px;font-size:13px;color:#aad9dc}h1{font-size:clamp(27px,3vw,43px);line-height:1.4;max-width:1050px;margin:15px 0 12px}header p{max-width:1050px;color:#d2e4eb;margin:8px 0}.tags{display:flex;gap:8px;flex-wrap:wrap;margin-top:23px}.tag{font-size:12px;background:#2b4c60;border:1px solid #476679;border-radius:20px;padding:3px 12px}.layout{display:grid;grid-template-columns:210px minmax(0,1060px);max-width:1330px;gap:28px;margin:32px auto;padding:0 22px}nav{position:sticky;top:20px;align-self:start;font-size:13px;line-height:1.5}nav a{display:block;padding:8px 10px;text-decoration:none;border-left:2px solid #d4e0e6}nav a:hover{background:white;border-color:var(--teal)}nav strong{display:block;margin:0 0 10px 10px}main{min-width:0;background:white;padding:30px 42px 55px;border:1px solid var(--line);border-radius:10px}section{margin-bottom:44px}h2{font-size:24px;line-height:1.5;margin:0 0 20px;padding-bottom:10px;border-bottom:2px solid var(--teal)}h2 .n{color:var(--teal);font-size:15px;margin-right:12px}h3{font-size:18px;margin:26px 0 10px}p{margin:12px 0}li{margin:5px 0}ul,ol{padding-left:24px}.lead{font-size:17px}.callout{background:#f0f7f7;border-left:4px solid var(--teal);padding:14px 18px;margin:18px 0;border-radius:0 6px 6px 0}.callout.amber{background:#fcf6e9;border-color:#c7953e}.callout p{margin:4px 0}.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0}.kpi{padding:18px;background:var(--pale);border-radius:6px}.kpi b{font-size:28px;color:var(--teal);display:block;line-height:1.4}.kpi span{font-size:12px;color:var(--muted)}.tablewrap{overflow:auto;margin:20px 0}table{border-collapse:collapse;width:100%;font-size:12.5px;line-height:1.65;font-variant-numeric:tabular-nums}caption{text-align:left;font-weight:600;margin-bottom:10px;color:var(--navy);font-size:13px}th{background:#eaf2f4;text-align:left;white-space:nowrap}th,td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:nth-child(even){background:#f8fafb}figure{margin:25px 0}figure img{display:block;width:100%;height:auto;border:1px solid #eef2f5}figcaption{font-size:12px;color:var(--muted);line-height:1.7;margin-top:9px}.equation{background:#f3f6f9;padding:16px 20px;overflow:auto;font:15px/1.9 Consolas,"Microsoft YaHei",monospace;border-radius:6px}pre{background:#172f40;color:#e0edf2;padding:18px;border-radius:6px;font:12px/1.8 Consolas,monospace;overflow:auto}code{font-family:Consolas,"Microsoft YaHei",monospace;background:#edf3f5;padding:1px 4px;border-radius:3px}pre code{background:transparent;padding:0}.small{font-size:12px;color:var(--muted)}details{border:1px solid var(--line);border-radius:6px;padding:10px 15px;margin:18px 0}summary{cursor:pointer;font-weight:600}.flow{display:block;width:100%;height:auto;margin:18px 0}.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:var(--pale);padding:14px;border-radius:6px}.controls label{font-size:13px}input,select,button{font:inherit;font-size:13px;border:1px solid #bdcdd5;padding:7px 9px;border-radius:4px;background:white;color:var(--ink)}button{cursor:pointer}button:hover{border-color:var(--teal);color:var(--teal)}#explorer tbody td{white-space:nowrap}footer{color:var(--muted);font-size:12px;margin-top:35px;padding-top:20px;border-top:1px solid var(--line)}@media(max-width:1000px){.layout{display:block;padding:0 12px}nav{position:static;display:flex;flex-wrap:wrap;margin-bottom:20px}nav strong{width:100%}nav a{padding:6px 9px}main{padding:25px 20px}.kpis{gap:8px}.kpi b{font-size:23px}}@media(max-width:550px){.kpis{grid-template-columns:1fr}h2{font-size:21px}.kpi b{font-size:26px}header{padding:30px 20px}}@media print{body{background:white;font-size:10pt}header{background:white;color:#15364b;padding:10px 0 20px}header p{color:#354f60}.tag{color:#15364b;background:#eef3f5}.layout{display:block;max-width:none;margin:0;padding:0}nav,.controls,.interactive-only{display:none}main{border:0;padding:10px 0}section{break-before:auto;margin-bottom:22px}h2,h3{break-after:avoid}figure,table,.callout{break-inside:avoid}details{display:block}details>*{display:block}a{color:inherit}figure img{max-height:220mm;object-fit:contain}.kpis{grid-template-columns:repeat(3,1fr)}@page{size:A4;margin:18mm}}
'''
navs=[('overview','复现结论与边界'),('paper','论文与管理问题'),('model','理论、标签与网络'),('data','材料与数据审计'),('steps','实际执行步骤'),('offline','离线结果与不确定性'),('simulation','库存模拟口径审计'),('field','现场样本统计复现'),('matching','匹配机制复现'),('robust','观察窗口与敏感性'),('explore','逐SKU结果查询'),('reproduce','复运行与校验'),('discussion','研究结论与限制'),('references','资料与证据索引')]
parts=[]
def section(id,title,content):
 n=next(i for i,(key,_) in enumerate(navs) if key==id)
 parts.append(f'<section id="{id}"><h2><span class="n">{n:02d}</span>{title}</h2>{content}</section>')
section('overview','复现结论与边界',f'''
<p class="lead">本报告围绕 T1 论文，完成作者公开测试数据上的离线评价、现场样本统计、匹配过程和理论标签数值验证，并检查实现细节对结论的影响。所有“本次重算”数值均由随附 Python 脚本实际运行产生。</p>
<div class="kpis"><div class="kpi"><b>2607</b><span>公开离线数据的唯一SKU数，来自3000行记录</span></div><div class="kpi"><b>3036.76</b><span>E2E-RNN平均总成本，原笔记本口径</span></div><div class="kpi"><b>55.46%</b><span>公开现场样本后期累计总成本降幅</span></div></div>
<div class="callout"><p><strong>结果：公开数据支持“在作者评价口径下，E2E-RNN平均成本低于各非事后基准”。</strong>与BM1、BM2相比，平均成本分别下降20.97%、20.87%；与E2E-GBM相比下降11.33%。现场样本的成本差异方向与论文一致。</p></div>
<div class="callout amber"><p><strong>结论适用范围：</strong>公开包主要提供预测输出、库存轨迹和脱敏子样本，没有完整训练特征、原始训练集、模型权重及训练源程序。因此本次完成的是<strong>公开材料的计算复现与方法审计</strong>；完整神经网络重新训练、全量样本指标和真实上线实验均未重建。</p><p>审计发现会改变解释的细节：负订单截断后，RNN不再是公开样本中成本最低的非事后方法；现场两组计费时长不等；无常数项回归下库存天数的E2E系数不显著。报告保留这些结果，不将原论文的因果结论直接移植到公开子样本。</p></div>
<p class="small">报告生成日期：2026-10-25（Asia/Shanghai）。复现方式：以AI协助完成资料阅读、代码整理和报告生成，使用本地Python执行数值计算。HTML内嵌图表与交互数据，离线打开即可查看；原始材料和运行脚本见配套ZIP。</p>
''')
section('paper','论文与经济管理问题','''
<p><strong>原文：</strong>Qi, M., Shi, Y., Qi, Y., Ma, C., Yuan, R., Wu, D., &amp; Shen, Z.-J. (2023). <em>A Practical End-to-End Inventory Management Model with Deep Learning</em>. <em>Management Science</em>, 69(2), 759–773. <a href="https://doi.org/10.1287/mnsc.2022.4564">DOI: 10.1287/mnsc.2022.4564</a>。在线发表日期为2022年12月13日。报告使用用户提供的最终刊发PDF。</p>
<p>电商平台面对大量需求稀疏、波动且补货提前期不确定的商品，必须平衡持有库存的资金与仓储成本，以及缺货造成的服务损失。传统“先预测、后优化”（PTO）先估计需求和提前期，再代入库存公式。预测误差最小与库存成本最小之间可能不一致。</p>
<p>论文提出从业务特征直接输出补货量的E2E模型：先用历史上已经发生的需求与提前期求出事后最优动作，作为监督学习标签，再训练神经网络逼近该动作。它以决策质量为最终目标，并保留需求预测和提前期预测两个辅助任务。</p>
<p>论文离线实验覆盖24,333个SKU；现场实验在京东12个配送中心开展，涉及61,430张补货订单和9,308个SKU，处理组与对照组各6,097个SKU–配送中心对。现场处理对象由业务管理者选择，具有选择性，不能按随机对照试验解释（原文§4–§5，印刷页765–769）。</p>
''')
architecture='''<svg class="flow" viewBox="0 0 950 290" role="img" aria-label="按论文整理的E2E网络结构示意，不表示已运行训练"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#758899"/></marker></defs><g stroke="#758899" stroke-width="2" fill="none" marker-end="url(#arrow)"><path d="M215 55H290"/><path d="M215 145H290"/><path d="M480 55H535V125H575"/><path d="M480 145H575"/><path d="M215 240H535V175H575"/><path d="M770 145H815"/><path d="M385 90V105"/><path d="M385 180V205"/></g><g fill="#eef5f6" stroke="#b6ced2"><rect x="10" y="20" width="205" height="70" rx="8"/><rect x="10" y="110" width="205" height="70" rx="8"/><rect x="10" y="205" width="205" height="70" rx="8"/><rect x="290" y="20" width="190" height="70" rx="8"/><rect x="290" y="110" width="190" height="70" rx="8"/><rect x="575" y="95" width="195" height="100" rx="8"/></g><rect x="815" y="110" width="125" height="70" rx="8" fill="#147c80"/><g font-family="Microsoft YaHei,sans-serif" font-size="15" text-anchor="middle" fill="#203345"><text x="112" y="50">需求与促销时序特征</text><text x="112" y="72" font-size="12">原文输入向量共132维</text><text x="112" y="140">提前期相关特征</text><text x="112" y="162" font-size="12">完整特征未公开</text><text x="112" y="236">商品、仓库、品牌特征</text><text x="112" y="258" font-size="12">盘点周期 / 初始库存</text><text x="385" y="50">需求子模块 MQRNN</text><text x="385" y="73" font-size="12">hidden = 50，辅助需求输出</text><text x="385" y="140">提前期子模块 MLP</text><text x="385" y="162" font-size="12">50 → 20，辅助VLT输出</text><text x="672" y="134">整合模块</text><text x="672" y="160">100 → 100</text><text x="672" y="181" font-size="12">ReLU / Dropout 0.2</text><text x="877" y="141" fill="white">补货建议</text><text x="877" y="163" fill="white" font-size="12">订单决策输出</text></g></svg>'''
section('model','理论、监督标签与网络结构',f'''
<h3>2.1 有限期库存决策</h3>
<p>设需求为d<sub>t</sub>，期末净库存为I<sub>t</sub>，负净库存代表延期交付需求。期末成本为h·max(I<sub>t</sub>,0)+b·max(−I<sub>t</sub>,0)。固定盘点日期、随机提前期决定订单到货时刻。理论推导假设完全延期交付，且各批订单的到货顺序不发生交叉。</p>
<div class="equation">min E[Σₜ (h·Iₜ⁺ + b·(−Iₜ)⁺)]，qₘ ≥ 0<br>α = b / (b+h)</div>
<h3>2.2 用已实现路径构造最优动作标签</h3>
<p>对于两个相邻到货时刻之间的n天，令c<sub>j</sub>为从本次到货日累计到第j天的需求，I为本次到货前净库存。非负需求使c单调。事后成本关于到货后库存水平是分段线性凸函数；平衡持有与缺货的边际成本，可选取累计需求的α分位点。</p>
<div class="equation">cⱼ = Σₖ₌₀ʲ dₖ，j=0,…,n−1<br>j* = min(n−1, floor(αn))<br>q* = max(0, cⱼ* − I)</div>
<p>αn为整数时可能存在一段等价最优解；上式给出其中一个。此标签使用未来已经实现的路径，属于<strong>事后监督信息</strong>，不能视为上线时已知信息。测试期的OPT同样只是事后参考，不是可部署算法，也不代表其他算法相对真实随机动态规划最优策略的差距。</p>
<p>本次对5组α（0.1、0.5、0.88、0.9、0.95），共1000个随机单周期实例，枚举整数补货量验证标签成本等于最小成本；另对100个两到货周期实例枚举两次动作。全部通过，最大数值成本差{theorem['max_cost_excess']:.2e}。这些有限规模检验是公式实现校验，不能替代论文的数学证明。</p>
<h3>2.3 多任务E2E网络与训练配置</h3>{architecture}
<div class="equation">L(θ) = (1/N) Σᵢ [ Lorder(Out1ᵢ, q*ᵢ) + λ₁ Ldemand(Out2ᵢ, DF*ᵢ) + λ₂ Lvlt(Out3ᵢ, VLT*ᵢ) ]</div>
<p>论文式(6)采用订单、需求与提前期三项损失；λ₁、λ₂为较小正权重，所提供正文没有给出其具体数值。表B.1给出学习率0.001、learning rate decay 10⁻⁴、momentum 0.85、batch size 64、高斯初始化均值0/标准差0.01。这里保留作者对decay的命名，缺少训练源程序时不推断其具体实现。</p>
<p>原实验用最早30天样本中的80%训练、20%验证，后30天测试；论文附录的全部训练规模为19,466个SKU，硬件为Tesla P40。公开CSV中没有相应完整132维特征与可还原的训练时间切分。本次只解释训练流程，不把现成预测列用于训练后宣称重训成功。</p>
<pre><code># 论文训练机制的说明性伪代码；本次未执行原始模型训练
for order in historical_orders:
    label = ex_post_optimal_order(realized_demand, realized_vlt, inventory)
train, validation, test = chronological_split(orders)
for batch in train:
    q_hat, demand_hat, vlt_hat = E2E(features_available_at_order_time)
    loss = order_loss(q_hat, label) + lambda1*demand_loss + lambda2*vlt_loss
    update_network(loss)</code></pre>
''')
inventory_table=table(['材料','实测规模','本次用途 / 限制'],[
['最终刊发PDF','16页（含末页版权说明）','阅读正文、图2、表2–4、附录B'],
['df_test.csv','3000行 × 13列；2607个唯一SKU','已有OPT/RNN/GBM等输出；聚合后逐SKU计算'],
['order_e2e_pre/post_500.csv','每份500行','处理组前后库存轨迹'],
['order_jd_pre/post_500.csv','每份500行','对照组前后库存轨迹'],
['control_demand_vlt.csv','55,333行','候选对照的需求与提前期协变量'],
['rdc_sales_1320.csv','5个SKU–DC示例','仅为需求数据格式示例'],
['stock.csv / vlt_2019_0305.csv','2个库存示例 / 1条提前期示例','不足以恢复原训练集'],
['3份.ipynb + README.docx','笔记本位于.ipynb_checkpoints目录','保留原代码和旧输出，另行重跑并比较']
],'表1　公开材料清点（上游文件未改写）')
section('data','材料清点与数据审计',inventory_table+'''
<p>输入来自用户的“文献和数据”目录及其中的<code>replication_package_MS-FTBDA-20-01585.zip</code>。README将离线数据称为“3000 SKUs”，实际为3000行、2607个唯一SKU；本报告使用实际读入与聚合后的规模。重复SKU记录按作者笔记本原有行序聚合，公开文件未提供足够时间标识来独立重建完整订单时序。</p>
<p>现场四份CSV均包含0–499的脱敏ID，组内前后ID集合完全重合。重合只能支持一种可能的面板对齐方式，不能证明与原始SKU–DC身份逐一对应，也不能将处理组ID与对照组同号ID视为匹配对。候选池身份与已公布控制结果间没有原始映射。</p>
<p>已为所有提取的上游文件、输入PDF和原始ZIP生成SHA-256清单。下文严格区分“论文全量报告值”“本次公开样本重算值”“改变计算口径的敏感性结果”。</p>
''')
section('steps','逐步复现的实际执行过程','''
<ol><li><strong>读取材料：</strong>提取PDF正文与附录，解压原始包，检查CSV维数、ID、库存向量和笔记本代码。</li>
<li><strong>执行离线评价：</strong>运行作者离线笔记本的数值单元格1–15，仅替换输入文件路径；跳过导入单元格0和LaTeX展示单元格16。将3000行聚合为2607个SKU，逐方法计算库存轨迹与成本。</li>
<li><strong>独立交叉核对：</strong>另写库存路径计算器，对全部SKU与全部7种方法逐项比较，成本最大绝对差为0；再与笔记本保存的6位小数汇总比较。</li>
<li><strong>统计与口径审计：</strong>执行2000次SKU层面配对bootstrap；检查负订单、提前期计费窗口、Normal基准公式；每个敏感性分支独立保留。</li>
<li><strong>现场结果重算：</strong>从四份原始库存CSV重新计算持有、缺货、总成本、库存天数和缺货比例；重算等方差t检验、Welch检验、无常数项OLS、含常数项OLS、HC3和四组均值DiD。</li>
<li><strong>核对原代码执行状态：</strong>顺序运行现场笔记本的28个非回归数值单元格，保存实际日志；回归用NumPy最小二乘独立实现，避免旧依赖版本阻碍重跑。</li>
<li><strong>复现匹配与理论检验：</strong>用SciPy求解L2逻辑回归，并区分原始协变量近邻和一维倾向得分近邻；验证事后补货标签。</li>
<li><strong>导出：</strong>保存逐SKU/逐单位CSV、统计JSON、数据指纹、独立PNG图表和本HTML；打包源材料、脚本与结果供复运行。</li></ol>
<p>执行脚本不需要GPU；这源于本次重算公开预测输出和库存轨迹，并不意味着原始E2E网络无需GPU训练。</p>
''')
section('offline','离线评价结果与不确定性',offline_table+fig('01_offline_costs.png','图1　成本结构比较。左右图来自不同规模数据；论文图2值由原PDF读取，右图为实际重算，OPT为事后参考。')+f'''
<p>作者原口径下，E2E-RNN总成本为3036.76，低于所有其他非事后方法；相对OPT高18.03%。这与论文全量数据的排序方向一致。不同样本成本水平不同，不能把右图与左图数值差作为复现误差；可验证目标是公开数据运行结果与该包原笔记本的一致性。</p>
<p>RNN缺货成本1153.17低于公开OPT的1209.75，同时持有成本更高，并不矛盾：OPT针对总成本，单个分项可以更高；并且公开“OPT”列也经过原始模拟器处理，不是本报告重新求解全路径优化得到的严格最优下界。</p>
<h3>配对SKU bootstrap</h3>
<p>以SKU为重采样单位，同时抽取RNN与基准的对应成本，重复2000次，报告“均值成本之比”的降幅与百分位95%区间。它度量此公开样本的跨SKU抽样不确定性，没有纳入训练随机性、原始抽样机制或SKU之间可能的相关性。</p>
'''+bootstrap_table+fig('03_bootstrap.png','图2　不同基准下RNN平均成本降幅及95%区间；区间只针对作者评价口径。')+'''
<p>相对BM2，RNN平均成本下降20.87%，但只有41.81%的SKU成本严格更低；相对GBM，更低的SKU占49.56%。平均优势并不代表多数商品都改善，应结合商品异质性决定部署或组合策略。</p>
''')
section('simulation','库存模拟口径审计',sensitivity_table+fig('02_simulator_sensitivity.png','图3　只改变一个口径的库存模拟敏感性。负订单截断与补计初始提前期分别进行，未同时更改。')+f'''
<h3>6.1 负订单会影响方法排序</h3>
<p>原笔记本用“预测列值减某个历史库存”再取整生成动作，未执行max(0,q)。在3000次RNN动作中，有525次为负（17.5%）；原材料将预测列描述为补货输出，但实际评价代码把它们按目标库存量解释。本次忠实复跑该代码，同时单独检查非负动作约束。</p>
<p><strong>只将负动作截为0时，RNN成本为2671.75，GBM为2564.07，BM2为2641.03；最低非事后成本变为GBM。</strong>这说明原排序依赖评价实现。该分支仍沿用其他原逻辑，不能称为完整业务修正版。</p>
<h3>6.2 提前期与欠交状态</h3>
<p>原模拟中，第一次到货前的库存变化不计入最终评分向量；后续记录在到货前的循环日直接跳过。每种方法均有2068个这样的后续循环日被跳过；有11次历史索引越界回退。到货日更新包含max(上一日库存,0)，会清除先前负净库存，不能直接视为论文理论中的完全延期交付递推。</p>
<p>“只补计首次到货前窗口”保留其余状态更新，只把已生成的库存路径纳入评分，因此各方法成本都增加约3485.00；它没有补齐后续被跳过的日，也没有修复延期交付逻辑。该相同增量并不构成新策略效果。</p>
<h3>6.3 PTO基准的实现差异</h3>
<div class="equation">论文式(7)：S = μᴅ(R+μᴸ) + zα·√[(R+μᴸ)σᴅ² + μᴅ²σᴸ²]</div>
<p>笔记本Normal基准使用z=1.64，而α=0.9对应z={normal['paper_90th_quantile']:.5f}；还把提前期不确定项写成σᴅ²·σᴸ。按论文式(7)改写两处、目标库存向下取整，沿用原模拟器，成本变为{normal['paper_eq7_normal_mean']:.2f}，原值为{normal['author_normal_mean']:.2f}。这只是公式一致性分支。</p>
<p>原笔记本的BM1/BM2以<code>sf_rnn</code>列表均值参与计算，而正文描述了多分位需求预测与最优分位选择。公开包没有完整预测结构、训练代码和选择过程，不能将这两个公开计算列当作完整恢复了论文的全部PTO建模流程。</p>
''')
section('field','现场样本的统计复现',field_table+fig('04_field_costs.png','图4　公开样本四组成本与前后变化（h=1,b=9，按库存向量除末日累计）。组间观察天数不同，详见第09节。')+'''
<p>公开笔记本设置h=1、b=9；论文现场实验为h=12、b=88。公开后期总成本降幅55.46%，论文表2为40.4%，二者既有样本范围差异，也有计价权重差异，不能据此断言原结论被精确复现。</p>
<p>成本由库存向量<code>inv[:-1]</code>累计。缺货比例的分子同样只数前T−1个元素，分母却用T；代码中的turnover是max(0,ave_inv/ave_demand)，量纲更接近“库存覆盖天数”，不是通常的年周转次数。表中库存天数下降按论文口径视为改善，但原ave_inv可能包含负净库存，不能直接解释为实体库存周转效率。</p>
<h3>7.1 回归：常数项会改变结论</h3>
<div class="equation">论文式(11)：Yᵢ = β₀ + β₁ E2Eᵢ + β₂ VLTᵢ + β₃ Demandᵢ + εᵢ</div>
'''+reg_table+'''
<p>作者笔记本把E2E、VLT和需求直接传给OLS，没有添加常数项；本文按该代码重算得到库存天数系数+0.3458，p=0.7698，不能支持其显著下降。按论文式(11)添加常数项后，同一样本的系数为−6.2045，p&lt;0.001；HC3稳健标准误亦支持负向相关。两者都是各自规格的计算结果，不能择其有利者来代表原代码。控制变量取自已公布的平均需求和提前期，尚不能排除后处理偏误和遗漏变量。</p>
<h3>7.2 四组均值DiD与原笔记本的t检验</h3>
<div class="equation">DiD = (ȲE2E,post − ȲE2E,pre) − (Ȳcontrol,post − Ȳcontrol,pre)</div>
'''+did_table+'''
<p>总成本DiD为−1603.73。表7区间来自含处理、后期及交互项的四组回归，按组内前后脱敏ID聚类并做有限样本修正；系数与四组均值公式交叉验证一致。该聚类结构依赖身份连续假设，且未处理匹配有放回带来的未知控制依赖，应将区间视为条件性统计诊断。</p>
'''+did_replay_table+'''
<p>原笔记本将同一行号的处理/对照结果相减，再对前后两列差做独立样本t检验；脱敏行号没有证明处理与对照逐行匹配关系，此检验还忽略同一单位前后的相关性。顺序重跑得到的5项p值均与保存的旧输出不同；不能从现有材料确定旧输出对应何种数据或运行状态。</p>
<p>原单元格29还对后期对照的库存天数使用未截断数组，其余三组使用截断数组。因此原代码库存天数DiD为−4.9927，表7统一截断后为−6.5376，两种口径分别保留。现场实验非随机分配，公开数据只有前后两个汇总窗口，无法检验平行趋势，DiD不能单独证明因果效果。</p>
''')
section('matching','匹配机制与平衡性复现',f'''
<p>使用500个处理样本与55,333个候选对照，以日均需求和提前期拟合带L2惩罚的逻辑回归（C=1、截距不惩罚）。SciPy直接最小化对数损失加惩罚，得到参数（截距、需求、提前期）=（{matching['logistic_beta'][0]:.6f}，{matching['logistic_beta'][1]:.6f}，{matching['logistic_beta'][2]:.6f}），梯度无穷范数{matching['gradient_inf_norm']:.2e}，求解成功。</p>
<p><strong>原代码虽计算倾向得分，但最近邻检索使用原始需求和提前期列，而非得分列。</strong>源代码还包括组别指示列；对所有处理—候选组合，该列差均为1，对欧氏近邻排序只增加常数，等价于未标准化的两项协变量匹配。故原方法在实现上属于协变量近邻匹配。为明确差别，本报告另算真正的一维倾向得分匹配作为补充，不替换原结果。</p>
'''+matchtable+fig('06_matching_balance.png','图5　已观察协变量的均值平衡；|SMD|=0.1的虚线仅是常用诊断参照，不是因果识别保证。')+f'''
<p>按原协变量欧氏距离匹配、有放回，使用“距离相同取最小候选行号”的确定性规则，500次匹配得到{matching['matched_unique_candidates']}个不同候选；{matching['zero_distance_matches']}次距离为0，{matching['ties']}个处理样本存在并列最近邻，最大距离{matching['max_distance']:.6f}。匹配后提前期均值完全平衡，需求SMD接近0。</p>
<p>本次选择的控制协变量与已公布控制样本<strong>排序后的500行协变量完全一致</strong>（最大差为{matching['released_control_sorted_covariate_max_difference']:.1f}），进一步支持原始协变量近邻这一实现机制。但原始行顺序及身份映射不能由此恢复。由于并列选择大量存在，不能将本次候选行号直接连接到公开对照的结果ID，也不据此重新估计所谓“精确匹配后的ATT”。匹配只处理这两项可观测变量，不能排除业务选择、商品类别或其他未观测因素。</p>
''')
section('robust','观察时长与现场敏感性',horizon_table+fig('05_observation_horizons.png','图6　公开样本的计费窗口差异。处理组后期246个单位计31天，对照组后期433个单位计31天；对照后期另有2个单位完全未计费。')+f'''
<p><strong>平均后期计费天数：处理组20.096天，对照组27.124天。</strong>同样的日成本因观察天数不同，也会产生累计成本差。以“总成本之和 / 总计费天数”计算，后期处理组为{horizon['e2e_post']['total_cost_per_observed_day']:.2f}，对照为{horizon['jd_post']['total_cost_per_observed_day']:.2f}，降幅为{daily_reduction:.2f}%，低于累计均值的55.46%。以各单位日成本再取均值则分别为40.38和71.77；它给每个非空单位同等权重，含义不同。</p>
<p>这种归一化仅检查暴露时长敏感性，不能恢复缺失的共同日历窗口，也不能消除非随机截尾。要估计可比的运营效应，需要原始逐日时间戳、统一起止日和可验证的处理/对照身份，再重新设计面板分析。</p>
'''+other_table+'''
<p>以论文现场权重h=12、b=88对既有轨迹重计价，降幅54.18%；这不等于让策略在α=0.88下重新训练和决策。包含末日也会改变成本和比例。原始结果、权重敏感性、窗口敏感性分别保留，不将其中任一选择性包装为“论文真值”。</p>
''')
section('explore','逐SKU结果查询与导出','''
<p>以下数据直接嵌入本HTML，为原笔记本口径的2607个SKU成本。输入SKU片段可筛选，选择基准可查看与RNN的差值。“差值”为RNN减基准，负数表示RNN更低；降幅按基准非零时计算。下载按钮导出当前筛选结果，所有计算在本地浏览器完成。</p>
<div class="controls"><label>SKU <input id="skuSearch" type="search" placeholder="输入ID片段" aria-label="筛选SKU"></label><label>比较基准 <select id="baseline" aria-label="比较基准"><option value="Bm2">BM2</option><option value="Bm1">BM1</option><option value="Normal">Normal</option><option value="Gamma">Gamma</option><option value="gbm">E2E-GBM</option><option value="OPT">OPT（事后参考）</option></select></label><button id="csvDownload">下载筛选CSV</button></div>
<p id="explorerSummary" class="small" aria-live="polite"></p><div class="tablewrap"><table id="explorer"><thead><tr><th>SKU</th><th>E2E-RNN成本</th><th>基准成本</th><th>差值</th><th>降幅</th></tr></thead><tbody id="skuBody"></tbody></table></div><div class="controls"><button id="prevPage">上一页</button><span id="pageLabel"></span><button id="nextPage">下一页</button></div>
<noscript>当前浏览器禁用JavaScript。以上静态表格与图仍可查看；逐SKU数据请打开ZIP中的results/offline_per_sku.csv。</noscript>
''')
envtable=table(['组件','本次版本'],[[k,esc(environment[k])] for k in ['python','numpy','pandas','scipy','matplotlib','platform']],'表12　实际数值环境')
section('reproduce','复运行步骤与校验证据',envtable+f'''
<p>配套ZIP解压后进入T1复现目录。安装所列数值依赖，再执行：</p>
<pre><code>python -m pip install -r requirements.txt
python bootstrap.py replicate.py
python bootstrap.py build_report.py
python bootstrap.py validate_delivery.py</code></pre>
<p>当前机器的bootstrap会优先复用同级A1复现的vendor目录，其次使用本目录vendor，之后使用当前Python环境；ZIP不打包数值运行库，单独使用时按requirements安装即可。生成路径为<code>results/</code>与<code>output/T1_论文复现报告.html</code>。原始PDF在<code>sources/</code>；上游CSV和笔记本在<code>upstream/</code>。</p>
<ul><li>离线汇总与原笔记本已保存输出最大差：{offlineaudit['golden_max_abs_error']:.2e}（原输出仅6位小数）；独立模拟器逐SKU成本差：0。</li><li>现场四组五项均值与笔记本输出最大差：{validation['golden_max_abs_error']:.2e}；4份数据均为500个样本。</li><li>事后标签验证：1000个单周期、100个两周期枚举案例通过。</li><li>四组均值DiD与交互项回归系数差小于10⁻⁸；逻辑回归梯度收敛通过。</li><li>历史DID保存输出不作为一致性通过项，已明确列出实际重跑差异。</li></ul>
<details><summary>主要输出文件的用途</summary>
<ul><li><code>offline_author_summary.csv / offline_per_sku.csv</code>：离线汇总与逐SKU成本。</li><li><code>offline_*audit.json / offline_simulator_sensitivity.json / offline_bootstrap.json</code>：代码语义审计与不确定性。</li><li><code>field_*_metrics.csv / field_summary.json / field_ttests.json</code>：四份现场样本逐单位指标、均值与检验。</li><li><code>field_regressions.json / field_did.json</code>：回归系数、标准误、p值与区间。</li><li><code>field_notebook_rerun.log / field_notebook_did_audit.json</code>：原现场单元格真实运行日志与旧输出对比。</li><li><code>field_horizon_audit.json / field_sensitivity.json</code>：计费天数与权重/末日敏感性。</li><li><code>matching.json / matching_pairs.csv</code>：候选匹配诊断与确定性选择，不代表公开结果ID映射。</li><li><code>source_manifest.json / environment.json / delivery_validation.json</code>：SHA-256、环境和交付校验。</li></ul></details>
''')
section('discussion','研究结论、管理含义与限制','''
<p><strong>第一，决策导向学习具有可检验的管理价值。</strong>在作者公开评价口径下，E2E-RNN实现了比多个PTO计算列更低的平均库存成本，且配对SKU bootstrap支持平均差异。但优势集中程度不均，部署时应比较商品级损失，而非只看全平台均值。</p>
<p><strong>第二，策略优势与评价器必须一起审计。</strong>负订单、欠交状态清除和提前期窗口会改变库存成本甚至方法排序。业务落地需要统一订单非负约束、日历、到货事件和欠交记账规则，再在相同事件模拟器中重新比较算法。</p>
<p><strong>第三，现场样本提供相关性证据，因果效应仍需更完整设计。</strong>成本差、回归和DiD方向大体有利于E2E，但管理者选择处理对象、窗口不等长、脱敏映射不明和缺乏多期趋势限制了识别。统计显著不能单独解决这些问题。</p>
<p><strong>本次已完成：</strong>公开数据评价复跑、历史结果核对、独立路径交叉检查、统计规格比较、匹配机制重建、理论公式数值验证、可离线HTML与代码数据导出。<strong>尚不能复现：</strong>原网络训练与收敛、完整分位预测与参数选择、24333个SKU全量实验、全量现场身份匹配、在线业务决策和原文全部网络超参数消融。补齐这些部分需要作者原训练数据、特征处理、损失权重、训练代码和全量面板，公开示例文件不足以支持。</p>
<p>因此，合适的作业结论是：成功重算了公开包可验证的主要评价结果，并发现数项影响解释与排序的实现差异；不能宣称完成原论文所有实验或证明E2E在任何业务口径下都最优。</p>
''')
manifest=load('source_manifest.json');hashrows=[[esc(d['path']),f"{d['bytes']:,}",f"<code>{d['sha256']}</code>"] for d in manifest if d['path'].endswith(('.pdf','.zip')) or d['path']=='upstream/df_test.csv']
section('references','参考资料与证据索引','''
<ol><li>Qi et al. (2023). <em>A Practical End-to-End Inventory Management Model with Deep Learning</em>. Management Science 69(2):759–773. <a href="https://doi.org/10.1287/mnsc.2022.4564">正式出版页</a>；<a href="https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2022.4564">补充材料页</a>。理论：§3及附录A；网络与超参数：§3、附录B；离线图2：印刷页766；现场表2–3：页768，表4：页769。</li><li>用户提供的原始<code>replication_package_MS-FTBDA-20-01585.zip</code>及其README、CSV和3份Jupyter笔记本，为本次数据与可执行评价逻辑的直接来源。</li><li>本报告的统计扩展和口径审计由随附<code>replicate.py</code>生成，非原论文报告结论。原文件保持原样。</li></ol>
'''+table(['关键输入','字节数','SHA-256'],hashrows,'表13　关键输入指纹；完整清单位于results/source_manifest.json')+'''
<p class="small">本HTML的导航与逐SKU查询使用内置脚本；图表、样式与数据均已嵌入，没有外部字体、脚本或网络请求。可通过浏览器打印功能另存PDF，但本次正式提交文件为HTML。</p>
''')
per=pd.read_csv(R/'offline_per_sku.csv',dtype={'SKU':str});embedded={'methods':methods,'rows':[[r['SKU']]+[float(r[m]) for m in methods] for _,r in per.iterrows()]}
datajson=json.dumps(embedded,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
JS='''
"use strict";
const D=JSON.parse(document.getElementById('skuData').textContent);
const ids={};['skuSearch','baseline','skuBody','explorerSummary','pageLabel','prevPage','nextPage','csvDownload'].forEach(id=>ids[id]=document.getElementById(id));
let page=0;const pageSize=30;let filtered=[];
const fmt=x=>x.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
function render(reset=false){
 if(reset)page=0;
 const term=ids.skuSearch.value.trim().toLowerCase();filtered=D.rows.filter(r=>r[0].toLowerCase().includes(term));
 const bi=D.methods.indexOf(ids.baseline.value)+1,ri=D.methods.indexOf('E2E_RNN')+1;
 const pages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.max(0,Math.min(page,pages-1));ids.skuBody.replaceChildren();
 filtered.slice(page*pageSize,(page+1)*pageSize).forEach(r=>{
  const tr=document.createElement('tr');const rate=r[bi]!==0?fmt(100*(1-r[ri]/r[bi]))+'%':'—';
  [r[0],fmt(r[ri]),fmt(r[bi]),fmt(r[ri]-r[bi]),rate].forEach(x=>{const td=document.createElement('td');td.textContent=x;tr.appendChild(td);});ids.skuBody.appendChild(tr);
 });
 const sum=(idx)=>filtered.reduce((s,r)=>s+r[idx],0);const av=filtered.length?sum(ri)/filtered.length:0;const bv=filtered.length?sum(bi)/filtered.length:0;
 ids.explorerSummary.textContent=`匹配 ${filtered.length} / ${D.rows.length} 个SKU；RNN平均成本 ${fmt(av)}；基准平均成本 ${fmt(bv)}；均值成本降幅 ${bv?fmt(100*(1-av/bv))+'%':'—'}。`;
 ids.pageLabel.textContent=`第 ${page+1} / ${pages} 页，每页 ${pageSize} 行`;ids.prevPage.disabled=page===0;ids.nextPage.disabled=page===pages-1;
}
ids.skuSearch.addEventListener('input',()=>render(true));ids.baseline.addEventListener('change',()=>render(true));ids.prevPage.addEventListener('click',()=>{page--;render();});ids.nextPage.addEventListener('click',()=>{page++;render();});
ids.csvDownload.addEventListener('click',()=>{
 const bi=D.methods.indexOf(ids.baseline.value)+1,ri=D.methods.indexOf('E2E_RNN')+1;
 const quote=x=>'"'+String(x).replace(/"/g,'""')+'"';const rows=[['SKU','E2E_RNN',ids.baseline.value,'RNN_minus_baseline','reduction_percent'],...filtered.map(r=>[r[0],r[ri],r[bi],r[ri]-r[bi],r[bi]?100*(1-r[ri]/r[bi]):''])];
 const blob=new Blob(['\\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\\r\\n')],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='T1_SKU_comparison.csv';a.click();URL.revokeObjectURL(a.href);
});render(true);
'''
content='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="T1库存管理论文公开数据复现报告：离线与现场统计、口径审计、匹配和可复运行代码。"><title>T1 论文复现报告｜端到端库存管理与深度学习</title><style>'''+CSS+'''</style></head><body><header><div class="overline">人工智能与经济管理研究课程 · 论文复现 T1</div><h1>端到端库存管理与深度学习<br>公开数据复现与方法审计</h1><p>A Practical End-to-End Inventory Management Model with Deep Learning</p><div class="tags"><span class="tag">Management Science · 2023</span><span class="tag">实际Python计算</span><span class="tag">离线HTML · 内嵌数据</span><span class="tag">2026-10-25</span></div></header><div class="layout"><nav aria-label="报告目录"><strong>报告目录</strong>'''+''.join(f'<a href="#{key}">{i:02d} {title}</a>' for i,(key,title) in enumerate(navs))+'''</nav><main>'''+''.join(parts)+'''<footer>生成工具：build_report.py · 数值来源：replicate.py的results目录 · 原始数据指纹见证据索引<br>本报告如实区分论文报告值、公开样本重算值与新增审计分析。</footer></main></div><script type="application/json" id="skuData">'''+datajson+'''</script><script id="reportScript">'''+JS+'''</script></body></html>'''
path=O/'T1_论文复现报告.html';path.write_text(content,encoding='utf-8');print(f'HTML: {path} ({path.stat().st_size:,} bytes)')
