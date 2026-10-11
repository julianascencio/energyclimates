import assert from 'node:assert/strict';
import fs from 'node:fs';
import {profile,predict,parseCSV,monthlyFeatures} from '../atlas/energy-core.mjs';
const f=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
for(const tech of ['pv','hybrid','bess'])assert.deepEqual(f.features.map(x=>profile(x,tech,f.rules).zone_id),f.expected[tech]);
const parsed=parseCSV(f.csv),features=monthlyFeatures(parsed.rows,f.mapping);
for(const x of features){const expected=f.example_features.find(r=>r.location_id===x.location_id);for(const key of Object.keys(x)){if(typeof x[key]==='number')assert.ok(Math.abs(x[key]-expected[key])<1e-8,`${key}: ${x[key]} / ${expected[key]}`)}}
for(const tech of ['pv','hybrid','bess'])for(const x of features){const p=predict(x,f.models[tech]),expected=f.predictions[tech].find(r=>r.location_id===x.location_id);assert.equal(p.zone_id,expected.zone_id);assert.equal(p.status,expected.status);assert.ok(Math.abs(p.feature_distance-expected.feature_distance)<1e-8);assert.ok(Math.abs(p.assignment_separation-expected.assignment_separation)<1e-8)}
assert.deepEqual(parseCSV('id,name\r\n1,"a,b"\r\n2,"quote""value"\r\n').rows,[{id:'1',name:'a,b'},{id:'2',name:'quote"value'}]);
assert.throws(()=>parseCSV('a,b\n"unclosed,2'));
assert.throws(()=>monthlyFeatures([...parsed.rows,parsed.rows[0]],f.mapping),/Duplicate/);
console.log('Python / JavaScript rule boundaries, real-data features and ML predictions agree.');
