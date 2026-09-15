"use client";
import { useState } from "react";

export default function DurationCalculator(){
  const [quantity,setQuantity]=useState(3600);
  const [productivity,setProductivity]=useState(30);
  const [crews,setCrews]=useState(3);
  const [result,setResult]=useState<any>(null);
  async function calculate(){
    const res=await fetch('/api/planning/duration',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({method:'PRODUCTIVITY',quantity,productivity,crews})});
    setResult(await res.json());
  }
  return <section className="panel" style={{marginTop:18}}><h2>Duration Calculator</h2><p className="muted">Deterministic Planning calculation. No Redis, ML or LLM dependency.</p><div className="grid" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}>
    <label>Quantity<input className="input" type="number" value={quantity} onChange={e=>setQuantity(Number(e.target.value))} style={{width:'100%',marginTop:6}}/></label>
    <label>Productivity / crew / day<input className="input" type="number" value={productivity} onChange={e=>setProductivity(Number(e.target.value))} style={{width:'100%',marginTop:6}}/></label>
    <label>No. of Crews<input className="input" type="number" min="1" value={crews} onChange={e=>setCrews(Number(e.target.value))} style={{width:'100%',marginTop:6}}/></label>
  </div><div style={{display:'flex',gap:12,alignItems:'center',marginTop:14}}><button className="button" onClick={calculate}>Calculate Duration</button>{result&&<strong className="accent">{result.valid?`${result.days} working days`:(result.reason||'Invalid')}</strong>}</div>{result?.basis&&<p className="muted">Basis: {result.basis}</p>}</section>
}
