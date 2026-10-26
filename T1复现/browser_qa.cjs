// Optional real-browser layout and interaction QA with bounded CDP calls.
// Starts a fresh headless profile inside the workspace, never the user's profile.
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),assert=require('node:assert/strict'),{pathToFileURL}=require('node:url');
const root=__dirname,qa=path.join(root,'output','qa');fs.mkdirSync(qa,{recursive:true});
const browser=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p=>fs.existsSync(p));assert.ok(browser,'An installed browser is required for optional visual QA.');
const tmp=path.resolve(root,'..','tmp');fs.mkdirSync(tmp,{recursive:true});const profile=fs.mkdtempSync(path.join(tmp,'T1_cdp_'));
assert.ok(profile.startsWith(tmp+path.sep));
const proc=spawn(browser,['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`],{windowsHide:true,stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let ws;let id=0;const pending=new Map();
async function main(){
 const active=path.join(profile,'DevToolsActivePort');for(let i=0;i<100&&!fs.existsSync(active);i++)await sleep(100);assert.ok(fs.existsSync(active),'DevTools ready in ten seconds');
 const [port,endpoint]=fs.readFileSync(active,'utf8').trim().split(/\r?\n/);ws=new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);
 await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
 ws.addEventListener('message',e=>{const msg=JSON.parse(e.data);if(msg.id&&pending.has(msg.id)){const x=pending.get(msg.id);clearTimeout(x.timer);pending.delete(msg.id);msg.error?x.reject(new Error(JSON.stringify(msg.error))):x.resolve(msg.result);}});
 const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>{pending.delete(n);reject(new Error('CDP timeout '+method));},10000);pending.set(n,{resolve,reject,timer});ws.send(JSON.stringify({id:n,method,params,...(sessionId?{sessionId}:{})}));});
 const {targetId}=await send('Target.createTarget',{url:'about:blank'});const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});const call=(method,params={})=>send(method,params,sessionId);
 await call('Page.enable');const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await call('Page.navigate',{url:pathToFileURL(path.join(root,'output','T1_论文复现报告.html')).href});
 for(let i=0;i<50;i++){if(await evaluate('document.readyState==="complete" && !!document.getElementById("skuBody") && document.getElementById("skuBody").children.length===30'))break;await sleep(100);}
 await evaluate('document.fonts.ready.then(()=>true)');const checks=[];
 for(const view of [{name:'desktop_top',width:1440,height:1100,section:null},{name:'desktop_field',width:1440,height:1100,section:'field'},{name:'mobile_top',width:430,height:1000,section:null},{name:'mobile_explorer',width:430,height:1000,section:'explore'}]){
  await call('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:false});
  await evaluate(`document.documentElement.style.scrollBehavior='auto';${view.section?`document.getElementById(${JSON.stringify(view.section)}).scrollIntoView();`:'window.scrollTo(0,0);'}true`);await sleep(200);
  const layout=await evaluate('({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,rows:document.getElementById("skuBody").children.length})');
  assert.equal(layout.viewport,view.width);assert.ok(layout.documentWidth<=view.width+1,'No page overflow: '+view.name+JSON.stringify(layout));assert.equal(layout.rows,30);
  const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(qa,view.name+'.png'),Buffer.from(shot.data,'base64'));checks.push({view:view.name,passed:true,...layout});
 }
 const controls=await evaluate(`(()=>{let input=document.getElementById('skuSearch');input.value='NO_SUCH_SKU_abcdef';input.dispatchEvent(new Event('input'));let empty=document.getElementById('skuBody').children.length===0;input.value='';input.dispatchEvent(new Event('input'));let b=document.getElementById('baseline');b.value='gbm';b.dispatchEvent(new Event('change'));let ok=document.getElementById('skuBody').children.length===30;document.getElementById('nextPage').click();return {empty,restored:ok,page:document.getElementById('pageLabel').textContent};})()`);
 assert.ok(controls.empty&&controls.restored&&controls.page.includes('第 2'));const result={passed:true,browser:path.basename(browser),checks,controls,note:'Actual Chrome headless: precise viewport, no page overflow, 30-row script render, section scrolling and controls; screenshots inspected separately'};
 fs.writeFileSync(path.join(root,'results','browser_validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));await send('Browser.close');
}
const watchdog=setTimeout(()=>{proc.kill();process.exitCode=1;console.error('Browser QA exceeded 55-second bound');},55000);
main().catch(e=>{console.error(e);proc.kill();process.exitCode=1;}).finally(async()=>{clearTimeout(watchdog);if(ws)ws.close();await sleep(500);try{const resolved=fs.realpathSync(profile);assert.ok(resolved.startsWith(fs.realpathSync(tmp)+path.sep));fs.rmSync(resolved,{recursive:true,force:true,maxRetries:5,retryDelay:200});}catch(e){console.error('Temporary profile cleanup:',e.message);}});
