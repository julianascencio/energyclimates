// The same versioned thresholds and portable models are used by Python.
export const required={pv:['ghi_annual_kwh_m2','solar_weighted_temperature_c','weak_month_ratio'],hybrid:['ghi_annual_kwh_m2','weak_month_ratio','temperature_coldest_month_c','temperature_warmest_month_c'],bess:['temperature_coldest_month_c','temperature_warmest_month_c']};
const finite=Number.isFinite;
export function profile(f,technology,r){
  if(!required[technology])throw Error('Choose PV, PV + battery or battery');
  const missing=required[technology].filter(k=>!finite(f[k]));
  const sun=r.solar_thresholds_kwh_m2_year.filter(v=>f.ghi_annual_kwh_m2>v).length;
  const t=f.solar_weighted_temperature_c,heat=t<r.pv_temperature_thresholds_c[0]?0:t>r.pv_temperature_thresholds_c[1]?2:1;
  const thermal=Number(f.temperature_coldest_month_c<r.bess_cold_month_c)+2*Number(f.temperature_warmest_month_c>r.bess_hot_month_c);
  const season=r.weak_month_ratio_thresholds.filter(v=>f.weak_month_ratio>=v).length;
  const code=technology==='pv'?sun*3+heat+1:technology==='hybrid'?season*4+thermal+1:thermal+1;
  const name=technology==='pv'?`${r.solar_names[sun]} · ${r.pv_temperature_names[heat]}`:technology==='hybrid'?`${r.season_names[season]} · ${r.bess_names[thermal].toLowerCase()}`:r.bess_names[thermal];
  return {zone_id:missing.length?0:code,zone_name:missing.length?'No data':name,status:missing.length?'Insufficient data':'Experimental profile',reason:missing.join('; '),seasonality:finite(f.weak_month_ratio)?r.season_names[season]:'Not available',thermal_context:finite(f.temperature_coldest_month_c)&&finite(f.temperature_warmest_month_c)?r.bess_names[thermal]:'Not available',scheme_version:r.version};
}
export function predict(f,m){
  if(m.schema!=='energy-climate-kmeans-v1')throw Error('Unsupported model');
  const x=m.features.map(k=>f[k]);
  if(!x.every(finite))return {zone_id:0,zone_name:'Insufficient data',status:'Insufficient data',feature_distance:NaN,assignment_separation:NaN,model_version:m.model_version};
  const z=x.map((v,i)=>(v-m.mean[i])/m.scale[i]);
  const d=m.centres.map((centre,i)=>({i,d:Math.sqrt(centre.reduce((s,v,j)=>s+(z[j]-v)**2,0))})).sort((a,b)=>a.d-b.d||a.i-b.i);
  const first=d[0],second=d[1].d;
  const outside=x.some((v,i)=>v<m.feature_min[i]||v>m.feature_max[i])||first.d>m.radius95[first.i];
  return {zone_id:first.i+1,zone_name:m.names[first.i],feature_distance:first.d,assignment_separation:(second-first.d)/Math.max(second,1e-12),status:outside?'Outside typical training conditions':'Within typical training conditions',model_version:m.model_version};
}
export function parseCSV(text){
  text=text.replace(/^\uFEFF/,'');const rows=[];let row=[],cell='',quoted=false,closed=false;
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(quoted){if(c==='"'){if(text[i+1]==='"'){cell+='"';i++}else {quoted=false;closed=true}}else cell+=c;continue}
    if(c==='"'){if(cell||closed)throw Error('Unexpected quote in CSV');quoted=true}
    else if(c===','){row.push(cell);cell='';closed=false}
    else if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(x=>x!==''))rows.push(row);row=[];cell='';closed=false}
    else {if(closed)throw Error('Unexpected text after quoted CSV field');cell+=c}
  }
  if(quoted)throw Error('Unclosed quoted CSV field');row.push(cell);if(row.some(x=>x!==''))rows.push(row);
  if(rows.length<2)throw Error('CSV needs a header and monthly observations');
  const header=rows.shift().map(x=>x.trim());if(new Set(header).size!==header.length||header.some(x=>!x))throw Error('CSV headers must be unique and nonempty');
  if(rows.length>120000)throw Error('Use Python for more than 120,000 monthly rows');
  return {header,rows:rows.map((r,i)=>{if(r.length!==header.length)throw Error(`Row ${i+2} has ${r.length} fields; expected ${header.length}`);return Object.fromEntries(header.map((h,j)=>[h,r[j]]))})};
}
export function monthlyFeatures(rows,mapping){
  const coord=mapping.coordinates,vars=mapping.variables,days=mapping.month_days||[31,28,31,30,31,30,31,31,30,31,30,31];
  if(days.length!==12||!days.every(x=>finite(x)&&x>0))throw Error('Provide 12 positive month durations');
  const groups=new Map();const number=x=>x===undefined||String(x).trim()===''?NaN:Number(x);
  for(const [i,row] of rows.entries()){
    const id=String(row[coord.id]||`${row[coord.latitude]},${row[coord.longitude]}`),lat=number(row[coord.latitude]),rawlon=number(row[coord.longitude]),month=number(row[coord.month]);
    if(!finite(lat)||!finite(rawlon)||Math.abs(lat)>90||Math.abs(rawlon)>360)throw Error(`Invalid coordinates in row ${i+2}`);
    if(!Number.isInteger(month)||month<1||month>12)throw Error(`Month must be 1–12 in row ${i+2}`);
    const lon=((rawlon+180)%360+360)%360-180;
    if(!groups.has(id))groups.set(id,{location_id:id,latitude:lat,longitude:lon,t:Array(12).fill(NaN),h:Array(12).fill(NaN),seen:new Set()});
    const g=groups.get(id);if(g.latitude!==lat||g.longitude!==lon)throw Error(`Location ${id} has changing coordinates`);
    if(g.seen.has(month))throw Error(`Duplicate month ${month} for ${id}; use one 12-month climatology per location`);g.seen.add(month);
    for(const key of ['temperature','ghi']){
      const spec=vars[key];if(!spec)continue;let v=number(row[spec.column]);
      if(!finite(v)){if(String(row[spec.column]??'').trim()!==''&&!['nan','na','null'].includes(String(row[spec.column]).toLowerCase()))throw Error(`Invalid ${key} value in row ${i+2}`);continue}
      if(key==='temperature'){
        if(spec.unit==='K')v-=273.15;else if(spec.unit==='F')v=(v-32)*5/9;else if(spec.unit!=='C')throw Error('Unsupported temperature unit');
        if(v< -100||v>70)throw Error(`Temperature outside the supported ambient range in row ${i+2}`);g.t[month-1]=v;
      }else {
        if(spec.unit==='Wh/m2')v/=1000;else if(spec.unit==='J/m2')v/=3600000;else if(spec.unit==='W/m2')v*=days[month-1]*24/1000;else if(spec.unit==='kWh/m2/day')v*=days[month-1];else if(spec.unit==='J/m2/day')v*=days[month-1]/3600000;else if(!['kWh/m2','kWh/m2/month','kWh/m2/interval'].includes(spec.unit))throw Error('Unsupported irradiation unit');
        if(v<0)throw Error(`Negative irradiation in row ${i+2}`);g.h[month-1]=v;
      }
    }
  }
  return [...groups.values()].sort((a,b)=>a.location_id.localeCompare(b.location_id)).map(g=>{
    const tf=g.t.every(finite),hf=g.h.every(finite),sum=a=>a.reduce((s,v)=>s+v,0),annual=hf?sum(g.h):NaN,daily=g.h.map((v,i)=>v/days[i]),n=days.reduce((s,v)=>s+v,0);
    return {location_id:g.location_id,latitude:g.latitude,longitude:g.longitude,temperature_months:g.t.filter(finite).length,ghi_months:g.h.filter(finite).length,temperature_mean_c:tf?sum(g.t)/12:NaN,temperature_coldest_month_c:tf?Math.min(...g.t):NaN,temperature_warmest_month_c:tf?Math.max(...g.t):NaN,ghi_annual_kwh_m2:annual,solar_weighted_temperature_c:tf&&hf&&annual>0?g.t.reduce((s,v,i)=>s+v*g.h[i],0)/annual:NaN,weak_month_ratio:hf&&annual>0?Math.min(...daily)/(annual/n):NaN,ghi_daily_weakest_month:hf?Math.min(...daily):NaN};
  });
}
