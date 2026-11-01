(function(){
  "use strict";
  var $=function(s,c){return (c||document).querySelector(s)}, $$=function(s,c){return Array.prototype.slice.call((c||document).querySelectorAll(s))};
  var trLower=function(s){return (s||"").replace(/I/g,"ı").replace(/İ/g,"i").toLowerCase()};

  // menü
  var mt=$(".menu-toggle");
  if(mt){mt.addEventListener("click",function(){var o=document.body.classList.toggle("menu-open");mt.setAttribute("aria-expanded",o)})}
  $$(".sub-toggle").forEach(function(b){b.addEventListener("click",function(e){e.stopPropagation();var li=b.parentNode;var o=li.classList.toggle("open");b.setAttribute("aria-expanded",o)})});
  document.addEventListener("click",function(){$$(".has-sub.open").forEach(function(li){li.classList.remove("open")})});
  document.addEventListener("keydown",function(e){if(e.key==="Escape"){document.body.classList.remove("menu-open");$$(".has-sub.open").forEach(function(li){li.classList.remove("open")})}});

  // envanter tablosu
  var inv=$("#inv");
  if(inv){
    var rows=$$("tbody tr",inv), q=$("#inv-q"), il=$("#inv-il"), cnt=$("#inv-count"), en=document.documentElement.lang==="en";
    var filt=function(){var t=trLower(q.value.trim()), p=il.value, n=0;rows.forEach(function(r){var ok=(!t||trLower(r.textContent).indexOf(t)>-1)&&(!p||r.children[1].textContent===p);r.hidden=!ok;if(ok)n++});cnt.textContent=n+(en?" records":" kayıt")};
    q.addEventListener("input",filt);il.addEventListener("change",filt);filt();
    $$("th button",inv).forEach(function(b){b.addEventListener("click",function(){
      var c=+b.dataset.col, d=b.dataset.dir==="asc"?"desc":"asc";
      $$("th button",inv).forEach(function(x){delete x.dataset.dir});b.dataset.dir=d;
      var tb=$("tbody",inv);
      rows.sort(function(a,z){var A=a.children[c],Z=z.children[c];var va=A.dataset.v!==undefined?A.dataset.v:A.textContent,vz=Z.dataset.v!==undefined?Z.dataset.v:Z.textContent;
        var na=parseFloat(va),nz=parseFloat(vz);var r=(!isNaN(na)&&!isNaN(nz)&&A.classList.contains("n"))?na-nz:va.localeCompare(vz,"tr");return d==="asc"?r:-r});
      rows.forEach(function(r){tb.appendChild(r)});
    })});
  }

  // saha günlüğü filtreleri
  var jr=$("#journal");
  if(jr){
    var cards=$$(".post-card",jr), jq=$("#j-q"), y="", k="";
    var jf=function(){var t=trLower(jq.value.trim()),n=0;cards.forEach(function(c){var ok=(!y||c.dataset.y===y)&&(!k||c.dataset.k===k)&&(!t||c.dataset.t.indexOf(t)>-1||trLower(c.textContent).indexOf(t)>-1);c.hidden=!ok;if(ok)n++});$("#j-empty").hidden=n>0};
    jq.addEventListener("input",jf);
    $$("#j-y .chip").forEach(function(b){b.addEventListener("click",function(){$$("#j-y .chip").forEach(function(x){x.classList.remove("is-on")});b.classList.add("is-on");y=b.dataset.y;jf()})});
    $$("#j-k .chip").forEach(function(b){b.addEventListener("click",function(){$$("#j-k .chip").forEach(function(x){x.classList.remove("is-on")});b.classList.add("is-on");k=b.dataset.k;jf()})});
  }

  // iletişim formu → mailto
  var cf=$("#contact");
  if(cf){cf.addEventListener("submit",function(e){e.preventDefault();
    var n=$("#c-name").value.trim(),m=$("#c-mail").value.trim(),t=$("#c-topic").value,msg=$("#c-msg").value.trim(),err=$("#c-err");
    if(!n||!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(m)||!msg){err.hidden=false;return}
    err.hidden=true;
    var to=["ayamac","gmail.com"].join("@");
    location.href="mailto:"+to+"?subject="+encodeURIComponent("[obruk.org] "+t+" – "+n)+"&body="+encodeURIComponent(msg+"\n\n"+n+"\n"+m);
  });$$("input,textarea",cf).forEach(function(i){i.addEventListener("input",function(){$("#c-err").hidden=true})})}

  // harita (harici harita servisi ve API anahtarı gerektirmez)
  var mp=$("#map");
  if(mp){var go=function(n){if(!window.L||!window.OBRUK_GEO){if((n||0)>60)return;return setTimeout(function(){go((n||0)+1)},150)}
    var pts=JSON.parse(mp.dataset.points), en=document.documentElement.lang==="en";
    var map=L.map(mp,{scrollWheelZoom:false,zoomSnap:.25,attributionControl:true,minZoom:5,maxZoom:9,maxBounds:[[33,22],[45,48]]});
    map.fitBounds([[35.8,25.6],[42.1,44.8]]);
    map.attributionControl.setPrefix(false);
    L.geoJSON(window.OBRUK_GEO,{interactive:false,style:function(f){var tr=f.properties.c==="TR";return{color:tr?"#8a7f72":"#d8ccb8",weight:tr?1.2:.8,fillColor:tr?"#FBF8F2":"#EAE1D2",fillOpacity:1}}}).addTo(map);
    map.attributionControl.addAttribution(en?"Borders: Natural Earth":"Sınırlar: Natural Earth");
    pts.forEach(function(p){var r=6+Math.sqrt(p.caves)*3.2, has=p.proj.length>0;
      var c=L.circleMarker(p.ll,{radius:r,color:has?"#B87618":"#A3452A",weight:2,fillColor:has?"#E9A23B":"#A3452A",fillOpacity:has?.75:.45}).addTo(map);
      c.bindTooltip(p.il,{direction:"top",offset:[0,-r]});
      var h="<strong>"+p.il+"</strong><br>"+(p.caves?p.caves+(en?" mapped cave records":" haritalı mağara kaydı"):"")+(p.proj.length?"<br>"+p.proj.join("<br>"):"");
      c.bindPopup(h)});
  };go()}

  // sınav
  var qz=$("#quiz");
  if(qz){
    var all=JSON.parse(qz.dataset.q), set, i, score;
    var esc=function(s){var d=document.createElement("div");d.textContent=s;return d.innerHTML};
    var start=function(){set=all.slice().sort(function(){return Math.random()-.5}).slice(0,10);i=0;score=0;show()};
    var show=function(){
      if(i>=set.length){qz.innerHTML='<p class="kicker">Sonuç</p><h2>10 soruda '+score+' doğru</h2><p>'+(score>=8?"Tebrikler, gerçek bir mağaracısınız.":score>=5?"Fena değil; biraz daha mağara, biraz daha okuma.":"Kaskınızı takın, öğrenecek çok şey var!")+'</p><button class="btn btn-primary" id="q-again">Yeniden dene</button>';$("#q-again").onclick=start;return}
      var q=set[i];
      qz.innerHTML='<div class="q-prog"><i style="width:'+(i/set.length*100)+'%"></i></div><p class="meta">Soru '+(i+1)+' / '+set.length+'</p><h2>'+esc(q.q)+'</h2><div class="q-opts">'+q.o.map(function(o,k){return '<button class="q-opt" data-k="'+k+'">'+esc(o)+'</button>'}).join("")+'</div><p id="q-fb" class="meta" aria-live="polite"></p>';
      $$(".q-opt",qz).forEach(function(b){b.addEventListener("click",function(){
        if(qz.dataset.lock)return;qz.dataset.lock=1;
        var ok=q.a.indexOf(q.o[+b.dataset.k])>-1;if(ok)score++;
        $$(".q-opt",qz).forEach(function(x){if(q.a.indexOf(q.o[+x.dataset.k])>-1)x.classList.add("ok")});
        if(!ok)b.classList.add("no");
        $("#q-fb").textContent=ok?"Doğru!":"Doğru cevap: "+q.a.join(", ");
        setTimeout(function(){delete qz.dataset.lock;i++;show()},1400);
      })});
    };
    start();
  }
})();
