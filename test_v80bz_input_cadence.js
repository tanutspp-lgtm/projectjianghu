// Validate exact inline onlineSendInput() from the Netlify output without a browser.
const fs=require('fs');const assert=require('assert');
const source=fs.readFileSync('../jianghu_v80bz_front/index.html','utf8');
const begin=source.indexOf('function onlineSendInput(force=false){');
if(begin<0)throw Error('input sender missing');
let depth=0,end=0;
for(let i=source.indexOf('{',begin);i<source.length;i++){
 if(source[i]==='{')depth++;else if(source[i]==='}'&&!--depth){end=i+1;break;}
}
const fn=source.substring(begin,end);
let time=1000,bits=0;
const sent=[];
const WebSocket={OPEN:1};
const performance={now:()=>time};
const document={hidden:false};
const online={mode:'connected',ws:{readyState:1,bufferedAmount:0,send:s=>sent.push(JSON.parse(s))},queue:[],seq:0,lastInputSentAt:0,lastButtonsSent:null,predictor:{input(){}}};
const inputBits=()=>bits;
const send=new Function('online','performance','WebSocket','document','inputBits',`return (${fn.replace('function onlineSendInput','function')} )`)(online,performance,WebSocket,document,inputBits);
function next(t,mask,pressed){time=t;bits=mask;if(pressed)online.queue.push(pressed);send();}
next(1000,0);assert.equal(sent.length,1);
next(1100,0);assert.equal(sent.length,1,'idle must not spam');
next(1200,2);assert.equal(sent.length,2,'movement transition immediate');
next(1280,2);assert.equal(sent.length,2);
next(1450,2);assert.equal(sent.length,3,'held heartbeat <= 250ms');
next(1455,2,'attack');assert.equal(sent.length,4,'attack immediate');
next(1460,0);assert.equal(sent.length,5,'release immediate');
next(1800,0);assert.equal(sent.length,5,'no idle spam');
for(let i=1;i<sent.length;i++)assert(sent[i].seq>sent[i-1].seq);
for(const pkt of sent)assert.deepEqual(Object.keys(pkt).sort(),['buttons','pressed','seq','t']);
console.log('PASS BZ instant press/release, 220ms held heartbeat, idle suppression, no forged authority');
