const BASE="/ab-premia-calendar/";
const indexUrl=BASE+"calendars/index.json";
const storageKey="ab-premia-favourite-teams";
const page=document.body.dataset.page;

function getFavourites(){try{return JSON.parse(localStorage.getItem(storageKey)||"[]")}catch{return[]}}
function setFavourites(value){localStorage.setItem(storageKey,JSON.stringify(value))}
async function getTeams(){const response=await fetch(indexUrl,{cache:"no-store"});if(!response.ok)throw new Error("No se pudieron cargar los equipos");return response.json()}
function unescapeIcs(value=""){return value.replace(/\\n/g,"\n").replace(/\\,/g,",").replace(/\\;/g,";").replace(/\\\\/g,"\\")}
function parseDate(value){const raw=value.split(":").pop();const match=raw.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);if(!match)return null;return new Date(+match[1],+match[2]-1,+match[3],+match[4],+match[5])}
function parseIcs(text,team){
  const unfolded=text.replace(/\r?\n[ \t]/g,"");
  return unfolded.split("BEGIN:VEVENT").slice(1).map(block=>{
    const get=name=>{const line=block.split(/\r?\n/).find(row=>row.startsWith(name));return line?unescapeIcs(line.slice(line.indexOf(":")+1)):""};
    const dtLine=block.split(/\r?\n/).find(row=>row.startsWith("DTSTART"))||"";
    return{team,uid:get("UID"),start:parseDate(dtLine),summary:get("SUMMARY"),location:get("LOCATION"),description:get("DESCRIPTION")};
  }).filter(item=>item.start);
}
async function getFavouriteGames(){
  const favourites=getFavourites();if(!favourites.length)return[];
  const teams=await getTeams();const selected=teams.filter(team=>favourites.includes(team.slug));
  const results=await Promise.all(selected.map(async team=>{
    const response=await fetch(BASE+"calendars/"+team.slug+".ics",{cache:"no-store"});
    return response.ok?parseIcs(await response.text(),team):[];
  }));
  const seen=new Set();
  return results.flat().filter(game=>{if(seen.has(game.uid))return false;seen.add(game.uid);return true}).sort((a,b)=>a.start-b.start);
}
function fmtDate(date){return new Intl.DateTimeFormat("es-ES",{weekday:"short",day:"numeric",month:"short"}).format(date)}
function fmtTime(date){return new Intl.DateTimeFormat("es-ES",{hour:"2-digit",minute:"2-digit"}).format(date)}
function gameCard(game){
  return '<article class="game"><div class="game-time"><span>'+fmtDate(game.start)+'</span><span>'+fmtTime(game.start)+'</span></div><div class="teams">'+game.summary+'</div><div class="meta">'+(game.location||"Pabellón pendiente")+'</div><span class="badge">'+game.team.name+'</span></article>';
}
function emptyState(title,text){
  return '<div class="empty"><h2>'+title+'</h2><p>'+text+'</p><a class="button" href="'+BASE+'settings/">Elegir equipos</a></div>';
}
async function renderHome(){
  const target=document.querySelector("#next-games");
  try{
    if(!getFavourites().length){target.innerHTML=emptyState("Aún no sigues ningún equipo","Selecciona tus equipos favoritos para ver aquí sus próximos partidos.");return}
    const now=new Date();const games=(await getFavouriteGames()).filter(g=>g.start>=now).slice(0,6);
    target.innerHTML=games.length?'<div class="grid">'+games.map(gameCard).join("")+'</div>':emptyState("Sin próximos partidos","Los equipos que sigues todavía no tienen nuevos partidos publicados.");
  }catch(error){target.innerHTML=emptyState("No se pudo actualizar",error.message)}
}
async function renderCalendar(){
  const target=document.querySelector("#calendar-agenda");
  try{
    if(!getFavourites().length){target.innerHTML=emptyState("Tu calendario está vacío","Elige equipos para ver sus partidos en el calendario.");return}
    const games=await getFavouriteGames();
    if(!games.length){target.innerHTML=emptyState("Sin partidos publicados","El calendario se completará automáticamente cuando la federación publique partidos.");return}
    const dateKey=date=>[date.getFullYear(),String(date.getMonth()+1).padStart(2,"0"),String(date.getDate()).padStart(2,"0")].join("-");
    const byDay=new Map();
    games.forEach(game=>{const key=dateKey(game.start);if(!byDay.has(key))byDay.set(key,[]);byDay.get(key).push(game)});
    const now=new Date();
    const nextGame=games.find(game=>game.start>=now);
    let visible=nextGame?new Date(nextGame.start.getFullYear(),nextGame.start.getMonth(),1):new Date(now.getFullYear(),now.getMonth(),1);
    let selected=nextGame?dateKey(nextGame.start):dateKey(now);
    const monthName=date=>new Intl.DateTimeFormat("es-ES",{month:"long",year:"numeric"}).format(date);
    const longDate=date=>new Intl.DateTimeFormat("es-ES",{weekday:"long",day:"numeric",month:"long"}).format(date);
    function render(){
      const year=visible.getFullYear(),month=visible.getMonth();
      const first=new Date(year,month,1);
      const gridStart=new Date(year,month,1-((first.getDay()+6)%7));
      const days=Array.from({length:42},(_,index)=>new Date(gridStart.getFullYear(),gridStart.getMonth(),gridStart.getDate()+index));
      const monthGames=days.filter(day=>day.getMonth()===month&&byDay.has(dateKey(day)));
      if(!days.some(day=>dateKey(day)===selected&&day.getMonth()===month)){
        selected=monthGames.length?dateKey(monthGames[0]):dateKey(new Date(year,month,1));
      }
      target.className="";
      target.innerHTML='<div class="month-calendar"><div class="calendar-head"><button class="month-button" id="prev-month" aria-label="Mes anterior">‹</button><div class="calendar-title">'+monthName(visible)+'</div><button class="month-button" id="next-month" aria-label="Mes siguiente">›</button></div><div class="weekdays"><span>Lun</span><span>Mar</span><span>Mié</span><span>Jue</span><span>Vie</span><span>Sáb</span><span>Dom</span></div><div class="month-grid">'+days.map(day=>{
        const key=dateKey(day),dayGames=byDay.get(key)||[];
        const classes=["calendar-day",day.getMonth()!==month?"other":"",key===dateKey(now)?"today":"",key===selected?"selected":"",dayGames.length?"has-games":""].filter(Boolean).join(" ");
        const dots=dayGames.length?'<span class="event-dots">'+dayGames.slice(0,3).map(()=>'<i class="event-dot"></i>').join("")+'</span>'+(dayGames.length>3?'<span class="event-more">+'+(dayGames.length-3)+'</span>':""):"";
        return '<button class="'+classes+'" data-date="'+key+'" aria-label="'+longDate(day)+(dayGames.length?", "+dayGames.length+" partidos":"")+'"><span class="day-number">'+day.getDate()+'</span>'+dots+'</button>';
      }).join("")+'</div></div><div id="selected-day" class="selected-day"></div>';
      const detail=target.querySelector("#selected-day");
      const selectedDate=new Date(selected+"T12:00:00"),selectedGames=byDay.get(selected)||[];
      detail.innerHTML='<div class="selected-day-head"><h2>'+longDate(selectedDate)+'</h2><span class="selected-day-count">'+selectedGames.length+' partido'+(selectedGames.length===1?"":"s")+'</span></div>'+(selectedGames.length?'<div class="day-list">'+selectedGames.map(gameCard).join("")+'</div>':'<div class="no-day-games">No hay partidos este día.</div>');
      target.querySelector("#prev-month").addEventListener("click",()=>{visible=new Date(year,month-1,1);render()});
      target.querySelector("#next-month").addEventListener("click",()=>{visible=new Date(year,month+1,1);render()});
      target.querySelectorAll(".calendar-day").forEach(button=>button.addEventListener("click",()=>{selected=button.dataset.date;const chosen=new Date(selected+"T12:00:00");if(chosen.getMonth()!==month){visible=new Date(chosen.getFullYear(),chosen.getMonth(),1)}render()}));
    }
    render();
  }catch(error){target.innerHTML=emptyState("No se pudo cargar el calendario",error.message)}
}
async function renderSettings(){
  const list=document.querySelector("#team-list"),search=document.querySelector("#team-search"),status=document.querySelector("#save-status"),subscriptions=document.querySelector("#subscription-list");
  try{
    const teams=await getTeams();let favourites=getFavourites();
    function drawSubscriptions(){
      const followed=teams.filter(team=>favourites.includes(team.slug)&&team.matches>0);
      if(!followed.length){subscriptions.innerHTML='<div class="subscription-empty">Selecciona un equipo con partidos publicados para añadirlo a Apple o Google Calendar.</div>';return}
      subscriptions.innerHTML=followed.map(team=>{
        const icsUrl=new URL(BASE+"calendars/"+team.slug+".ics",window.location.origin).href;
        const appleUrl=icsUrl.replace(/^https?:/,"webcal:");
        const googleUrl="https://calendar.google.com/calendar/r?cid="+encodeURIComponent(icsUrl);
        return '<article class="subscription-card"><strong>'+team.name+'</strong><div class="subscription-actions"><a class="calendar-button apple" href="'+appleUrl+'"><span></span> Apple</a><a class="calendar-button google" href="'+googleUrl+'" target="_blank" rel="noopener"><span>G</span> Google</a></div></article>';
      }).join("");
    }
    function draw(query=""){
      const filtered=teams.filter(team=>team.name.toLowerCase().includes(query.toLowerCase()));
      list.innerHTML=filtered.map(team=>'<label class="team-option"><input type="checkbox" value="'+team.slug+'" '+(favourites.includes(team.slug)?"checked":"")+' '+(team.matches===0?"disabled":"")+'><span><strong>'+team.name+'</strong><small>'+(team.matches?"Calendario publicado":"Pendiente de partidos")+'</small></span><span class="count">'+team.matches+'</span></label>').join("");
      list.querySelectorAll("input:not(:disabled)").forEach(input=>input.addEventListener("change",()=>{
        const selected=new Set(favourites);
        if(input.checked)selected.add(input.value);else selected.delete(input.value);
        favourites=[...selected];
        setFavourites(favourites);drawSubscriptions();status.textContent="Preferencias guardadas";setTimeout(()=>status.textContent="",1800);
      }));
    }
    draw();drawSubscriptions();search.addEventListener("input",()=>draw(search.value));
  }catch(error){list.innerHTML='<div class="empty"><h2>Error</h2><p>'+error.message+'</p></div>'}
}
function initPage(){
  if(page==="home")renderHome();
  if(page==="calendar")renderCalendar();
  if(page==="settings")renderSettings();
}
initPage();
window.addEventListener("pageshow",event=>{if(event.persisted)initPage()});
