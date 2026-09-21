const form=document.querySelector("#grab"),input=document.querySelector("#url"),status=document.querySelector("#status");

const platforms=[
  {name:"YouTube",hosts:["youtube.com","youtu.be"]},
  {name:"Facebook",hosts:["facebook.com","fb.watch"]},
  {name:"Instagram",hosts:["instagram.com"]},
  {name:"TikTok",hosts:["tiktok.com"]},
  {name:"X",hosts:["x.com","twitter.com"]},
  {name:"Pinterest",hosts:["pinterest.com","pin.it"]},
  {name:"Reddit",hosts:["reddit.com","redd.it"]}
];

function detectPlatform(url){
  const host=url.hostname.toLowerCase().replace(/^www\./,"");
  return platforms.find(p=>p.hosts.some(h=>host===h||host.endsWith("."+h)))?.name||"Otro sitio";
}

form.addEventListener("submit",e=>{
  e.preventDefault();
  status.className="";
  let url;
  try{url=new URL(input.value.trim());if(!/^https?:$/.test(url.protocol))throw new Error();}
  catch{status.textContent="Pega un enlace web válido para continuar.";status.className="error";return;}
  const platform=detectPlatform(url);
  status.textContent=`✓ Enlace detectado: ${platform}. Preparando análisis multimedia…`;
  status.className="ok";
  // El frontend ya detecta plataforma. La extracción real se conectará a un backend
  // compatible sin simular resultados ni intentar eludir controles de acceso.
});