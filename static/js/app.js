document.addEventListener('DOMContentLoaded',()=>{
  const navBtn=document.querySelector('.menu-toggle');
  const nav=document.querySelector('.nav-links');
  if(navBtn&&nav) navBtn.addEventListener('click',()=>nav.classList.toggle('open'));
  const sideBtn=document.querySelector('.mobile-sidebar-toggle');
  const side=document.querySelector('.sidebar');
  if(sideBtn&&side) sideBtn.addEventListener('click',()=>side.classList.toggle('open'));
  setTimeout(()=>document.querySelectorAll('.alert').forEach(el=>el.style.display='none'),5000);
});
