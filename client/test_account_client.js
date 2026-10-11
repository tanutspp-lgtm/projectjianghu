"use strict";
const assert=require('node:assert/strict');

global.window=global;
const saved=new Map();
global.sessionStorage={
  getItem:key=>saved.get(key)||null,
  setItem:(key,value)=>saved.set(key,value),
  removeItem:key=>saved.delete(key),
};
let refreshCount=0;
global.fetch=async(url,options)=>{
  let payload={};
  if(url.includes('grant_type=password'))payload={access_token:'access-1',refresh_token:'refresh-1',expires_at:Math.floor(Date.now()/1000)+30,user:{id:'user-1',email:'test@example.invalid'}};
  else if(url.includes('grant_type=refresh_token')){refreshCount++;payload={access_token:'access-2',refresh_token:'refresh-2',expires_at:Math.floor(Date.now()/1000)+3600,user:{id:'user-1',email:'test@example.invalid'}};}
  return {ok:true,status:200,json:async()=>payload};
};

require('./account_client.js');

(async()=>{
  const account=WuxiaAccount.create('https://project.supabase.co','p'.repeat(32));
  assert.equal(account.configured,true);
  await account.signIn('test@example.invalid','password123');
  assert.equal((await account.getAccessToken()),'access-2');
  assert.equal(refreshCount,1);
  assert.equal(account.getSession().refresh_token,'refresh-2');
  await account.signOut();
  assert.equal(account.getSession(),null);
  console.log('ACCOUNT CLIENT TESTS PASSED: session storage, refresh rotation, sign-out');
})().catch(error=>{console.error(error);process.exitCode=1});
