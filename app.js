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
form.addEventListener("submit",e=>{e.preventDefault();result.hidden=true;let url;try{url=new URL(input.value.trim());if(!["https:","http:"].includes(url.protocol))throw Error();}catch{setStatus("Introduce una URL http o https válida.");return;}const platform=detectPlatform(url);if(mediaExt.test(url.pathname))showDirect(url);else showUnsupported(platform);});
const query=new URLSearchParams(location.search).get("url");if(query){input.value=query;form.requestSubmit();}
