// Browser rendering gate: synthetic assessments only; blocks all inference requests.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {chromium,webkit,expect} from '@playwright/test';
const base=process.env.WRITING_QA_ORIGIN??'http://127.0.0.1:3369',dir=process.env.WRITING_QA_OUTPUT??'/tmp/alua-writing-accuracy-v2/ui';
await mkdir(dir,{recursive:true});
const auth=JSON.parse(await readFile(process.env.WRITING_QA_TOKEN,'utf8'));
const fixture=JSON.parse(await readFile(new URL('../tests/fixtures/writing-advertising-v2.json',import.meta.url),'utf8'));
const task={id:'writing-t2-qa',title:'Advertising QA',topic_id:'media',essay_type:'discussion',practice_prompt:fixture.prompt,task_requirements:['Discuss both views','Give your own opinion'],dataset_version:'qa'};
const quote=fixture.essay.split('. ')[0]+'.',anchor={quote,start:0,end:quote.length};
const review={criteria:['task_response','coherence_cohesion','lexical_resource','grammar'].map((name,i)=>({name,band:6+i,rationale_en:'Synthetic descriptor rationale for a browser rendering test.',explanation_ru:'Синтетический тест отображения.',evidence:[anchor],improvement:null,target:null})),top_improvements:[],issues:[],uncertainty:'Synthetic display fixture, not model quality.',quality_policy:'writing-accuracy-v3',estimated_band:7.5,provider:'mock',model:'mock',assessed_at:'2026-11-12T00:00:00Z',essay_version:1};
review.task_understanding={essay_type:'discussion',position:'A clear synthetic position.',position_development:'A central action is asserted rather than developed.',position_claims:[{claim:'A central action.',development:'asserted',basis:'No body development in this fixture.'}],requirements:[{requirement:'Discuss both views',coverage:'addressed',explanation:'Both sides are discussed.'}]};for(const c of review.criteria){c.strengths=['A concrete observed strength.'];c.limitations=[];c.descriptor_fit='A synthetic descriptor fit.';}
const attempt={id:'11111111-2222-4333-8444-555555555555',task_id:task.id,task,essay:fixture.essay,version:1,word_count:320,status:'submitted',created_at:'2026-11-12T00:00:00Z',updated_at:'2026-11-12T00:00:00Z',ai_status:'completed',assessment:structuredClone(review)};
const results=[];
for(const [name,engine,viewport]of [['desktop',chromium,{width:1366,height:900}],['mobile',webkit,{width:390,height:844}]]){
 const browser=await engine.launch();try{
 const ctx=await browser.newContext({viewport});
 const user={uid:auth.uid,email:auth.email,emailVerified:true,isAnonymous:false,providerData:[],stsTokenManager:{refreshToken:auth.refreshToken,accessToken:auth.idToken,expirationTime:Date.now()+Number(auth.expiresIn)*1000},apiKey:auth.apiKey,appName:'alua-web'};
 await ctx.addInitScript(({key,user})=>localStorage.setItem(key,JSON.stringify(user)),{key:`firebase:authUser:${auth.apiKey}:alua-web`,user});
 const page=await ctx.newPage();page.setDefaultTimeout(25000);const errors=[],inference=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/writing/assess',r=>{inference.push('blocked');return r.abort()});
 await page.route('**/api/alua/writing/**',r=>{const p=new URL(r.request().url()).pathname;return r.fulfill({json:p.endsWith('/tasks')?{items:[task]}:p.endsWith('/attempts')?{items:[attempt]}:attempt})});
 await page.goto(base+`/writing/attempts/${attempt.id}/results`);
 await expect(page.getByText('Estimated Task 2 Band',{exact:true})).toBeVisible();
 await expect(page.locator('main strong')).toHaveText('7.5');await expect(page.getByRole('heading',{name:'Task analysis',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Strengths',exact:true})).toHaveCount(4);
 await expect(page.locator('main ol')).toHaveCount(0);await expect(page.locator('main p').filter({hasText:/^→/})).toHaveCount(0);
 await page.getByRole('button',{name:'Review mistakes',exact:true}).click();
 await expect(page.getByText('No specific issues were identified. This does not guarantee an error-free essay.',{exact:true})).toBeVisible();
 await page.screenshot({path:`${dir}/${name}-empty.png`});
 // Read the prior schema directly: no targets/policy, three improvements, half-band criteria.
 delete attempt.assessment.quality_policy;delete attempt.assessment.task_understanding;
 for(const c of attempt.assessment.criteria){delete c.target;delete c.strengths;delete c.limitations;delete c.descriptor_fit;c.improvement='Develop the relevant argument.';c.band=7;}
 attempt.assessment.criteria[2].band=6.5;attempt.assessment.estimated_band=7;
 attempt.assessment.top_improvements=[1,2,3].map(n=>({action:`Develop relevant idea ${n}.`,quote}));
 await page.reload();await expect(page.locator('main strong')).toHaveText('7.0');await expect(page.locator('main ol li')).toHaveCount(3);await expect(page.getByText('6.5',{exact:true})).toBeVisible();
 expect(errors).toEqual([]);expect(inference).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`${dir}/${name}-legacy.png`});results.push({name,v3_empty:'PASS',legacy_v1_v2:'PASS',v4_review:'PASS',inference_requests:0});
 attempt.assessment.quality_policy='writing-accuracy-v2';for(const c of attempt.assessment.criteria)c.target=null;for(const i of attempt.assessment.top_improvements)i.target=null;await page.reload();await expect(page.locator('main strong')).toHaveText('7.0');await expect(page.getByRole('heading',{name:'Task analysis',exact:true})).toHaveCount(0);
 // Compact V4 renders a genuine agreement correction without invented translations.
 const tiny='People has cars.';attempt.essay=tiny;attempt.assessment={quality_policy:'writing-accuracy-v4',criteria:review.criteria.map(c=>({name:c.name,strength:'An intelligible statement.',limitation:null,descriptor_fit:'Synthetic browser fixture.',evidence:[{quote:tiny,start:0,end:tiny.length}],band:c.band,improvement:null,improvement_quote:null})),top_improvements:[],issues:[{quote:'People has',start:0,end:10,category:'grammar_error',why:'Plural people requires have.',better:'People have'}],uncertainty:'Synthetic render fixture; not a model assessment.',estimated_band:7.5,provider:'mock',model:'mock',assessed_at:'2026-11-13T00:00:00Z',essay_version:1};
 await page.reload();await expect(page.locator('main strong')).toHaveText('7.5');await page.getByRole('button',{name:'Review mistakes',exact:true}).click();await page.locator('button[data-kind]').first().click();await expect(page.getByRole('heading',{name:'Better version',exact:true})).toBeVisible();await expect(page.getByText('People have',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Russian translation of the corrected example',exact:true})).toHaveCount(0);attempt.essay=fixture.essay;
 // Reset mutable fixture for the next browser.
 attempt.assessment=structuredClone(review);attempt.assessment.estimated_band=7.5;attempt.assessment.top_improvements=[];attempt.assessment.issues=[];for(const c of attempt.assessment.criteria){c.improvement=null;c.target=null;}
 }finally{await browser.close();}
}
await writeFile(dir+'/results.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results));
