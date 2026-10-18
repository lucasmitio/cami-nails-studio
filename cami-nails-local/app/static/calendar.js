"use strict";
document.querySelectorAll('.time-event').forEach(event => {
  const minute=Number(event.dataset.minute), duration=Number(event.dataset.duration);
  if(Number.isFinite(minute)&&Number.isFinite(duration)){
    event.style.top=`${minute}px`;
    event.style.height=`${Math.max(duration-2,14)}px`;
    event.classList.toggle('short-event',duration<45);
  }
});
const viewport=document.getElementById('time-scroll');
if(viewport){
  const first=document.querySelector('.time-event');
  const minute=first?Number(first.dataset.minute):480;
  viewport.scrollTop=Math.max(0,Math.min(480,minute)-30);
}
