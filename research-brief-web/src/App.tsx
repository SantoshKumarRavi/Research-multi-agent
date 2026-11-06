import { FormEvent, useEffect, useState } from 'react'
import { ArrowUpRight, BookOpen, Check, CircleAlert, Clock3, FileText, LoaderCircle, Search, ShieldCheck, Sparkles } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
type Event = {event_id:number; run_id:string; sequence:number; timestamp:string; node:string; status:string; message:string}
type Source = {id:string; title:string; url:string; snippet:string; publisher:string}
type Brief = {title:string; summary:string; key_findings:string[]; limitations:string[]; citations:{source_id:string;claim:string}[]}
type Run = {run_id:string;status:string;query:string;audience:string;steps:Event[];sources:Source[];brief:Brief|null;error:string|null}

export default function App(){
  const [query,setQuery]=useState('How do urban green spaces affect public health?')
  const [audience,setAudience]=useState('general')
  const [maxSources,setMaxSources]=useState(5)
  const [run,setRun]=useState<Run|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [provider,setProvider]=useState('mock')
  useEffect(()=>{fetch(`${API}/health`).then(r=>r.json()).then(d=>setProvider(d.provider)).catch(()=>setProvider('offline'))},[])
  useEffect(()=>{
    if(!run?.run_id || !['queued','running'].includes(run.status)) return
    const source=new EventSource(`${API}/api/research/runs/${run.run_id}/events`)
    source.addEventListener('step',()=>fetch(`${API}/api/research/runs/${run.run_id}`).then(r=>r.json()).then(setRun).catch(()=>{}))
    const timer=setInterval(()=>fetch(`${API}/api/research/runs/${run.run_id}`).then(r=>r.json()).then(setRun).catch(()=>{}),1000)
    return ()=>{source.close();clearInterval(timer)}
  },[run?.run_id,run?.status])
  async function submit(e:FormEvent){e.preventDefault();setError('');setBusy(true);setRun(null)
    try{const res=await fetch(`${API}/api/research/runs`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,audience,max_sources:maxSources})});const data=await res.json();if(!res.ok)throw new Error(data.detail?.[0]?.msg||data.detail||'Could not start the workflow');const detail=await fetch(`${API}/api/research/runs/${data.run_id}`).then(r=>r.json());setRun(detail)}catch(err){setError(err instanceof Error?err.message:'API unavailable. Start the backend and try again.')}finally{setBusy(false)}}
  return <main className="shell">
    <header className="topbar"><a className="brand" href="#"><span className="brand-icon"><Sparkles size={17}/></span> FIELDNOTE <span className="brand-divider">/</span> RESEARCH</a><div className="top-actions"><span className={`provider ${provider==='offline'?'offline':''}`}><i/> {provider==='groq'?'Groq connected':provider==='offline'?'API offline':'Mock mode'}</span><span className="version">V1.0</span></div></header>
    <section className="intro"><div className="eyebrow"><span/> RESEARCH WORKFLOW</div><h1>Turn a question into<br/><em>a clear brief.</em></h1><p className="intro-copy">A focused research workflow that gathers sources, checks evidence, and builds a cited brief you can review.</p></section>
    <div className="workspace">
      <section className="panel compose"><div className="panel-heading"><div><div className="panel-kicker">01 <span>·</span> YOUR QUESTION</div><h2>Start with a question</h2></div><span className="subtle-badge">UP TO 10 SOURCES</span></div>
        <form onSubmit={submit}><label htmlFor="question">Research question</label><textarea id="question" maxLength={2000} value={query} onChange={e=>setQuery(e.target.value)} placeholder="What would you like to understand?" required/><div className="field-meta"><span>Be specific for stronger results</span><span>{query.length}/2000</span></div>
          <div className="form-row"><div className="field"><label htmlFor="audience">Write for</label><select id="audience" value={audience} onChange={e=>setAudience(e.target.value)}><option value="general">General audience</option><option value="technical">Technical readers</option><option value="executive">Decision makers</option></select></div><div className="field"><label htmlFor="sources">Source limit <b>{maxSources}</b></label><input id="sources" type="range" min="1" max="10" value={maxSources} onChange={e=>setMaxSources(Number(e.target.value))}/></div></div>
          {error&&<div className="error-box"><CircleAlert size={17}/>{error}</div>}<button className="submit" type="submit" disabled={busy||!query.trim()}>{busy?<><LoaderCircle className="spin" size={17}/> Starting workflow</>:<><Search size={17}/> Build my brief <ArrowUpRight size={17}/></>}</button>
        </form><div className="privacy-note"><ShieldCheck size={15}/> Runs are temporary. Groq mode sends the query and source excerpts to Groq; mock mode stays local.</div>
      </section>
      <section className="panel progress"><div className="panel-heading"><div><div className="panel-kicker">02 <span>·</span> WORKFLOW</div><h2>{run?run.status==='completed'?run.brief?'Brief is ready':'No brief generated':run.status==='failed'?'Workflow stopped':'Working through it':'What happens next'}</h2></div><span className={`run-state ${run?.status||'idle'}`}>{run?.status||'READY'}</span></div>
        <div className="steps">{[
          {id:'scope',title:'Check the question',desc:'Validate the request and set its scope',icon:ShieldCheck},
          {id:'plan',title:'Plan the research',desc:'Split the question into focused search tasks',icon:Sparkles},
          {id:'search',title:'Find useful sources',desc:'Search the public web for relevant material',icon:Search},
          {id:'evidence',title:'Prepare evidence',desc:'Collect bounded source information',icon:BookOpen},
          {id:'synthesis',title:'Draft the brief',desc:'Synthesize findings for your audience',icon:FileText},
          {id:'review',title:'Review citations',desc:'Keep references tied to gathered sources',icon:Check},
        ].map((step,i)=>{const ev=[...(run?.steps||[])].reverse().find(x=>x.node===step.id);const active=run?.status==='running'&&ev?.status==='started';const done=ev?.status==='completed';const Icon=step.icon;return <div className={`step ${done?'done':''} ${active?'active':''}`} key={step.id}><div className="step-marker">{done?<Check size={15}/>:active?<LoaderCircle size={15} className="spin"/>:<Icon size={15}/>}</div><div className="step-copy"><strong>{step.title}</strong><span>{ev?.message||step.desc}</span></div><div className="step-tail">{done?'DONE':active?'NOW':`0${i+1}`}</div></div>})}</div>
        {!run&&<div className="empty-hint"><Clock3 size={15}/> Your workflow steps will appear here as they run.</div>}
      </section>
    </div>
    {run?.status==='completed'&&!run.brief&&<div className="privacy-note result-error"><ShieldCheck size={15}/>{[...run.steps].reverse().find(x=>x.node==='clarify')?.message||'This request did not produce a research brief. Try a more specific research question.'}</div>}
    {run?.error&&<div className="error-box result-error"><CircleAlert size={17}/>{run.error}</div>}
    {run?.brief&&<section className="panel result"><div className="panel-heading"><div><div className="panel-kicker">03 <span>·</span> YOUR RESEARCH BRIEF</div><h2>{run.brief.title}</h2></div><span className="subtle-badge">{run.sources.length} SOURCES</span></div><p className="summary">{run.brief.summary}</p><div className="result-grid"><div><h3>Key findings</h3><ul>{run.brief.key_findings.map((x,i)=><li key={i}>{x}</li>)}</ul><h3>Limitations</h3><ul className="limitations">{run.brief.limitations.map((x,i)=><li key={i}>{x}</li>)}</ul>{run.brief.citations.length>0&&<><h3>Claim references</h3><ul className="limitations">{run.brief.citations.map((c,i)=><li key={i}><a className="claim-link" href={`#${c.source_id}`}>[{c.source_id}]</a> {c.claim}</li>)}</ul></>}</div><aside><h3>Sources</h3>{run.sources.map(s=><a id={s.id} className="source" href={s.url} key={s.id} target="_blank" rel="noreferrer"><span className="source-id">{s.id}</span><span><b>{s.title}</b><small>{s.publisher}</small></span><ArrowUpRight size={15}/></a>)}{run.brief.citations.length>0&&<div className="citation-note">{run.brief.citations.length} citation link(s) checked against this source list.</div>}</aside></div><div className="mock-note">{provider==='mock'?'Mock mode validates the workflow structure. Add a Groq API key to generate model-written synthesis.':'Generated brief — verify important claims at the linked sources.'}</div></section>}
    <footer><span>FIELDNOTE RESEARCH</span><span>Local-first · Evidence-linked · Human-reviewed</span></footer>
  </main>
}
