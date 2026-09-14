const BASE="/ab-premia-calendar/";
const indexUrl=BASE+"calendars/index.json";

function escapeHtml(value=""){
  return String(value).replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
}
async function getTeams(){
  const response=await fetch(indexUrl+"?t="+Date.now(),{cache:"no-store"});
  if(!response.ok)throw new Error("No se pudieron cargar los equipos");
  return response.json();
}
function subscriptionCard(team){
  const icsUrl=new URL(BASE+"calendars/"+team.slug+".ics",window.location.origin).href;
  const appleUrl=icsUrl.replace(/^https?:/,"webcal:");
  const googleUrl="https://calendar.google.com/calendar/r?cid="+encodeURIComponent(icsUrl);
  const ready=team.matches>0;
  return '<article class="team-card">'+
    '<div class="team-copy"><span class="club-tag">'+escapeHtml(team.club||"Club")+'</span><h3>'+escapeHtml(team.name)+'</h3><p>'+(ready?team.matches+" partidos publicados":"Calendario pendiente")+'</p></div>'+
    (ready?'<div class="calendar-actions"><a class="calendar-action apple" href="'+appleUrl+'"><span class="action-icon"></span><span><small>Añadir a</small>Apple Calendar</span><b>↗</b></a><a class="calendar-action google" href="'+googleUrl+'" target="_blank" rel="noopener"><span class="action-icon google-g">G</span><span><small>Añadir a</small>Google Calendar</span><b>↗</b></a></div>':'<div class="pending">Disponible cuando se publiquen los partidos</div>')+
  '</article>';
}
async function init(){
  const list=document.querySelector("#team-list");
  const empty=document.querySelector("#empty-results");
  const search=document.querySelector("#team-search");
  const filter=document.querySelector("#club-filter");
  try{
    const teams=await getTeams();
    const clubs=[...new Set(teams.map(team=>team.club).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"es"));
    filter.innerHTML='<option value="">Todos los clubes</option>'+clubs.map(club=>'<option value="'+escapeHtml(club)+'">'+escapeHtml(club)+'</option>').join("");
    document.querySelector("#team-total").textContent=teams.length+" equipos";
    function draw(){
      const query=search.value.trim().toLocaleLowerCase("es");
      const club=filter.value;
      const visible=teams.filter(team=>(!club||team.club===club)&&(!query||(team.name+" "+(team.club||"")).toLocaleLowerCase("es").includes(query)));
      list.className="team-list";
      list.innerHTML=visible.map(subscriptionCard).join("");
      empty.hidden=visible.length>0;
    }
    search.addEventListener("input",draw);
    filter.addEventListener("change",draw);
    draw();
  }catch(error){
    list.className="team-list";
    list.innerHTML='<div class="load-error"><strong>No se pudieron cargar los equipos.</strong><span>'+escapeHtml(error.message)+'</span><button onclick="location.reload()">Reintentar</button></div>';
  }
}
init();
window.addEventListener("pageshow",event=>{if(event.persisted)init()});
