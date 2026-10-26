// Functional QA of the actual embedded HTML script using a minimal DOM.
// This checks controls and CSV output; it does not replace a browser rendering check.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=__dirname,text=fs.readFileSync(path.join(root,'output','T1_论文复现报告.html'),'utf8');
const data=text.match(/<script type="application\/json" id="skuData">([\s\S]*?)<\/script>/)[1];
const code=text.match(/<script id="reportScript">([\s\S]*?)<\/script>/)[1];
class Element{constructor(){this.value='';this.textContent='';this.children=[];this.listeners={};this.disabled=false;}replaceChildren(){this.children=[];}appendChild(c){this.children.push(c);}addEventListener(k,f){this.listeners[k]=f;}click(){if(this.listeners.click)this.listeners.click();}}
const nodes={},ids=['skuData','skuSearch','baseline','skuBody','explorerSummary','pageLabel','prevPage','nextPage','csvDownload'];ids.forEach(id=>nodes[id]=new Element());nodes.skuData.textContent=data;nodes.baseline.value='Bm2';let blob;
const ctx=vm.createContext({document:{getElementById:id=>nodes[id],createElement:()=>new Element()},Blob,URL:{createObjectURL:b=>{blob=b;return'blob:test';},revokeObjectURL:()=>{}},console});
vm.runInContext(code,ctx);assert.equal(nodes.skuBody.children.length,30);assert.match(nodes.explorerSummary.textContent,/2607 \/ 2607/);assert.equal(nodes.prevPage.disabled,true);
nodes.nextPage.click();assert.match(nodes.pageLabel.textContent,/第 2/);assert.equal(nodes.prevPage.disabled,false);
const first=JSON.parse(data).rows[0][0];nodes.skuSearch.value=first;nodes.skuSearch.listeners.input();assert.ok(nodes.skuBody.children.length>0);assert.ok(nodes.skuBody.children.every(tr=>tr.children[0].textContent.toLowerCase().includes(first.toLowerCase())));
nodes.skuSearch.value='NO_SUCH_SKU_abcdef';nodes.skuSearch.listeners.input();assert.equal(nodes.skuBody.children.length,0);assert.match(nodes.explorerSummary.textContent,/匹配 0/);
nodes.skuSearch.value='';nodes.skuSearch.listeners.input();nodes.baseline.value='OPT';nodes.baseline.listeners.change();assert.equal(nodes.skuBody.children.length,30);nodes.csvDownload.click();assert.ok(blob instanceof Blob);
blob.text().then(csv=>{assert.match(csv,/"SKU","E2E_RNN","OPT"/);assert.equal(csv.trim().split('\r\n').length,2608);const result={passed:true,checks:['initial render','next-page pagination','SKU filtering','empty filter','baseline change','CSV export 2607 rows'],note:'Node minimal-DOM interaction test; native browser rendering not performed'};fs.writeFileSync(path.join(root,'results','javascript_validation.json'),JSON.stringify(result,null,2));console.log('PASS: embedded script controls and CSV download');}).catch(e=>{console.error(e);process.exitCode=1;});
