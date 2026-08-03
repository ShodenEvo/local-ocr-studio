const $=s=>document.querySelector(s);let file=null,images={},active='source',crop=null,imgMeta=null,dragStart=null;
const canvas=$('#imageCanvas'),ctx=canvas.getContext('2d');
['confidence','upscale','clahe','sharpen','deblur_strength','denoise_strength','restoration_sharpen'].forEach(id=>{$('#'+id).addEventListener('input',e=>$('#'+id+'Value').textContent=e.target.value)});
fetch('/api/status').then(r=>r.json()).then(s=>{
  const p=$('#statusPills');
  const gpu=s.gpu||{};
  const accelerated=gpu.gpu_available??gpu.cuda_available;
  const runtime=gpu.backend==='rocm'
    ?`ROCm/HIP ${gpu.hip_runtime||'ready'}`
    :gpu.backend==='cuda'
      ?`CUDA ${gpu.cuda_runtime||'ready'}`
      :'CPU';

  let gpuLabel;
  if(accelerated){
    gpuLabel=`GPU: ${gpu.device_name} (${runtime})`;
  }else if(gpu.amd_hardware_detected){
    gpuLabel='AMD GPU detected — EasyOCR currently using CPU';
  }else if(gpu.nvidia_hardware_detected){
    gpuLabel='NVIDIA GPU detected — CPU-only PyTorch installed';
  }else{
    gpuLabel=gpu.installed
      ?'CPU mode — no supported GPU backend'
      :'PyTorch missing';
  }

  const gpuTitle=gpu.note||'';
  p.innerHTML=`
    <span class="pill ${s.tesseract.available?'ok':'bad'}"
      title="${s.tesseract.available?'':'Install the native Tesseract OCR executable'}">
      Tesseract ${s.tesseract.available?'ready':'missing'}
    </span>
    <span class="pill ${s.easyocr.available?'ok':'bad'}">
      EasyOCR ${s.easyocr.available?'ready':'missing'}
    </span>
    <span class="pill ${accelerated?'ok':'bad'}" title="${gpuTitle}">
      ${gpuLabel}
    </span>
    <span class="pill ${s.restoration?.ai_available?'ok':''}" title="${s.restoration?.ai_note||''}">
      ${s.restoration?.ai_available?'AI super-resolution ready':'OCR-safe restoration ready'}
    </span>`;
});
function updateRestorationUi(){
  const enabled=$('#restoration_enabled').checked;
  $('#restorationOptions').classList.toggle('disabled-options',!enabled);
  $('#restorationOptions').querySelectorAll('input,select').forEach(el=>el.disabled=!enabled);
  if(enabled){$('#restoration_mode').disabled=false;updateRestorationMode();}
}
function updateRestorationMode(){
  const manual=$('#restoration_mode').value==='manual';
  $('#manualRestorationOptions').classList.toggle('hidden',!manual);
  $('#restorationHelp').textContent=manual
    ?'Manual mode uses exactly the selected restoration controls.'
    :'Automatic mode tests original, Lanczos upscale, and light/balanced/strong restoration. Review all attempts manually.';
}
$('#restoration_enabled').addEventListener('change',updateRestorationUi);
$('#restoration_mode').addEventListener('change',updateRestorationMode);
updateRestorationUi();
const drop=$('#dropzone'),input=$('#fileInput');drop.onclick=()=>input.click();input.onchange=e=>loadFile(e.target.files[0]);['dragenter','dragover'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.add('drag')}));['dragleave','drop'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.remove('drag')}));drop.addEventListener('drop',e=>loadFile(e.dataTransfer.files[0]));
function loadFile(f){if(!f)return;file=f;crop=null;const url=URL.createObjectURL(f);images={source:url};const im=new Image();im.onload=()=>{imgMeta={w:im.naturalWidth,h:im.naturalHeight};show(url);$('#processBtn').disabled=false;$('#cropBtn').disabled=false;$('#clearCropBtn').disabled=false;$('#cropInfo').textContent=`${imgMeta.w} × ${imgMeta.h}px — full image`;};im.src=url}
function show(src){if(!src)return;const im=new Image();im.onload=()=>{const box=$('#viewer').getBoundingClientRect();const scale=Math.min((box.width-20)/im.width,(box.height-20)/im.height,1);canvas.width=Math.round(im.width*scale);canvas.height=Math.round(im.height*scale);canvas.dataset.scale=scale;ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(im,0,0,canvas.width,canvas.height);$('#emptyState').style.display='none';};im.src=src}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');active=b.dataset.tab;show(images[active])});
$('#cropBtn').onclick=()=>{active='source';document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab==='source'));show(images.source);$('#cropInfo').textContent='Drag a rectangle on the source image';};
canvas.onmousedown=e=>{if(active!=='source'||!file)return;const r=canvas.getBoundingClientRect();dragStart={x:e.clientX-r.left,y:e.clientY-r.top};};
canvas.onmousemove=e=>{if(!dragStart)return;show(images.source);const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;ctx.strokeStyle='#00d4ff';ctx.lineWidth=2;ctx.strokeRect(dragStart.x,dragStart.y,x-dragStart.x,y-dragStart.y)};
canvas.onmouseup=e=>{if(!dragStart)return;const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,s=parseFloat(canvas.dataset.scale||1);const x1=Math.max(0,Math.min(dragStart.x,x)),y1=Math.max(0,Math.min(dragStart.y,y)),x2=Math.max(dragStart.x,x),y2=Math.max(dragStart.y,y);crop={x:Math.round(x1/s),y:Math.round(y1/s),w:Math.round((x2-x1)/s),h:Math.round((y2-y1)/s)};dragStart=null;$('#cropInfo').textContent=`Crop: x ${crop.x}, y ${crop.y}, ${crop.w} × ${crop.h}px`;};
$('#clearCropBtn').onclick=()=>{crop=null;$('#cropInfo').textContent=`${imgMeta.w} × ${imgMeta.h}px — full image`;show(images.source)};
$('#processBtn').onclick=async()=>{if(!file)return;$('#busy').classList.remove('hidden');const fd=new FormData();fd.append('file',file);['engine','method','psm','upscale','clahe','sharpen','blur','confidence','allowlist','restoration_mode','restoration_scale','deblur_strength','denoise_strength','deblock_strength','restoration_sharpen'].forEach(id=>fd.append(id,$('#'+id).value));fd.append('invert',$('#invert').checked);fd.append('restoration_enabled',$('#restoration_enabled').checked);fd.append('compare_original',$('#compare_original').checked);fd.append('ai_super_resolution',$('#ai_super_resolution').checked);fd.append('crop_x',crop?.x||0);fd.append('crop_y',crop?.y||0);fd.append('crop_w',crop?.w||0);fd.append('crop_h',crop?.h||0);try{const r=await fetch('/api/process',{method:'POST',body:fd});if(!r.ok)throw new Error(await r.text());const d=await r.json();images.source=d.source_image;images.restored=d.restored_image;images.enhanced=d.enhanced_image;images.annotated=d.annotated_image;active='annotated';document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab==='annotated'));show(images.annotated);$('#resultText').value=d.text||'No OCR text detected.';$('#summary').textContent=`Engine: ${d.engine} | Source: ${d.processing_source} | Method: ${d.method} | Reported confidence: ${d.confidence}% | Detections: ${d.hits.length}`;const notice=$('#restorationNotice');const notes=d.restoration_notes||[];notice.textContent=notes.join(' ');notice.classList.toggle('hidden',notes.length===0);$('#attempts').innerHTML=d.attempts.slice(0,30).map(a=>`<div class="attempt"><strong>${a.engine} · ${(a.method||'').replace('::',' → ')}</strong><span>${(a.confidence||0).toFixed(1)}% — ${escapeHtml(a.text||a.error||'No text')}</span></div>`).join('');}catch(e){alert(e.message)}finally{$('#busy').classList.add('hidden')}};
$('#copyBtn').onclick=()=>navigator.clipboard.writeText($('#resultText').value);
function escapeHtml(s){return s.replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
