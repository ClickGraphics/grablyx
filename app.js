const form=document.querySelector("#grab");
const input=document.querySelector("#url");
const status=document.querySelector("#status");
const result=document.querySelector("#result");
const platforms=[
{name:"YouTube",hosts:["youtube.com","youtu.be"]},
{name:"Facebook",hosts:["facebook.com","fb.watch"]},
{name:"Instagram",hosts:["instagram.com"]},
{name:"TikTok",hosts:["tiktok.com"]},
{name:"X",hosts:["x.com","twitter.com"]},
{name:"Pinterest",hosts:["pinterest.com","pin.it"]},
{name:"Reddit",hosts:["reddit.com","redd.it"]}
];
const mediaExt=/\.(mp4|webm|mov|m4v|mp3|m4a|ogg|opus|wav|jpg|jpeg|png|webp|gif|avif)(?:$|[?#])/i;
function detectPlatform(url){const host=url.hostname.toLowerCase().replace(/^www\./,"");return platforms.find(p=>p.hosts.some(h=>host===h||host.endsWith("."+h)))?.name||"Enlace directo";}
function setStatus(message){status.textContent=message;}
function addAction(label,href,download){const a=document.createElement("a");a.textContent=label;a.href=href;a.target="_blank";a.rel="noopener noreferrer";a.className="download-action";if(download)a.download=download;result.append(a);}
function showDirect(url){result.hidden=false;result.replaceChildren();const h=document.createElement("h2");h.textContent="Archivo multimedia detectado";result.append(h);const p=document.createElement("p");p.textContent="Puedes abrir o guardar este archivo si el servidor de origen permite el acceso. Algunos sitios bloquean las descargas externas.";result.append(p);const filename=decodeURIComponent(url.pathname.split("/").pop()||"archivo");addAction("Abrir archivo",url.href);addAction("Intentar descargar",url.href,filename);setStatus("Enlace multimedia directo reconocido.");}
function showUnsupported(platform){result.hidden=false;result.replaceChildren();const h=document.createElement("h2");h.textContent=platform+" detectado";const p=document.createElement("p");p.textContent="La extracción de publicaciones de esta plataforma aún no está disponible. No te mostraremos descargas inventadas. Si tienes un enlace directo a un archivo multimedia público, puedes descargarlo aquí.";result.append(h,p);setStatus("Enlace reconocido; extractor de esta plataforma pendiente.");}
const API="https://grablyx-api.onrender.com";
async function analyze(url){
  status.textContent="Analizando enlace. El servidor gratuito puede tardar en activarse…";
  const button=form.querySelector("button");button.disabled=true;
  try {
    const response=await fetch(API+"/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:url.href})});
    const data=await response.json();
    if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:"No se pudo analizar el enlace.");
    result.hidden=false;result.replaceChildren();
    const title=document.createElement("h2");title.textContent=data.title||"Contenido detectado";result.append(title);
    const formats=(data.formats||[]).filter(f=>f.url&&f.url.startsWith("https://"));
    const unique=new Map();
    for(const f of formats){
      const kind=f.video?(f.audio?"video-audio":"video-only"):"audio";
      const key=[kind,f.ext||"",f.height||0].join(":");
      if(!unique.has(key))unique.set(key,f);
    }
    const sorted=[...unique.values()].sort((a,b)=>{
      const rank=f=>f.video&&f.audio?0:f.video?1:2;
      return rank(a)-rank(b)||(Number(b.height)||0)-(Number(a.height)||0);
    });
    if(!sorted.length){const p=document.createElement("p");p.textContent="No hay formatos de descarga compatibles disponibles.";result.append(p);}
    for(const [index,f] of sorted.slice(0,20).entries()){
      const quality=f.height?f.height+"p":f.video?"Video":"Audio";
      const label=(index===0&&f.video&&f.audio?"★ Recomendado · ":"")+quality+" · "+(f.ext||"archivo")+(f.video?(f.audio?" · con audio":" · sin audio"):"");
      addAction(label,f.url);
    }
    setStatus("Análisis finalizado. Los enlaces pueden caducar o estar restringidos por el origen.");
  }catch(error){setStatus("No se pudo analizar: "+error.message);}
  finally{button.disabled=false;}
}
form.addEventListener("submit",e=>{e.preventDefault();result.hidden=true;let url;try{url=new URL(input.value.trim());if(!["https:","http:"].includes(url.protocol))throw Error();}catch{setStatus("Introduce una URL http o https válida.");return;}if(mediaExt.test(url.pathname)){showDirect(url);return;}if(detectPlatform(url)==="Enlace directo"){setStatus("Plataforma no compatible.");return;}analyze(url);});
const query=new URLSearchParams(location.search).get("url");if(query){input.value=query;form.requestSubmit();}
