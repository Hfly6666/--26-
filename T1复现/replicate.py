from pathlib import Path
import numpy as np,pandas as pd
from scipy import stats,optimize,special
from scipy.spatial import cKDTree
import json,ast,hashlib,platform,sys,math,io,contextlib,collections
ROOT=Path(__file__).resolve().parent;UP=ROOT/'upstream';RES=ROOT/'results';RES.mkdir(exist_ok=True)
METRICS=['holding','stockout','total','turnover','stockout_rate']
def dump(name,obj):
 def default(x):
  if isinstance(x,np.ndarray):return x.tolist()
  if isinstance(x,np.generic):return x.item()
  raise TypeError(type(x).__name__)
 (RES/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=default,allow_nan=False),encoding='utf-8')
def notebook(name):return json.loads(next(UP.rglob(name+'*.ipynb')).read_text(encoding='utf-8'))

def replay_offline():
 nb=notebook('E2E_Section4');ns={'pd':pd,'np':np,'gamma':stats.gamma,'math':math};audit=[]
 for i,c in enumerate(nb['cells']):
  if c['cell_type']!='code' or not ''.join(c['source']).strip():continue
  if i in [0,16]:
   audit.append({'cell':i,'status':'skipped imports/LaTeX display only'});continue
  src=''.join(c['source']).replace('pd.read_csv("df_test.csv")',f'pd.read_csv({str(UP/"df_test.csv")!r})')
  exec(compile(src,f'<author offline cell {i}>','exec'),ns)
  audit.append({'cell':i,'status':'executed','source_sha256':hashlib.sha256(''.join(c['source']).encode()).hexdigest()})
 agg=ns['df_aggcom'];agg.to_csv(RES/'offline_author_summary.csv',encoding='utf-8-sig')
 costs=ns['df_cost_agg'].copy();costs['SKU']=ns['df_test'].index.tolist();costs.to_csv(RES/'offline_per_sku.csv',index=False,encoding='utf-8-sig')
 # Cross-check actual recomputation against the notebook's captured golden output.
 golden=np.array([[2572.964327,3036.758343,3842.305332,3837.828539,3961.691600,4099.949751,3424.869965],[1363.218642,1883.591484,1709.364020,1541.630610,2317.097814,1947.838128,1424.929804],[1209.745685,1153.166858,2132.941312,2296.197929,1644.593786,2152.111623,1999.940161]])
 assert np.max(abs(agg.to_numpy()-golden))<1e-5
 dump('offline_notebook_audit.json',{'cells':audit,'golden_max_abs_error':float(np.max(abs(agg.to_numpy()-golden))),'input_rows':3000,'grouped_skus':len(costs),'summary':agg.to_dict()})
 return ns,costs

def independent_path(row,name,clip=False,include_all=False):
 I=[row['initial_stock'][0]];score=[];actions=[];fallback=0;skipped=0
 for r in range(len(row['OPT_pred'])):
  demand=row['demand_hist'][r];n=len(demand)-(r<len(row['OPT_pred'])-1);lead=int(round(row['vlt'][r]))
  for t in range(n):
   if t==0:
    if r==0:before=I[0]
    else:
     idx=-lead-1
     if abs(idx)<=len(I):before=I[idx]
     else:before=I[1];fallback+=1
    action=int(round(row[name+'_pred'][r]-before));actions.append(action)
    if clip:action=max(0,action)
   if t<lead:
    if r==0:I.append(I[-1]-demand[t])
    else:skipped+=1
   else:
    if t==lead:new=max(I[-1],0)+action-demand[t]
    else:new=I[-1]-demand[t]
    I.append(new);score.append(new)
 scored=I[1:] if include_all else score
 a=np.asarray(scored);return np.sum(np.maximum(a,0)),9*np.sum(np.maximum(-a,0)),actions,fallback,skipped

def audit_offline(ns,costs):
 grouped=ns['df_test'];names=ns['str_list'];checks=[];variants=[]
 for name in names:
  holds=[];backs=[];clipped=[];allperiod=[];negative=0;fallback=0;skip=0;actionn=0
  for _,row in grouped.iterrows():
   h,b,actions,fb,sk=independent_path(row,name);holds.append(h);backs.append(b);negative+=sum(a<0 for a in actions);actionn+=len(actions);fallback+=fb;skip+=sk
   h1,b1,*_=independent_path(row,name,clip=True);clipped.append(h1+b1)
   h2,b2,*_=independent_path(row,name,include_all=True);allperiod.append(h2+b2)
  assert np.max(abs(np.array(holds)+backs-costs[name].to_numpy()))<1e-8
  checks.append({'method':name,'negative_orders':negative,'order_decisions':actionn,'fallback_count':fallback,'skipped_pre_arrival_loop_days':skip,'max_independent_cost_difference':float(np.max(abs(np.array(holds)+backs-costs[name].to_numpy())))})
  variants.append({'method':name,'author_cost':float(costs[name].mean()),'clip_negative_orders_cost':float(np.mean(clipped)),'include_initial_lead_window_cost':float(np.mean(allperiod))})
 dump('offline_semantic_audit.json',checks);dump('offline_simulator_sensitivity.json',variants)
 # Eq.(7) Normal correction, while retaining the author's evaluation dynamics.
 raw=pd.read_csv(UP/'df_test.csv');L=raw.review_period+raw.vendor_vlt_mean
 raw['normal_paper_pred']=np.floor(raw.demand_mean*L+stats.norm.ppf(.9)*np.sqrt(L*raw.demand_std**2+raw.demand_mean**2*raw.vendor_vlt_std**2))
 raw['sf_rnn']=raw.sf_rnn.map(ast.literal_eval);raw['demand_hist']=raw.demand_hist.map(lambda x:np.fromstring(x.strip('[]'),sep=' '))
 gr=raw.groupby('SKU').agg(lambda x:x.tolist());v=[]
 for _,r in gr.iterrows():a,b,*_=independent_path(r,'normal_paper');v.append(a+b)
 dump('normal_equation_audit.json',{'author_normal_mean':float(costs.Normal.mean()),'paper_eq7_normal_mean':float(np.mean(v)),'author_z':1.64,'paper_90th_quantile':float(stats.norm.ppf(.9)),'source_issue':'notebook uses demand_std**2*vendor_vlt_std instead of demand_mean**2*vendor_vlt_std**2; equation-based branch floors the resulting stock target; same sequential evaluator retained'})
 # Paired-SKU bootstrap: sampled identities, not individual demand periods.
 rng=np.random.default_rng(20261025);rows=[];n=len(costs);indices=rng.integers(0,n,size=(2000,n))
 for name in names:
  if name in ['OPT','E2E_RNN']:continue
  x=costs.E2E_RNN.to_numpy();y=costs[name].to_numpy();delta=x-y;means=delta[indices].mean(axis=1)
  reductions=100*(1-x[indices].mean(axis=1)/y[indices].mean(axis=1))
  rows.append({'baseline':name,'difference':float(delta.mean()),'difference_ci':np.quantile(means,[.025,.975]),'reduction_pct':100*(1-x.mean()/y.mean()),'reduction_ci':np.quantile(reductions,[.025,.975]),'e2e_lower_sku_pct':100*float((x<y).mean())})
 dump('offline_bootstrap.json',rows)

def field_rows(path,include_last=False,weight_h=1.,weight_b=9.):
 d=pd.read_csv(path);out=[]
 for _,r in d.iterrows():
  inv=np.array(ast.literal_eval(r.test_inv));a=inv if include_last else inv[:-1]
  hold=weight_h*np.maximum(a,0).sum();back=weight_b*np.maximum(-a,0).sum();vlt=float(str(r.vlt).split()[0])
  out.append({'id':int(r.sku_dc_pair_index),'holding':hold,'stockout':back,'total':hold+back,'turnover':max(0,r.ave_inv/r.ave_demand),'raw_turnover':r.ave_inv/r.ave_demand,'stockout_rate':float((a<0).sum()/len(inv)),'stockout_rate_consistent_denominator':float((a<0).mean()) if len(a) else None,'demand':r.ave_demand,'vlt':vlt,'curve_length':len(inv),'measured_days':len(a),'total_per_measured_day':float((hold+back)/len(a)) if len(a) else None,'last_inv':float(inv[-1])})
 return pd.DataFrame(out)

def ols(y,X,cov='classical',clusters=None):
 y=np.asarray(y,float);X=np.asarray(X,float);N,k=X.shape;rank=np.linalg.matrix_rank(X);assert rank==k
 bread=np.linalg.inv(X.T@X);beta=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@beta
 if cov=='classical':V=(e@e)/(N-k)*bread;df=N-k
 elif cov=='HC3':
  lever=np.einsum('ij,jk,ik->i',X,bread,X);z=X*(e/(1-lever))[:,None];V=bread@(z.T@z)@bread;df=N-k
 elif cov=='cluster':
  groups=np.unique(clusters);scores=np.array([(X[clusters==g]*e[clusters==g,None]).sum(axis=0) for g in groups]);V=bread@(scores.T@scores)@bread*(len(groups)/(len(groups)-1))*((N-1)/(N-k));df=len(groups)-1
 se=np.sqrt(np.diag(V));t=beta/se;p=2*stats.t.sf(abs(t),df);ci=np.c_[beta-stats.t.ppf(.975,df)*se,beta+stats.t.ppf(.975,df)*se]
 return {'beta':beta,'se':se,'t':t,'p':p,'ci':ci,'n':N,'rank':int(rank),'covariance':cov}

def replay_field():
 frames={f'{g}_{t}':field_rows(UP/f'order_{g}_{t}_500.csv') for g in ['e2e','jd'] for t in ['pre','post']}
 for k,d in frames.items():d.to_csv(RES/f'field_{k}_metrics.csv',index=False,encoding='utf-8-sig')
 summary={k:d[METRICS].mean().to_dict() for k,d in frames.items()};dump('field_summary.json',summary)
 golden={'e2e_post':[497.99,386.1,884.09,12.268704620140678,.10827010628260629],'jd_post':[841.428,1143.72,1985.148,18.47105619138942,.23652916666666668],'e2e_pre':[666.394,815.868,1482.262,15.487856815194194,.23613333333333333],'jd_pre':[506.46,473.13,979.59,15.152613035317902,.19752527930902117]}
 maxerr=max(float(np.max(abs(np.array(list(summary[k].values()))-v))) for k,v in golden.items());assert maxerr<1e-6
 tt=[];reg=[];did=[];sens=[]
 A=frames['e2e_post'];B=frames['jd_post'];yframe=pd.concat([A,B],ignore_index=True);treat=np.r_[np.ones(len(A)),np.zeros(len(B))];X=np.c_[treat,yframe.vlt,yframe.demand]
 for m in METRICS:
  pooled=stats.ttest_ind(A[m],B[m]);welch=stats.ttest_ind(A[m],B[m],equal_var=False)
  tt.append({'metric':m,'treatment_mean':A[m].mean(),'control_mean':B[m].mean(),'reduction_pct':100*(1-A[m].mean()/B[m].mean()),'pooled_t':float(pooled.statistic),'pooled_p':float(pooled.pvalue),'welch_p':float(welch.pvalue)})
  for mode,mat,cov in [('notebook_no_intercept',X,'classical'),('paper_eq11_intercept',np.c_[np.ones(len(X)),X],'classical'),('intercept_HC3',np.c_[np.ones(len(X)),X],'HC3')]:
   r=ols(yframe[m],mat,cov);j=0 if mode=='notebook_no_intercept' else 1;reg.append({'metric':m,'specification':mode,'e2e_coef':r['beta'][j],'se':r['se'][j],'p':r['p'][j],'ci':r['ci'][j],'n':r['n']})
  preA=frames['e2e_pre'][m].to_numpy();preB=frames['jd_pre'][m].to_numpy();post=A[m].to_numpy()-B[m].to_numpy();pre=preA-preB;dt=stats.ttest_ind(post,pre)
  changeA=A[m].to_numpy()-preA;changeB=B[m].to_numpy()-preB;effect=changeA.mean()-changeB.mean()
  # Build a four-cell panel, grouping only within the supplied arm-specific IDs.
  yy=np.r_[preA,A[m],preB,B[m]];tr=np.r_[np.ones(1000),np.zeros(1000)];po=np.tile(np.r_[np.zeros(500),np.ones(500)],2);unit=np.r_[np.arange(500),np.arange(500),np.arange(500,1000),np.arange(500,1000)]
  rr=ols(yy,np.c_[np.ones(2000),tr,po,tr*po],'cluster',unit);assert abs(effect-rr['beta'][3])<1e-8
  did.append({'metric':m,'e2e_pre':preA.mean(),'e2e_post':A[m].mean(),'control_pre':preB.mean(),'control_post':B[m].mean(),'effect':effect,'notebook_row_difference_t':float(dt.statistic),'notebook_row_difference_p':float(dt.pvalue),'cluster_se':rr['se'][3],'cluster_p':rr['p'][3],'cluster_ci':rr['ci'][3],'panel_id_assumption':'supplied row IDs represent same unit within arm across periods; no original identity crosswalk published'})
 # Different field weights and terminal-day choices are audit branches, not selected replacements.
 for label,last,h,b in [('notebook',False,1,9),('paper_h12_b88',False,12,88),('include_last_day',True,1,9)]:
  vals={k:field_rows(UP/f'order_{k}_500.csv',last,h,b) for k in frames}
  for m in METRICS:
   a=vals['e2e_post'][m].mean();b0=vals['jd_post'][m].mean();effect=(a-vals['e2e_pre'][m].mean())-(b0-vals['jd_pre'][m].mean())
   sens.append({'branch':label,'metric':m,'treatment_post':a,'control_post':b0,'reduction_pct':100*(1-a/b0),'did':effect})
 dump('field_ttests.json',tt);dump('field_regressions.json',reg);dump('field_did.json',did);dump('field_sensitivity.json',sens);dump('field_validation.json',{'golden_max_abs_error':maxerr,'cell_counts':{k:len(v) for k,v in frames.items()},'pre_post_id_coverage':{g:len(set(frames[g+'_pre'].id)&set(frames[g+'_post'].id)) for g in ['e2e','jd']}})
 horizons={k:{'n':len(d),'min_measured_days':int(d.measured_days.min()),'max_measured_days':int(d.measured_days.max()),'mean_measured_days':float(d.measured_days.mean()),'zero_measured_days':int((d.measured_days==0).sum()),'negative_average_inventory_records':int((d.raw_turnover<0).sum()),'day_histogram':{str(int(a)):int(b) for a,b in d.measured_days.value_counts().sort_index().items()},'total_cost_per_observed_day':float(d.total.sum()/d.measured_days.sum()),'unweighted_mean_unit_day_cost':float(d.total_per_measured_day.mean()),'nonempty_units':int(d.total_per_measured_day.notna().sum())} for k,d in frames.items()}
 dump('field_horizon_audit.json',horizons)
 # Inspect source notebook cells in order; retained outputs are not taken as evidence of a rerun.
 nb=notebook('Field_experiments_summary');scope={'pd':pd,'np':np,'stats':stats};executed=[];captured=io.StringIO();tests=[]
 with contextlib.redirect_stdout(captured):
  for i,c in enumerate(nb['cells']):
   if c['cell_type']!='code' or not ''.join(c['source']).strip() or i==0 or 19<=i<=27:continue
   src=''.join(c['source'])
   for key in frames:src=src.replace(f"'order_{key}_500.csv'",repr(str(UP/f'order_{key}_500.csv')))
   exec(compile(src,f'<author field cell {i}>','exec'),scope);executed.append(i)
   if i in [38,40,42,44,46]:
    j=[38,40,42,44,46].index(i);saved=''.join(''.join(o.get('text',[])) for o in c.get('outputs',[]))
    tests.append({'metric':METRICS[j],'cell':i,'reexecuted_t':float(scope['t']),'reexecuted_p':float(scope['p']),'saved_output':saved,'post_gap_mean':float(np.mean(scope['post'])),'pre_gap_mean':float(np.mean(scope['pre'])),'reexecuted_effect':float(np.mean(scope['post'])-np.mean(scope['pre']))})
 (RES/'field_notebook_rerun.log').write_text(captured.getvalue(),encoding='utf-8')
 dump('field_notebook_did_audit.json',{'executed_cells':executed,'skipped':'imports cell 0; regressions cells 19-27 independently evaluated by NumPy OLS; others replayed unchanged except absolute input paths','did_tests':tests,'note':'cell 29 uses unclipped control post turnover while other three turnover vectors are clipped; harmonized DID reported separately'})
 return frames

def matching(frames):
 treat=frames['e2e_post'][['demand','vlt']].to_numpy();pool=pd.read_csv(UP/'control_demand_vlt.csv');control=pool[['ave_demand','vlt_num']].to_numpy(float)
 X=np.vstack([treat,control]);y=np.r_[np.ones(len(treat)),np.zeros(len(control))];Z=np.c_[np.ones(len(X)),X]
 # Same L2 C=1 objective as default logistic regression: intercept unpenalized.
 def objective(beta):
  a=Z@beta;return np.logaddexp(0,a).sum()-y@a+.5*(beta[1:]@beta[1:])
 def grad(beta):g=Z.T@(special.expit(Z@beta)-y);g[1:]+=beta[1:];return g
 def hess(beta):p=special.expit(Z@beta);H=Z.T@((p*(1-p))[:,None]*Z);H[1:,1:]+=np.eye(2);return H
 fit=optimize.minimize(objective,np.array([math.log(len(treat)/len(control)),0.,0.]),jac=grad,hess=hess,method='trust-exact',options={'gtol':1e-7,'maxiter':200});beta=fit.x;score=special.expit(Z@beta)
 # Author matching is raw covariate Euclidean NN with replacement, not score NN.
 tree=cKDTree(control);dist,idx=tree.query(treat,k=1)
 # Deterministic smallest-row-index rule among numerical ties; distance is unchanged.
 tie_counts=[]
 for i,x in enumerate(treat):
  candidates=tree.query_ball_point(x,float(dist[i])+1e-10);d2=((control[candidates]-x)**2).sum(axis=1);best=d2.min();near=np.asarray(candidates)[abs(d2-best)<1e-10];idx[i]=near.min();tie_counts.append(len(near))
 chosen=control[idx];matchscore=score[len(treat):][idx]
 def balance(other,label):
  sd=np.sqrt((treat.var(axis=0,ddof=1)+control.var(axis=0,ddof=1))/2)
  return [{'sample':label,'feature':f,'treatment_mean':float(treat[:,j].mean()),'control_mean':float(other[:,j].mean()),'standardized_mean_difference':float((treat[:,j].mean()-other[:,j].mean())/sd[j])} for j,f in enumerate(['demand','vlt'])]
 bal=balance(control,'candidate_pool')+balance(chosen,'raw_covariate_nn')+balance(frames['jd_post'][['demand','vlt']].to_numpy(),'released_control')
 # Supplementary one-dimensional propensity-score matching for distinction.
 dps,ips=cKDTree(score[len(treat):,None]).query(score[:len(treat),None],k=1);bal+=balance(control[ips],'score_nn')
 (RES/'matching_pairs.csv').write_text(pd.DataFrame({'treatment_row':np.arange(500),'candidate_row':idx,'euclidean_distance':dist,'ties_at_best_distance':tie_counts,'treated_score':score[:500],'matched_score':matchscore}).to_csv(index=False),encoding='utf-8-sig')
 np.savez_compressed(RES/'propensity_arrays.npz',treated=score[:500],candidate=score[500:],matched=matchscore)
 released=frames['jd_post'][['demand','vlt']].to_numpy()
 sortrows=lambda a:a[np.lexsort((a[:,1],a[:,0]))]
 dump('matching.json',{'n_treated':500,'n_candidates':len(control),'logistic_beta':beta,'gradient_inf_norm':float(abs(grad(beta)).max()),'solver_success':bool(fit.success),'solver_message':str(fit.message),'matched_unique_candidates':len(set(idx.tolist())),'zero_distance_matches':int((dist<1e-10).sum()),'ties':int((np.array(tie_counts)>1).sum()),'max_distance':float(dist.max()),'released_control_covariate_max_row_difference':float(np.max(abs(chosen-released))),'released_control_sorted_covariate_max_difference':float(np.max(abs(sortrows(chosen)-sortrows(released)))),'balance':bal,'limitations':'matching candidate covariates cannot be linked to released 500 control outcome IDs; no private identity mapping is inferred'})

def validate_theorem():
 rng=np.random.default_rng(20261025);single=0;worst=0.;dynamic=0
 for alpha in [.1,.5,.88,.9,.95]:
  for _ in range(200):
   d=rng.integers(0,8,size=int(rng.integers(1,20)));I=int(rng.integers(-10,30));c=np.cumsum(d);q=max(0,int(c[min(len(c)-1,math.floor(alpha*len(c)))])-I)
   opts=np.arange(max(1,int(c[-1]-I+2)));C=((1-alpha)*np.maximum(I+opts[:,None]-c,0)+alpha*np.maximum(c-I-opts[:,None],0)).sum(axis=1)
   cand=float(((1-alpha)*np.maximum(I+q-c,0)+alpha*np.maximum(c-I-q,0)).sum());worst=max(worst,cand-C.min());assert cand<=C.min()+1e-9;single+=1
 # Two arrival cycles; exhaustive actions vs sequential ex-post formula.
 for _ in range(100):
  d=rng.integers(0,4,size=4);I=int(rng.integers(-3,7));h=1;b=9;c1=np.cumsum(d[:2]);q1=max(0,int(c1[1])-I);I2=I+q1-d[:2].sum();q2=max(0,int(np.cumsum(d[2:])[1])-I2)
  def cost(a1,a2):
   levels=np.array([I+a1-d[0],I+a1-d[0]-d[1],I+a1+a2-d[:3].sum(),I+a1+a2-d.sum()]);return np.maximum(levels,0).sum()+9*np.maximum(-levels,0).sum()
  upper=int(d.sum()+abs(I)+2);best=min(cost(a1,a2) for a1 in range(upper+1) for a2 in range(upper+1));assert abs(cost(q1,q2)-best)<1e-9;dynamic+=1
 dump('theorem_validation.json',{'single_cycle_cases':single,'two_cycle_exhaustive_cases':dynamic,'max_cost_excess':worst,'note':'finite numerical checks under nonnegative demand and no arrival crossover; not a new mathematical proof'})

def provenance():
 import scipy,matplotlib
 files=[]
 for p in UP.rglob('*'):
  if p.is_file():files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 for p in [ROOT.parent/'文献和数据/T1-A practical End to End invontory management model with deep learning.pdf',ROOT.parent/'文献和数据/replication_package_MS-FTBDA-20-01585.zip']:
  if not p.exists():p=ROOT/'sources'/p.name
  if p.exists():files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 dump('source_manifest.json',files);dump('environment.json',{'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'platform':platform.platform(),'date':'2026-10-25 Asia/Shanghai','seed':20261025,'training':'no original training corpus or fitted weights in supplied package; supplied outputs evaluated'})
if __name__=='__main__':
 print('Offline notebook replay',flush=True);ns,costs=replay_offline();audit_offline(ns,costs)
 print('Field evaluation and robustness',flush=True);frames=replay_field()
 print('Matching',flush=True);matching(frames)
 print('Theorem validation',flush=True);validate_theorem();provenance();print('ALL REPLICATION CHECKS PASSED',flush=True)
