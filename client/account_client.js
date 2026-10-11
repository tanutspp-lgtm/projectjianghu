/* v7.9N minimal Supabase Auth adapter for the static browser client.
   Only the public URL/key live here. Access/refresh tokens stay in sessionStorage
   and are never placed in the WebSocket URL. */
(function(global){
  'use strict';
  function create(url,publishableKey){
    url=String(url||'').replace(/\/+$/,'');publishableKey=String(publishableKey||'').trim();
    const configured=/^https:\/\/[^/]+$/i.test(url)&&publishableKey.length>=20;
    const storageKey='jianghu-auth-session-v1:'+url;
    let session=null,refreshPromise=null;
    function save(value){session=value||null;try{if(session)sessionStorage.setItem(storageKey,JSON.stringify(session));else sessionStorage.removeItem(storageKey)}catch{}}
    function restore(){
      if(!configured)return null;
      try{const value=JSON.parse(sessionStorage.getItem(storageKey)||'null');if(value&&value.access_token&&value.refresh_token)session=value;}catch{}
      return session;
    }
    async function request(path,body,accessToken){
      const response=await fetch(url+path,{method:'POST',headers:{'apikey':publishableKey,'Content-Type':'application/json',...(accessToken?{'Authorization':'Bearer '+accessToken}:{})},body:body===undefined?undefined:JSON.stringify(body)});
      let payload={};try{payload=await response.json()}catch{}
      if(!response.ok){const error=new Error(payload.msg||payload.message||payload.error_description||payload.error||'ยืนยันบัญชีไม่สำเร็จ');error.status=response.status;throw error;}
      return payload;
    }
    function normalize(payload){
      const expiresAt=Number(payload.expires_at)||Math.floor(Date.now()/1000)+Number(payload.expires_in||0);
      const value={access_token:payload.access_token,refresh_token:payload.refresh_token,expires_at:expiresAt,user:payload.user||session?.user||null};
      if(!value.access_token||!value.refresh_token)throw new Error('เซิร์ฟเวอร์บัญชีไม่ส่ง session กลับมา');
      save(value);return value;
    }
    async function signIn(email,password){return normalize(await request('/auth/v1/token?grant_type=password',{email,password}));}
    async function signUp(email,password){
      const payload=await request('/auth/v1/signup',{email,password});
      if(payload.access_token)return {session:normalize(payload),needsConfirmation:false};
      return {session:null,needsConfirmation:true,user:payload.user||null};
    }
    async function refresh(){
      if(!session?.refresh_token)throw new Error('กรุณาเข้าสู่ระบบใหม่');
      if(refreshPromise)return refreshPromise;
      refreshPromise=request('/auth/v1/token?grant_type=refresh_token',{refresh_token:session.refresh_token}).then(normalize).catch(error=>{save(null);throw error}).finally(()=>{refreshPromise=null});
      return refreshPromise;
    }
    async function getAccessToken(){
      if(!session)restore();
      if(!session)throw new Error('กรุณาเข้าสู่ระบบก่อน');
      if(Number(session.expires_at||0)<=Math.floor(Date.now()/1000)+90)await refresh();
      return session.access_token;
    }
    async function signOut(){
      const current=session;save(null);
      if(current?.access_token)try{await request('/auth/v1/logout',undefined,current.access_token)}catch{}
    }
    restore();
    return {configured,signIn,signUp,signOut,getAccessToken,refresh,getSession:()=>session};
  }
  global.WuxiaAccount={create};
})(window);
