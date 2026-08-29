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
    if(!getFavourites().length){target.innerHTML=emptyState("Tu calendario está vacío","Elige equipos para reunir sus partidos en esta agenda.");return}
    const games=(await getFavouriteGames()).filter(g=>g.start>=new Date());
    if(!games.length){target.innerHTML=emptyState("Sin partidos publicados","La agenda se completará automáticamente cuando la federación publique partidos.");return}
    const groups=new Map();
    games.forEach(game=>{const key=game.start.toISOString().slice(0,10);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(game)});
    target.innerHTML=[...groups.values()].map(day=>'<section class="day"><div class="day-heading"><h2>'+fmtDate(day[0].start)+'</h2></div><div class="day-list">'+day.map(gameCard).join("")+'</div></section>').join("");
  }catch(error){target.innerHTML=emptyState("No se pudo cargar la agenda",error.message)}
}
async function renderSettings(){
  const list=document.querySelector("#team-list"),search=document.querySelector("#team-search"),status=document.querySelector("#save-status");
  try{
    const teams=await getTeams();let favourites=getFavourites();
    function draw(query=""){
      const filtered=teams.filter(team=>team.name.toLowerCase().includes(query.toLowerCase()));
      list.innerHTML=filtered.map(team=>'<label class="team-option"><input type="checkbox" value="'+team.slug+'" '+(favourites.includes(team.slug)?"checked":"")+' '+(team.matches===0?"disabled":"")+'><span><strong>'+team.name+'</strong><small>'+(team.matches?"Calendario publicado":"Pendiente de partidos")+'</small></span><span class="count">'+team.matches+'</span></label>').join("");
      list.querySelectorAll("input:not(:disabled)").forEach(input=>input.addEventListener("change",()=>{
        const selected=new Set(favourites);
        if(input.checked)selected.add(input.value);else selected.delete(input.value);
        favourites=[...selected];
        setFavourites(favourites);status.textContent="Preferencias guardadas";setTimeout(()=>status.textContent="",1800);
      }));
    }
    draw();search.addEventListener("input",()=>draw(search.value));
  }catch(error){list.innerHTML='<div class="empty"><h2>Error</h2><p>'+error.message+'</p></div>'}
}
if(page==="home")renderHome();
if(page==="calendar")renderCalendar();
if(page==="settings")renderSettings();
