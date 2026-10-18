"use strict";
document.querySelectorAll('[data-autosubmit]').forEach(el=>el.addEventListener('change',()=>el.form.requestSubmit()));
document.querySelectorAll('.money-plot').forEach(plot=>{
 const bars=[...plot.querySelectorAll('.plot-bar')];const max=Math.max(1,...bars.map(b=>Number(b.dataset.value)));
 bars.forEach(b=>b.style.height=`${Number(b.dataset.value)/max*145}px`);
});
document.querySelectorAll('.status-plot').forEach(plot=>{
 const bars=[...plot.querySelectorAll('.status-fill')];const max=Math.max(1,...bars.map(b=>Number(b.dataset.value)));
 bars.forEach(b=>b.style.width=`${Number(b.dataset.value)/max*100}%`);
});
